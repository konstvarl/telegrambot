city_codes = {
    "АНКОРИДЖ": "ANC",
    "АТЛАНТА": "ATL",
    "ОСТИН": "AUS",
    "БЕЛУ-ОРИЗОНТИ": "BHZ",
    "ПЕКИН": "BJS",
    "БАНГАЛОР": "BLR",
    "НЭШВИЛЛ": "BNA",
    "БОГОТА": "BOG",
    "МУМБАЙ": "BOM",
    "БОСТОН": "BOS",
    "БУФФАЛО": "BUF",
    "ЧИКАГО": "CHI",  # Примечание: CHI не является стандартным кодом IATA для Чикаго
    "КЛИВЛЕНД": "CLE",
    "ШАРЛОТТ": "CLT",
    "КОЛУМБУС": "CMH",
    "ЦИНЦИННАТИ": "CVG",
    "ДЕЙТОН": "DAY",
    "НЬЮ-ДЕЛИ": "DEL",
    "ДЕНВЕР": "DEN",
    "ДАЛЛАС/ФОРТ-УЭРТ": "DFW",
    "ДЕТРОЙТ": "DTT",  # Примечание: Обычно используются DTW для аэропорта Детройта
    "ФОРТ-ЛОДЕРДЕЙЛ": "FLL",
    "ФРАНКФУРТ-НА-МАЙНЕ": "FRA",
    "ГРИНВИЛЛ-СПАРТАНБУРГ": "GSP",
    "ХЬЮСТОН": "HOU",
    "ДЖЕКСОНВИЛЛ": "JAX",
    "ЛАС-ВЕГАС": "LAS",
    "ЛОС-АНДЖЕЛЕС": "LAX",
    "САНКТ-ПЕТЕРБУРГ": "LED",
    "ЛОНГ-БИЧ": "LGB",
    "ЛОНДОН": "LON",  # Примечание: Обычно используются LHR для Хитроу, LGW для Гатвика и STN для Станстеда
    "МАДРИД": "MAD",
    "МАЙАМИ": "MIA",
    "КАНЗАС-СИТИ": "MKC",  # Примечание: Обычно используются MCI для международного аэропорта Канзас-Сити
    "МИЛУОКИ": "MKE",
    "МОСКВА": "MOW",
    "МИННЕАПОЛИС-СЕНТ-ПОЛ": "MSP",
    "МЮНХЕН": "MUC",
    "НИЦЦА": "NCE",
    "НЬЮ-ЙОРК": "NYC",  # Примечание: Обычно используются JFK для Кеннеди, LGA для Ла-Гуардия и EWR для Ньюарка
    "ОКЛЕНД": "OAK",
    "ОКЛАХОМА-СИТИ": "OKC",
    "ОМАХА": "OMA",
    "ОНТАРИО": "ONT",
    "НОРФОЛК": "ORF",
    "ОРЛАНДО": "ORL",
    "ПАРИЖ": "PAR",  # Примечание: Обычно используются CDG для Шарля де Голля и ORY для Орли
    "УЭСТ-ПАЛМ-БИЧ": "PBI",
    "ПОРТЛЕНД": "PDX",
    "ФИЛАДЕЛЬФИЯ": "PHL",
    "ФЕНИКС": "PHX",
    "ПИТТСБУРГ": "PIT",
    "РОЛИ-ДАРЕМ": "RDU",
    "РИО-ДЕ-ЖАНЕЙРО": "RIO",  # Примечание: Обычно используются GIG для Галеан и SDU для Санто-Думонта
    "САН-ДИЕГО": "SAN",
    "САН-ПАУЛУ": "SAO",  # Примечание: Обычно используются GRU для Гуарульюса
    "САНТЬЯГО": "SCL",
    "СИЭТЛ": "SEA",
    "САН-ФРАНЦИСКО": "SFO",
    "ШАНХАЙ": "SHA",  # Примечание: Обычно используются PVG для Пудун и SHA для Хунцяо
    "САН-ХОСЕ": "SJC",
    "СОЛТ-ЛЕЙК-СИТИ": "SLC",
    "САНТА-АНА": "SNA",
    "САЛВАДОР": "SSA",
    "СЕНТ-ЛУИС": "STL",
    "СИДНЕЙ": "SYD",
    "ТАМПА": "TPA",
    "ВАШИНГТОН": "WAS",  # Примечание: Обычно используются IAD для Даллеса, DCA для Рейгана и BWI для Балтимора
    "ГАЛИФАКС": "YHZ",
    "КЕЛОУНА": "YLW",
    "МОНРЕАЛЬ": "YMQ",  # Примечание: Обычно используются YUL для Пьера Эллиота Трюдо
    "ОТТАВА": "YOW",
    "КВЕБЕК": "YQB",
    "РЕДЖАЙНА": "YQR",
    "ТОРОНТО": "YTO",  # Примечание: Обычно используются YYZ для Пирсона и YTZ для Билли Бишопа
    "ВАНКУВЕР": "YVR",
    "ВИННИПЕГ": "YWG",
    "САСКАТУН": "YXE",
    "КАЛГАРИ": "YYC",
    "ВИКТОРИЯ": "YYJ"
}

