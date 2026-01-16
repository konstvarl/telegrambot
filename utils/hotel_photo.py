from config_data.config import PHOTOS
from keyboards.inline.pagination import gen_markup_pagin_photos
from loader import bot
from utils.telegram_safe import safe_edit_media


def send_hotel_photo(user_id, chat_id, hotel: dict) -> None:
    num_photo = hotel['num_photo']
    num_photos = hotel['num_photos']

    with bot.retrieve_data(user_id, chat_id) as data:
        message_photo_id = data['message_photo_id']
        session_id = data['session_id']

    photo = hotel['photos'][num_photo]
    photo_caption = (f'Отель {hotel['name']}\n'
                     f'Фотография {num_photo + 1} из {num_photos}\n'
                     f'Название: {photo['title']}')

    new_message_photo_id = safe_edit_media(
        photo['url'],
        photo_caption,
        chat_id,
        message_photo_id,
        markup=gen_markup_pagin_photos(session_id) if num_photos > 1 else None
    )

    if new_message_photo_id is not None:
        with bot.retrieve_data(user_id, chat_id) as data:
            data.update({
                'message_photo_id': new_message_photo_id,
            })


def send_message_no_photo(user_id: int, chat_id: int, hotel_name: str) -> None:
    with bot.retrieve_data(user_id, chat_id) as data:
        message_photo_id = data.get('message_photo_id')

    message_photo_id = safe_edit_media(
        PHOTOS['not_found'],
        f'Фотографии отеля {hotel_name}\nне найдены',
        chat_id,
        message_photo_id
    )

    with bot.retrieve_data(user_id, chat_id) as data:
        data.update({
            'message_photo_id': message_photo_id,
        })
