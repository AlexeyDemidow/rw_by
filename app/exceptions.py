import httpx


class ParserError(Exception):
    """Базовая ошибка парсера."""


class FetchError(ParserError):
    """Не удалось получить страницу."""
    def __init__(self, msg: str, status_code: int | None = None):
        super().__init__(msg)
        self.status_code = status_code


class ParseError(ParserError):
    """Не удалось разобрать данные."""


RETRYABLE = (httpx.TransportError, httpx.HTTPStatusError)
