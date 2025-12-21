"""
Enhanced i18n middleware with database language support
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.i18n import load_translation, get_user_language, DEFAULT_LANGUAGE
import logging

logger = logging.getLogger(__name__)


class I18nMiddleware(BaseMiddleware):
    """
    Middleware for determining user language from database or Telegram
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Determine user language and add translation function
        """
        session: AsyncSession = data.get("session")
        user: TgUser = data.get("event_from_user")

        lang_code = DEFAULT_LANGUAGE

        if user:
            # Try to get language from database
            if session:
                try:
                    from app.database.crud import get_user_by_telegram_id
                    db_user = await get_user_by_telegram_id(session, user.id)

                    if db_user and hasattr(db_user, 'language') and db_user.language:
                        lang_code = db_user.language
                    elif user.language_code:
                        # Fallback to Telegram language
                        lang_code = get_user_language(user.language_code)
                except Exception as e:
                    logger.error(f"Error getting user language from DB: {e}")
                    # Fallback to Telegram language
                    if user.language_code:
                        lang_code = get_user_language(user.language_code)
            elif user.language_code:
                # If no database session, use Telegram language
                lang_code = get_user_language(user.language_code)

        # Load translation
        translation = load_translation(lang_code)

        # Add to context
        data["_"] = translation.gettext
        data["lang"] = lang_code

        return await handler(event, data)
