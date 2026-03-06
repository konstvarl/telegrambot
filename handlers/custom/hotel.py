import threading
from datetime import date
from typing import Union

from amadeus import ClientError
from requests import Timeout, ReadTimeout, RequestException
from telebot.types import CallbackQuery, Message, ReplyKeyboardRemove

from api.request_amadeus import (get_hotel_offer, get_hotels_by_city,
                                 get_hotel_offers_search, get_hotel_sentiments,
                                 logger)
from api.search_hotel_images_url import get_urls_photos_hotel
from config_data.config import (SORT_COMMANDS, PHOTOS,
                                COMMANDS_TO_REPLY_KEYBOARD)
from database.data_storage import add_request_to_history, Hotel
from handlers.custom.calendar import start_calendar
from keyboards.inline.pagination import gen_markup_pagin_hotels
from keyboards.inline.sorting_command import gen_markup_command_sorting
from keyboards.reply.controls import gen_reply_controls_for_display
from loader import bot
from states.user_states import States
from utils.exceptions import (ExternalServiceUnavailable, HotelNotFound,
                              OffersNotFound)
from utils.hotel import (format_hotel_text, sorting_hotels, sorting_order,
                         media_lock)
from utils.hotel_photo import send_hotel_photo, send_message_no_photo
from utils.parsing import safe_parse_callback_index
from utils.telegram_safe import (safe_delete_message, safe_edit_message,
                                 safe_edit_media, safe_remove_markup,
                                 fail_search)
from utils.user import get_user_and_chat_ids
from utils.validation import require_valid_session


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('hotel_page'),
    state=States.search_hotels_stop
)
@require_valid_session()
def hotel_change(callback_query: CallbackQuery) -> None:
    """
    Обработчик для разбивки отелей на страницы.
    Изменяет текущий отель и отправляет информацию о новом отеле
    или фотографии. Если фотографий нет, отправляет сообщение об этом.

    :param callback_query: CallbackQuery
    :return: None
    """
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

    bot.set_state(user_id, States.display_hotels, chat_id)
    try:
        with media_lock(bot, user_id, chat_id, 'loading_photos'):
            display_hotels(callback_query)
    except RuntimeError:
        pass


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('hotel_offer'),
    state=States.search_hotels_stop
)
@require_valid_session()
def accept_hotel_offer(callback_query: CallbackQuery):
    """
    Обработчик для подтверждения предложения отеля.
    Проверяет доступность предложения, удаляет сообщение с фото
    и отправляет ответ.

    :param callback_query: CallbackQuery
    :return: None
    """
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


def search_hotels_core(
        request: dict,
        *,
        on_progress: callable = None,
) -> dict:
    """
    Выполняет основную логику поиска отелей, обращаясь к API.

    :param request: Словарь с параметрами поиска.
    :param on_progress: Callback-функция для отслеживания прогресса.
    :return: Словарь с результатами поиска.
    :raises ExternalServiceUnavailable: Если внешний сервис недоступен.
    :raises HotelNotFound: Если отели по заданным критериям не найдены.
    :raises OffersNotFound: Если от найденных отелей нет предложений.
    :raises SentimentsUnavailable: Если не удалось загрузить отзывы.
    """
    def progress(text: str) -> None:
        if on_progress:
            on_progress(text)

    # --- 1. Извлечение параметров из запроса ---
    city = request['city']
    city_name = city['name']
    city_iata_code = city['iataCode']
    check_in_date = str(request['date']['check_in'])
    check_out_date = str(request['date']['check_out'])
    price_range = request['range_prices']
    currency_code = request['currency']['code']
    search_radius = request['radius']
    command = request['command']

    # --- 2. Получение списка отелей ---
    progress(f'Подождите, получаю информацию\n'
             f'о отелях в городе {city_name}...')
    try:
        hotels_by_city = get_hotels_by_city(
            city_code=city_iata_code,
            radius=search_radius
        )
    except (ClientError, ConnectionError, Timeout, ReadTimeout) as error:
        raise ExternalServiceUnavailable('get_hotels_by_city') from error

    if not hotels_by_city.get('data'):
        raise HotelNotFound()

    # --- 3. Получение предложений (offers) ---
    progress(f'Отели в городе {city_name} найдены.\n'
             f'Подождите, получаю предложения от отелей...')
    hotel_ids = [hotel['hotelId'] for hotel in hotels_by_city['data']]
    try:
        hotel_offers = get_hotel_offers_search(
            hotel_ids=hotel_ids,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            price_range=price_range,
            currency=currency_code
        )
    except (ClientError, ConnectionError, Timeout, ReadTimeout) as error:
        raise ExternalServiceUnavailable('get_hotel_offers_search') from error

    # --- 4. Фильтрация отелей с доступными предложениями ---
    hotels_dict = {hotel['hotelId']: hotel for hotel in hotels_by_city['data']}
    hotels_with_offer = {}
    for offer in hotel_offers.get('data', []):
        if offer.get('available'):
            hotel_id = offer['hotel']['hotelId']
            if hotel_id in hotels_dict:
                hotel = hotels_dict[hotel_id]
                hotel['offer'] = offer['offers'][0]
                hotels_with_offer[hotel_id] = hotel

    if not hotels_with_offer:
        raise OffersNotFound()

    # --- 5. Получение отзывов (sentiments) ---
    progress(f'Отели в городе {city_name} найдены.\n'
             f'Отели с предложениями найдены.\n'
             f'Подождите, получаю отзывы о отелях...')
    hotels_keys_with_offer = list(hotels_with_offer.keys())
    hotel_sentiments = get_hotel_sentiments(hotels_keys_with_offer)
    for sentiment in hotel_sentiments.get('data', []):
        hotels_with_offer[sentiment['hotelId']]['sentiments'] = sentiment

    # --- 6. Сортировка ---
    progress(f'Отели в городе {city_name} найдены.\n'
             f'Отели с предложениями найдены.\n'
             f'Отзывы о отелях получены.\n'
             f'Сортирую отели...')
    sorting_hotels(hotels_keys_with_offer, hotels_with_offer, command)

    # --- 7. Возврат результата ---
    return {
        'hotels_by_city': hotels_by_city,
        'hotels_with_offer': hotels_with_offer,
        'hotels_keys_with_offer': hotels_keys_with_offer,
    }


