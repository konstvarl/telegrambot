from telebot.types import Message
from telegram_bot_calendar import DetailedTelegramCalendar
from datetime import date, timedelta

from loader import bot
from states.search_info import States
from database.city_codes import city_codes


LSTEP = {'y': 'год', 'm': 'месяц', 'd': 'день'}

class MyStyleCalendar(DetailedTelegramCalendar):
    prev_button = "⬅️"
    next_button = "➡️"
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.days_of_week['ru'] = \
            ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']
        self.months['ru'] = \
            ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн',
             'Июл', 'Авг', 'Сен', 'Окт', 'Нояб', 'Дек']


@bot.message_handler(commands=['start'])
def bot_start(message: Message) -> None:
    user_id = message.from_user.id
    bot.send_message(
        user_id,
        f'Привет, {message.from_user.full_name}! Я бот который поможет найти '
        f'подходящие отели в нужном городе.'
    )
    bot.send_message(
        user_id,
        'В каком городе будем искать?'
    )
    bot.set_state(
        user_id,
        States.city,
        message.chat.id
    )

@bot.message_handler(state=States.city)
def get_city(message: Message) -> None:
    city_name = message.text.strip().upper()
    city_code = city_codes.get(city_name)
    user_id = message.from_user.id
    chat_id = message.chat.id
    if city_code:
        bot.send_message(
            user_id,
            f'{city_name} хороший выбор'
        )
        bot.set_state(
            user_id,
            States.check_in,
            chat_id
        )
        with bot.retrieve_data(user_id, chat_id) as data:
            data['city'] = {'name': city_name, 'code': city_code}
        bot.send_message(
            user_id,
            'Выберите дату заезда...'
        )
        calendar, step = MyStyleCalendar(
            calendar_id=0,
            locale='ru',
            min_date=date.today()
        ).build()
        bot.send_message(
            chat_id,
            f"Выберите {LSTEP[step]}",
            reply_markup=calendar
        )
    else:
        bot.send_message(
            user_id,
            f'Не знаю такого города {city_name}\n'
            f'Введите другой город.'
        )

@bot.callback_query_handler(
    func=lambda call: MyStyleCalendar.func()(call),
    state=[States.check_in, States.check_out],
)
def cal(c):
    if not c.message:
        return
    chat_id = c.message.chat.id
    user_id = c.from_user.id
    message_id = c.message.message_id
    user_state = bot.get_state(user_id, chat_id)
    user_state_check_out = States.check_out.name
    if user_state == user_state_check_out:
        with bot.retrieve_data(user_id, chat_id) as data:
            date_min = data['date']['check_in'] + timedelta(days=1)
    else:
        date_min = date.today()
    result, key, step = MyStyleCalendar(
        calendar_id=0,
        locale='ru',
        min_date=date_min
    ).process(c.data)
    if not result and key:
        bot.edit_message_text(
            f'Выберите {LSTEP[step]}',
            chat_id,
            message_id,
            reply_markup=key
        )
        return
    elif result:
        with bot.retrieve_data(user_id, chat_id) as data:
            if user_state == user_state_check_out:
                data['date'].update({'check_out': result})
                bot.edit_message_text(
                    f'Выбрана дата выезда {result}\n',
                    chat_id,
                    message_id)
                bot.send_message(
                    chat_id,
                    f'Сохраненные данные:\n'
                    f'{data['city']['name']}\n'
                    f'{data['city']['code']}\n'
                    f'{data['date']['check_in']}\n'
                    f'{data['date']['check_out']}'
                )
                return
            else:
                data['date'] = {'check_in': result}
                date_min = result + timedelta(days=1)
                bot.edit_message_text(
                    f'Выбрана дата заезда {data['date']['check_in']}\n'
                    f'Теперь выберите дату выезда...',
                    chat_id,
                    message_id
                )
                bot.set_state(user_id, States.check_out, chat_id)
            calendar_out, step_new = MyStyleCalendar(
                calendar_id=0,
                locale='ru',
                min_date=date_min
            ).build()
            bot.send_message(
                chat_id,
                f"Выберите {LSTEP[step_new]}",
                reply_markup=calendar_out
            )
