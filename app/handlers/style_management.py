"""
Style Management Handlers
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession

from app.states import StyleManagementStates
from app.services.style_manager import StyleManager
from app.keyboards.inline import get_style_management_keyboard, get_saved_styles_keyboard, get_aspect_ratio_keyboard
from app.config import settings

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "manage_styles")
async def show_style_management(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    styles = await StyleManager.get_user_styles(session, callback.from_user.id)

    if not styles:
        await callback.message.edit_text("📁 Нет сохраненных стилей.")
        return

    # Create custom keyboard for management (not application)
    buttons = []
    for style in styles:
        text = f"{style['name']} ({style['aspect_ratio']})"
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"manage_style:{style['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    text_list = "\n".join([f"{i+1}. <b>{s['name']}</b> ({s['aspect_ratio']})" for i, s in enumerate(styles)])
    await callback.message.edit_text(
        f"📁 <b>Управление стилями ({len(styles)}/{settings.MAX_SAVED_STYLES}):</b>\n\n{text_list}\n\nВыберите стиль для управления:",
        reply_markup=keyboard, parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("manage_style:"))
async def show_style_options(callback: CallbackQuery, session: AsyncSession):
    """Show management options for a specific style"""
    pid = int(callback.data.split(":")[1])

    # Get style details
    styles = await StyleManager.get_user_styles(session, callback.from_user.id)
    style = next((s for s in styles if s['id'] == pid), None)

    if not style:
        await callback.answer("Стиль не найден", show_alert=True)
        return

    text = (
        f"📝 <b>Управление стилем</b>\n\n"
        f"Название: <b>{style['name']}</b>\n"
        f"Пропорции: {style['aspect_ratio']}\n\n"
        f"Выберите действие:"
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_style_management_keyboard(pid)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("delete_style:"))
async def delete_style(callback: CallbackQuery, session: AsyncSession):
    pid = int(callback.data.split(":")[1])
    if await StyleManager.delete_style(session, callback.from_user.id, pid):
        await callback.answer("Удалено")
        await show_style_management(callback, session)
    else:
        await callback.answer("Ошибка", show_alert=True)

@router.callback_query(F.data.startswith("rename_style:"))
async def rename_init(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    pid = int(callback.data.split(":")[1])
    await state.update_data(renaming_preset_id=pid)
    await callback.message.answer("Введите новое название:")
    await state.set_state(StyleManagementStates.editing_style_name)

@router.message(StateFilter(StyleManagementStates.editing_style_name))
async def rename_confirm(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    pid = data["renaming_preset_id"]
    if await StyleManager.rename_style(session, message.from_user.id, pid, message.text):
        await message.answer("✅ Переименовано")
    else:
        await message.answer("❌ Ошибка")
    await state.clear()

@router.callback_query(F.data.startswith("change_aspect_ratio:"))
async def change_aspect_ratio_init(callback: CallbackQuery, state: FSMContext):
    """Start changing aspect ratio for a style"""
    await callback.answer()
    pid = int(callback.data.split(":")[1])
    await state.update_data(editing_preset_id=pid)

    text = (
        "📐 <b>Изменение пропорций</b>\n\n"
        "Выберите новые пропорции для сохраненного стиля:"
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_aspect_ratio_keyboard()
    )
    await state.set_state(StyleManagementStates.editing_aspect_ratio)

@router.callback_query(F.data.startswith("aspect_ratio:"), StateFilter(StyleManagementStates.editing_aspect_ratio))
async def change_aspect_ratio_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Confirm aspect ratio change"""
    # Extract ratio correctly: "aspect_ratio:16:9" -> "16:9"
    new_ratio = ":".join(callback.data.split(":")[1:])
    data = await state.get_data()
    pid = data.get("editing_preset_id")

    if not pid:
        await callback.answer("❌ Ошибка: ID стиля не найден", show_alert=True)
        await state.clear()
        return

    # Update aspect ratio
    if await StyleManager.update_aspect_ratio(session, callback.from_user.id, pid, new_ratio):
        await callback.answer("✅ Пропорции обновлены")
        # Show updated style details
        styles = await StyleManager.get_user_styles(session, callback.from_user.id)
        style = next((s for s in styles if s['id'] == pid), None)

        if style:
            text = (
                f"📝 <b>Управление стилем</b>\n\n"
                f"Название: <b>{style['name']}</b>\n"
                f"Пропорции: {style['aspect_ratio']}\n\n"
                f"✅ Пропорции успешно изменены на <b>{new_ratio}</b>\n\n"
                f"Выберите действие:"
            )
            await callback.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=get_style_management_keyboard(pid)
            )
        else:
            await callback.message.edit_text("✅ Пропорции обновлены")
    else:
        await callback.answer("❌ Ошибка при обновлении", show_alert=True)

    await state.clear()
