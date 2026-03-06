import logging
from http.client import RemoteDisconnected
from time import sleep

from requests import ReadTimeout
from telebot import TeleBot
from telebot.apihelper import ApiTelegramException
from telebot.custom_filters import StateFilter

import handlers  # noqa
from loader import bot
from utils.set_bot_commands import set_default_commands


def start_polling(tg_bot: TeleBot):
    """
    Запускает polling с автоперезапуском при сетевых ошибках.

    :param tg_bot: Экземпляр бота.
    :return: None.
    """
    plogger = logging.getLogger(__name__)
    while True:
        try:
            plogger.info('Запуск long polling...')
            tg_bot.infinity_polling(timeout=60, long_polling_timeout=20)
        except (ConnectionError, ReadTimeout, RemoteDisconnected) as error:
            plogger.warning(f'⚠️ Потеряно соединение с Telegram: {error}. '
                            f'Перезапуск через 5 сек...')
            sleep(5)
        except ApiTelegramException as error:
            if error.error_code == 429:
                plogger.warning('⏳ Telegram API: Слишком много запросов. '
                                'Перезапуск через 10 сек...')
                sleep(10)
            else:
                plogger.error(f'Ошибка Telegram API: {error}')
                sleep(5)
        except Exception as error:
            plogger.exception(f'❌ Необработанная ошибка polling: {error}')
            tg_bot.stop_polling()
            sleep(10)
        except KeyboardInterrupt:
            plogger.info('🛑 Остановка polling по Ctrl+C')
            break


if __name__ == '__main__':
    from logging.handlers import RotatingFileHandler

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    file_handler = RotatingFileHandler(
        'bot.log',
        maxBytes=5 * 1024 * 1024,
        backupCount=1,
        encoding='utf-8'
    )
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    from database.data_storage import create_tables

    create_tables()

    bot.add_custom_filter(StateFilter(bot))
    set_default_commands(bot)
    start_polling(bot)
