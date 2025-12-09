"""
Custom Styles Handlers
Handles custom style creation and product name editing
"""
import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.states import PhotoshootStates
from app.keyboards.inline import (
    get_style_selection_keyboard,
    get_style_preview_keyboard,
    get_image_count_keyboard
)
from app.services.prompt_generator import PromptGenerator

logger = logging.getLogger(__name__)
router = Router()

prompt_generator = PromptGenerator()

def _format_styles_preview(styles):
    """Format styles for preview"""
    return "\n\n".join([f"{i+1}. <b>{s['style_name']}</b>" for i, s in enumerate(styles)])


# ==================== CUSTOM STYLE CREATION ====================

@router.callback_query(F.data == "styles:custom")
async def custom_style_start(callback: CallbackQuery, state: FSMContext):
    """Start custom style creation"""
    await callback.answer()
    await callback.message.edit_text(
        "✍️ <b>Создание кастомного стиля</b>\n\n"
        "Шаг 1 из 3: Опишите ваш товар\n\n"
        "📝 <b>Примеры:</b>\n"
        "• iPhone 15 Pro Max\n"
        "• Деревянная разделочная доска\n"
        "• Парфюм Chanel N°5\n"
        "• Керамическая ваза ручной работы\n\n"
        "✏️ Введите название товара:\n\n"
        "Для отмены отправьте /cancel",
        parse_mode="HTML"
    )
    await state.set_state(PhotoshootStates.custom_style_product)


@router.message(StateFilter(PhotoshootStates.custom_style_product), F.text == "/cancel")
async def cancel_custom_style_product(message: Message, state: FSMContext):
    """Cancel custom style creation from product input stage"""
    data = await state.get_data()
    aspect_ratio = data.get("aspect_ratio", "1:1")

    await state.set_state(PhotoshootStates.selecting_styles_method)
    await message.answer(
        f"❌ Создание кастомного стиля отменено.\n\n"
        f"✅ Пропорции: <b>{aspect_ratio}</b>\n"
        f"Выберите другой метод:",
        parse_mode="HTML",
        reply_markup=get_style_selection_keyboard()
    )


@router.message(StateFilter(PhotoshootStates.custom_style_product))
async def custom_style_product_input(message: Message, state: FSMContext):
    """Handle custom product name input"""
    product_name = message.text.strip()
    
    if len(product_name) < 3:
        await message.answer("⚠️ Название слишком короткое (минимум 3 символа). Попробуйте ещё раз:")
        return
    
    if len(product_name) > 100:
        await message.answer("⚠️ Название слишком длинное (максимум 100 символов). Попробуйте короче:")
        return
    
    await state.update_data(custom_product_name=product_name)
    
    await message.answer(
        f"✅ Товар: <b>{product_name}</b>\n\n"
        "Шаг 2 из 3: Опишите желаемый стиль\n\n"
        "🎨 <b>Примеры:</b>\n"
        "• Минималистичный белый фон, мягкое освещение\n"
        "• Тёмный драматичный фон, контрастный свет\n"
        "• Природный стиль, деревянная поверхность, утренний свет\n"
        "• Неоновые огни, киберпанк, футуристично\n"
        "• Роскошный стиль, золотые аксессуары, блеск\n\n"
        "✏️ Введите описание стиля:\n\n"
        "Для отмены отправьте /cancel",
        parse_mode="HTML"
    )
    await state.set_state(PhotoshootStates.custom_style_description)


@router.message(StateFilter(PhotoshootStates.custom_style_description), F.text == "/cancel")
async def cancel_custom_style_description(message: Message, state: FSMContext):
    """Cancel custom style creation from description input stage"""
    data = await state.get_data()
    aspect_ratio = data.get("aspect_ratio", "1:1")

    await state.set_state(PhotoshootStates.selecting_styles_method)
    await message.answer(
        f"❌ Создание кастомного стиля отменено.\n\n"
        f"✅ Пропорции: <b>{aspect_ratio}</b>\n"
        f"Выберите другой метод:",
        parse_mode="HTML",
        reply_markup=get_style_selection_keyboard()
    )


@router.message(StateFilter(PhotoshootStates.custom_style_description))
async def custom_style_description_input(message: Message, state: FSMContext):
    """Handle custom style description input"""
    style_description = message.text.strip()
    
    if len(style_description) < 10:
        await message.answer("⚠️ Описание слишком короткое (минимум 10 символов). Попробуйте подробнее:")
        return
    
    if len(style_description) > 300:
        await message.answer("⚠️ Описание слишком длинное (максимум 300 символов). Сократите:")
        return
    
    await state.update_data(custom_style_description=style_description)
    
    await message.answer(
        "Шаг 3 из 3: Выберите количество изображений для генерации:",
        reply_markup=get_image_count_keyboard(max_count=4)
    )
    await state.set_state(PhotoshootStates.custom_style_count)


