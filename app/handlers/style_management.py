"""
Style Management Handlers
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession

from app.states import StyleManagementStates
from app.services.style_manager import StyleManager
from app.keyboards.inline import get_style_management_keyboard, get_saved_styles_keyboard
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
    
    text = "\n".join([f"{i+1}. <b>{s['name']}</b>" for i, s in enumerate(styles)])
    await callback.message.edit_text(
        f"📁 <b>Управление ({len(styles)}/{settings.MAX_SAVED_STYLES}):</b>\n\n{text}\n\nВыберите стиль:",
        reply_markup=get_style_management_keyboard(styles), parse_mode="HTML"
    )

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
