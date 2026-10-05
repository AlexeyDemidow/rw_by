from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


mode_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Минск-Светлогорск 21.10.2026"),
            KeyboardButton(text="Светлогорск-Минск 25.10.2026"),
        ]
    ],
    resize_keyboard=True
)
