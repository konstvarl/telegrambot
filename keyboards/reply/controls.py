from telebot.types import ReplyKeyboardMarkup

from config_data.config import COMMANDS_TO_REPLY_KEYBOARD


def gen_reply_controls_for_display():
    kb = ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=False
    )
    kb.row(
        COMMANDS_TO_REPLY_KEYBOARD['Choose city'],
        COMMANDS_TO_REPLY_KEYBOARD['Choose dates'],
        COMMANDS_TO_REPLY_KEYBOARD['Set price range'],
        COMMANDS_TO_REPLY_KEYBOARD['Set search radius']
    )
    kb.row(
        COMMANDS_TO_REPLY_KEYBOARD['Choose sorting criteria'],
        COMMANDS_TO_REPLY_KEYBOARD['Repeat search'],
        COMMANDS_TO_REPLY_KEYBOARD['Complete']
    )
    return kb
