from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def gen_markup_pagin_hotels(
        name: str,
        offer_id: str,
        session_id: str,
        need_pagin: bool
) -> InlineKeyboardMarkup | None:
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(
            text=f'Принять предложение отеля {name}',
            callback_data=f'hotel_offer|{session_id}|{offer_id}'
        )
    )

    if need_pagin:
        keyboard.add(
            InlineKeyboardButton(
                text='◀️ предыдущий отель',
                callback_data=f'hotel_page|{session_id}|-1'
            ),
            InlineKeyboardButton(
                text='следующий отель ▶️',
                callback_data=f'hotel_page|{session_id}|1'
            ),
        )

    return keyboard


def gen_markup_pagin_photos(
        session_id: str
) -> InlineKeyboardMarkup | None:
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(
            text='◀️ предыдущая фотография',
            callback_data=f'photo_page|{session_id}|-1'
        ),
        InlineKeyboardButton(
            text='следующая фотография ▶️',
            callback_data=f'photo_page|{session_id}|1'
        )
    )
    return keyboard