city_names = {
    "ANC": "Анкоридж",
    "ATL": "Атланта",
    "AUS": "Остин",
    "BHZ": "Белу-Оризонти",
    "BJS": "Пекин",
    "BLR": "Бангалор",
    "BNA": "Нэшвилл",
    "BOG": "Богота",
    "BOM": "Мумбаи",
    "BOS": "Бостон",
    "BUF": "Буффало",
    "CHI": "Чикаго",  # Примечание: CHI не является стандартным кодом IATA для Чикаго
    "CLE": "Кливленд",
    "CLT": "Шарлотт",
    "CMH": "Колумбус",
    "CVG": "Цинциннати",
    "DAY": "Дейтон",
    "DEL": "Нью-Дели",
    "DEN": "Денвер",
    "DFW": "Даллас/Форт-Уэрт",
    "DTT": "Детройт",  # Примечание: Обычно используются DTW для аэропорта Детройта
    "FLL": "Форт-Лодердейл",
    "FRA": "Франкфурт-на-Майне",
    "GSP": "Гринвилл-Спартанбург",
    "HOU": "Хьюстон",
    "JAX": "Джексонвилл",
    "LAS": "Лас-Вегас",
    "LAX": "Лос-Анджелес",
    "LED": "Санкт-Петербург",
    "LGB": "Лонг-Бич",
    "LON": "Лондон",  # Примечание: Обычно используются LHR для Хитроу, LGW для Гатвика и STN для Станстеда
    "MAD": "Мадрид",
    "MIA": "Майами",
    "MKC": "Канзас-Сити",  # Примечание: Обычно используются MCI для международного аэропорта Канзас-Сити
    "MKE": "Милуоки",
    "MOW": "Москва",
    "MSP": "Миннеаполис-Сент-Пол",
    "MUC": "Мюнхен",
    "NCE": "Ницца",
    "NYC": "Нью-Йорк",  # Примечание: Обычно используются JFK для Кеннеди, LGA для Ла-Гуардия и EWR для Ньюарка
    "OAK": "Окленд",
    "OKC": "Оклахома-Сити",
    "OMA": "Омаха",
    "ONT": "Онтарио",
    "ORF": "Норфолк",
    "ORL": "Орландо",
    "PAR": "Париж",  # Примечание: Обычно используются CDG для Шарля де Голля и ORY для Орли
    "PBI": "Уэст-Палм-Бич",
    "PDX": "Портленд",
    "PHL": "Филадельфия",
    "PHX": "Феникс",
    "PIT": "Питтсбург",
    "RDU": "Роли-Дарем",
    "RIO": "Рио-де-Жанейро",  # Примечание: Обычно используются GIG для Галеан и SDU для Санто-Думонта
    "SAN": "Сан-Диего",
    "SAO": "Сан-Паулу",  # Примечание: Обычно используются GRU для Гуарульюса
    "SCL": "Сантьяго",
    "SEA": "Сиэтл",
    "SFO": "Сан-Франциско",
    "SHA": "Шанхай",  # Примечание: Обычно используются PVG для Пудун и SHA для Хунцяо
    "SJC": "Сан-Хосе",
    "SLC": "Солт-Лейк-Сити",
    "SNA": "Санта-Ана",
    "SSA": "Салвадор",
    "STL": "Сент-Луис",
    "SYD": "Сидней",
    "TPA": "Тампа",
    "WAS": "Вашингтон",  # Примечание: Обычно используются IAD для Даллеса, DCA для Рейгана и BWI для Балтимора
    "YHZ": "Галифакс",
    "YLW": "Келоуна",
    "YMQ": "Монреаль",  # Примечание: Обычно используются YUL для Пьера Эллиота Трюдо
    "YOW": "Оттава",
    "YQB": "Квебек",
    "YQR": "Реджайна",
    "YTO": "Торонто",  # Примечание: Обычно используются YYZ для Пирсона и YTZ для Билли Бишопа
    "YVR": "Ванкувер",
    "YWG": "Виннипег",
    "YXE": "Саскатун",
    "YYC": "Калгари",
    "YYJ": "Виктория"
}
