from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config_data.config import DEFAULT_COMMANDS, SORT_COMMANDS


def gen_markup_command_sorting(session_id: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    for command, desk in DEFAULT_COMMANDS:
        if command in SORT_COMMANDS:
            keyboard.add(
                InlineKeyboardButton(
                    text=desk,
                    callback_data=f'bot_command|{session_id}|{command}'
                )
            )
    return keyboard
