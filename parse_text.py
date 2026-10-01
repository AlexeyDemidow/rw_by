import re


RE_HEADER = re.compile(
    r'(?P<train_type>[А-Яа-я\s\-]+?класса)\s+'
    r'(?P<train_number>\d+[А-Яа-я]?)\s+'
    r'(?P<from_station>.+?)\s+—\s+'
    r'(?P<to_station>.+?)\s+Маршрут\s+'
)
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
        price = float(m.group('price').replace(',', '.'))
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
        raise ValueError(f"Не распознана шапка: {block[:80]}...")
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
