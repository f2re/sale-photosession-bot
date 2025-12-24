"""
Inline Keyboards
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict

def get_aspect_ratio_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting aspect ratio with visual representation"""
    builder = InlineKeyboardBuilder()

    # Simplified ratio names
    ratios = {
        "1:1": "⬜ 1:1   Квадрат (Instagram)",
        "9:16": "📱 9:16  Вертикально (Stories)",
        "16:9": "🖼️ 16:9  Горизонтально (сайт)",
        "4:5": "📄 4:5   Вертикально (карточка)"
    }

    for ratio, label in ratios.items():
        builder.button(text=label, callback_data=f"aspect_ratio:{ratio}")

    builder.button(text="◀️ Назад", callback_data="back_to_initial")
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
    builder.button(text="📦 Пакетная обработка", callback_data="batch_style_start")
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
    builder.button(text="📐 Изменить пропорции", callback_data=f"change_aspect_ratio:{preset_id}")
    builder.button(text="🗑 Удалить", callback_data=f"delete_style:{preset_id}")
    builder.button(text="🔙 Назад к списку", callback_data="manage_styles")
    builder.adjust(2, 1, 1)
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

def get_initial_photo_keyboard(aspect_ratio: str = "1:1") -> InlineKeyboardMarkup:
    """
    Keyboard shown immediately after photo upload and auto-analysis
    Simplified UX: confirm or change aspect ratio
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, создать 4 варианта", callback_data="confirm_auto_generation")
    builder.button(text="📐 Изменить пропорции", callback_data="change_aspect_ratio")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(1)
    return builder.as_markup()

def get_style_choice_keyboard(styles: List[Dict], product_name: str = "") -> InlineKeyboardMarkup:
    """
    Keyboard for choosing which styles to generate after seeing style previews
    """
    builder = InlineKeyboardBuilder()

    # Add buttons for each individual style (1-4)
    for i in range(len(styles)):
        builder.button(
            text=f"{i+1}️⃣ Только стиль №{i+1} (4 фото)",
            callback_data=f"generate_single_style:{i}"
        )

    # Separator
    builder.button(text="────────────────", callback_data="separator_ignore")
    builder.button(text="🎨 По одному каждого (4 фото)", callback_data="generate_mixed_styles")
    builder.button(text="────────────────", callback_data="separator_ignore")

    # Additional options
    builder.button(text="🔄 Создать другие стили", callback_data="styles:random")
    builder.button(text="📐 Изменить пропорции", callback_data="change_aspect_ratio")
    builder.button(text="❌ Отмена", callback_data="cancel_action")

    builder.adjust(1)
    return builder.as_markup()

def get_post_result_keyboard(has_balance: bool, can_continue_style: bool = False, balance: int = 0) -> InlineKeyboardMarkup:
    """
    Keyboard shown after successful generation
    Adapts based on context (single style vs mixed)
    """
    builder = InlineKeyboardBuilder()

    if has_balance:
        if can_continue_style:
            # User generated single style - offer to continue with same
            builder.button(text="➕ Ещё 4 вариации (тот же стиль)", callback_data="continue_same_style")
            builder.button(text="🎨 Попробовать другой стиль", callback_data="try_other_styles")
        else:
            # User generated mixed styles - offer to pick favorite
            builder.button(text="🎨 Выбрать любимый стиль", callback_data="pick_favorite_style")

        builder.button(text="────────────────", callback_data="separator_ignore")
        builder.button(text="🔄 Новое фото товара", callback_data="new_photoshoot")
        builder.button(text="📐 Изменить пропорции", callback_data="change_aspect_ratio")
        builder.button(text="💾 Сохранить этот стиль", callback_data="save_style")
        builder.button(text="────────────────", callback_data="separator_ignore")
        builder.button(text=f"📊 Мой баланс ({balance} генераций)", callback_data="check_balance")
        builder.button(text="💎 Купить генерации", callback_data="show_packages")
    else:
        # No balance
        builder.button(text="💎 Купить пакет", callback_data="show_packages")
        builder.button(text="📊 Мой баланс", callback_data="check_balance")

    builder.adjust(1)
    return builder.as_markup()

def get_favorite_style_keyboard(styles: List[Dict]) -> InlineKeyboardMarkup:
    """
    Keyboard for selecting favorite style after mixed generation
    """
    builder = InlineKeyboardBuilder()

    for i, style in enumerate(styles):
        style_name = style.get("style_name", f"Стиль {i+1}")
        builder.button(
            text=f"{i+1}️⃣ {style_name} - ещё 4 варианта",
            callback_data=f"favorite_style:{i}"
        )

    builder.button(text="────────────────", callback_data="separator_ignore")
    builder.button(text="◀️ Назад к результатам", callback_data="back_to_results")
    builder.button(text="🔄 Новое фото товара", callback_data="new_photoshoot")
    builder.button(text="🎨 Создать другие стили", callback_data="styles:random")
    builder.button(text="💾 Сохранить стиль", callback_data="save_style")

    builder.adjust(1)
    return builder.as_markup()
