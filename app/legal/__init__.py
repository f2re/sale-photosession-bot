"""
Legal documents management module
Handles Privacy Policy, Terms of Service, user consent
"""
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Directory with templates
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Supported documents
DOCUMENT_TYPES = ["privacy_policy", "terms_of_service"]


def get_document_path(doc_type: str, lang: str) -> Path:
    """
    Get path to document

    Args:
        doc_type: Document type (privacy_policy, terms_of_service)
        lang: Language (en, ru)

    Returns:
        Path to document file
    """
    if doc_type not in DOCUMENT_TYPES:
        raise ValueError(f"Invalid document type: {doc_type}")

    filename = f"{doc_type}_{lang}.md"
    return TEMPLATES_DIR / filename


def load_document(doc_type: str, lang: str) -> Optional[str]:
    """
    Load document text

    Args:
        doc_type: Document type
        lang: Language

    Returns:
        Document text or None if not found
    """
    try:
        path = get_document_path(doc_type, lang)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Document not found: {doc_type} ({lang})")
        return None
    except Exception as e:
        logger.error(f"Error loading document {doc_type}: {e}")
        return None
