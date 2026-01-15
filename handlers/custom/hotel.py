import threading
from datetime import date
from typing import Union

from amadeus import ClientError
from requests import Timeout, ReadTimeout, RequestException
from telebot.types import CallbackQuery, Message, ReplyKeyboardRemove

from api.request_amadeus import (get_hotel_offer, get_hotels_by_city,
                                 get_hotel_offers_search, get_hotel_sentiments, logger)
from api.search_hotel_images_url import get_urls_photos_hotel
from config_data.config import SORT_COMMANDS, PHOTOS, COMMANDS_TO_REPLY_KEYBOARD
from database.data_storage import add_request_to_history, Hotel
from handlers.custom.calendar import start_calendar
from keyboards.inline.pagination import gen_markup_pagin_hotels
from keyboards.inline.sorting_command import gen_markup_command_sorting
from keyboards.reply.controls import gen_reply_controls_for_display
from loader import bot
from states.user_states import States
from utils.hotel import format_hotel_text, sorting_hotels, sorting_order, media_lock
from utils.hotel_photo import send_hotel_photo, send_message_no_photo
from utils.parsing import safe_parse_callback_index
from utils.telegram_safe import safe_delete_message, safe_edit_message, safe_edit_media, safe_remove_markup
from utils.user import get_user_and_chat_ids
from utils.validation import require_valid_session


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('hotel_page'),
    state=States.display_hotels
)
@require_valid_session()
def hotel_change(callback_query: CallbackQuery) -> None:
    user_id, chat_id = get_user_and_chat_ids(callback_query)
    step = safe_parse_callback_index(callback_query, 2, transform=int)
    bot.answer_callback_query(callback_query.id)

    with bot.retrieve_data(user_id, chat_id) as data:
        num_hotels = data['num_hotels']
        num_hotel = data['num_hotel']
        next_hotel = (num_hotel + step) % num_hotels
        data.update({
            'num_hotel': next_hotel,
            'message_hotel_id': callback_query.message.message_id,
        })

    try:
        with media_lock(bot, user_id, chat_id, 'loading_photos'):
            display_hotels(callback_query)
    except RuntimeError:
        pass


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('hotel_offer'),
    state=States.display_hotels
)
@require_valid_session()
def accept_hotel_offer(callback_query: CallbackQuery):
    user_id, chat_id = get_user_and_chat_ids(callback_query)

    with bot.retrieve_data(user_id, chat_id) as data:
        num_hotel = data['num_hotel']
        hotel_id = data['response']['hotels_keys_with_offer'][num_hotel]
        hotel = data['response']['hotels_with_offer'][hotel_id]
        hotel_offer_id = hotel['offer']['id']
        message_hotel_id = data['message_hotel_id']
        message_photo_id = data.get('message_photo_id')

    try:
        response = get_hotel_offer(hotel_offer_id)
        if response['data']['available']:
            bot.answer_callback_query(callback_query.id)
            safe_delete_message(chat_id, [message_photo_id])
            bot.delete_state(user_id, chat_id)
            safe_remove_markup(chat_id, message_hotel_id)
            restart_cmds = ', '.join(f'/{cmd}' for cmd in SORT_COMMANDS)
            bot.send_message(
                chat_id,
                f'Вы выбрали предложение отеля {hotel["name"]}.\n'
                f'Бронирование номера в данной версии бота не реализовано.\n'
                f'На этом работа бота завершена.\n'
                f'Для повторного запуска бота используйте одну из команд:\n'
                f'/start, {restart_cmds}',
                reply_markup=ReplyKeyboardRemove()
            )
    except ClientError:
        bot.answer_callback_query(
            callback_query.id, 'Это предложение отеля уже устарело '
                               'и более недоступно!'
        )


