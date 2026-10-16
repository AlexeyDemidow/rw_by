from datetime import date

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tg_bot.service.subscriptions import INTERVAL_CHOICES, interval_label

MAIN_STATIONS = [
    'Минск',
    'Брест',
    'Гомель',
    'Могилев',
    'Гродно',
    'Витебск',
]

all_stations = [
    "Барановичи",
    "Бастуны",
    "Белоозёрск",
    "Беняконе",
    "Берёза",
    "Бобруйск",
    "Борисов",
    "Брест",
    "Бронная+Гора",
    "Буда-Кошелёвская",
    "Быхов",
    "Вилейка",
    "Витебск",
    "Волковыск",
    "Воропаево",
    "Ганцевичи",
    "Глубокое",
    "Гомель",
    "Погодино",
    "Городея",
    "Городок",
    "Воложин",
    "Гродно",
    "Гудогай",
    "Дзержинск",
    "Добруш",
    "Доманово",
    "Дрогичин",
    "Дубица",
    "Гутно",
    "Ельск",
    "Жабинка",
    "Житковичи",
    "Жлобин",
    "Жодино",
    "Залесье",
    "Беларусь",
    "Зельва",
    "Янов-Полесский",
    "Ивацевичи",
    "Калинковичи",
    "Клецк",
    "Климовичи",
    "Кобрин",
    "Колодищи",
    "Коммунары",
    "Красное+Знамя",
    "Уша",
    "Кричев-1",
    "Крулевщизна",
    "Крупки",
    "Лесная",
    "Лида",
    "Оранчицы",
    "Лиозно",
    "Гавья",
    "Лунинец",
    "Ляховичи",
    "Малорита",
    "Пуховичи",
    "Свислочь",
    "Микашевичи",
    "Минск",
    "Миоры",
    "Могилев",
    "Мозырь",
    "Молодечно",
    "Мосты",
    "Муляровка",
    "Новоельня",
    "Озерница",
    "Рабкор",
    "Олехновичи",
    "Орша",
    "Осиповичи",
    "Ошмяны",
    "Берёза-Картузская",
    "Радошковичи",
    "Пинск",
    "Берестовица",
    "Полоцк",
    "Поречье",
    "Поставы",
    "Приямино",
    "Речица",
    "Рогачев",
    "Рожанка",
    "Светлогорск-на-Березине",
    "Скидель",
    "Скрибовцы",
    "Слоним",
    "Слуцк",
    "Смолевичи",
    "Сморгонь",
    "Солигорск",
    "Старые+Дороги",
    "Столбцы",
    "Толочин",
    "Уречье",
    "Хойники",
    "Чаусы",
    "Шарковщизна",
    "Шклов",
    "Шумилино",
    "Юратишки",
]

STORES = [
    ("🤖Открыть приложение на Android", "https://play.google.com/store/apps/details?id=by.rw.client"),
    ("🍏Открыть приложение на iPhone", "https://apps.apple.com/us/app/id1489334970"),
    # ("📱 Huawei", "https://appgallery.cloud.huawei.com/ag/n/app/C103446265"),  # не работает, хотя на сайте ссылка есть
]

# Сортируем, оригинальные значения (с "+") сохраняем для парсера
ALL_STATIONS: list[str] = sorted(all_stations, key=lambda s: s.replace("+", " "))
# если название основной станции не найдётся в списке, это упадёт при старте, а не в чате
MAIN_IDX: list[int] = [ALL_STATIONS.index(n) for n in MAIN_STATIONS]
MAX_RESULTS = 10


def station_title(idx: int) -> str:
    return ALL_STATIONS[idx].replace("+", " ")


class StationCb(CallbackData, prefix="st"):
    action: str       # действия на клавиатуре
    step: str         # "from" | "to"
    value: int = 0    # номер страницы или индекс станции
    src: int = -1     # индекс станции отправления (для шага "to")


def _norm(s: str) -> str:
    return s.casefold().replace("ё", "е").replace("+", " ").strip()


