import logging
import random
import time
from functools import wraps
from http.client import RemoteDisconnected

from amadeus import Client, ResponseError, Response
from requests.exceptions import ReadTimeout, HTTPError, ConnectionError

from config_data.config import AMADEUS_API_KEY, AMADEUS_API_SECRET
from database.data_storage import create_tables
from utils.cache_response import api_cache

amadeus = Client(
    client_id=AMADEUS_API_KEY,
    client_secret=AMADEUS_API_SECRET
)

logger = logging.getLogger(__name__)


def get_delay(
        attempt: int, retry_delay: int, retry_after: int | None = None
) -> float:
    """Рассчитывает задержку между попытками."""
    if retry_after is not None:
        return retry_after
    return retry_delay * (2 ** attempt - 1) + random.random()


def safe_request(
        max_retries: int = 3, retry_delay: int = 1, reraise: bool = True
):
    """
    Декоратор для безопасного выполнения запросов к API.
    Повторяет запрос при временных ошибках (429, timeouts, disconnect).

    :param max_retries: Максимальное количество попыток (включая первую).
    :param retry_delay: Базовая задержка в секундах.
    :param reraise: Если True - выбрасывает последнее исключение после всех
        попыток.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            retryable_codes = {429, 500, 502, 503, 504}
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (HTTPError, ResponseError) as error:
                    last_error = error
                    status_code = getattr(error.response, 'status_code', None)
                    if status_code not in retryable_codes:
                        logger.error(f'[{func.__name__}] HTTPError '
                                     f'{status_code}: {error}')
                        raise
                    retry_after = None
                    headers = getattr(error.response, 'headers', {})
                    if isinstance(headers, dict):
                        retry_after = headers.get('Retry-After')
                    try:
                        retry_after = int(retry_after) if retry_after else None
                    except (ValueError, TypeError):
                        retry_after = None
                    delay = get_delay(attempt, retry_delay, retry_after)
                    logger.warning(f'[{func.__name__}] Ошибка {status_code} '
                                   f'({type(error).__name__}), '
                                   f'попытка {attempt}/{max_retries}. '
                                   f'Повтор через {delay:.1f} сек...')
                    if attempt < max_retries:
                        time.sleep(delay)

                except (ReadTimeout, RemoteDisconnected, ConnectionError) as error:
                    last_error = error
                    delay = get_delay(attempt, retry_delay)
                    logger.warning(f'[{func.__name__}] Сетевая ошибка '
                                   f'({type(error).__name__}),'
                                   f'попытка {attempt}/{max_retries}. '
                                   f'Повтор через {delay:.1f} сек...')
                    if attempt < max_retries:
                        time.sleep(delay)

                except Exception as error:
                    logger.exception(f'[{func.__name__}] Неожиданная ошибка: {error}')
                    raise

            logger.error(f'[{func.__name__}] Превышено число попыток {max_retries}')
            if last_error:
                if reraise:
                    raise last_error
                return last_error

        return wrapper

    return decorator


@api_cache(
    'amadeus.reference_data.locations.cities.get',
    ttl_hours=720
)
@safe_request()
def get_cities(
        keyword: str,
        country_code: str = None,
        max_cities: int = None,
        include: str = None
) -> dict:
    """
    Возвращает список городов чьи названия содержат ключевое слово.

    :param keyword: Ключевое слово, которое должно содержать название города.
    :param country_code: Код страны согласно ISO 3166 Alpha-2,
        например, 'RU' - Россия.
    :param max_cities: Максимальное количество результатов в ответе.
    :param include: Если значение 'AIRPORTS', то в результаты поиска
        включаются аэропорты.
    :return: Ответ Amadeus в виде Response.result.
    """
    params = {'keyword': keyword}
    if country_code is not None:
        params['countryCode'] = country_code
    if max_cities is not None:
        params['max'] = max_cities
    if include is not None:
        params['include'] = include
    response = amadeus.reference_data.locations.cities.get(**params)
    return response.result


@safe_request()
def get_locations(
        keyword: str,
        subtype: list[str] | str = 'CITY',
        country_code: str = None,
        pages_offset: int = None,
        pages_limit: int = None,
        view: str = 'FULL'
) -> Response:
    """
    Возвращает список аэропортов и/или городов, соответствующих ключевому слову.

    :param keyword: Ключевое слово, с которого начинается название.
    :param subtype: Тип поиска: город 'CITY' и/или аэропорт 'AIRPORT'.
    :param country_code: Код страны согласно ISO 3166 Alpha-2, например, 'RU' - Россия.
    :param pages_offset: Начальный индекс запрашиваемой страницы.
    :param pages_limit: Максимальное количество результатов на одной странице.
    :param view: Уровень информативности ответа:
        'LIGHT' - только код IATA, название, подробное название города и название страны.
        'FULL' - в дополнение к информации уровня 'LIGHT': смещение часового пояса,
            географические координаты, код страны.
        По-умолчанию - 'FULL'.
    :return: Ответ Amadeus в виде Response.
    """
    params = {'keyword': keyword, 'subType': subtype, 'view': view}
    if country_code is not None:
        params['countryCode'] = country_code
    if pages_offset is not None and pages_limit is not None:
        params['page'] = {
            'offset': pages_offset,
            'limit': pages_limit
        }
    return amadeus.reference_data.locations.get(**params)


@api_cache(
    'amadeus.reference_data.locations.hotels.by_city.get',
    ttl_hours=720
)
@safe_request()
def get_hotels_by_city(
        city_code: str,
        radius: int = 5,
        radius_unit: str = 'KM',
        chain_codes: list[str] = None,
        amenities: list[str] = None,
        ratings: list[int] = None,  # В спецификации Amadeus параметр ratings
        # описывается как list[str], но в таком случае
        # возникает ошибка Bad Request.
        hotel_source: str = 'ALL'
) -> dict:
    """
    Возвращает информацию об отелях в указанном городе.

    :param city_code: Код города назначения или аэропорта. Если указан код
        города, поиск будет производиться по центру города. Доступные коды
        можно найти в таблице кодов IATA (3 буквы кода IATA).
    :param radius: Радиус поиска от центра.
    :param radius_unit: Единица измерения радиуса: километр 'KM' или миля 'MILE'.
        По-умолчанию 'KM'.
    :param chain_codes: Список кодов гостиничных сетей. Каждый код представляет
        собой строку, состоящую из 2 прописных букв.
    :param amenities: Список удобств.
    :param ratings: Звезды отеля. В строке можно указать до четырех значений.
    :param hotel_source: Источник отелей со значениями 'BEDBANK'
        для агрегаторов, 'DIRECT CHAIN' для GDS / дистрибуции и 'ALL' для обоих.
    :return: Ответ Amadeus в виде Response.result.
    """
    params = {
        'cityCode': city_code,
        'radius': radius,
        'radiusUnit': radius_unit,
        'hotelSource': hotel_source
    }
    if chain_codes is not None:
        params['chainCodes'] = ','.join(chain_codes)
    if amenities is not None:
        params['amenities'] = ','.join(amenities)
    if ratings is not None:
        params['ratings'] = ','.join(str(item) for item in ratings)
    else:
        params['ratings'] = '1,3,4,5'
    response = amadeus.reference_data.locations.hotels.by_city.get(**params)
    return response.result


@api_cache(
    'amadeus.reference_data.locations.hotels.by_hotels.get',
    ttl_hours=720
)
@safe_request()
def get_hotels_by_hotels(hotel_ids: list[str]) -> dict:
    """
    Возвращает список отелей по их идентификатору.

    :param hotel_ids: Список кодов отелей (8 символов).
    :return: Ответ Amadeus в виде Response.result.
    """
    HOTEL_IDS_MAX = 99
    pointer_left = 0
    hotel_ids_len = len(hotel_ids)
    pointer_right = HOTEL_IDS_MAX if HOTEL_IDS_MAX < hotel_ids_len \
        else hotel_ids_len
    result = {
        'data': [],
        'meta': []
    }
    while pointer_left < hotel_ids_len:
        response = amadeus.reference_data.locations.hotels.by_hotels.get(
            hotelIds=','.join(hotel_ids[pointer_left:pointer_right])
        )
        if response.result.get('data') is not None:
            result['data'].extend(response.result['data'])
        result['meta'].append(response.result['meta'])
        pointer_left = pointer_right
        pointer_right += HOTEL_IDS_MAX
        if pointer_right >= hotel_ids_len:
            pointer_right = hotel_ids_len
    return result


@api_cache(
    'amadeus.shopping.hotel_offers_search.get',
    ttl_hours=1
)
@safe_request()
def get_hotel_offers_search(
        hotel_ids: list[str],
        guest_adults: int = 1,
        check_in_date: str = None,
        check_out_date: str = None,
        country_of_residence: str = None,
        room_quantity: int = 1,
        price_range: str = None,
        currency: str = None,
        payment_policy: str = 'NONE',
        board_type: str = None,
        include_closed: bool = True,
        best_rate_only: bool = True,
        lang: str = None
) -> dict:
    """
    Возвращает предложения от указанных отелей.

    :param hotel_ids: Список кодов отелей Amadeus, состоящих из 8 символов.
    :param guest_adults: Количество (1-9) взрослых гостей в номере.
    :param check_in_date: Дата регистрации заезда (дата по местному времени
        отеля). Формат ГГГГ-ММ-ДД. Наименьшим допустимым значением является
        текущая дата. Если дата не указана, значением по умолчанию будет
        сегодняшняя дата в часовом поясе GMT.
    :param check_out_date: Дата выезда из отеля (дата по местному времени
        отеля). Формат ГГГГ-ММ-ДД. Наименьшее допустимое значение -
        check_in_date+1. Если не указано, по умолчанию будет выбрана
        check_in_date+1.
    :param country_of_residence: Код страны проживания путешественника,
        выраженный в формате ISO 3166-1.
    :param room_quantity: Запрашиваемое количество комнат (1-9).
    :param price_range: Фильтрация предложений отелей по цене за ночь (например,
        200-300, -300 или 100). При выборе этого поля обязательно указывайте
        валюту currency.
    :param currency: Код валюты, в которой возвращаются цены. Код валюты ISO
        (http://www.iso.org/iso/home/standards/currency_codes.htm). Если отель
        не поддерживает запрашиваемую валюту, цены на проживание в отеле будут
        возвращены в местной валюте отеля.
    :param payment_policy: Фильтрация ответа на основе определенного типа
        платежа. "NONE" означает "все типы" (по умолчанию).
    :param board_type: Фильтрация ответов на основе доступных блюд:
        * ROOM_ONLY = Только номер,
        * BREAKFAST = Завтрак,
        * HALF_BOARD = Ужин и завтрак (только для агрегаторов),
        * FULL_BOARD = Полный пансион (только для агрегаторов),
        * ALL_INCLUSIVE = Все включено (только для агрегаторов).
    :param include_closed: Показать все объекты (включая распроданные)
        или только доступные. Что касается распроданных объектов, пожалуйста,
        уточняйте наличие на другие даты.
    :param best_rate_only: Используется для возврата только самого дешевого
        предложения для каждого отеля или всех доступных предложений.
    :param lang: Язык описательных текстов.
        Примеры: 'FR', 'fr', 'fr-FR'. Если язык недоступен, текст будет
        возвращен на английском языке. Код языка ISO
        (https://www.iso.org/iso-639-language-codes.html).
    :return: Ответ Amadeus в виде Response.result.
    """
    offer_params = {
        'adults': guest_adults,
        'roomQuantity': room_quantity,
        'paymentPolicy': payment_policy,
        'includeClosed': str(include_closed).lower(),
        'bestRateOnly': str(best_rate_only).lower(),
    }
    if check_in_date is not None:
        offer_params['checkInDate'] = check_in_date
    if check_out_date is not None:
        offer_params['checkOutDate'] = check_out_date
    if country_of_residence is not None:
        offer_params['countryOfResidence'] = country_of_residence
    if price_range is not None:
        offer_params['priceRange'] = price_range
    if currency is not None:
        offer_params['currency'] = currency
    if board_type is not None:
        offer_params['boardType'] = board_type
    if lang is not None:
        offer_params['lang'] = lang
    HOTEL_IDS_MAX = 20
    pointer_left = 0
    hotel_ids_len = len(hotel_ids)
    pointer_right = HOTEL_IDS_MAX if HOTEL_IDS_MAX < hotel_ids_len \
        else hotel_ids_len
    result = {
        'data': [],
        'meta': []
    }
    while pointer_left < hotel_ids_len:
        offer_params['hotelIds'] = ','.join(
            hotel_ids[pointer_left:pointer_right]
        )
        response = amadeus.shopping.hotel_offers_search.get(**offer_params)
        if response.result.get('data') is not None:
            result['data'].extend(response.result.get('data'))
        result['meta'].append(response.result.get('meta'))
        pointer_left = pointer_right
        pointer_right += HOTEL_IDS_MAX
        if pointer_right >= hotel_ids_len:
            pointer_right = hotel_ids_len
    return result


@api_cache(
    'amadeus.shopping.hotel_offer_search(offer_id).get',
    ttl_hours=1
)
@safe_request()
def get_hotel_offer(offer_id: str, lang: str = None) -> dict:
    """
    Возвращает окончательную цену и условия бронирования.

    :param offer_id: Уникальный идентификатор предложения. Это может быть либо
        код бронирования GDS, либо предложение агрегатора с ограниченным сроком
        действия.
    :param lang: Язык описательных текстов.
        Примеры: 'FR', 'fr', 'fr-FR'. Если язык недоступен, текст будет
        возвращен на английском языке. Код языка ISO
        (https://www.iso.org/iso-639-language-codes.html).
    :return: Ответ Amadeus в виде Response.result.
    """
    if lang is not None:
        params = {'lang': lang}
        response = amadeus.shopping.hotel_offer_search(offer_id).get(**params)
    else:
        response = amadeus.shopping.hotel_offer_search(offer_id).get()
    return response.result


@safe_request()
def post_hotel_orders(
        guests: list[dict[str, str]],
        travel_agent: dict,
        room_associations: list[dict],
        payment: dict
) -> dict:
    """
    Создаёт бронирование отеля по предложению.

    :param guests: Список гостей. Каждый элемент — словарь с ключами:
        - 'tid': Идентификатор гостя (например, 1),
        - 'firstName': Имя,
        - 'lastName': Фамилия,
        - 'childAge': Если гость - ребенок, обязательно укажите его возраст (например, 5).
            В противном случае система будет считать его взрослым,
        - 'title': Обращение (MR / MRS / MS),
        - 'phone': Телефон в международном формате,
        - 'email': Email для подтверждения брони.

        Пример:
        [
            {
                'tid': 1,
                'firstName': 'BOB',
                'lastName': 'SMITH',
                'title': 'MR',
                'phone': '+33679278416',
                'email': 'bob.smith@email.com'
            }
        ]

    :param travel_agent: Информация об агенте, совершающем бронирование (может быть пустым).
        Пример:
        {
            'contact': {
                'email': 'bob.smith@email.com'
            }
        }

    :param room_associations: Список соответствий гостей и предложений.
        Каждый элемент должен содержать:
        - guestReferences: список словарей с ключом 'guestReference', совпадающим с 'tid' гостя,
        - hotelOfferId: идентификатор предложения отеля (получен из hotel_offers_search).

        Пример:
        [
            {
                'guestReferences': [{'guestReference': '1'}],
                'hotelOfferId': 'LJMD6D33CT'
            }
        ]

    :param payment: Платёжная информация.
        Обязательные поля:
        - method: способ оплаты (например, 'CREDIT_CARD'),
        - paymentCard: объект с полями:
            - paymentCardInfo:
                - vendorCode: Код платёжной системы (VI — VISA, MC — MasterCard),
                - cardNumber: Номер карты,
                - expiryDate: Срок действия (ГГГГ-ММ),
                - holderName: Имя держателя.

        Пример:
        {
            'method': 'CREDIT_CARD',
            'paymentCard': {
                'paymentCardInfo': {
                    'vendorCode': 'VI',
                    'cardNumber': '4111111111111111',
                    'expiryDate': '2026-08',
                    'holderName': 'BOB SMITH'
                }
            }
        }

    :return: Ответ Amadeus в виде Response.result — содержит статус,
        бронирование и идентификатор.
    """
    response = amadeus.booking.hotel_orders.post(
        guests=guests,
        travel_agent=travel_agent,
        room_associations=room_associations,
        payment=payment
    )
    return response.result


@api_cache(
    'amadeus.e_reputation.hotel_sentiments.get',
    ttl_hours=720)
@safe_request()
def get_hotel_sentiments(hotel_ids: list[str]) -> dict:
    """
    Возвращает рейтинги и оценки отелей на основе отзывов клиентов.

    :param hotel_ids: Список строк с идентификаторами отелей.
        Например:
            ['TELONMFS', 'PILONBHG', 'RTLONWAT']
    :return: Ответ Amadeus в виде Response.result.
    """
    HOTEL_IDS_MAX = 3
    pointer_left = 0
    hotel_ids_len = len(hotel_ids)
    pointer_right = HOTEL_IDS_MAX if HOTEL_IDS_MAX < hotel_ids_len \
        else hotel_ids_len
    result = {
        'data': [],
        'meta': [],
        'warnings': []
    }
    while pointer_left < hotel_ids_len:
        response = amadeus.e_reputation.hotel_sentiments.get(
            hotelIds=','.join(hotel_ids[pointer_left:pointer_right])
        )
        if response.result.get('data') is not None:
            result['data'].extend(response.result['data'])
        result['meta'].append(response.result['meta'])
        if response.result.get('warnings') is not None:
            result['warnings'].extend(response.result['warnings'])
        pointer_left = pointer_right
        pointer_right += HOTEL_IDS_MAX
        if pointer_right >= hotel_ids_len:
            pointer_right = hotel_ids_len
    return result


if __name__ == '__main__':
    create_tables()
    list_hotel_ids = ['TELONMFS', 'PILONBHG', 'RTLONWAT', 'RILONJBG',
                      'HOLON187', 'AELONCNP', 'MCLONGHM']
    ratings_hotels = get_hotel_sentiments(list_hotel_ids)
    if ratings_hotels.get('data'):
        for i_hotel in ratings_hotels['data']:
            print('\nРейтинг отеля')
            print(f'идентификатор отеля: {i_hotel['hotelId']}')
            print(f'общий рейтинг: {i_hotel['overallRating']}')
            print(f'количество отзывов: {i_hotel['numberOfReviews']}')
            print(f'количество оценок: {i_hotel['numberOfRatings']}')
            print('мнения')
            i_hotel_sentiments = i_hotel['sentiments']
            print(f'\tперсонал: {i_hotel_sentiments['staff']}')
            print(f'\tместоположение: {i_hotel_sentiments['location']}')
            print(f'\tсервис: {i_hotel_sentiments['service']}')
            print(f'\tудобства в номере: {i_hotel_sentiments['roomComforts']}')
            print(f'\tинтернет: {i_hotel_sentiments['internet']}')
            print(f'\tкачество сна: {i_hotel_sentiments['sleepQuality']}')
            print(f'\tсоотношение цены и качества: {i_hotel_sentiments['valueForMoney']}')
            print(f'\tоборудование: {i_hotel_sentiments['facilities']}')
            print(f'\tорганизация питания: {i_hotel_sentiments['catering']}')
            print(f'\tдостопримечательности: {i_hotel_sentiments['pointsOfInterest']}')
    if ratings_hotels.get('warnings'):
        print('\nПредупреждения')
        for i_warning in ratings_hotels['warnings']:
            print(f'Код: {i_warning['code']}')
            print(f'Заголовок: {i_warning['title']}')
            print(f'Источник')
            i_warning_source = i_warning['source']
            print(f'\tпараметр: {i_warning_source['parameter']}')
            print(f'\tуказатель: {i_warning_source['pointer']}')
            print(f'Подробности: {i_warning['detail']}')

    key_city_1 = 'London'
    code_country = 'GB'
    print(f'\nКлючевое слово для поиска города: {key_city_1}')
    print('Результат поиска:')
    cities = get_cities(
        keyword=key_city_1,
        country_code=code_country,
        max_cities=10,
        include='AIRPORTS'
    )

    if cities.get('data') is not None:
        for city in cities['data']:
            print(city)
        print(f'Список отелей в городе {cities['data'][0]['name']}')
        hotels_by_city = get_hotels_by_city(
            city_code=cities['data'][0]['iataCode'],
            radius=5,
            radius_unit='KM',
            # amenities=['FITNESS_CENTER', 'SWIMMING_POOL'],
            ratings=[1, 3, 4, 5],
            hotel_source='ALL'
        )

        if hotels_by_city.get('data'):
            for hotel in hotels_by_city['data']:
                print(hotel)
            hotel_Ids = [hotel['hotelId'] for hotel in hotels_by_city['data']]
            print('Информация об отелях')
            hotels_info = get_hotels_by_hotels(hotel_Ids)
            for hotel in hotels_info['data']:
                print(hotel)

            hotel_offers = get_hotel_offers_search(
                hotel_ids=hotel_Ids,
                guest_adults=2,
                check_in_date='2026-01-19',
                check_out_date='2026-01-25',
                lang='RU'
            )

            for offer in hotel_offers['data']:
                if offer['available']:
                    print(f'\nПредложение отеля ', end='')
                    print(offer['hotel']['name'])
                    print(f'идентификатор отеля: {offer['hotel']['hotelId']}')
                    print(f'широта: {offer['hotel']['latitude']}')
                    print(f'долгота: {offer['hotel']['longitude']}')
                    for elem in offer['offers']:
                        print()
                        print(f'Идентификатор предложения: {elem['id']}')
                        print(f'Дата заезда: {elem['checkInDate']}')
                        print(f'Дата выезда: {elem['checkOutDate']}')
                        print('Комната:')
                        print(f'\tтип - {elem['room'].get('type', 'нет информации')}')
                        print(
                            f'\tкатегория - {elem['room']['typeEstimated'].get('category', 'нет информации')}'
                        )
                        print(f'\tкроватей - {elem['room']['typeEstimated'].get('beds', 'нет информации')}')
                        print(
                            f'\tтип кровати - {elem['room']['typeEstimated'].get('bedType', 'нет информации')}'
                        )
                        print(f'Описание: {elem['room']['description']['text']}')
                        print(f'Цена:')
                        print(f'\tвалюта - {elem['price'].get('currency', 'нет информации')}')
                        print(f'\tбазовая - {elem['price'].get('base', 'нет информации')}')
                        print(f'\tобщая - {elem['price'].get('total', 'нет информации')}')
                    hotel_Offer_Id = offer['offers'][0]['id']
                    print(f'Подтверждаем цену и условия по предложению {hotel_Offer_Id}')
                    hotel_offer = get_hotel_offer(
                        offer_id=hotel_Offer_Id,
                        lang='RU'
                    )
                    print(hotel_offer)

                    adults = [
                        {
                            'tid': 1,
                            'title': 'MR',
                            'firstName': 'BOB',
                            'lastName': 'SMITH',
                            'phone': '+33679278416',
                            'email': 'bob.smith@email.com'
                        },
                        {
                            'tid': 2,
                            'title': 'MS',
                            'firstName': 'EVA',
                            'lastName': 'SMITH',
                            'phone': '+33679278416',
                            'email': 'eva.smith@email.com'
                        }
                    ]
                    agent = {
                        'contact': {
                            'email': 'bob.smith@email.com'
                        }
                    }
                    associations = [
                        {
                            'guestReferences': [
                                {
                                    'guestReference': '1'
                                },
                                {
                                    'guestReference': '2'
                                }
                            ],
                            'hotelOfferId': hotel_Offer_Id
                        }
                    ]
                    pay = {
                        'method': 'CREDIT_CARD',
                        'paymentCard': {
                            'paymentCardInfo': {
                                'vendorCode': 'VI',
                                'cardNumber': '4111111111111111',
                                'expiryDate': '2026-12',
                                'holderName': 'BOB SMITH'
                            }
                        }
                    }
                    print('Бронируем номер')
                    hotel_orders = post_hotel_orders(
                        guests=adults,
                        travel_agent=agent,
                        room_associations=associations,
                        payment=pay
                    )
                    if hotel_orders.get('data') is not None:
                        print(hotel_orders['data'])
                        print('Статус бронирования: ', end='')
                        for hotel_booking in hotel_orders['data']['hotelBookings']:
                            print(hotel_booking['bookingStatus'])

    elif cities.get('warnings') is not None:
        print(cities['warnings'])

    key_city_2 = 'Par'
    print(f'\nКлючевое слово для поиска города: {key_city_2}')
    print('Результат поиска')
    response_locations = get_locations(
        keyword=key_city_2,
        subtype='CITY',
        pages_offset=0,
        pages_limit=50
    )

    if isinstance(response_locations, dict):
        if response_locations.get('errors') is None:
            print(f'Ошибка: {response_locations['errors']}')
    else:
        num_page = 0
        err_num = 0
        while response_locations is not None:
            num_page += 1
            print(f'Страница {num_page}')
            for city in response_locations.data:
                print(city)
            err_count = 0
            try:
                response_locations = amadeus.next(response_locations)
            except ResponseError as exc:
                err_count += 1
                if err_count == 3:
                    print(exc)
                    break
