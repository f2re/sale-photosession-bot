"""
Reply Keyboards
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📸 Создать фотосессию")],
            [KeyboardButton(text="💎 Купить пакет"), KeyboardButton(text="📊 Баланс")],
            [KeyboardButton(text="📁 Мои стили"), KeyboardButton(text="👥 Рефералы")],
            [KeyboardButton(text="ℹ️ Инфо"), KeyboardButton(text="💬 Поддержка")]
        ],
        resize_keyboard=True
    )
    return keyboard
