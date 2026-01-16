from telebot.types import Message

from config_data.config import SORT_COMMANDS
from handlers.custom.hotel import search_hotels
from keyboards.inline.sorting_command import gen_markup_command_sorting
from loader import bot
from states.user_states import States
from utils.user import get_user_and_chat_ids
from utils.validation import validate_value


@bot.message_handler(state=States.radius)
def set_radius(message: Message) -> None:
    """
    Обрабатывает ввод радиуса поиска от пользователя.
    Радиус задаётся в километрах и должен быть целым числом
    не менее 1 и не более 300.
    """
    RADIUS_MIN, RADIUS_MAX = 1, 300
    user_id, chat_id = get_user_and_chat_ids(message)
    radius_value = validate_value(message.text.strip(), RADIUS_MIN, RADIUS_MAX)
    if radius_value is None:
        bot.send_message(
            chat_id,
            f'Радиус должен быть целым числом не менее {RADIUS_MIN} '
            f'и не более {RADIUS_MAX}! '
            f'Повторите ввод.'
        )
        return

    with bot.retrieve_data(user_id, chat_id) as data:
        request = data['request']
        request['radius'] = radius_value
        data['data_for_search'] = True
        city_name = request['city']['name']
        command = request.get('command')
        session_id = data['session_id']
        return_to = data.pop('return_to', None)

    bot.send_message(
        chat_id,
        f'🎯 Ищем отели в радиусе {radius_value} км от центра города {city_name}'
    )

    if return_to:
        return
    bot.set_state(user_id, States.sorting_criteria, chat_id)
    if command in SORT_COMMANDS:
        search_hotels(message)
    else:
        bot.send_message(
            chat_id,
            'Выберите по какому критерию будем сортировать отели?',
            reply_markup=gen_markup_command_sorting(session_id)
        )
