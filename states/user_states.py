from telebot.states import State, StatesGroup


class States(StatesGroup):
    city_search = State()
    city_confirm = State()
    check_in = State()
    check_out = State()
    price_range = State()
    sorting_criteria = State()
    search_hotels = State()
    display_hotels = State()
    radius = State()
    date_search = State()
