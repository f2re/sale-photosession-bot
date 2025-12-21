"""
Middleware для проверки принятия пользователем правовых документов
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)


class ConsentMiddleware(BaseMiddleware):
    """
    Middleware для проверки согласия пользователя с Privacy Policy и ToS
    Блокирует доступ к функциям бота до принятия условий
    """

    # Commands that work without consent
    ALLOWED_WITHOUT_CONSENT = [
        "/start",
        "/privacy",
        "/terms",
        "/help"
    ]

    # Callback data that works without consent
    ALLOWED_CALLBACKS = [
        "accept_terms",  # Accept terms button
        "view_privacy",  # View Privacy Policy
        "view_terms",    # View Terms of Service
        "back_to_consent",  # Back button
    ]

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Check consent before processing event
        """
        session: AsyncSession = data.get("session")
        user_tg = data.get("event_from_user")

        if not session or not user_tg:
            return await handler(event, data)

        # Get user from database
        try:
            from app.database.crud import get_user_by_telegram_id
            user = await get_user_by_telegram_id(session, user_tg.id)
        except Exception as e:
            logger.error(f"Error getting user in consent middleware: {e}")
            return await handler(event, data)

        if not user:
            # New user, will be created in /start handler
            return await handler(event, data)

        # Check if user has accepted terms
        if user.has_accepted_terms():
            # All ok, continue
            return await handler(event, data)

        # User hasn't accepted terms
        # Check if current command is allowed

        if isinstance(event, Message):
            # Check command
            if event.text and event.text.startswith("/"):
                command = event.text.split()[0]
                if command in self.ALLOWED_WITHOUT_CONSENT:
                    return await handler(event, data)

            # Block access, show consent screen
            await self._show_consent_screen(event, data)
            return

        elif isinstance(event, CallbackQuery):
            # Check callback data
            if event.data in self.ALLOWED_CALLBACKS:
                return await handler(event, data)

            # Block access
            _ = data.get("_")
            lang = data.get("lang", "en")
            await event.answer(
                _("error_accept_terms_first") if _ else "❌ Please accept Terms of Service first",
                show_alert=True
            )
            return

        # For other event types, allow
        return await handler(event, data)

    async def _show_consent_screen(
        self,
        message: Message,
        data: Dict[str, Any]
    ):
        """
        Show consent screen
        """
        from app.keyboards.legal import get_consent_keyboard

        _ = data.get("_")
        lang = data.get("lang", "en")

        text = _(
            "consent_required_message"
        ) if _ else (
            "📋 <b>Terms and Conditions</b>\n\n"
            "Before using the bot, please review and accept:\n\n"
            "• <b>Privacy Policy</b> - how we handle your data\n"
            "• <b>Terms of Service</b> - rules and conditions\n\n"
            "By clicking 'Accept', you confirm that you are 18+ and agree to both documents."
        )

        keyboard = get_consent_keyboard(lang)

        await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
