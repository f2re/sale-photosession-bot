"""
Legal documents handlers
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.legal import load_document
from app.keyboards.legal import get_consent_keyboard, get_document_keyboard
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "view_privacy")
async def callback_view_privacy(
    callback: CallbackQuery,
    lang: str = "en"
):
    """
    Show Privacy Policy
    """
    document = load_document("privacy_policy", lang)

    if not document:
        await callback.answer("❌ Document not found", show_alert=True)
        return

    # Telegram limits message length to 4096 characters
    # Split into parts if needed
    max_length = 4000

    if len(document) <= max_length:
        await callback.message.edit_text(
            text=document,
            reply_markup=get_document_keyboard("privacy_policy", lang),
            parse_mode="Markdown"
        )
    else:
        # Send in multiple messages
        parts = [
            document[i:i+max_length]
            for i in range(0, len(document), max_length)
        ]

        # Edit first message
        await callback.message.edit_text(
            text=parts[0],
            parse_mode="Markdown"
        )

        # Send middle parts
        for part in parts[1:-1]:
            await callback.message.answer(
                text=part,
                parse_mode="Markdown"
            )

        # Last part with button
        await callback.message.answer(
            text=parts[-1],
            reply_markup=get_document_keyboard("privacy_policy", lang),
            parse_mode="Markdown"
        )

    await callback.answer()


@router.callback_query(F.data == "view_terms")
async def callback_view_terms(
    callback: CallbackQuery,
    lang: str = "en"
):
    """
    Show Terms of Service
    """
    document = load_document("terms_of_service", lang)

    if not document:
        await callback.answer("❌ Document not found", show_alert=True)
        return

    # Similar to Privacy Policy
    max_length = 4000

    if len(document) <= max_length:
        await callback.message.edit_text(
            text=document,
            reply_markup=get_document_keyboard("terms_of_service", lang),
            parse_mode="Markdown"
        )
    else:
        parts = [
            document[i:i+max_length]
            for i in range(0, len(document), max_length)
        ]

        await callback.message.edit_text(text=parts[0], parse_mode="Markdown")
        for part in parts[1:-1]:
            await callback.message.answer(text=part, parse_mode="Markdown")
        await callback.message.answer(
            text=parts[-1],
            reply_markup=get_document_keyboard("terms_of_service", lang),
            parse_mode="Markdown"
        )

    await callback.answer()


@router.callback_query(F.data == "back_to_consent")
async def callback_back_to_consent(
    callback: CallbackQuery,
    lang: str = "en"
):
    """
    Return to consent screen
    """
    if lang == "ru":
        text = (
            "📋 <b>Условия использования</b>\n\n"
            "Перед использованием бота, пожалуйста, ознакомьтесь и примите:\n\n"
            "• <b>Политику конфиденциальности</b> - как мы обрабатываем ваши данные\n"
            "• <b>Условия использования</b> - правила и условия\n\n"
            "Нажимая 'Принимаю', вы подтверждаете что вам 18+ и соглашаетесь с обоими документами."
        )
    else:
        text = (
            "📋 <b>Terms and Conditions</b>\n\n"
            "Before using the bot, please review and accept:\n\n"
            "• <b>Privacy Policy</b> - how we handle your data\n"
            "• <b>Terms of Service</b> - rules and conditions\n\n"
            "By clicking 'Accept', you confirm that you are 18+ and agree to both documents."
        )

    keyboard = get_consent_keyboard(lang)

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "accept_terms")
async def callback_accept_terms(
    callback: CallbackQuery,
    session: AsyncSession,
    lang: str = "en"
):
    """
    Accept terms of service
    """
    from app.database.crud import get_user_by_telegram_id

    user = await get_user_by_telegram_id(session, callback.from_user.id)

    if not user:
        await callback.answer("❌ User not found", show_alert=True)
        return

    # Save consent
    user.consent_privacy_policy = True
    user.consent_terms_of_service = True
    user.consent_date = datetime.utcnow()
    # consent_ip can be obtained from webhook if used

    await session.commit()

    logger.info(f"User {user.telegram_id} accepted terms")

    # Show confirmation
    if lang == "ru":
        success_text = "✅ Спасибо за принятие условий!\n\nТеперь вы можете использовать все функции бота."
        menu_text = "📋 Главное меню"
    else:
        success_text = "✅ Thank you for accepting!\n\nYou can now use all bot features."
        menu_text = "📋 Main Menu"

    await callback.message.edit_text(text=success_text)
    
    # Show main menu
    from app.keyboards.main import get_main_keyboard
    keyboard = get_main_keyboard()

    await callback.message.answer(
        text=menu_text,
        reply_markup=keyboard
    )

    await callback.answer()


@router.message(Command("privacy"))
async def cmd_privacy(
    message: Message,
    lang: str = "en"
):
    """
    Command to view Privacy Policy
    """
    document = load_document("privacy_policy", lang)

    if not document:
        error_text = "❌ Документ не найден. Пожалуйста, свяжитесь с поддержкой." if lang == "ru" else "❌ Document not found. Please contact support."
        await message.answer(error_text)
        return

    # Send document (split into parts if needed)
    max_length = 4000

    if len(document) <= max_length:
        await message.answer(text=document, parse_mode="Markdown")
    else:
        parts = [
            document[i:i+max_length]
            for i in range(0, len(document), max_length)
        ]
        for part in parts:
            await message.answer(text=part, parse_mode="Markdown")


@router.message(Command("terms"))
async def cmd_terms(
    message: Message,
    lang: str = "en"
):
    """
    Command to view Terms of Service
    """
    document = load_document("terms_of_service", lang)

    if not document:
        error_text = "❌ Документ не найден. Пожалуйста, свяжитесь с поддержкой." if lang == "ru" else "❌ Document not found. Please contact support."
        await message.answer(error_text)
        return

    # Send document
    max_length = 4000

    if len(document) <= max_length:
        await message.answer(text=document, parse_mode="Markdown")
    else:
        parts = [
            document[i:i+max_length]
            for i in range(0, len(document), max_length)
        ]
        for part in parts:
            await message.answer(text=part, parse_mode="Markdown")
