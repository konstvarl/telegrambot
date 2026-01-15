from pycountry import countries, subdivisions
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def gen_markup_select_city(
        cities: list, session_id: str
) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    for index, city in enumerate(cities):
        subdivision = subdivisions.get(code=city['address'].get('stateCode', ''))
        keyboard.add(
            InlineKeyboardButton(
                text=f'Город: {city['name']}, '
                     f'Страна: {
                     countries.get(alpha_2=city['address']['countryCode']).name
                     }'
                     f'{', ' + subdivision.name if subdivision else ''}',
                callback_data=f'selected_city|{session_id}|{index}'
            )
        )
    return keyboard