@bot.message_handler(state=States.search_hotels)
def search_hotels(message: Union[Message, CallbackQuery]) -> None:
    """
    Основная логика поиска отелей:
    1. Получает список отелей в городе.
    2. Фильтрует по наличию доступных предложений.
    3. Получает отзывы.
    4. Сортирует и выводит результат.
    """
    user_id, chat_id = get_user_and_chat_ids(message)

    with bot.retrieve_data(user_id, chat_id) as data:
        request = data['request']
        city = request['city']
        city_name = city['name']
        city_iata_code = city['iataCode']
        check_in_date = str(request['date']['check_in'])
        check_out_date = str(request['date']['check_out'])
        price_range = request['range_prices']
        currency_code = request['currency']['code']
        search_radius = request['radius']
        command = request['command']

    num_hotel = 0
    message_info_1 = (f'Подождите, получаю информацию\n'
                      f'о отелях в городе {city_name}...')
    loading_message = bot.send_message(
        chat_id,
        message_info_1
    )
    loading_message_id = loading_message.message_id

    try:
        # 1. Получаем список отелей по городу
        hotels_by_city = get_hotels_by_city(
            city_code=city_iata_code,
            radius=search_radius
        )
        if not hotels_by_city:
            safe_edit_message(
                f'Отели в городе {city_name} не найдены.'
                f'Измените параметры поиска',
                chat_id,
                loading_message_id,
                markup=gen_reply_controls_for_display()
            )
            return
        message_info_2 = (f'Отели в городе {city_name} найдены.\n'
                          f'Подождите, получаю предложения от отелей...')
        loading_message_id = safe_edit_message(
            message_info_2,
            chat_id,
            loading_message_id
        )
        # 2. Получаем предложения и фильтруем только доступные
        hotel_ids = [hotel['hotelId'] for hotel in hotels_by_city['data']]
        hotel_offers = get_hotel_offers_search(
            hotel_ids=hotel_ids,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            price_range=price_range,
            currency=currency_code
        )

        hotels_dict = {hotel['hotelId']: hotel for hotel in hotels_by_city['data']}
        hotels_with_offer = {}
        for offer in hotel_offers.get('data', []):
            if not offer.get('available'):
                continue
            hotel_id = offer['hotel']['hotelId']
            if hotel_id in hotels_dict:
                hotel = hotels_dict[hotel_id]
                hotel['offer'] = offer['offers'][0]
                hotels_with_offer[hotel_id] = hotel
        if not hotels_with_offer:
            safe_edit_message(
                f'В городе {city_name} нет доступных отелей на выбранные '
                f'даты в указанном ценовом диапазоне',
                chat_id,
                loading_message_id,
                markup=gen_reply_controls_for_display()
            )
            bot.set_state(user_id, States.display_hotels, chat_id)
            return
        message_info_3 = (f'Отели в городе {city_name} найдены.\n'
                          f'Отели с предложениями найдены.\n'
                          f'Подождите, получаю отзывы о отелях...')
        loading_message_id = safe_edit_message(
            message_info_3,
            chat_id,
            loading_message_id
        )
        # 3. Получаем отзывы
        hotels_keys_with_offer = list(hotels_with_offer.keys())
        hotel_sentiments = get_hotel_sentiments(hotels_keys_with_offer)
    except (ClientError, ConnectionError, Timeout, ReadTimeout) as error:
        logger.warning(f'Ошибка при обращении к Amadeus API: {error}, '
                       f'запрос пользователя: {request}')
        safe_edit_message(
            f'⚠️ Проблема с подключением к сервису Amadeus!\n'
            f'Повторите поиск позже, нажав кнопку '
            f'{COMMANDS_TO_REPLY_KEYBOARD["Repeat search"]}',
            chat_id,
            loading_message_id,
            markup=gen_reply_controls_for_display()
        )
        return

    except RequestException as error:
        logger.warning(f'Сетевая ошибка при обращении к Amadeus API: {error}')
        safe_edit_message(
            '🌐 Не удалось связаться с сервером Amadeus.\n'
            'Проверьте соединение с интернетом или попробуйте позже',
            chat_id,
            loading_message_id,
            markup=gen_reply_controls_for_display()
        )
        return

    except Exception as error:
        logger.exception(f'Ошибка при поиске отелей: {error}, '
                         f'запрос пользователя: {request}')
        safe_edit_message(
            f'😞 Что-то пошло не так! Повторите поиск позже, '
            f'нажав кнопку {COMMANDS_TO_REPLY_KEYBOARD["Repeat search"]}',
            chat_id,
            loading_message_id,
            markup=gen_reply_controls_for_display()
        )
        return

    for sentiment in hotel_sentiments.get('data', []):
        hotels_with_offer[sentiment['hotelId']]['sentiments'] = sentiment
    message_info_4 = (f'Отели в городе {city_name} найдены.\n'
                      f'Отели с предложениями найдены.\n'
                      f'Отзывы о отелях получены.\n'
                      f'Сортирую отели...')
    loading_message_id = safe_edit_message(
        message_info_4,
        chat_id,
        loading_message_id
    )

    sorting_hotels(hotels_keys_with_offer, hotels_with_offer, command)

    with bot.retrieve_data(user_id, chat_id) as data:
        response = data['response']
        response.update({
            'hotels_by_city': hotels_by_city,
            'hotels_with_offer': hotels_with_offer,
            'hotels_keys_with_offer': hotels_keys_with_offer,
        })
        data.update({
            'num_hotel': num_hotel,
            'num_hotels': len(hotels_with_offer),
        })
        request_data = data['request']
        response_data = response

    add_request_to_history(
        user_id,
        message.from_user.full_name,
        request_data,
        response_data['hotels_with_offer']
    )

    bot.set_state(user_id, States.display_hotels, chat_id)
    safe_edit_message(
        f'В городе {city_name} найдены следующие отели, '
        f'{sorting_order(command)}:',
        chat_id,
        loading_message_id,
        markup=gen_reply_controls_for_display()
    )
    display_hotels(message)


