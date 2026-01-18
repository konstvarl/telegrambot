from datetime import timedelta

from telebot.types import Message

from config_data.config import CALENDAR_SERVICE_MESSAGE
from handlers.custom.calendar import start_calendar
from loader import bot
from states.user_states import States
from utils.user import get_user_and_chat_ids


@bot.message_handler(
    func=lambda m: m.text == CALENDAR_SERVICE_MESSAGE,
    state=States.check_in
)
def date_check_in(message: Message) -> None:
    user_id, chat_id = get_user_and_chat_ids(message)

    with bot.retrieve_data(user_id, chat_id) as data:
        result = data['calendar_date']['result']
        request = data['request']
        request['date'] = {**request.get('date', {}), 'check_in': result}
        date_message_id = data['date_message_id']

    bot.edit_message_text(
        f'📅 Выбрана дата заезда {result.strftime("%d.%m.%Y")}',
        chat_id,
        date_message_id
    )
    bot.set_state(user_id, States.check_out, chat_id)
    date_message = bot.send_message(
        chat_id, 'Теперь, выберите дату отъезда...'
    )
    with bot.retrieve_data(user_id, chat_id) as data:
        data['date_message_id'] = date_message.message_id

    start_calendar(user_id, chat_id, date_min=result + timedelta(days=1))


@bot.message_handler(
    func=lambda m: m.text == CALENDAR_SERVICE_MESSAGE,
    state=States.check_out
)
def date_check_out(message: Message) -> None:
    user_id, chat_id = get_user_and_chat_ids(message)

    with bot.retrieve_data(user_id, chat_id) as data:
        result = data['calendar_date']['result']
        request = data['request']
        request['date'] = {**request.get('date', {}), 'check_out': result}
        date_message_id = data['date_message_id']
        request_country = request['country']
        currency_name = request['currency']['name']
        return_to = data.pop('return_to', None)

    bot.edit_message_text(
        f'📅 Выбрана дата отъезда {result.strftime("%d.%m.%Y")}',
        chat_id,
        date_message_id
    )

    if return_to:
        bot.set_state(user_id, States.search_hotels_stop, chat_id)
        return

    bot.set_state(user_id, States.price_range, chat_id)
    bot.send_message(
        chat_id,
        f'Введите диапазон цен в валюте страны {request_country}\n'
        f'в формате [min]-[max].\n'
        f'Валюта: {currency_name}\n'
        f'Например: 200-300, -300 или 100\n'
    )
