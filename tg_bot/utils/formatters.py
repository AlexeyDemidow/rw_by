from html import escape


def _format_carriages(carriages: list[dict]) -> str:
    """Формирует строку с типами вагонов, ценами и местами."""
    if not carriages:
        return ""

    parts = []
    for car in carriages:
        ctype = escape(str(car.get("type", "—")))
        options = car.get("options", [])
        if not options:
            parts.append(ctype)
            continue

        opts = []
        for opt in options:
            price = opt.get("price")
            seats = opt.get("seats")
            opts.append(f"{price} BYN ({seats} мест)")
        parts.append(f"{ctype}: " + ", ".join(opts))

    return " | ".join(parts)


def format_trains(response: dict) -> str:
    """Превращает ответ бэкенда в читаемый текст для Telegram."""
    trains = response.get("trains", []) if isinstance(response, dict) else []

    if not trains:
        return "🚆 Рейсов не найдено."

    header = f"🚆 Найдено рейсов: {len(trains)}\n"
    blocks = []

    for t in trains:
        number = escape(str(t.get("train_number", "—")))
        train_type = escape(str(t.get("train_type", "")))
        dep_station = escape(str(t.get("dep_station", "—")))
        arr_station = escape(str(t.get("arr_station", "—")))
        dep_time = escape(str(t.get("dep_time", "—")))
        arr_time = escape(str(t.get("arr_time", "—")))
        duration = escape(str(t.get("duration", "—")))
        days = escape(str(t.get("days", "")))
        badges = t.get("badges", [])

        title = f"🚆 <b>№ {number}</b>"
        if badges:
            safe_badges = ", ".join(escape(str(b)) for b in badges)
            title += f"  <i>({safe_badges})</i>"

        lines = [
            title,
            f"   {dep_station} → {arr_station}",
            f"   🕐 {dep_time} → {arr_time}  ({duration})",
        ]

        if train_type:
            lines.append(f"   🚉 {train_type}")
        if days:
            lines.append(f"   📅 {days}")

        carriages = _format_carriages(t.get("carriages", []))
        if carriages:
            lines.append(f"   💺 {carriages}")

        blocks.append("\n".join(lines))

    text = header + "\n" + "\n\n".join(blocks)

    order_url = response.get("order_url") if isinstance(response, dict) else None
    if order_url:
        safe_url = escape(order_url, quote=True)
        text += f'\n\n🎫 <a href="{safe_url}">Купить билет на pass.rw.by</a>'

    return text


def split_message(text: str, limit: int = 3500) -> list[str]:
    """Режет текст на куски по limit символов"""
    if len(text) <= limit:
        return [text]

    parts = []
    current = ""
    for block in text.split("\n\n"):
        candidate = (current + "\n\n" + block) if current else block
        if len(candidate) > limit:
            if current:
                parts.append(current)
            while len(block) > limit:
                parts.append(block[:limit])
                block = block[limit:]
            current = block
        else:
            current = candidate
    if current:
        parts.append(current)

    return parts
