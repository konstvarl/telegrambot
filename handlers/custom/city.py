from datetime import date

from amadeus import ClientError
from countryinfo import CountryInfo
from pycountry import currencies
from requests import Timeout, ReadTimeout, RequestException
from telebot.types import Message, CallbackQuery

from api.request_amadeus import get_cities, logger
from handlers.custom.calendar import start_calendar
from keyboards.inline.city_select import gen_markup_select_city
from loader import bot
from states.user_states import States
from utils.parsing import safe_parse_callback_index
from utils.telegram_safe import safe_edit_message
from utils.user import get_user_and_chat_ids
from utils.validation import require_valid_session


@bot.message_handler(state=States.city_search)
def get_city(message: Message) -> None:
    user_id, chat_id = get_user_and_chat_ids(message)
    template_find_city = message.text
    with bot.retrieve_data(user_id, chat_id) as data:
        data['response'] = {**data.get('response', {})}
        data['request']['template_find_city'] = template_find_city

    try:
        found_cities = get_cities(template_find_city)
    except (ClientError, ConnectionError, Timeout, ReadTimeout) as error:
        logger.warning(f'Ошибка при обращении к Amadeus API: {error}, '
                       f'запрос пользователя: {template_find_city}')
        bot.send_message(
            chat_id,
            '⚠️ Проблема с подключением к сервису Amadeus!\n'
            'Повторите ввод города позже'
        )
        return

    except RequestException as error:
        logger.warning(f'Сетевая ошибка при обращении к Amadeus API: {error}')
        bot.send_message(
            chat_id,
            '🌐 Не удалось связаться с сервером Amadeus.\n'
            'Проверьте соединение с интернетом или попробуйте позже'
        )
        return

    except Exception as error:
        logger.exception(f'Ошибка при поиске города: {error}, '
                         f'запрос пользователя: {template_find_city}')
        bot.send_message(
            chat_id,
            '😞 Что-то пошло не так! Повторите ввод города позже'
        )
        return

    cities = [
        city_data for city_data in found_cities.get('data', [])
        if city_data.get('iataCode', None)
    ]
    if cities:
        with bot.retrieve_data(user_id, chat_id) as data:
            data['response']['cities'] = cities
            session_id = data['session_id']

        bot.set_state(user_id, States.city_confirm, chat_id)
        bot.send_message(
            chat_id,
            'Выберите город из следующих найденных:',
            reply_markup=gen_markup_select_city(cities[:50], session_id)
        )
    else:
        bot.send_message(
            chat_id,
            f'Не могу найти город по Вашему запросу: {template_find_city}\n'
            f'Введите другой город.'
        )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('selected_city'),
    state=States.city_confirm
)
@require_valid_session()
def city_select(callback_query: CallbackQuery) -> None:
    index_city = safe_parse_callback_index(callback_query, 2, transform=int)
    if index_city is None:
        return

    user_id, chat_id = get_user_and_chat_ids(callback_query)

    with bot.retrieve_data(user_id, chat_id) as data:
        response = data['response']
        if not (0 <= index_city < len(response['cities'])):
            bot.answer_callback_query(
                callback_query.id,
                f'Некорректный индекс города: {index_city}!'
            )
            return
        city = response['cities'][index_city]

    bot.answer_callback_query(callback_query.id)
    country = CountryInfo(country_name=city['address'].get('countryCode'))
    country_name = country.name().title()
    currency_code = country.currencies()[0]
    currency = currencies.get(alpha_3=currency_code)
    safe_edit_message(
        f'🌇 Город {city['name']}, {country_name}, хороший выбор.',
        user_id,
        callback_query.message.message_id
    )
    with bot.retrieve_data(user_id, chat_id) as data:
        return_to = data.pop('return_to', None)

    bot.set_state(user_id, States.check_in, chat_id)
    if not return_to:
        date_message = bot.send_message(
            user_id,
            'Выберите дату заезда...'
        )

    with bot.retrieve_data(user_id, chat_id) as data:
        data['request'].update({
            'city': city,
            'country': country_name,
            'currency': {
                'name': currency.name,
                'code': currency_code
            },
        })
        try:
            data['date_message_id'] = date_message.message_id
        except NameError:
            data['date_message_id'] = None

    if not return_to:
        start_calendar(user_id, chat_id, date.today())
