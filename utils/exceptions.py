class HotelSearchError(Exception):
    """Базовая ошибка поиска отелей"""


class HotelNotFound(HotelSearchError):
    pass


class OffersNotFound(HotelSearchError):
    pass


class ExternalServiceUnavailable(HotelSearchError):
    def __init__(self, service: str):
        self.service = service
        super().__init__(f'Service unavailable: {service}')
