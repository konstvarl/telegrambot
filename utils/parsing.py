from typing import Callable, Any

from telebot.types import CallbackQuery

from loader import bot


def safe_parse_callback_index(
        callback_query: CallbackQuery,
        part_index: int,
        sep: str = '|',
        transform: Callable[[str], Any] | None = None,
        error_message: str = 'Некорректные данные!'
) -> Any | None:
    """
    Пытается извлечь указанную часть callback_query.data и, при необходимости,
    преобразует её функцией transform, например, int.
    Возвращает None, если данные некорректны.

    :param callback_query: Объект CallbackQuery
    :param part_index: Индекс нужной части callback_query.data
    :param sep: Символ разделяющий части в callback_query.data
    :param transform: Функция преобразования (int, str.upper и т.д.)
    :param error_message: Сообщение об ошибке
    :return: Преобразованное значение или None при ошибке
    """
    try:
        part = callback_query.data.split(sep)[part_index]
        return transform(part) if transform else part
    except (ValueError, IndexError):
        bot.answer_callback_query(callback_query.id, error_message)
        return None


def verify_range_prices(range_prices: str) -> str | None:
    """
    Проверяет строку с диапазоном цен на соответствие формату:
    [min]-[max], где min/max - число float или int.
    Например, '200-300' или '-300' или '100'.

    :param range_prices: Строка содержащая диапазон цен.
    :return: "Исправленную" строку с диапазоном цен, если формат правильный,
            иначе None.
    """
    range_prices = range_prices.strip()
    range_prices = range_prices.replace('_', ' ')
    range_prices = range_prices.replace(',', '.')
    parts = [p.strip() for p in range_prices.split('-')]
    if len(parts) == 1:
        if parts[0] == '':
            return None
        try:
            float(parts[0])
            return parts[0]
        except ValueError:
            return None
    if len(parts) == 2:
        min_price, max_price = parts
        if min_price == '' and max_price == '':
            return None
        try:
            if min_price != '' and max_price != '':
                float(min_price)
                float(max_price)
                if float(min_price) > float(max_price):
                    return None
            elif min_price != '':
                float(min_price)
            else:
                float(max_price)
        except ValueError:
            return None
        return '-'.join(parts)
    return None


if __name__ == '__main__':
    ranges_prices_good = [
        '200-300.5', '-300', '200.5-', '100.5', '100-', '0', ' -100',
        '  200-  ', '200 - 300'
    ]
    ranges_prices_bad = [
        '-', '1oo', '200_300', 'з00', '100--', 'o', 'от 200  до 300',
        '100--300', '200...250', '-200-250', '1oo-250', '200 300', '',
        '100-2oo'
    ]
    print('Правильные цены')
    for i_range_prices in ranges_prices_good:
        print(f'{i_range_prices}: ', end='')
        print(verify_range_prices(i_range_prices))

    print('Неправильные цены')
    for i_range_prices in ranges_prices_bad:
        print(f'{i_range_prices}: ', end='')
        print(verify_range_prices(i_range_prices))
