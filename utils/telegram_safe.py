from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InputMediaPhoto

from loader import bot


def safe_delete_message(chat_id: int, message_id: int | list[int]) -> None:
    """
    Безопасно удаляет одно или несколько сообщений, игнорируя ошибки
    если сообщение уже удалено.
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
            print(f'[safe_delete_message] Ошибка при удалении {mid}:\n')
            print(f'Функция {error.function_name}, код: {error.error_code}')
            print(error.result_json['description'])


def safe_edit_message(
        text: str,
        chat_id: int,
        message_id: int,
        mode: str | None = None,
        markup: InlineKeyboardMarkup | None = None
) -> int:
    """
    Безопасно редактирует сообщение, игнорируя ошибки
    если сообщение уже удалено. Если сообщение для редактирования отсутствует,
    то создает новое.

    :param text: Новый текст сообщения.
    :param chat_id: Идентификатор чата.
    :param message_id: Идентификатор редактируемого сообщения.
    :param mode: Режим парсинга нового текста сообщения.
    :param markup: Объект для inline-клавиатуры.
    :return: Идентификатор отредактированного/нового сообщения.
    """
    try:
        if message_id is None:
            raise ValueError

        new_message = bot.edit_message_text(
            text, chat_id, message_id, parse_mode=mode, reply_markup=markup
        )
    except (ApiTelegramException, ValueError, TypeError) as exc:
        if isinstance(exc, ApiTelegramException):
            bot.delete_message(chat_id, message_id)
        new_message = bot.send_message(
            chat_id, text, parse_mode=mode, reply_markup=markup
        )

    return new_message.message_id


def safe_edit_media(
        url_photo: str,
        photo_caption: str,
        chat_id: int,
        message_id: int,
        mode: str | None = None,
        markup: InlineKeyboardMarkup | None = None
) -> int | None:
    """
    Безопасно редактирует фото-сообщение, игнорируя ошибки
    если фото-сообщение, уже удалено. Если фото-сообщение, для редактирования
    отсутствует, то создает новое.

    :param url_photo: Ссылка на фотографию.
    :param photo_caption: Подпись к фотографии.
    :param chat_id: Идентификатор чата.
    :param message_id: Идентификатор редактируемого фото-сообщения.
    :param mode: Режим парсинга нового подписи к фотографии.
    :param markup: Объект для inline-клавиатуры.
    :return: Идентификатор отредактированного/нового сообщения.
    """
    try:
        if message_id is None:
            raise ValueError

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
    except ApiTelegramException:
        return None

    except ValueError:
        try:
            new_message = bot.send_photo(
                chat_id=chat_id,
                photo=url_photo,
                caption=photo_caption,
                parse_mode=mode,
                reply_markup=markup
            )
        except (ApiTelegramException, ValueError):
            return None

    return new_message.message_id


def safe_remove_markup(chat_id: int, message_id: int) -> None:
    """
    Безопасно удаляет inline-клавиатуру у сообщения.

    :param chat_id: Идентификатор чата.
    :param message_id: Идентификатор сообщения.
    :return: None
    """
    try:
        bot.edit_message_reply_markup(
            chat_id, message_id, reply_markup=None
        )
    except ApiTelegramException:
        pass
