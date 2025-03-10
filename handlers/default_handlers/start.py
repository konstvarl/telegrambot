from telebot.states.sync import StateContext
from telebot.storage import StateMemoryStorage
from telebot.types import Message
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from datetime import datetime

from loader import bot
from states.search_info import States
from database.city_codes import city_codes

# state_storage = StateMemoryStorage()


@bot.message_handler(commands=['start'])
def bot_start(message: Message) -> None:
    bot.set_state(message.from_user.id, States.city, message.chat.id)
    bot.send_message(
        message.chat.id,
        f'Привет, {message.from_user.full_name}! Я бот который поможет найти '
        f'подходящие отели в нужном городе.')
    bot.send_message(message.from_user.id, 'В каком городе будем искать?')

@bot.message_handler(state=States.city)
def get_city(message: Message) -> None:
    city_name = message.text.upper()
    city_code = city_codes.get(city_name)
    if city_code:
        bot.send_message(message.from_user.id, f'{city_name} хороший '
                                               f'выбор')
        with (bot.retrieve_data(message.from_user.id, message.chat.id)
              as data):
            data['city'] = {'name': city_name, 'code': city_code}
        bot.send_message(message.from_user.id, 'Укажите дату заезда')
        bot.set_state(message.from_user.id, States.stay, message.chat.id)
    else:
        bot.send_message(message.from_user.id, f'Не знаю такого города '
                                               f'{city_name}\n'
                                               f'Введите другой город.')

@bot.message_handler(state=States.stay)
def date_stay(m):
    calendar, step = DetailedTelegramCalendar().build()
    bot.send_message(m.chat.id,
                     f"Выберите {LSTEP[step]}",
                     reply_markup=calendar)

@bot.callback_query_handler(
    func=DetailedTelegramCalendar.func(),
    calendar_id=0,
    locale='ru',
)
def cal(c):
    result, key, step = DetailedTelegramCalendar().process(c.data)
    if not result and key:
        bot.edit_message_text(f"Выберите {LSTEP[step]}",
                              c.message.chat.id,
                              c.message.message_id,
                              reply_markup=key)
    elif result:
        # with (bot.retrieve_data(message.from_user.id, message.chat.id)
        #       as data):
        #     data['date'] = {'check_in': result}
        bot.edit_message_text(f"Дата заезда {result}",
                              c.message.chat.id,
                              c.message.message_id)
