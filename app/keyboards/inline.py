"""
Inline Keyboards
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict

def get_aspect_ratio_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    ratios = {
        "1:1": "□ Квадрат (Instagram)",
        "3:4": "◭ Вертикаль (Stories)",
        "4:3": "◭ Горизонталь",
        "16:9": "◬ Широкий (YouTube)",
        "9:16": "◮ Вертикальный (TikTok)"
    }
    for ratio, label in ratios.items():
        builder.button(text=label, callback_data=f"aspect_ratio:{ratio}")
    builder.adjust(1)
    return builder.as_markup()

def get_style_selection_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting style generation method"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎨 Проанализировать товар", callback_data="styles:analyze")
    builder.button(text="🎲 Случайные стили", callback_data="styles:random")
    builder.button(text="✍️ Задать свой стиль", callback_data="styles:custom")  # NEW
    builder.button(text="📁 Мои сохранённые стили", callback_data="styles:saved")
    builder.button(text="🔙 Назад", callback_data="back_to_ratio")
    builder.adjust(1)
    return builder.as_markup()

def get_style_preview_keyboard(can_save: bool = True, product_name: str = None) -> InlineKeyboardMarkup:
    """Keyboard for style preview with option to edit product name"""
    builder = InlineKeyboardBuilder()
    
    # Add edit product name button if product name is provided
    if product_name:
        builder.button(text=f"✏️ Изменить товар: {product_name[:20]}...", callback_data="edit_product_name")  # NEW
    
    builder.button(text="✅ Создать фотосессию", callback_data="confirm_generation")
    builder.button(text="🔄 Другие случайные стили", callback_data="styles:random")
    
    if can_save:
        builder.button(text="💾 Сохранить этот стиль", callback_data="save_style")
    
    builder.button(text="🔙 Назад", callback_data="back_to_style_selection")
    builder.adjust(1)
    return builder.as_markup()

def get_image_count_keyboard(max_count: int = 4) -> InlineKeyboardMarkup:
    """Keyboard for selecting number of images to generate (NEW)"""
    builder = InlineKeyboardBuilder()
    for i in range(1, max_count + 1):
        emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"][i-1] if i <= 4 else str(i)
        builder.button(text=f"{emoji} {i} изображений", callback_data=f"image_count:{i}")
    builder.button(text="❌ Отмена", callback_data="cancel_custom_style")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def get_saved_styles_keyboard(styles: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for style in styles:
        text = f"{style['name']} ({style['aspect_ratio']})"
        builder.button(text=text, callback_data=f"apply_style:{style['id']}")
    builder.button(text="🔙 Назад", callback_data="back_to_style_selection")
    builder.adjust(1)
    return builder.as_markup()

def get_style_management_keyboard(preset_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Переименовать", callback_data=f"rename_style:{preset_id}")
    builder.button(text="🗑 Удалить", callback_data=f"delete_style:{preset_id}")
    builder.button(text="🔙 Назад к списку", callback_data="manage_styles")
    builder.adjust(2, 1)
    return builder.as_markup()

def get_post_generation_keyboard(has_balance: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_balance:
        builder.button(text="🎨 Создать ещё фотосессию", callback_data="new_photoshoot")
    else:
        builder.button(text="💳 Купить пакет", callback_data="buy_package")
    
    # Allow saving the style used for this generation
    builder.button(text="💾 Сохранить этот стиль", callback_data="save_style")
    builder.button(text="📁 Мои стили", callback_data="manage_styles")
    builder.button(text="ℹ️ Мой профиль", callback_data="profile")
    builder.adjust(1)
    return builder.as_markup()

def get_confirm_save_style_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, сохранить", callback_data="confirm_save_style")
    builder.button(text="❌ Отмена", callback_data="cancel_save_style")
    builder.adjust(2)
    return builder.as_markup()

def get_buy_packages_keyboard() -> InlineKeyboardMarkup:
    """Alias for buy package"""
    builder = InlineKeyboardBuilder()
    builder.button(text="💎 Перейти к пакетам", callback_data="show_packages")
    return builder.as_markup()
