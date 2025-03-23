from telebot.handler_backends import State, StatesGroup


class States(StatesGroup):
    city = State()
    check_in = State()
    check_out = State()
    price_range = State()
    quest_rating = State()
    confirm = State()
