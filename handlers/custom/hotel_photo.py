from telebot.types import CallbackQuery

from loader import bot
from states.user_states import States
from utils.hotel import media_lock
from utils.hotel_photo import send_message_no_photo, send_hotel_photo
from utils.parsing import safe_parse_callback_index
from utils.user import get_user_and_chat_ids
from utils.validation import require_valid_session


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('photo_page'),
    state=States.display_hotels
)
@require_valid_session()
def photo_change(callback_query: CallbackQuery) -> None:
    user_id, chat_id = get_user_and_chat_ids(callback_query)
    step = safe_parse_callback_index(callback_query, 2, transform=int)
    bot.answer_callback_query(callback_query.id)

    with bot.retrieve_data(user_id, chat_id) as data:
        num_hotel = data['num_hotel']
        hotel_id = data['response']['hotels_keys_with_offer'][num_hotel]
        hotel = data['response']['hotels_with_offer'][hotel_id]
        num_photo = hotel['num_photo']
        num_photos = hotel['num_photos']
        next_photo = (num_photo + step) % num_photos
        photos = hotel.get('photos')
        hotel['num_photo'] = next_photo

    if not photos:
        send_message_no_photo(user_id, chat_id, hotel['name'])
        return
    try:
        with media_lock(bot, user_id, chat_id, 'photo_changing'):
            send_hotel_photo(user_id, chat_id, hotel)
    except RuntimeError:
        pass
