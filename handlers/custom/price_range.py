from telebot.types import Message

from loader import bot
from states.user_states import States
from utils.parsing import verify_range_prices
from utils.user import get_user_and_chat_ids


@bot.message_handler(state=States.price_range)
def set_prices_range(message: Message) -> None:
    user_id, chat_id = get_user_and_chat_ids(message)
    range_prices = verify_range_prices(message.text)
    if range_prices is not None:
        with bot.retrieve_data(user_id, chat_id) as data:
            data['request']['range_prices'] = range_prices
        bot.send_message(
            chat_id,
            f'💰 Установлен диапазон цен: {range_prices}'
        )
        with bot.retrieve_data(user_id, chat_id) as data:
            return_to = data.pop('return_to', None)

        if return_to:
            return

        bot.set_state(user_id, States.radius, chat_id)
        bot.send_message(
            chat_id,
            f'Введите радиус, т.е. в пределах скольки километров от центра города '
            f'будем искать отели? (Радиус должен быть целым числом не менее 1 '
            f'и не более 300)'
        )
    else:
        bot.send_message(
            chat_id,
            'Неправильный формат диапазона цен. Повторите ввод.'
        )
