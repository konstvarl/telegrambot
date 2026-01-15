import uuid

from telebot.types import Message, ReplyKeyboardRemove

from config_data.config import SORT_COMMANDS
from database.data_storage import User
from handlers.custom.hotel import search_hotels
from loader import bot
from states.user_states import States
from utils.user import get_user_and_chat_ids


@bot.message_handler(
    commands=['start', *SORT_COMMANDS]
)
def bot_start(message: Message) -> None:
    user_id, chat_id = get_user_and_chat_ids(message)
    user_name = message.from_user.full_name

    User.get_or_create(id=user_id, defaults={'name': user_name})
    command = message.text.replace('/', '')

    if command == 'start':
        with bot.retrieve_data(user_id, chat_id) as data:
            data.clear()
        bot.delete_state(user_id, chat_id)
        bot.send_message(
            user_id,
            f'Привет, {user_name}! Я бот который поможет '
            f'найти подходящие отели в нужном городе.',
            reply_markup=ReplyKeyboardRemove()
        )

    with bot.retrieve_data(user_id, chat_id) as data:
        data_for_search = data.get('data_for_search')

    if data_for_search:
        bot.set_state(user_id, States.search_hotels, chat_id)
        with bot.retrieve_data(user_id, chat_id) as data:
            data['request'] = {}
            data['request']['command'] = command
            data['data_for_search'] = True
            data['session_id'] = str(uuid.uuid4())
        search_hotels(message)
    else:
        bot.set_state(user_id, States.city_search, chat_id)
        with bot.retrieve_data(user_id, chat_id) as data:
            data.clear()
            data['request'] = {}
            data['request']['command'] = command
            data['session_id'] = str(uuid.uuid4())
        bot.send_message(
            user_id,
            'В каком городе будем искать?\n'
            'Введите название на английском.',
            reply_markup=ReplyKeyboardRemove()
        )
