from datetime import date

from telebot.types import CallbackQuery
from telegram_bot_calendar import DetailedTelegramCalendar

from loader import bot
from utils.telegram_safe import safe_delete_message
from utils.user import get_user_and_chat_ids, send_calendar_done
from utils.validation import require_valid_session

LSTEP = {'y': 'год', 'm': 'месяц', 'd': 'день'}


class MyStyleCalendar(DetailedTelegramCalendar):
    prev_button = "⬅️"
    next_button = "➡️"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.days_of_week['ru'] = [
            'ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС'
        ]
        self.months['ru'] = [
            'Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн',
            'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'
        ]


def start_calendar(
        user_id: int,
        chat_id: int,
        date_min: date | None = None,
        date_max: date | None = None,
) -> None:
    """
    Создает и показывает inline-календарь для выбора даты.

    :param user_id: Идентификатор пользователя.
    :param chat_id: Идентификатор чата.
    :param date_min: Минимальная дата календаря.
    :param date_max: Максимальная дата календаря.
    :return: None
    """
    with bot.retrieve_data(user_id, chat_id) as data:
        session_id = data['session_id']
        data['calendar_date'] = {
            'min': date_min,
            'max': date_max
        }

    calendar, step = MyStyleCalendar(
        calendar_id=session_id,
        locale='ru',
        min_date=date_min,
        max_date=date_max
    ).build()

    bot.send_message(
        chat_id,
        f"Выберите {LSTEP[step]}",
        reply_markup=calendar
    )


@bot.callback_query_handler(
    func=lambda call: bool(call.data) and call.data.startswith('cbcal')
                      and MyStyleCalendar.func(),
)
@require_valid_session(1, '_')
def calendar_processor(callback_query: CallbackQuery) -> None:
    user_id, chat_id = get_user_and_chat_ids(callback_query)
    message_id = callback_query.message.message_id

    with bot.retrieve_data(user_id, chat_id) as data:
        session_id = data['session_id']
        date_min = data['calendar_date']['min']
        date_max = data['calendar_date']['max']

    result, key, step = MyStyleCalendar(
        calendar_id=session_id,
        locale='ru',
        min_date=date_min,
        max_date=date_max
    ).process(callback_query.data)

    if not result and key:
        bot.edit_message_text(
            f'Выберите {LSTEP[step]}',
            chat_id,
            message_id,
            reply_markup=key
        )
    elif result:
        with bot.retrieve_data(user_id, chat_id) as data:
            data['calendar_date'].update({'result': result})

        safe_delete_message(chat_id, message_id)
        send_calendar_done(callback_query)
