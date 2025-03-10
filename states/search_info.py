from telebot.handler_backends import State, StatesGroup


class States(StatesGroup):
    start = State()
    city = State()
    stay = State()
