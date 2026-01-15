from functools import wraps
from typing import Any, Callable

from telebot.types import CallbackQuery

from loader import bot
from utils.parsing import safe_parse_callback_index
from utils.user import get_user_and_chat_ids


def validate_session(
        callback_query: CallbackQuery,
        data: dict[str, Any],
        part_index: int = 1,
        sep: str = '|'
) -> bool:
    """
    Проверяет, что callback_query относится к текущей сессии пользователя.

    :param callback_query: Объект CallbackQuery
    :param data: Словарь, полученный из bot.retrieve_data(user_id, chat_id).
        Должен содержать ключ 'session_id'.
    :param part_index: Индекс извлекаемой части в callback_query.data
    :param sep: Символ разделяющий части в callback_query.data
    :return: True - если сессия валидна или False - если не валидна
        или данные некорректны
    """
    session_from_cb = safe_parse_callback_index(callback_query, part_index, sep)
    if session_from_cb is None:
        return False

    if not data or data.get('session_id') != session_from_cb:
        bot.answer_callback_query(
            callback_query.id, 'Эта кнопка больше неактивна!'
        )
        return False
    return True


def _is_session_valid(
        callback_query: CallbackQuery,
        part_index: int,
        sep: str
) -> bool:
    user_id, chat_id = get_user_and_chat_ids(callback_query)

    with bot.retrieve_data(user_id, chat_id) as data:
        return validate_session(callback_query, data, part_index, sep)


def require_valid_session(part_index: int = 1, sep: str = '|'):
    """
    Декоратор для callback_query-хэндлеров.
    Проверяет session_id перед выполнением.
    Если сессия невалидна - завершает обработку.

    :param part_index: Индекс извлекаемой части в callback_query.data
    :param sep: Символ разделяющий части в callback_query.data
    """

    def decorator(handler: Callable):
        @wraps(handler)
        def wrapper(callback_query: CallbackQuery, *args, **kwargs):
            if not _is_session_valid(callback_query, part_index, sep):
                return None

            return handler(callback_query, *args, **kwargs)

        return wrapper

    return decorator


def validate_value(value: str, min_value: int, max_value: int) -> int | None:
    """
    Проверяет, что value - целое число в диапазоне [min_value, max_value].

    :param value: Строка, введённая пользователем
    :param min_value: Минимальное допустимое значение
    :param max_value: Максимальное допустимое значение
    :return: Число или None если value не целое число или вне заданного
    диапазона.
    """
    try:
        value = int(value)
    except ValueError:
        return None
    if min_value <= value <= max_value:
        return value
    return None
