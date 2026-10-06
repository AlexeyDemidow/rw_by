from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_routes_inline() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Минск → Светлогорск", callback_data="route:minsk_svetlogorsk")
    kb.button(text="Светлогорск → Минск", callback_data="route:svetlogorsk_minsk")
    kb.adjust(1)
    return kb.as_markup()
