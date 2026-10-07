import logging
import re
from decimal import Decimal

from bs4 import BeautifulSoup

from backend.app.schemas import Train
from backend.app.exceptions import ParseError

log = logging.getLogger(__name__)

RE_HEADER = re.compile(
    r'(?P<train_type>[А-Яа-я\s\-]+?(?:класса|линии))\s+'
    r'(?P<train_number>\d+[А-Яа-я]?)\s+'
    r'(?P<from_station>.+?)\s+—\s+'
    r'(?P<to_station>.+?)\s+Маршрут\s+'
)
DURATION = r'\d+\s*(?:д|ч|мин)(?:\s+\d+\s*(?:ч|мин))*'

RE_TIMES = re.compile(
    r'(?P<dep_time>\d{2}:\d{2})\s+(?P<dep_station>.+?)\s+'
    r'(?P<arr_time>\d{2}:\d{2})\s+(?P<arr_station>.+?)\s+'
    r'(?P<duration>\d+\s*ч\s*\d+\s*мин)\s+'
)
RE_DAYS = re.compile(
    r'Дни курсирования:\s+(?P<days>.+?)\s+\d+\s*ч\s*\d+\s*мин\s+'
)
RE_CARRIAGE = re.compile(
    r'(?P<carriage_type>[А-Яа-я]+)\s+'
    r'(?P<options>(?:\d*\s*[\d,]+\s*BYN\s*)+)'
)
RE_OPTION = re.compile(r'(?:(?P<seats>\d+)\s+)?(?P<price>[\d,]+)\s*BYN')
BADGES = re.compile(r'\b(Самый недорогой|Самый быстрый)\b')


def parse_options(text: str) -> list[dict]:
    options, last_seats = [], None
    for m in RE_OPTION.finditer(text):
        seats = int(m.group('seats')) if m.group('seats') else last_seats
        price = Decimal(m.group('price').replace(',', '.'))
        options.append({'seats': seats, 'price': price})
        if m.group('seats'):
            last_seats = int(m.group('seats'))
    return options


def parse_train(block: str) -> dict:
    block = block.strip().replace('Выбрать места', '').strip()
    badges = BADGES.findall(block)
    block = BADGES.sub('', block).strip()

    m = RE_HEADER.search(block)
    if not m:
        raise ParseError(f"Не распознана шапка: {block[:80]}...")
    result = m.groupdict()
    result['badges'] = badges
    rest = block[m.end():]

    m = RE_TIMES.search(rest)
    if m:
        result.update(m.groupdict())
        rest = rest[m.end():]

    m = RE_DAYS.search(rest)
    if m:
        result['days'] = m.group('days').strip()
        rest = rest[m.end():]

    carriages = []
    for cm in RE_CARRIAGE.finditer(rest):
        carriages.append({
            'type': cm.group('carriage_type'),
            'options': parse_options(cm.group('options')),
        })
    result['carriages'] = carriages
    return result


def parse_trains(html: str) -> list[Train]:
    soup = BeautifulSoup(html, "html.parser")
    rows = [
        r.get_text(" ", strip=True)
        for r in soup.select("div.sch-table__row-wrap")
    ]
    candidates = [t for t in rows if "Выбрать места" in t]

    trains, failed = [], 0
    for text in candidates:
        try:
            trains.append(Train.model_validate(parse_train(text)))
        except (ParseError, ValueError) as e:   # ValidationError наследует ValueError
            failed += 1
            log.warning("Не удалось разобрать строку: %s", e)

    if candidates and not trains:
        raise ParseError(f"Не разобрано ни одной из {failed} строк, вёрстка изменилась?")
    return trains
