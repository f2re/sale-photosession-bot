"""
Style Manager Service
"""
import logging
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.database.crud import (
    create_style_preset,
    get_user_style_presets,
    get_style_preset_by_id,
    update_style_preset,
    delete_style_preset,
    count_user_active_presets,
    get_or_create_user
)
from app.config import settings

logger = logging.getLogger(__name__)

class StyleManager:
    """Manages user saved styles"""
    
    @staticmethod
    async def save_style(
        session: AsyncSession,
        user_id: int,
        name: str,
        product_name: str,
        aspect_ratio: str,
        styles: List[Dict]
    ) -> Dict:
        """Save style preset for user"""
        try:
            # Ensure user exists in database before trying to save style
            # This prevents ForeignKeyViolationError
            logger.info(f"User {user_id} | Saving style '{name}' | Ensuring user exists in DB...")
            
            # This will create user if doesn't exist (with telegram_id as primary lookup)
            user = await get_or_create_user(session, telegram_id=user_id)
            logger.info(f"User {user_id} | User record confirmed | DB id: {user.id}")
            
            # Check style limit
            count = await count_user_active_presets(session, user_id)
            if count >= settings.MAX_SAVED_STYLES:
                logger.warning(f"User {user_id} | Style limit reached: {count}/{settings.MAX_SAVED_STYLES}")
                return {"success": False, "error": f"Лимит стилей ({settings.MAX_SAVED_STYLES})"}
            
            style_data = {
                "product_name": product_name,
                "aspect_ratio": aspect_ratio,
                "prompts": styles
            }
            
            logger.info(f"User {user_id} | Creating style preset in DB...")
            preset = await create_style_preset(session, user_id, name, style_data)
            logger.info(f"User {user_id} | Style '{name}' saved successfully | preset_id: {preset.id}")
            
            return {"success": True, "preset_id": preset.id, "error": None}
            
        except IntegrityError as e:
            # More specific handling of integrity errors
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"User {user_id} | Database integrity error saving style: {error_msg}", exc_info=True)
            
            # User-friendly error message
            if "foreign key" in error_msg.lower():
                return {"success": False, "error": "Ошибка связи с пользователем. Попробуйте /start"}
            elif "unique" in error_msg.lower():
                return {"success": False, "error": "Стиль с таким названием уже существует"}
            else:
                return {"success": False, "error": "Ошибка базы данных"}
            
        except Exception as e:
            logger.error(f"User {user_id} | Unexpected error saving style: {e}", exc_info=True)
            return {"success": False, "error": "Непредвиденная ошибка"}
    
    @staticmethod
    async def get_user_styles(session: AsyncSession, user_id: int) -> List[Dict]:
        """Get all saved styles for user"""
        try:
            logger.info(f"User {user_id} | Getting saved styles...")
            presets = await get_user_style_presets(session, user_id)
            logger.info(f"User {user_id} | Found {len(presets)} saved styles")
            
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "product_name": p.style_data.get("product_name", "Unknown"),
                    "aspect_ratio": p.style_data.get("aspect_ratio", "1:1"),
                    "created_at": p.created_at
                }
                for p in presets
            ]
        except Exception as e:
            logger.error(f"User {user_id} | Error getting styles: {e}", exc_info=True)
            return []
    
    @staticmethod
    async def apply_style(session: AsyncSession, user_id: int, preset_id: int) -> Optional[Dict]:
        """Apply saved style preset"""
        try:
            logger.info(f"User {user_id} | Applying style preset {preset_id}...")
            preset = await get_style_preset_by_id(session, preset_id, user_id)
            
            if not preset:
                logger.warning(f"User {user_id} | Style preset {preset_id} not found")
                return None
            
            logger.info(f"User {user_id} | Style preset '{preset.name}' applied successfully")
            return {
                "product_name": preset.style_data["product_name"],
                "aspect_ratio": preset.style_data["aspect_ratio"],
                "styles": preset.style_data["prompts"]
            }
        except Exception as e:
            logger.error(f"User {user_id} | Error applying style: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def delete_style(session: AsyncSession, user_id: int, preset_id: int) -> bool:
        """Delete saved style preset"""
        try:
            logger.info(f"User {user_id} | Deleting style preset {preset_id}...")
            result = await delete_style_preset(session, preset_id, user_id)
            
            if result:
                logger.info(f"User {user_id} | Style preset {preset_id} deleted successfully")
            else:
                logger.warning(f"User {user_id} | Style preset {preset_id} not found for deletion")
            
            return result
        except Exception as e:
            logger.error(f"User {user_id} | Error deleting style: {e}", exc_info=True)
            return False
            
    @staticmethod
    async def rename_style(session: AsyncSession, user_id: int, preset_id: int, new_name: str) -> bool:
        """Rename saved style preset"""
        try:
            logger.info(f"User {user_id} | Renaming style preset {preset_id} to '{new_name}'...")
            preset = await update_style_preset(session, preset_id, user_id, name=new_name)
            
            if preset:
                logger.info(f"User {user_id} | Style preset {preset_id} renamed successfully")
                return True
            else:
                logger.warning(f"User {user_id} | Style preset {preset_id} not found for renaming")
                return False
        except Exception as e:
            logger.error(f"User {user_id} | Error renaming style: {e}", exc_info=True)
            return False
