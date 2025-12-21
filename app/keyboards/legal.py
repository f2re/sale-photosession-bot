"""
Legal documents keyboards
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_consent_keyboard(lang: str) -> InlineKeyboardMarkup:
    """
    Keyboard for accepting terms
    """
    # Simple version without i18n for now (will add translations later)
    if lang == "ru":
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Политика конфиденциальности",
                    callback_data="view_privacy"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📄 Условия использования",
                    callback_data="view_terms"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Принимаю (18+)",
                    callback_data="accept_terms"
                )
            ],
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Privacy Policy",
                    callback_data="view_privacy"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📄 Terms of Service",
                    callback_data="view_terms"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ I Accept (18+)",
                    callback_data="accept_terms"
                )
            ],
        ])


def get_document_keyboard(doc_type: str, lang: str) -> InlineKeyboardMarkup:
    """
    Keyboard for viewing document
    """
    back_text = "◀️ Назад" if lang == "ru" else "◀️ Back"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=back_text,
                callback_data="back_to_consent"
            )
        ],
    ])
