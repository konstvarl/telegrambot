from telebot.types import Message

from loader import bot


@bot.message_handler(commands=['guest_rating'])
def bot_start(message: Message):
    bot.reply_to(message, f'Здесь будет вывод guest_rating')
