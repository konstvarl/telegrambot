from telebot import TeleBot
from telebot.storage import StateMemoryStorage

from config_data.config import BOT_TOKEN
from database.data_storage import create_tables

storage = StateMemoryStorage()
bot = TeleBot(token=BOT_TOKEN, state_storage=storage)
create_tables()
