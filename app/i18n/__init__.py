"""
Internationalization module for bot
Supports EN (default) and RU languages
"""
from typing import Optional
from pathlib import Path
import gettext
import logging

logger = logging.getLogger(__name__)

# Supported languages
SUPPORTED_LANGUAGES = ["en", "ru"]
DEFAULT_LANGUAGE = "en"

# Directory with translations
LOCALES_DIR = Path(__file__).parent / "locales"

# Translation cache
_translations = {}


def load_translation(lang_code: str) -> gettext.GNUTranslations:
    """
    Load translation for specified language

    Args:
        lang_code: Language code (en, ru)

    Returns:
        GNUTranslations object
    """
    if lang_code not in SUPPORTED_LANGUAGES:
        logger.warning(f"Unsupported language: {lang_code}, fallback to {DEFAULT_LANGUAGE}")
        lang_code = DEFAULT_LANGUAGE

    if lang_code not in _translations:
        try:
            translation = gettext.translation(
                "messages",
                localedir=LOCALES_DIR,
                languages=[lang_code],
                fallback=(lang_code == DEFAULT_LANGUAGE)
            )
            _translations[lang_code] = translation
            logger.info(f"Loaded translation for: {lang_code}")
        except Exception as e:
            logger.error(f"Failed to load translation for {lang_code}: {e}")
            # Fallback to default
            if lang_code != DEFAULT_LANGUAGE:
                return load_translation(DEFAULT_LANGUAGE)
            else:
                # Create empty translation for English as fallback
                _translations[lang_code] = gettext.NullTranslations()

    return _translations[lang_code]


def get_user_language(telegram_language_code: Optional[str]) -> str:
    """
    Determine user language based on Telegram settings

    Args:
        telegram_language_code: Language code from Telegram (en, ru, ru-RU, etc.)

    Returns:
        Supported language code (en or ru)
    """
    if not telegram_language_code:
        return DEFAULT_LANGUAGE

    # Extract base language code (ru-RU -> ru)
    base_lang = telegram_language_code.split("-")[0].lower()

    if base_lang in SUPPORTED_LANGUAGES:
        return base_lang

    return DEFAULT_LANGUAGE


def _(text: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """
    Translate text to specified language

    Args:
        text: Text to translate
        lang: Language code

    Returns:
        Translated text
    """
    translation = load_translation(lang)
    return translation.gettext(text)
