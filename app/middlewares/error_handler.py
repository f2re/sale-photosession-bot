"""
Error handling middleware that notifies admins about critical errors
"""
import logging
import traceback
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Update, CallbackQuery, Message

from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseMiddleware):
    """
    Middleware that catches unhandled exceptions and notifies admins
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            # Get bot instance
            bot: Bot = data.get("bot")

            # Extract user information
            user_telegram_id = None
            username = None
            handler_name = None

            # Try to extract user info from event
            if isinstance(event, Update):
                if event.callback_query:
                    user_telegram_id = event.callback_query.from_user.id
                    username = event.callback_query.from_user.username
                    if event.callback_query.data:
                        handler_name = f"callback: {event.callback_query.data}"
                elif event.message:
                    user_telegram_id = event.message.from_user.id
                    username = event.message.from_user.username
                    handler_name = "message handler"
            elif isinstance(event, CallbackQuery):
                user_telegram_id = event.from_user.id
                username = event.from_user.username
                if event.data:
                    handler_name = f"callback: {event.data}"
            elif isinstance(event, Message):
                user_telegram_id = event.from_user.id
                username = event.from_user.username
                handler_name = "message handler"

            # Get error info
            error_type = type(e).__name__
            error_message = str(e)
            traceback_info = traceback.format_exc()

            # Log the error
            logger.error(
                f"Unhandled error in handler: {error_type}: {error_message}\n"
                f"User: {username} ({user_telegram_id})\n"
                f"Handler: {handler_name}",
                exc_info=True
            )

            # Notify admins if bot instance is available
            if bot:
                try:
                    await NotificationService.notify_admins_critical_error(
                        bot=bot,
                        error_type=error_type,
                        error_message=error_message,
                        user_telegram_id=user_telegram_id,
                        username=username,
                        handler_name=handler_name,
                        traceback_info=traceback_info
                    )
                except Exception as notify_error:
                    logger.error(f"Failed to notify admins about error: {notify_error}")

            # Try to notify user about error
            try:
                if isinstance(event, CallbackQuery):
                    await event.answer("❌ Произошла ошибка. Попробуйте снова.", show_alert=True)
                    if event.message:
                        await event.message.answer(
                            "❌ Произошла ошибка при обработке запроса.\n"
                            "Администраторы уже уведомлены. Попробуйте позже или обратитесь в поддержку."
                        )
                elif isinstance(event, Message):
                    await event.answer(
                        "❌ Произошла ошибка при обработке запроса.\n"
                        "Администраторы уже уведомлены. Попробуйте позже или обратитесь в поддержку."
                    )
            except Exception as user_notify_error:
                logger.error(f"Failed to notify user about error: {user_notify_error}")

            # Re-raise the exception so it's logged by aiogram as well
            raise
