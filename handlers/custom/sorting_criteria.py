from telebot.types import CallbackQuery

from config_data.config import SORT_COMMANDS
from handlers.custom.hotel import search_hotels
from loader import bot
from states.user_states import States
from utils.hotel import sorting_order
from utils.parsing import safe_parse_callback_index
from utils.telegram_safe import safe_delete_message
from utils.user import get_user_and_chat_ids
from utils.validation import require_valid_session


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('bot_command'),
    state=States.sorting_criteria
)
@require_valid_session()
def get_sorting_criteria(callback_query: CallbackQuery) -> None:
    command = safe_parse_callback_index(callback_query, 2)
    if command is None:
        return

    user_id, chat_id = get_user_and_chat_ids(callback_query)

    with bot.retrieve_data(user_id, chat_id) as data:
        return_to = data.pop('return_to', None)
        if command in SORT_COMMANDS:
            data['request']['command'] = command
        else:
            available = '\n'.join(f'/{cmd}' for cmd in SORT_COMMANDS)
            bot.send_message(
                chat_id,
                f'Некорректная команда: {command}.\n'
                f'Введите одну из допустимых команд:\n{available}'
            )
            return

    bot.answer_callback_query(callback_query.id)
    safe_delete_message(user_id, callback_query.message.message_id)
    if return_to:
        bot.send_message(chat_id, f'Сортировка отелей {sorting_order(command)}')
        return
    bot.set_state(user_id, States.search_hotels, chat_id)
    search_hotels(callback_query)