@bot.message_handler(
    func=lambda m: m.text in tuple(COMMANDS_TO_REPLY_KEYBOARD.values())
)
def display_controls_handler(message: Message) -> None:
    user_id, chat_id = get_user_and_chat_ids(message)
    txt = message.text

    with bot.retrieve_data(user_id, chat_id) as data:
        data['return_to'] = True

    if txt == COMMANDS_TO_REPLY_KEYBOARD['Choose city']:
        bot.set_state(user_id, States.city_search, chat_id)
        bot.send_message(
            chat_id,
            'В каком городе будем искать?\n'
            'Введите название на английском.',
        )
        return

    if txt == COMMANDS_TO_REPLY_KEYBOARD['Choose dates']:
        bot.set_state(user_id, States.check_in, chat_id)
        date_message = bot.send_message(chat_id, 'Выберите дату заезда...')
        with bot.retrieve_data(user_id, chat_id) as data:
            data['date_message_id'] = date_message.message_id

        start_calendar(user_id, chat_id, date.today())
        return

    if txt == COMMANDS_TO_REPLY_KEYBOARD['Set price range']:
        bot.set_state(user_id, States.price_range, chat_id)
        with bot.retrieve_data(user_id, chat_id) as data:
            request = data['request']
            request_country = request['country']
            currency_name = request['currency']['name']
        bot.send_message(
            chat_id,
            f'Введите диапазон цен в валюте страны {request_country}\n'
            f'в формате [min]-[max].\n'
            f'Валюта: {currency_name}\n'
            f'Например: 200-300, -300 или 100\n'
        )
        return

    if txt == COMMANDS_TO_REPLY_KEYBOARD['Set search radius']:
        bot.set_state(user_id, States.radius, chat_id)
        bot.send_message(
            chat_id,
            f'Введите радиус, т.е. в пределах скольки километров от центра города '
            f'будем искать отели? (Радиус должен быть целым числом не менее 1 '
            f'и не более 300)'
        )
        return

    if txt == COMMANDS_TO_REPLY_KEYBOARD['Choose sorting criteria']:
        with bot.retrieve_data(user_id, chat_id) as data:
            session_id = data['session_id']
        bot.set_state(user_id, States.sorting_criteria, chat_id)
        bot.send_message(
            chat_id,
            'Выберите по какому критерию будем сортировать отели?',
            reply_markup=gen_markup_command_sorting(session_id)
        )
        return

    if txt == COMMANDS_TO_REPLY_KEYBOARD['Repeat search']:
        with bot.retrieve_data(user_id, chat_id) as data:
            message_hotel_id = data.get('message_hotel_id')
            message_photo_id = data.get('message_photo_id')
            data['message_hotel_id'] = None
            data['message_photo_id'] = None

        safe_remove_markup(chat_id, message_hotel_id)
        safe_remove_markup(chat_id, message_photo_id)
        bot.set_state(user_id, States.search_hotels, chat_id)
        search_hotels(message)
        return

    if txt == COMMANDS_TO_REPLY_KEYBOARD['Complete']:
        with bot.retrieve_data(user_id, chat_id) as data:
            message_hotel_id = data.get('message_hotel_id')
            message_photo_id = data.get('message_photo_id')

        safe_remove_markup(chat_id, message_hotel_id)
        safe_remove_markup(chat_id, message_photo_id)
        bot.delete_state(user_id, chat_id)
        with bot.retrieve_data(user_id, chat_id) as data:
            data.clear()
        bot.send_message(
            user_id, 'OK! Работа завершена', reply_markup=ReplyKeyboardRemove()
        )
        return


