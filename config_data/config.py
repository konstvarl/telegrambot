import os

from dotenv import load_dotenv, find_dotenv

if not find_dotenv():
    exit('Переменные окружения не загружены т.к. отсутствует файл .env')
else:
    load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
AMADEUS_API_KEY = os.getenv('AMADEUS_API_KEY')
AMADEUS_API_SECRET = os.getenv('AMADEUS_API_SECRET')

DEFAULT_COMMANDS = (
    ('start', 'Запустить бота'),
    ('help', 'Вывести справку'),
    ('lowprice', 'Самые доступные по цене отели в городе'),
    ('guest_rating', 'Самые популярные отели в городе'),
    ('bestdeal', 'Отели расположенные ближе других к центру города'),
    ('history', 'История запросов и результатов поисков'),
)

SORT_COMMANDS = {'lowprice', 'bestdeal', 'guest_rating'}

CALENDAR_SERVICE_MESSAGE = '_calendar_done_'

PHOTOS = {
    'searching': 'AgACAgIAAxkBAAJOtmjr0621-_BG1ajuBVcBz6xcEkQIAAKGATIbE7FhS8bNr'
                 'DDNDmylAQADAgADeQADNgQ',
    'not_found': 'AgACAgIAAxkBAAJOuGjr09kmk0yHwxgl3STk1mJUd01UAAKHATIbE7FhS7UYR'
                 'hSbkHEZAQADAgADeQADNgQ',
}

COMMANDS_TO_REPLY_KEYBOARD = {
    'Choose city': '🌇 Выбрать город',
    'Choose dates': '📅 Выбрать даты',
    'Set price range': '💰 Задать диапазон цен',
    'Set search radius': '🎯 Задать радиус поиска',
    'Choose sorting criteria': '📊 Выбрать критерий сортировки',
    'Repeat search': '🔁 Повторить поиск',
    'Complete': '❌ Завершить'
}
