from datetime import datetime
from peewee import (SqliteDatabase, Model, CharField, IntegerField,
                    ForeignKeyField, IntegrityError,
                    DateTimeField, TextField, FloatField)
import json

db = SqliteDatabase('data_history.db')


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    user_id = IntegerField(unique=True)
    user_name = CharField()


class Request(BaseModel):
    user = ForeignKeyField(User, backref='requests', on_delete='CASCADE')
    command = CharField()
    city = CharField()
    city_code = CharField()
    check_in = CharField()
    check_out = CharField()
    price_range = CharField(null=True)
    created_at = DateTimeField(default=datetime.now)
    raw_response = TextField()

    def set_response_data(self, data: dict):
        """Сериализуем данные в строку"""
        self.raw_response = json.dumps(data, ensure_ascii=False)

    def get_response_data(self) -> dict:
        """Десериализуем JSON-строку"""
        return json.loads(self.raw_response) if self.raw_response else {}


class Hotel(BaseModel):
    request = ForeignKeyField(Request, backref='hotels')
    name = CharField()
    url = TextField()
    description = TextField()
    price = CharField()
    photos = TextField()
    latitude = FloatField()
    longitude = FloatField()

    def set_photos(self, photo_urls: list):
        ...

    def get_photos(self) -> list:
        ...

    def __str__(self):
        return f'{self.request}. '

def create_models():
    db.create_tables(BaseModel.__subclasses__())

if __name__ == '__main__':
    create_models()
    try:
        User.create(
            user_id=12345,
            user_name='Петя',
        )
        print(f'Пользователь Петя добавлен в базу.')
    except IntegrityError:
        print(f'Пользователь Петя уже есть в базе.')
