import re
from urllib.parse import quote_plus, urlparse

import requests

from utils.cache_response import api_cache

BAD_HOSTS = [
    'googleusercontent.com',
    'gstatic.com',
    'ssl.gstatic.com',
    'xx.bstatic.com',
    'encrypted-tbn0.gstatic.com',
    'pinimg.com',
    'pinterest',
    'fbcdn.net',
]


def normalize(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', text.lower())


def relevance_score(title: str, hotel: str, city: str) -> int:
    if not title:
        return 0

    score = 0

    for key_wrd in hotel.split():
        if key_wrd in title:
            score += 1

    for key_wrd in city.split():
        if key_wrd in title and key_wrd not in hotel:
            score += 1

    return score


def is_bad_host(url: str) -> bool:
    host = urlparse(url).netloc
    return any(bad in host for bad in BAD_HOSTS)


def is_url_alive(url: str) -> bool:
    try:
        resp = requests.head(url, timeout=3, allow_redirects=True)
        if resp.status_code == 200:
            ct = resp.headers.get('Content-Type', '')
            return ct.startswith('image/')
        return False
    except requests.RequestException:
        return False


def get_urls_photos_hotel_from(
        hotel_name: str,
        city: str,
        max_images: int,
        height_min: int,
        width_min: int,
        site: str = ''
) -> list[dict]:
    hotel_norm = normalize(hotel_name)
    city_norm = normalize(city)
    if city_norm in hotel_norm:
        query = hotel_norm
    else:
        query = f'{hotel_norm} {city_norm}'
    if site:
        query = f'{query} site:{site}'
    search_url = (
        f'https://duckduckgo.com/?q={quote_plus(query)}'
        f'&iax=images&ia=images'
    )
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            'AppleWebKit/537.36 (KHTML, like Gecko)'
            'Chrome/113.0.0.0 Safari/537.36'
        ),
        'Referer': 'https://duckduckgo.com',
    }
    session = requests.Session()
    session.headers.update(headers)
    # Получаем токен
    res = session.get(search_url)
    if 'vqd=' not in res.text:
        return []
    # Извлечение vqd ключа
    try:
        vqd = res.text.split('vqd="')[1].split('"')[0]
    except IndexError:
        return []
    # Поиск изображений
    api_url = (
        f'https://duckduckgo.com/i.js'
        f'?l=us-en&o=json&q={quote_plus(query)}'
        f'&vqd={vqd}&p=1'
    )
    res = session.get(api_url)
    if not res.ok or not res.text:
        return []
    try:
        data = res.json()
    except ValueError:
        return []

    candidates = []
    score_needful = len(hotel_norm.split())
    if city_norm not in hotel_norm:
        score_needful += 1

    for img in data.get('results', []):
        url = img.get('image')
        title = img.get('title', '')

        if not url or is_bad_host(url):
            continue

        height = img.get('height', 0)
        width = img.get('width', 0)
        if height < height_min or width < width_min:
            continue

        score = relevance_score(normalize(title), hotel_norm, city_norm)

        if score < score_needful:
            continue

        if not is_url_alive(url):
            continue

        candidates.append({'score': score, 'url': url, 'title': title})

    # Сортировка пока не нужна при текущей реализации релевантности,
    # т.к. score не может быть больше чем score_needful
    # и в candidates все score имеют одинаковое значение
    # candidates.sort(key=lambda x: x['score'], reverse=True)

    return candidates[:max_images]


@api_cache('hotel_photos_fallback', ttl_hours=720)
def get_urls_photos_hotel(
        hotel_name: str,
        city: str,
        max_images: int = 50,
        height_min: int = 400,
        width_min: int = 600
) -> list[dict]:
    photos = get_urls_photos_hotel_from(
        hotel_name,
        city,
        max_images,
        height_min,
        width_min,
    )
    if len(photos) > 0:
        return photos[:max_images]

    return []


if __name__ == '__main__':
    for elem_img in get_urls_photos_hotel(
            hotel_name='HOTEL PRINCE ALBERT LOUVRE',
            city='PARIS',
            max_images=50,
    ):
        print(elem_img)
