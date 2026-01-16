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
    logger = logging.getLogger(__name__)
    while True:
        try:
            logger.info('Запуск long polling...')
            tg_bot.infinity_polling(timeout=60, long_polling_timeout=20)
        except (ConnectionError, ReadTimeout, RemoteDisconnected) as error:
            logger.warning(f'⚠️ Потеряно соединение с Telegram: {error}. '
                           f'Перезапуск через 5 сек...')
            sleep(5)
        except ApiTelegramException as error:
            if error.error_code == 429:
                logger.warning('⏳ Telegram API: Слишком много запросов. '
                               'Перезапуск через 10 сек...')
                sleep(10)
            else:
                logger.error(f'Ошибка Telegram API: {error}')
                sleep(5)
        except Exception as error:
            logger.exception(f'❌ Необработанная ошибка polling: {error}')
            tg_bot.stop_polling()
            sleep(10)
        except KeyboardInterrupt:
            logger.info('🛑 Остановка polling по Ctrl+C')
            break


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler('bot.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    bot.add_custom_filter(StateFilter(bot))
    set_default_commands(bot)
    start_polling(bot)
