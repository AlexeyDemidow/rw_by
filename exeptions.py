import httpx


class ParserError(Exception):
    """Базовая ошибка парсера."""


class FetchError(ParserError):
    """Не удалось получить страницу."""


class ParseError(ParserError):
    """Не удалось разобрать данные."""


RETRYABLE = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
)