def search_stations(query: str, exclude: int = -1) -> list[int]:
    """Индексы станций: сначала начинающиеся с запроса, потом содержащие его."""
    q = _norm(query)
    if len(q) < 2:
        return []
    starts, contains = [], []
    for i, name in enumerate(ALL_STATIONS):
        if i == exclude:
            continue
        n = _norm(name)
        if n.startswith(q):
            starts.append(i)
        elif q in n:
            contains.append(i)
    return starts + contains


def build_stations_inline(step: str = "from", src: int = -1) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i in MAIN_IDX:
        if i == src:          # на шаге "to" исключаем станцию отправления
            continue
        kb.button(
            text=station_title(i),
            callback_data=StationCb(action="pick", step=step, value=i, src=src),
        )
    kb.adjust(2)
    kb.row(
        InlineKeyboardButton(
            text="🔎 Найти другую станцию",
            callback_data=StationCb(action="search", step=step, src=src).pack(),
        )
    )
    return kb.as_markup()


def build_search_results_inline(indices: list[int], step: str, src: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i in indices:
        kb.button(
            text=station_title(i),
            callback_data=StationCb(action="pick", step=step, value=i, src=src),
        )
    kb.adjust(2)
    kb.row(
        InlineKeyboardButton(
            text="◀️ К основным станциям",
            callback_data=StationCb(action="back", step=step, src=src).pack(),
        )
    )
    return kb.as_markup()


def build_again_inline(order_url: str | None = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if order_url:
        kb.button(text="🌐 Купить на сайте", url=order_url)
    for text, url in STORES:
        kb.button(text=text, url=url)
    kb.button(text="🔁 Другой маршрут", callback_data="again:route")
    kb.button(text="📅 Другая дата и маршрут", callback_data="again:date")
    kb.adjust(1)
    return kb.as_markup()


def build_buy_inline(order_url: str | None = None) -> InlineKeyboardMarkup:
    """Кнопки покупки для рассылки"""
    kb = InlineKeyboardBuilder()
    if order_url:
        kb.button(text="🌐 Купить на сайте", url=order_url)
    for text, url in STORES:
        kb.button(text=text, url=url)
    kb.adjust(1)
    return kb.as_markup()


def build_route_actions_inline() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⚡ Показать сейчас", callback_data="route:now")
    kb.button(text="🔔 Следить за рейсом", callback_data="route:sub")

    kb.button(text="🔁 Другой маршрут", callback_data="again:route")
    kb.button(text="📅 Другая дата и маршрут", callback_data="again:date")

    kb.adjust(1)
    return kb.as_markup()


def build_interval_inline() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for minutes, title in INTERVAL_CHOICES:
        kb.button(text=title, callback_data=f"interval:{minutes}")
    kb.adjust(2)
    return kb.as_markup()


def build_train_pick_inline(trains: list[dict]) -> InlineKeyboardMarkup:
    """Список поездов маршрута для подписки + ввод номера вручную (пока что распроданных рейсов в выдаче нет)."""
    kb = InlineKeyboardBuilder()
    seen: set[str] = set()
    for t in trains:
        number = str(t.get("train_number", "")).strip()
        if not number or number in seen:
            continue
        seen.add(number)
        dep_time, arr_time = t.get("dep_time"), t.get("arr_time")
        times = f" · {dep_time} → {arr_time}" if dep_time and arr_time else ""
        kb.button(text=f"🚆 № {number}{times}", callback_data=f"trainpick:{number}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="✍️ Ввести номер вручную", callback_data="trainmanual"))
    return kb.as_markup()


def build_unsub_inline(items: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in items:
        d = date.fromisoformat(s["trip_date"]).strftime("%d.%m")
        title = (
            f"❌ {s['dep'].replace('+', ' ')} → {s['arr'].replace('+', ' ')}, {d}"
            f" · {interval_label(s['interval_min'])}"
        )
        kb.button(text=title, callback_data=f"unsub:{s['id']}")
    kb.adjust(1)
    return kb.as_markup()