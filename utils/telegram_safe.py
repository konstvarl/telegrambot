import logging

from telebot.apihelper import ApiTelegramException
from telebot.types import (
    InlineKeyboardMarkup, InputMediaPhoto, ReplyKeyboardMarkup
)

from loader import bot
from states.user_states import States


def fail_search(
        user_id: int,
        chat_id: int,
        msg_id: int | None,
        text: str,
        markup: ReplyKeyboardMarkup
) -> None:
    """
    Универсальная обработка ошибок поиска: удаляет сообщение прогресса,
    переводит состояние бота и отправляет уведомление пользователю.
    """
    safe_delete_message(chat_id, msg_id)
    bot.set_state(user_id, States.search_hotels_stop, chat_id)
    bot.send_message(chat_id, text, reply_markup=markup)


def safe_delete_message(
        chat_id: int,
        message_id: int | list[int] | None
) -> None:
    """
    Безопасно удаляет одно или несколько сообщений, игнорируя ошибки
    если сообщение уже удалено или недоступно.
    """
    if message_id is None:
        return

    ids = [message_id] if isinstance(message_id, int) else message_id
    for mid in ids:
        if mid is None:
            continue
        try:
            bot.delete_message(chat_id, mid)
        except ApiTelegramException as error:
            description = getattr(error, 'result_json', {}).get(
                'description', 'no description'
            )
            logging.warning(
                f'[safe_delete_message] Ошибка при удалении {mid} в чате {chat_id}:\n'
                f'Функция {error.function_name}, код: {error.error_code}, '
                f'описание {description}'
            )
        except Exception as exc:
            logging.warning(f'[safe_delete_message] Не удалось удалить {mid} '
                            f'в чате {chat_id}: {exc}')


def safe_edit_message(
        text: str,
        chat_id: int,
        message_id: int | None = None,
        mode: str | None = None,
        markup: InlineKeyboardMarkup | None = None
) -> int:
    """
    Безопасно редактирует сообщение или создает новое.
    Если редактирование невозможно (удалено, ошибка) - отправляет новое.

    :param text: Новый текст сообщения.
    :param chat_id: Идентификатор чата.
    :param message_id: Идентификатор редактируемого сообщения.
    :param mode: Режим парсинга нового текста сообщения.
    :param markup: Объект для inline-клавиатуры.
    :return: Идентификатор отредактированного/нового сообщения.
    """
    new_message = None
    if message_id is not None:
        try:
            new_message = bot.edit_message_text(
                text, chat_id, message_id, parse_mode=mode,
                reply_markup=markup
            )
            return new_message.message_id
        except ApiTelegramException as exc:
            description = getattr(exc, 'result_json', {}).get('description', '')
            if 'message is not modified' in description:
                return message_id
        except Exception:
            pass

    try:
        new_message = bot.send_message(
            chat_id, text, parse_mode=mode, reply_markup=markup
        )
        return new_message.message_id
    except Exception as exc:
        logging.warning(f'[safe_edit_message] Не удалось отправить '
                        f'сообщение в чат {chat_id}: {exc}')
        return -1


def safe_edit_media(
        url_photo: str,
        photo_caption: str,
        chat_id: int,
        message_id: int | None,
        mode: str | None = None,
        markup: InlineKeyboardMarkup | None = None
) -> int | None:
    """
    Безопасно редактирует фото-сообщение или создает новое.
    Любые ошибки редактирования (удалено, устарело) приводят
    к созданию нового сообщения.

    :param url_photo: Ссылка на фотографию.
    :param photo_caption: Подпись к фотографии.
    :param chat_id: Идентификатор чата.
    :param message_id: Идентификатор редактируемого фото-сообщения.
    :param mode: Режим парсинга новой подписи к фотографии.
    :param markup: Объект для inline-клавиатуры.
    :return: Идентификатор отредактированного/нового сообщения или None
        при неудаче.
    """
    if not url_photo:
        logging.warning(f'[safe_edit_media] Пустой URL фото для чата {chat_id}')
        return None

    new_message = None

    if message_id is not None:
        try:
            new_media = InputMediaPhoto(
                media=url_photo,
                caption=photo_caption,
                parse_mode=mode
            )
            new_message = bot.edit_message_media(
                media=new_media,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=markup
            )
            return new_message.message_id
        except ApiTelegramException as exc:
            description = getattr(exc,'result_json', {}).get('description', '')
            if 'message is not modified' in description:
                return message_id
        except Exception:
            pass

    try:
        new_message = bot.send_photo(
            chat_id=chat_id,
            photo=url_photo,
            caption=photo_caption,
            parse_mode=mode,
            reply_markup=markup
        )
        return new_message.message_id
    except Exception as exc:
        logging.warning(
            f'[safe_edit_media] Не удалось отправить фото '
            f'в чат {chat_id}: {exc}'
        )
        return None


def safe_remove_markup(chat_id: int, message_id: int) -> None:
    """
    Безопасно удаляет inline-клавиатуру у сообщения.

    :param chat_id: Идентификатор чата.
    :param message_id: Идентификатор сообщения.
    :return: None
    """
    if message_id is None:
        return

    try:
        bot.edit_message_reply_markup(
            chat_id, message_id, reply_markup=None
        )
    except ApiTelegramException:
        pass
    except Exception as exc:
        logging.warning(f'[safe_remove_markup] Не удалось убрать '
                        f'клавиатуру {message_id}: {exc}')
