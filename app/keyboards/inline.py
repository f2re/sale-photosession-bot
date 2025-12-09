"""
Inline Keyboards
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict

def get_aspect_ratio_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting aspect ratio with visual representation"""
    builder = InlineKeyboardBuilder()
    
    # Improved visual representation with actual format names
    ratios = {
        "1:1": "🔳 Квадрат 1:1 (Instagram пост)",
        "4:5": "📱 Вертикальный 4:5 (Instagram)",
        "9:16": "📲 Stories/Reels 9:16 (Instagram, TikTok)",
        "16:9": "📺 Широкий 16:9 (YouTube, ПК)",
        "4:3": "🖼️ Классический 4:3 (Фото)"
    }
    
    for ratio, label in ratios.items():
        builder.button(text=label, callback_data=f"aspect_ratio:{ratio}")
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()

def get_style_selection_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting style generation method"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎨 Проанализировать товар", callback_data="styles:analyze")
    builder.button(text="🎲 Случайные стили", callback_data="styles:random")
    builder.button(text="✍️ Задать свой стиль", callback_data="styles:custom")
    builder.button(text="📁 Мои сохранённые стили", callback_data="styles:saved")
    builder.button(text="🔙 Назад к форматам", callback_data="back_to_ratio")
    builder.adjust(1)
    return builder.as_markup()

def get_style_preview_keyboard(can_save: bool = True, product_name: str = None) -> InlineKeyboardMarkup:
    """Keyboard for style preview with option to edit product name"""
    builder = InlineKeyboardBuilder()
    
    # Add edit product name button if product name is provided
    if product_name:
        short_name = product_name[:25] + "..." if len(product_name) > 25 else product_name
        builder.button(
            text=f"✏️ Изменить: {short_name}",
            callback_data="edit_product_name"
        )
    
    builder.button(text="✅ Создать фотосессию", callback_data="confirm_generation")
    builder.button(text="🔄 Другие случайные стили", callback_data="styles:random")
    
    if can_save:
        builder.button(text="💾 Сохранить этот стиль", callback_data="save_style")
    
    builder.button(text="🔙 Назад к выбору", callback_data="back_to_style_selection")
    builder.adjust(1)
    return builder.as_markup()

def get_image_count_keyboard(max_count: int = 4) -> InlineKeyboardMarkup:
    """Keyboard for selecting number of images to generate"""
    builder = InlineKeyboardBuilder()
    
    count_labels = {
        1: "1️⃣",
        2: "2️⃣",
        3: "3️⃣",
        4: "4️⃣"
    }
    
    for i in range(1, min(max_count, 4) + 1):
        emoji = count_labels.get(i, str(i))
        plural = "изображение" if i == 1 else ("изображения" if i < 5 else "изображений")
        builder.button(
            text=f"{emoji} {i} {plural}",
            callback_data=f"image_count:{i}"
        )
    
    builder.button(text="❌ Отмена", callback_data="cancel_custom_style")
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()

def get_saved_styles_keyboard(styles: List[Dict]) -> InlineKeyboardMarkup:
    """Keyboard showing saved styles list"""
    builder = InlineKeyboardBuilder()
    
    for style in styles:
        text = f"{style['name']} ({style['aspect_ratio']})"
        builder.button(text=text, callback_data=f"apply_style:{style['id']}")
    
    builder.button(text="🔙 Назад к выбору", callback_data="back_to_style_selection")
    builder.adjust(1)
    return builder.as_markup()

def get_style_management_keyboard(preset_id: int) -> InlineKeyboardMarkup:
    """Keyboard for managing a specific style preset"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Переименовать", callback_data=f"rename_style:{preset_id}")
    builder.button(text="🗑 Удалить", callback_data=f"delete_style:{preset_id}")
    builder.button(text="🔙 Назад к списку", callback_data="manage_styles")
    builder.adjust(2, 1)
    return builder.as_markup()

def get_post_generation_keyboard(has_balance: bool) -> InlineKeyboardMarkup:
    """Keyboard shown after image generation"""
    builder = InlineKeyboardBuilder()
    
    if has_balance:
        builder.button(text="🎨 Создать ещё фотосессию", callback_data="new_photoshoot")
    else:
        builder.button(text="💳 Купить пакет", callback_data="buy_package")
    
    builder.button(text="💾 Сохранить этот стиль", callback_data="save_style")
    builder.button(text="📁 Мои стили", callback_data="manage_styles")
    builder.button(text="ℹ️ Мой профиль", callback_data="profile")
    builder.adjust(1)
    return builder.as_markup()

def get_confirm_save_style_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for confirming style save"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, сохранить", callback_data="confirm_save_style")
    builder.button(text="❌ Отмена", callback_data="cancel_save_style")
    builder.adjust(2)
    return builder.as_markup()

def get_buy_packages_keyboard() -> InlineKeyboardMarkup:
    """Keyboard to navigate to packages"""
    builder = InlineKeyboardBuilder()
    builder.button(text="💎 Перейти к пакетам", callback_data="show_packages")
    return builder.as_markup()
