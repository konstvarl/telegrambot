from telebot.types import Message

from loader import bot


@bot.message_handler(commands=['bestdeal'])
def bot_start(message: Message):
    bot.reply_to(message, f'Здесь будет вывод bestdeal-отелей')
