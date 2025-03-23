from telebot.types import Message

from loader import bot


# Эхо хендлер, куда летят текстовые сообщения без указанного состояния
#  В ответ отсылается сообщение с просьбой ввести команду
@bot.message_handler(state=None)
def bot_echo(message: Message):
    bot.reply_to(message, 'Выберите команду.')
