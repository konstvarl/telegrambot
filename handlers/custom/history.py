import uuid
from datetime import date

from telebot import types
from telebot.types import Message

from config_data.config import CALENDAR_SERVICE_MESSAGE
from database.data_storage import get_user_history
from handlers.custom.calendar import start_calendar
from loader import bot
from states.user_states import States
from utils.telegram_safe import safe_delete_message
from utils.user import get_user_and_chat_ids


@bot.message_handler(commands=['history'])
def bot_history(message: Message) -> None:
    user_id, chat_id = get_user_and_chat_ids(message)
    bot.send_message(
        chat_id, f'История поисков пользователя {message.from_user.full_name}:'
    )
    bot.set_state(user_id, States.date_search, chat_id)
    search_date = bot.send_message(chat_id, 'За какую дату показать историю?\n'
                                            'Выберите дату...')
    with bot.retrieve_data(user_id, chat_id) as data:
        data['session_id'] = str(uuid.uuid4())
        data['history'] = {'message_search_date_id': search_date.message_id}

    start_calendar(user_id, chat_id, date_max=date.today())


ITEMS_PER_PAGE = 3


@bot.message_handler(
    func=lambda m: m.text == CALENDAR_SERVICE_MESSAGE,
    state=States.date_search
)
def get_date_search(message: Message) -> None:
    user_id, chat_id = get_user_and_chat_ids(message)

    with bot.retrieve_data(user_id, chat_id) as data:
        result = data['calendar_date']['result']
        message_search_date_id = data['history']['message_search_date_id']

    bot.edit_message_text(
        f'📅 Выбрана дата поиска {result.strftime("%d.%m.%Y")}',
        chat_id,
        message_search_date_id
    )

    user_history = get_user_history(user_id, result)
    if not user_history:
        bot.send_message(chat_id, '😔 История за эту дату пуста.')
        return

    with bot.retrieve_data(user_id, chat_id) as data:
        data['user_history'] = user_history
        data['history_page'] = 0

    show_history_page(chat_id, user_history, 0)


def show_history_page(chat_id: int, history: list[dict], page: int) -> None:
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    items = history[start:end]

    text = f'<b>📖 История поиска (страница {page + 1})</b>\n\n'
    for i, request in enumerate(items, start=1):
        text += (
            f'<b>{request['city']}, {request['country']}</b>\n'
            f'Дата поиска: {request['created_at']}\n'
            f'Заезд: {request['check_in_date']}, выезд: {request['check_out_date']}\n'
            f'Диапазон цен: {request['price_range']} {request['currency_name']}\n'
            f'Команда: {request['command']}\n\n'
        )

    markup = types.InlineKeyboardMarkup()
    buttons = []
    if page > 0:
        buttons.append(
            types.InlineKeyboardButton(
                '⬅️ Назад', callback_data=f'history_prev_{page - 1}'
            )
        )
    if end < len(history):
        buttons.append(
            types.InlineKeyboardButton(
                '➡️ Вперёд', callback_data=f'history_next_{page + 1}'
            )
        )
    markup.row(*buttons)

    bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')


@bot.callback_query_handler(func=lambda call: call.data.startswith('history'))
def paginate_history(call):
    user_id, chat_id = get_user_and_chat_ids(call)

    with bot.retrieve_data(user_id, chat_id) as data:
        history = data.get('user_history')
        if not history:
            return
        parts = call.data.split('_')
        action, _, new_page = parts
        new_page = int(new_page)

        safe_delete_message(chat_id, call.message.message_id)
        show_history_page(chat_id, history, new_page)
