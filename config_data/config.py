import os
from dotenv import load_dotenv, find_dotenv

if not find_dotenv():
    exit('Переменные окружения не загружены т.к. отсутствует файл .env')
else:
    load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
# RAPID_API_KEY = os.getenv('RAPID_API_KEY')
API_BASE_URL = 'https://test.api.amadeus.com/'
AMADEUS_API_KEY = os.getenv('AMADEUS_API_KEY')
AMADEUS_API_SECRET = os.getenv('AMADEUS_API_SECRET')
# AMADEUS_TOKEN = os.getenv('AMADEUS_TOKEN')
DEFAULT_COMMANDS = (
    ('start', 'Запустить бота'),
    ('help', 'Вывести справку'),
    ('lowprice', 'Самые доступные отели в городе'),
    ('guest_rating', 'Самые популярные отели в городе'),
    ('bestdeal', 'Отели расположенные ближе других к центру города'),
    ('history', 'История запросов и результатов поисков'),
)
