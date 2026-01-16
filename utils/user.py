from telebot.types import Message, CallbackQuery

from config_data.config import CALENDAR_SERVICE_MESSAGE
from loader import bot


def get_user_and_chat_ids(obj: Message | CallbackQuery) -> tuple[int, int]:
    """
    Возвращает user_id и chat_id из Message или CallbackQuery.
    """
    if isinstance(obj, Message):
        return obj.from_user.id, obj.chat.id
    if isinstance(obj, CallbackQuery):
        return obj.from_user.id, obj.message.chat.id
    raise TypeError(f'Неподдерживаемый тип объекта: {type(obj)}')


def send_calendar_done(callback_query: CallbackQuery) -> None:
    """
    Сигнализирует о завершении работы календаря.

    Создает и отправляет служебное сообщение в message_handler,
    таким образом, эмулируется ввод пользователя, что позволяет
    автоматически передать управление в handler,
    привязанный к текущему состоянию.

    :param callback_query: Объект CallbackQuery, завершивший выбор даты.
    :return: None
    """
    message = Message(
        message_id=0,
        from_user=callback_query.from_user,
        chat=callback_query.message.chat,
        date=None,
        content_type='text',
        options={'text': CALENDAR_SERVICE_MESSAGE},
        json_string=None,
    )
    bot.process_new_messages([message])
