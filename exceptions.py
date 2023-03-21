class ApiResonseError(Exception):
    """Нет ответа от API."""
    pass


class StatusCodeError(Exception):
    """Получен код ответа, отличный от ожидаемого."""
    pass
