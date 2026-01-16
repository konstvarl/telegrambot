import json
import os
from datetime import datetime, date
from typing import Any, Dict

from peewee import (SqliteDatabase, Model, CharField, IntegerField,
                    ForeignKeyField, DateTimeField, TextField, FloatField, DateField)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data_history.db')
db = SqliteDatabase(DB_PATH)


class BaseModel(Model):
    class Meta:
        database = db


class APICache(BaseModel):
    end_point = CharField()
    request_hash = CharField()
    value = TextField()
    created_at = DateTimeField(default=datetime.now)
    expires_at = DateTimeField(null=True)

    class Meta:
        indexes = [
            (('end_point', 'request_hash'), True)
        ]


class User(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField(max_length=255)


class Request(BaseModel):
    user = ForeignKeyField(User, backref='requests', on_delete='CASCADE')
    command = CharField()
    template_find_city = CharField()
    city = CharField()
    country = CharField()
    currency_code = CharField()
    currency_name = CharField()
    check_in_date = DateField()
    check_out_date = DateField()
    price_range = CharField(null=True)
    radius = IntegerField()
    created_at = DateTimeField(default=datetime.now)


class Hotel(BaseModel):
    EMPTY_PHOTOS = '[]'
    hotel_id = CharField()
    request = ForeignKeyField(Request, backref='hotels')
    name = CharField()
    description = TextField(null=True)
    price = FloatField(null=True)
    latitude = FloatField()
    longitude = FloatField()
    rating = FloatField(null=True)
    postal_code = CharField(null=True)
    distance = FloatField()
    unit = CharField()
    hotel_sentiments = FloatField(null=True)
    board_type = CharField()
    lines = TextField()
    photos = TextField(default=EMPTY_PHOTOS)

    class Meta:
        indexes = (
            (('hotel_id', 'request'), True),
        )

    def set_photos(self, photo_urls: list[str]) -> None:
        """
        Сохраняет фото, если они есть и если у отеля ещё не сохранены.

        :param photo_urls: Список ссылок на фотографии отеля.
        :return: None
        """
        if photo_urls and self.photos == self.EMPTY_PHOTOS:
            self.photos = json.dumps(photo_urls, ensure_ascii=False)
            self.save(only=[Hotel.photos])

    def get_photos(self) -> list[str]:
        try:
            return json.loads(self.photos or '[]')
        except (json.JSONDecodeError, TypeError):
            return []

    def get_lines(self) -> list[str]:
        try:
            return json.loads(self.lines or '[]')
        except (json.JSONDecodeError, TypeError):
            return []


def create_tables():
    with db:
        db.create_tables([APICache, User, Request, Hotel], safe=True)


def add_request_to_history(
        user_id: int,
        user_name: str,
        request_data: dict[str, Any],
        hotels_data: dict[str, dict[str, Any]]
):
    """
    Сохраняет запрос пользователя и найденные отели в историю.

    :param user_id: Идентификатор пользователя.
    :param user_name: Имя пользователя.
    :param request_data: Словарь с данными запроса.
    :param hotels_data: Словарь с данными отелей.
    """
    user, created = User.get_or_create(
        id=user_id, defaults={'name': user_name}
    )
    if not created and user.name != user_name:
        user.name = user_name
        user.save()

    request_record = Request.create(
        user=user,
        command=request_data['command'],
        template_find_city=request_data['template_find_city'],
        city=request_data['city']['name'],
        country=request_data['country'],
        currency_code=request_data['currency']['code'],
        currency_name=request_data['currency']['name'],
        check_in_date=request_data['date']['check_in'],
        check_out_date=request_data['date']['check_out'],
        price_range=request_data['range_prices'],
        radius=request_data['radius'],
    )

    from loader import bot
    with bot.retrieve_data(user_id) as data:
        data['request_record'] = request_record

    hotels_to_create = []
    for hotel_id, hotel in hotels_data.items():
        hotels_to_create.append(
            Hotel(
                hotel_id=hotel_id,
                request=request_record,
                name=hotel['name'],
                description=hotel.get('offer', {}).get('room', {}) \
                    .get('description', {}).get('text', 'не указано'),
                price=hotel['offer']['price']['total'],
                latitude=hotel['geoCode']['latitude'],
                longitude=hotel['geoCode']['longitude'],
                rating=hotel['rating'],
                postal_code=hotel['address'].get('postalCode', 'не указано'),
                distance=hotel['distance']['value'],
                unit=hotel['distance']['unit'],
                hotel_sentiments=hotel.get('sentiments', {}).get('overallRating', None),
                board_type=hotel['offer'].get('boardType', 'не указано'),
                photos=json.dumps(hotel.get('photos', []), ensure_ascii=False),
                lines=json.dumps(hotel['address']['lines'], ensure_ascii=False)
            )
        )
    if hotels_to_create:
        Hotel.bulk_create(hotels_to_create, batch_size=50)


def get_user_history(user_id: int, search_date: date | None = None) -> list[Dict]:
    """
    Возвращает историю запросов пользователя с данными отелей.
    Можно указать дату для фильтрации (по полю created_at).

    :param user_id: Идентификатор пользователя.
    :param search_date: Датаб за которую нужно получить историю.
    :return: Список словарей с запросами и вложенным списком отелей.
    """
    user = User.get_or_none(User.id == user_id)
    if not user:
        return []

    query = Request.select().where(Request.user == user)

    if search_date:
        start_dt = datetime.combine(search_date, datetime.min.time())
        end_dt = datetime.combine(search_date, datetime.max.time())
        query = query.where((Request.created_at >= start_dt) &
                            (Request.created_at <= end_dt))

    query = query.order_by(Request.created_at.desc())

    history = []
    for request in query:
        hotels = [{
            'name': h.name,
            'description': h.description,
            'price': h.price,
            'latitude': h.latitude,
            'longitude': h.longitude,
            'rating': h.rating,
            'postal_code': h.postal_code,
            'distance': h.distance,
            'unit': h.unit,
            'hotel_sentiments': h.hotel_sentiments,
            'boardType': h.board_type,
            'lines': h.get_lines(),
            'photos': h.get_photos(),
        } for h in request.hotels
        ]
        history.append({
            'command': request.command,
            'template_find_city': request.template_find_city,
            'city': request.city,
            'country': request.country,
            'currency_code': request.currency_code,
            'currency_name': request.currency_name,
            'check_in_date': request.check_in_date,
            'check_out_date': request.check_out_date,
            'price_range': request.price_range,
            'radius': request.radius,
            'created_at': request.created_at.strftime('%Y-%m-%d %H:%M'),
            'hotels': hotels,
        })
    return history
