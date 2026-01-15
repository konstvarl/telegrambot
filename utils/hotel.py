from contextlib import contextmanager

from pycountry import countries
from telebot import TeleBot


def format_hotel_text(hotel: dict, num_page: int, num_hotels: int) -> str:
    hotel_offer = hotel['offer']
    num_nights = int(hotel_offer['checkOutDate'].split('-')[2]) - \
                 int(hotel_offer['checkInDate'].split('-')[2])
    if hotel.get('sentiments'):
        hotel_sentiments = hotel['sentiments']['overallRating']
    else:
        hotel_sentiments = 'нет данных'
    return f"""
        Отель: {hotel['name']}
Звёзды: {hotel['rating']}
Адрес: {countries.get(alpha_2=hotel['address']['countryCode']).name}, \
{hotel['address']['cityName']}, {hotel['address'].get('postalCode', 'не указано')}, \
{', '.join(item_address for item_address in hotel['address']['lines'])}
Географические координаты
    - широта: {hotel['geoCode']['latitude']}
    - долгота: {hotel['geoCode']['longitude']}
Расстояние до центра: {hotel['distance']['value']} {hotel['distance']['unit'].lower()}
Рейтинг: {hotel_sentiments}
Предложение отеля
    Описание: {hotel_offer['room'].get('description', {}).get('text', 'не указано')}
    Тип проживания: {hotel_offer.get('boardType', 'не указано')}
    Дата заезда: {hotel_offer['checkInDate']}
    Дата отъезда: {hotel_offer['checkOutDate']}
    Общая стоимость: {hotel_offer['price']['total']} {hotel_offer['price']['currency']}
    Цена за ночь: {round(float(hotel_offer['price']['total']) / num_nights, 2)} {hotel_offer['price']['currency']}
Страница {num_page + 1} из {num_hotels}
    """


def sorting_hotels(hotel_ids: list, hotels: dict, command: str) -> None:
    if command == 'bestdeal':
        hotel_ids.sort(
            key=lambda x: hotels[x]['distance']['value'],
        )
    elif command == 'lowprice':
        hotel_ids.sort(
            key=lambda x: float(hotels[x]['offer']['price']['total'])
        )
    elif command == 'guest_rating':
        hotel_ids.sort(
            key=lambda x: hotels[x]['sentiments']['overallRating'] \
                if hotels[x].get('sentiments') else 0,
            reverse=True
        )


def sorting_order(command_sorting: str) -> str | None:
    if command_sorting == 'bestdeal':
        return 'в порядке удаления от центра города'
    elif command_sorting == 'lowprice':
        return 'в порядке увеличения цены'
    elif command_sorting == 'guest_rating':
        return 'в порядке убывания популярности'


@contextmanager
def media_lock(bot: TeleBot, user_id: int, chat_id: int, flag_name: str) -> None:
    """
    Предотвращает конфликты при обработке контента в конкурентной среде
    Telegram-бота.

    Гарантирует, что операции с сообщениями (редактирование, отправка)
    не выполняются параллельно при быстрых повторных действиях пользователя,
    используя флаг в FSM-хранилище.

    :param bot: Экземпляр Telegram-бота (TeleBot).
    :param user_id: Идентификатор пользователя.
    :param chat_id: Идентификатор чата.
    :param flag_name: Имя флага-блокировки в FSM.
    :raise RuntimeError: Если операция с данным флагом уже выполняется.
    :return: None
    """
    with bot.retrieve_data(user_id, chat_id) as data:
        if data.get(flag_name):
            raise RuntimeError(flag_name)
        data[flag_name] = True
    try:
        yield
    finally:
        with bot.retrieve_data(user_id, chat_id) as data:
            data[flag_name] = False