def do_search_hotels(message: Union[Message, CallbackQuery]) -> None:
    """
    Управляет процессом поиска отелей.

    Не выполняет запросы к API напрямую, а координирует весь процесс:
    1. Вызывает search_hotels_core для фактического поиска данных.
    2. Отображает пользователю сообщения о прогрессе поиска.
    3. Перехватывает и обрабатывает все возможные исключения,
        информируя пользователя.
    4. В случае успеха, сохраняет результаты в базу данных.
    5. Обновляет состояние (FSM) пользователя.
    6. Передает управление функции display_hotels для показа первого
       найденного отеля.
    """
    user_id, chat_id = get_user_and_chat_ids(message)

    with bot.retrieve_data(user_id, chat_id) as data:
        request = data['request']
        city_name = request['city']['name']
        command = request['command']

    # --- 1. Подготовка к поиску ---
    msg_id = None

    def on_progress(text: str):
        """
        Callback-функция для отображения прогресса.
        Будет вызываться из search_hotels_core для обновления
        статуса поиска в чате с пользователем.
        """
        nonlocal msg_id
        msg_id = safe_edit_message(text, chat_id, msg_id)

    # --- 2. Основной блок: вызов ядра поиска и обработка всех исключений ---
    try:
        search_result = search_hotels_core(
            request,
            on_progress=on_progress
        )
    except HotelNotFound:
        fail_search(
            user_id, chat_id, msg_id,
            f'Отели в городе {city_name} не найдены.\n'
            f'Измените параметры поиска.',
            gen_reply_controls_for_display()
        )
        return
    except OffersNotFound:
        fail_search(
            user_id, chat_id, msg_id,
            f'В городе {city_name} нет доступных отелей на выбранные '
            f'даты или в указанном ценовом диапазоне.',
            gen_reply_controls_for_display()
        )
        return
    except (ExternalServiceUnavailable, RequestException) as error:
        logger.warning(f'Ошибка при поиске отелей: {error}, запрос: {request}')
        fail_search(
            user_id, chat_id, msg_id,
            f'⚠️ Проблема с подключением к сервису Amadeus!\n'
            f'Повторите поиск позже, нажав кнопку '
            f'{COMMANDS_TO_REPLY_KEYBOARD["Repeat search"]}.',
            gen_reply_controls_for_display()
        )
        return
    except Exception as error:
        logger.exception(f'Непредвиденная ошибка при поиске отелей: {error}, '
                         f'запрос: {request}')
        fail_search(
            user_id, chat_id, msg_id,
            f'😞 Что-то пошло не так! Повторите поиск позже, '
            f'нажав кнопку {COMMANDS_TO_REPLY_KEYBOARD["Repeat search"]}.',
            gen_reply_controls_for_display()
        )
        return

    # --- 3. Сохранение успешного результата в историю (БД) ---
    request_record = add_request_to_history(
        user_id,
        message.from_user.full_name,
        request,
        search_result['hotels_with_offer']
    )

    # --- 4. Обновление состояния пользователя (FSM) ---
    with bot.retrieve_data(user_id, chat_id) as data:
        data['response'].update(search_result)
        data.update({
            'num_hotel': 0,
            'num_hotels': len(search_result['hotels_with_offer']),
            'request_record': request_record,
        })

    # --- 5. Переход к отображению результатов ---
    bot.set_state(user_id, States.display_hotels, chat_id)
    safe_delete_message(chat_id, msg_id)
    bot.send_message(
        chat_id,
        f'В городе {city_name} найдены следующие отели, '
        f'{sorting_order(command)}:',
        reply_markup=gen_reply_controls_for_display()
    )
    display_hotels(message)


@bot.message_handler(state=States.search_hotels)
def search_hotels_handler(message: Union[Message, CallbackQuery]) -> None:
    do_search_hotels(message)


@bot.message_handler(
    func=lambda m: m.text in tuple(COMMANDS_TO_REPLY_KEYBOARD.values()),
    state=States.search_hotels_stop
)
def display_controls_handler(message: Message) -> None:
    """
    Обрабатывает управляющие сообщения от пользователя.

    :param message: Управляющее сообщение от пользователя.
    :return: None.
    """
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
        do_search_hotels(message)

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

    bot.set_state(user_id, States.search_hotels_stop, chat_id)
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
