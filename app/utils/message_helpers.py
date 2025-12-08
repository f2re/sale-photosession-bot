"""
Helper functions for safe message operations in Telegram bot.
"""

from typing import Optional
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest
import logging

logger = logging.getLogger(__name__)


async def safe_edit_text(
    message: Message,
    text: str,
    parse_mode: Optional[str] = None,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    disable_web_page_preview: bool = False
) -> bool:
    """
    Safely edit message text, handling "message is not modified" errors.

    Args:
        message: The message to edit
        text: New text content
        parse_mode: Parse mode (HTML, Markdown, etc.)
        reply_markup: Inline keyboard markup
        disable_web_page_preview: Whether to disable link previews

    Returns:
        bool: True if message was edited successfully, False if it was not modified
    """
    try:
        await message.edit_text(
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            disable_web_page_preview=disable_web_page_preview
        )
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            logger.debug(f"Message not modified (content unchanged): {message.message_id}")
            return False
        else:
            # Re-raise other TelegramBadRequest errors
            raise
    except Exception as e:
        logger.error(f"Error editing message {message.message_id}: {e}")
        raise


async def safe_edit_reply_markup(
    message: Message,
    reply_markup: Optional[InlineKeyboardMarkup] = None
) -> bool:
    """
    Safely edit message reply markup, handling "message is not modified" errors.

    Args:
        message: The message to edit
        reply_markup: New inline keyboard markup

    Returns:
        bool: True if markup was edited successfully, False if it was not modified
    """
    try:
        await message.edit_reply_markup(reply_markup=reply_markup)
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            logger.debug(f"Message markup not modified (content unchanged): {message.message_id}")
            return False
        else:
            # Re-raise other TelegramBadRequest errors
            raise
    except Exception as e:
        logger.error(f"Error editing message markup {message.message_id}: {e}")
        raise
