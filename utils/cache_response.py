import hashlib
import json
import random
from datetime import datetime, timedelta
from functools import wraps

from database.data_storage import APICache


def get_cached_response(end_point: str, request_hash: str) -> dict | None:
    """
    Возвращает из базы данных кэшированный ответ API.

    :param end_point: Метка (namespace) кэша, идентифицирующая группу записей.
    :param request_hash: Хэш запроса, вычисляемый на основе параметров функции,
        чтобы различать уникальные вызовы.
    :return: Словарь с данными, если запись найдена и срок её жизни не истёк;
        None, если записи нет или истёк срок её жизни.
    """
    try:
        cached = APICache.get(
            (APICache.end_point == end_point)
            & (APICache.request_hash == request_hash)
        )
        if cached.expires_at and cached.expires_at < datetime.now():
            cached.delete_instance()
            return None
        return json.loads(cached.value)
    except APICache.DoesNotExist:
        return None


def save_cache_response(
        end_point: str, request_hash: str, data: dict, ttl_hours: float = 6
):
    """
    Сохраняет ответ API в базе данных. Если запись
    с такими end_point и request_hash существует, то она перезаписывается,
    и обновляется срок её жизни.

    :param end_point: Метка (namespace) кэша, идентифицирующая группу записей.
    :param request_hash: Хэш запроса, определяющий конкретный вызов.
    :param data: Словарь с данными ответа, который будет сохранён.
    :param ttl_hours: Время жизни записи (в часах).
    """
    APICache.insert(
        end_point=end_point,
        request_hash=request_hash,
        value=json.dumps(data, ensure_ascii=False),
        expires_at=datetime.now() + timedelta(hours=ttl_hours)
    ).on_conflict(
        conflict_target=[APICache.end_point, APICache.request_hash],
        preserve=[APICache.value, APICache.created_at, APICache.expires_at]
    ).execute()


def clear_expired_cache():
    """
    Удаляет из базы данных записи кэша API, срок жизни которых истёк.
    """
    deleted_count = APICache.delete().where(
        (APICache.expires_at.is_null(False)) &
        (APICache.expires_at < datetime.now())
    ).execute()
    if deleted_count:
        print(f'[clear_expired_cache] Удалено '
              f'устаревших записей: {deleted_count}')


def api_cache(end_point: str, ttl_hours: float = 6):
    """
    Декоратор для кэширования результатов, возвращаемых функцией.

    :param end_point: Строковая метка для кэша (namespace).
        Используется как префикс ключа кэша, чтобы:
        * различать кэш разных функций;
        * облегчить просмотр и отладку кэша человеком;
        * не допустить коллизий ключей.
        Может быть любым уникальным описанием, например, именем функции
        или названием API-метода.
    :param ttl_hours: Время жизни записи (в часах).
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Удаление устаревших записей с вероятностью ~1% на каждый вызов.
            if random.random() < 0.01:
                clear_expired_cache()

            key_data = {
                'func_name': func.__name__,
                'args': args,
                'kwargs': kwargs
            }
            key_string = json.dumps(key_data, sort_keys=True, default=str)
            key = hashlib.sha256(key_string.encode()).hexdigest()

            cached = get_cached_response(end_point, key)
            if cached is not None:
                return cached

            response = func(*args, **kwargs)
            save_cache_response(end_point, key, response, ttl_hours=ttl_hours)
            return response

        return wrapper

    return decorator