active_photo_loads: dict[int, dict] = {}
active_photo_loads_lock = threading.Lock()


@bot.message_handler(state=States.display_hotels)
def display_hotels(message: Message | CallbackQuery) -> None:
    """
    Отображает информацию по текущему отелю и его фотографии.
    Если фотографии ещё не загружены - скачивает их и сохраняет в базу.
    1. Берёт текущий отель по индексу из состояния.
    2. Отправляет сообщение с информацией об отеле и кнопками пагинации.
    3. Отправляет фото или сообщение, что фото нет.
    """
    user_id, chat_id = get_user_and_chat_ids(message)

    with bot.retrieve_data(user_id, chat_id) as data:
        session_id = data['session_id']
        # 1. Получаем текущий отель
        num_hotel = data['num_hotel']
        num_hotels = data['num_hotels']
        hotel_id = data['response']['hotels_keys_with_offer'][num_hotel]
        hotel = data['response']['hotels_with_offer'][hotel_id]
        request_record = data['request_record']
        message_hotel_id = data.get('message_hotel_id')
        message_photo_id = data.get('message_photo_id')
    # 2. Отправляем сообщение с описанием отеля
    message_hotel_id = safe_edit_message(
        format_hotel_text(hotel, num_hotel, num_hotels),
        chat_id,
        message_hotel_id,
        markup=gen_markup_pagin_hotels(
            hotel['name'],
            hotel['offer']['id'],
            session_id,
            True if num_hotels > 1 else False
        )
    )
    # 3. Готовим фото
    photos_urls = hotel.get('photos_urls')
    if photos_urls:
        send_hotel_photo(user_id, chat_id, hotel)
        return

    if user_id in active_photo_loads:
        active_photo_loads[user_id]['cancel'] = True

    cancel_flag = {'cancel': False}
    with active_photo_loads_lock:
        active_photo_loads[user_id] = cancel_flag

    message_photo_id = safe_edit_media(
        PHOTOS['searching'],
        f'Ищу фотографии отеля {hotel["name"]}...\n'
        f'Не переключайтесь!',
        chat_id,
        message_photo_id
    )

    with bot.retrieve_data(user_id, chat_id) as data:
        data.update({
            'message_hotel_id': message_hotel_id,
            'message_photo_id': message_photo_id
        })

    thread = threading.Thread(
        target=_load_photos_background,
        args=(user_id, chat_id, hotel, hotel_id, request_record, cancel_flag),
        daemon=True
    )
    thread.start()


def _load_photos_background(user_id: int, chat_id: int,
                            hotel: dict, hotel_id: str,
                            request_record, cancel_flag: dict) -> None:
    """Фоновая загрузка фото с возможностью отмены."""
    hotel_name = hotel['name']
    if cancel_flag.get('cancel'):
        return
    try:
        photos = get_urls_photos_hotel(
            hotel_name,
            hotel['address']['cityName']
        )

        if cancel_flag.get('cancel'):
            return

        if photos:
            hotel['photos'] = photos
            hotel_record = Hotel.get(
                (Hotel.hotel_id == hotel_id) &
                (Hotel.request == request_record)
            )
            if hotel_record.photos == Hotel.EMPTY_PHOTOS:
                hotel_record.set_photos(photos)

            with bot.retrieve_data(user_id, chat_id) as data:
                hotel = data['response']['hotels_with_offer'][hotel_id]
                hotel.update({
                    'photos': photos,
                    'num_photo': 0,
                    'num_photos': len(photos or [])
                })

            if cancel_flag.get('cancel'):
                return

            send_hotel_photo(user_id, chat_id, hotel)
        else:
            send_message_no_photo(user_id, chat_id, hotel_name)

    except Exception as error:
        logger.exception(f'Ошибка при загрузке фото отеля {hotel_name}: {error}')

    finally:
        with active_photo_loads_lock:
            current_flag = active_photo_loads.get(user_id)
            if current_flag is cancel_flag:
                active_photo_loads.pop(user_id, None)