@router.callback_query(F.data.startswith("image_count:"))
async def custom_style_count_select(callback: CallbackQuery, state: FSMContext):
    """Handle image count selection and generate custom styles"""
    count = int(callback.data.split(":")[1])
    await callback.answer()
    
    data = await state.get_data()
    product_name = data["custom_product_name"]
    style_desc = data["custom_style_description"]
    aspect_ratio = data.get("aspect_ratio", "1:1")
    
    logger.info(f"Generating {count} custom styles for product '{product_name}' with style '{style_desc[:50]}...'")
    
    msg = await callback.message.edit_text(
        f"🎨 Генерирую {count} стилей на основе вашего описания...\n\n"
        f"📦 Товар: <b>{product_name}</b>\n"
        f"🎨 Стиль: {style_desc[:60]}...",
        parse_mode="HTML"
    )
    
    # Combine product name and style description for generation
    combined_description = f"{product_name}. Style requirements: {style_desc}"
    
    try:
        res = await prompt_generator.generate_styles_from_description(
            combined_description,
            aspect_ratio,
            random=False
        )
        
        if not res["success"]:
            await msg.edit_text(
                "❌ Ошибка генерации стилей.\n\nПопробуйте ещё раз или выберите другой метод:",
                reply_markup=get_style_selection_keyboard()
            )
            return
        
        # Trim to requested count
        styles = res["styles"][:count]
        
        await state.update_data(
            product_name=product_name,
            styles=styles,
            custom_style_count=count
        )
        
        text = _format_styles_preview(styles)
        await msg.edit_text(
            f"✨ <b>Ваши кастомные стили:</b>\n"
            f"📦 {product_name}\n"
            f"🎨 {style_desc[:60]}...\n\n"
            f"{text}",
            reply_markup=get_style_preview_keyboard(True, product_name),
            parse_mode="HTML"
        )
        await state.set_state(PhotoshootStates.reviewing_suggested_styles)
        
    except Exception as e:
        logger.error(f"Error generating custom styles: {e}", exc_info=True)
        await msg.edit_text(
            "❌ Произошла ошибка при генерации.\n\nПопробуйте ещё раз:",
            reply_markup=get_style_selection_keyboard()
        )


@router.callback_query(F.data == "cancel_custom_style")
async def cancel_custom_style(callback: CallbackQuery, state: FSMContext):
    """Cancel custom style creation"""
    await callback.answer()
    
    data = await state.get_data()
    aspect_ratio = data.get("aspect_ratio", "1:1")
    
    await callback.message.edit_text(
        f"❌ Создание кастомного стиля отменено.\n\n"
        f"✅ Пропорции: <b>{aspect_ratio}</b>\n"
        f"Выберите другой метод:",
        parse_mode="HTML",
        reply_markup=get_style_selection_keyboard()
    )
    await state.set_state(PhotoshootStates.selecting_styles_method)


# ==================== EDIT PRODUCT NAME ====================

@router.callback_query(F.data == "edit_product_name")
async def edit_product_name_start(callback: CallbackQuery, state: FSMContext):
    """Start editing product name"""
    await callback.answer()
    data = await state.get_data()
    current_name = data.get("product_name", "Product")

    # Store the original message ID so we can go back to it
    await state.update_data(edit_message_id=callback.message.message_id)

    await callback.message.edit_text(
        f"✏️ <b>Изменение названия товара</b>\n\n"
        f"📋 Текущее: <b>{current_name}</b>\n\n"
        "📝 Введите новое название товара:\n"
        "(Стили будут перегенерированы на основе нового названия)\n\n"
        "Для отмены отправьте /cancel",
        parse_mode="HTML"
    )
    await state.set_state(PhotoshootStates.editing_product_name)


@router.message(StateFilter(PhotoshootStates.editing_product_name), F.text == "/cancel")
async def cancel_edit_product_name(message: Message, state: FSMContext):
    """Cancel product name editing and return to previous state"""
    data = await state.get_data()
    product_name = data.get("product_name", "Product")
    styles = data.get("styles", [])

    # Return to reviewing state
    await state.set_state(PhotoshootStates.reviewing_suggested_styles)

    text = _format_styles_preview(styles)
    await message.answer(
        f"❌ <b>Редактирование отменено</b>\n\n"
        f"✨ <b>Текущие стили:</b>\n📦 {product_name}\n\n{text}",
        reply_markup=get_style_preview_keyboard(True, product_name),
        parse_mode="HTML"
    )


@router.message(StateFilter(PhotoshootStates.editing_product_name))
async def edit_product_name_input(message: Message, state: FSMContext):
    """Handle new product name input and regenerate styles"""
    new_name = message.text.strip()

    if len(new_name) < 3:
        await message.answer("⚠️ Название слишком короткое (минимум 3 символа). Попробуйте ещё раз:")
        return
    
    if len(new_name) > 100:
        await message.answer("⚠️ Название слишком длинное (максимум 100 символов). Попробуйте короче:")
        return
    
    data = await state.get_data()
    aspect_ratio = data.get("aspect_ratio", "1:1")
    
    logger.info(f"User changing product name from '{data.get('product_name')}' to '{new_name}'")
    
    msg = await message.answer(
        f"🔄 Перегенерирую стили для: <b>{new_name}</b>...",
        parse_mode="HTML"
    )
    
    try:
        # Regenerate styles with new product name
        res = await prompt_generator.generate_styles_from_description(
            new_name,
            aspect_ratio,
            random=False
        )
        
        if not res["success"]:
            await msg.edit_text(
                "❌ Ошибка генерации стилей.\n\nПопробуйте другое название:"
            )
            return
        
        await state.update_data(product_name=new_name, styles=res["styles"])
        
        text = _format_styles_preview(res["styles"])
        await msg.edit_text(
            f"✅ <b>Стили обновлены!</b>\n"
            f"📦 {new_name}\n\n"
            f"{text}",
            reply_markup=get_style_preview_keyboard(True, new_name),
            parse_mode="HTML"
        )
        await state.set_state(PhotoshootStates.reviewing_suggested_styles)
        
    except Exception as e:
        logger.error(f"Error regenerating styles: {e}", exc_info=True)
        await msg.edit_text(
            "❌ Произошла ошибка.\n\nПопробуйте ещё раз или вернитесь назад:",
            reply_markup=get_style_selection_keyboard()
        )
