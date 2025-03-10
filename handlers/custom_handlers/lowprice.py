from telebot.types import Message
from loader import bot
from states.search_info import States


@bot.message_handler(commands=['lowprice'])
def lowprice(message: Message) -> None:
    bot.send_message(
        message.chat.id,
        f'Ищем самые доступные отели в городе N')
    # bot.set_state(message.from_user.id, States.city, message.chat.id)

