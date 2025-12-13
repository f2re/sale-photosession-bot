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
        telegram_id: int,  # This is telegram_id, not database id!
        name: str,
        product_name: str,
        aspect_ratio: str,
        styles: List[Dict]
    ) -> Dict:
        """Save style preset for user"""
        try:
            # CRITICAL: Ensure user exists and get database ID
            logger.info(f"User {telegram_id} | Saving style '{name}' | Ensuring user exists in DB...")
            
            # Get user object - this returns the database user with id field
            user = await get_or_create_user(session, telegram_id=telegram_id)
            logger.info(f"User {telegram_id} | User record confirmed | DB id: {user.id} | telegram_id: {user.telegram_id}")
            
            # IMPORTANT: Use database user.id, NOT telegram_id!
            database_user_id = user.id
            
            # Check style limit using database id
            count = await count_user_active_presets(session, database_user_id)
            if count >= settings.MAX_SAVED_STYLES:
                logger.warning(f"User {telegram_id} | Style limit reached: {count}/{settings.MAX_SAVED_STYLES}")
                return {"success": False, "error": f"Лимит стилей ({settings.MAX_SAVED_STYLES})"}
            
            style_data = {
                "product_name": product_name,
                "aspect_ratio": aspect_ratio,
                "prompts": styles
            }
            
            logger.info(f"User {telegram_id} | Creating style preset in DB with database user_id={database_user_id}...")
            
            # Pass database user.id to create_style_preset
            preset = await create_style_preset(session, database_user_id, name, style_data)
            
            logger.info(f"User {telegram_id} | Style '{name}' saved successfully | preset_id: {preset.id}")
            
            return {"success": True, "preset_id": preset.id, "error": None}
            
        except IntegrityError as e:
            # More specific handling of integrity errors
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"User {telegram_id} | Database integrity error saving style: {error_msg}", exc_info=True)
            
            # User-friendly error message
            if "foreign key" in error_msg.lower():
                return {"success": False, "error": "Ошибка связи с пользователем. Попробуйте /start"}
            elif "unique" in error_msg.lower():
                return {"success": False, "error": "Стиль с таким названием уже существует"}
            else:
                return {"success": False, "error": "Ошибка базы данных"}
            
        except Exception as e:
            logger.error(f"User {telegram_id} | Unexpected error saving style: {e}", exc_info=True)
            return {"success": False, "error": "Непредвиденная ошибка"}
    
    @staticmethod
    async def get_user_styles(session: AsyncSession, telegram_id: int) -> List[Dict]:
        """Get all saved styles for user"""
        try:
            logger.info(f"User {telegram_id} | Getting saved styles...")
            
            # Get database user id
            user = await get_or_create_user(session, telegram_id=telegram_id)
            database_user_id = user.id
            
            presets = await get_user_style_presets(session, database_user_id)
            logger.info(f"User {telegram_id} | Found {len(presets)} saved styles")
            
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
            logger.error(f"User {telegram_id} | Error getting styles: {e}", exc_info=True)
            return []
    
    @staticmethod
    async def apply_style(session: AsyncSession, telegram_id: int, preset_id: int) -> Optional[Dict]:
        """Apply saved style preset"""
        try:
            logger.info(f"User {telegram_id} | Applying style preset {preset_id}...")
            
            # Get database user id
            user = await get_or_create_user(session, telegram_id=telegram_id)
            database_user_id = user.id
            
            preset = await get_style_preset_by_id(session, preset_id, database_user_id)
            
            if not preset:
                logger.warning(f"User {telegram_id} | Style preset {preset_id} not found")
                return None
            
            logger.info(f"User {telegram_id} | Style preset '{preset.name}' applied successfully")
            return {
                "product_name": preset.style_data["product_name"],
                "aspect_ratio": preset.style_data["aspect_ratio"],
                "styles": preset.style_data["prompts"]
            }
        except Exception as e:
            logger.error(f"User {telegram_id} | Error applying style: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def delete_style(session: AsyncSession, telegram_id: int, preset_id: int) -> bool:
        """Delete saved style preset"""
        try:
            logger.info(f"User {telegram_id} | Deleting style preset {preset_id}...")
            
            # Get database user id
            user = await get_or_create_user(session, telegram_id=telegram_id)
            database_user_id = user.id
            
            result = await delete_style_preset(session, preset_id, database_user_id)
            
            if result:
                logger.info(f"User {telegram_id} | Style preset {preset_id} deleted successfully")
            else:
                logger.warning(f"User {telegram_id} | Style preset {preset_id} not found for deletion")
            
            return result
        except Exception as e:
            logger.error(f"User {telegram_id} | Error deleting style: {e}", exc_info=True)
            return False
            
    @staticmethod
    async def rename_style(session: AsyncSession, telegram_id: int, preset_id: int, new_name: str) -> bool:
        """Rename saved style preset"""
        try:
            logger.info(f"User {telegram_id} | Renaming style preset {preset_id} to '{new_name}'...")

            # Get database user id
            user = await get_or_create_user(session, telegram_id=telegram_id)
            database_user_id = user.id

            preset = await update_style_preset(session, preset_id, database_user_id, name=new_name)

            if preset:
                logger.info(f"User {telegram_id} | Style preset {preset_id} renamed successfully")
                return True
            else:
                logger.warning(f"User {telegram_id} | Style preset {preset_id} not found for renaming")
                return False
        except Exception as e:
            logger.error(f"User {telegram_id} | Error renaming style: {e}", exc_info=True)
            return False

    @staticmethod
    async def update_aspect_ratio(session: AsyncSession, telegram_id: int, preset_id: int, new_aspect_ratio: str) -> bool:
        """Update aspect ratio for saved style preset"""
        try:
            logger.info(f"User {telegram_id} | Updating aspect ratio for style preset {preset_id} to '{new_aspect_ratio}'...")

            # Get database user id
            user = await get_or_create_user(session, telegram_id=telegram_id)
            database_user_id = user.id

            # Get current preset
            preset = await get_style_preset_by_id(session, preset_id, database_user_id)

            if not preset:
                logger.warning(f"User {telegram_id} | Style preset {preset_id} not found")
                return False

            # Update aspect_ratio in style_data
            updated_style_data = preset.style_data.copy()
            updated_style_data["aspect_ratio"] = new_aspect_ratio

            # Update preset with new style_data
            updated_preset = await update_style_preset(
                session,
                preset_id,
                database_user_id,
                style_data=updated_style_data
            )

            if updated_preset:
                logger.info(f"User {telegram_id} | Aspect ratio for style preset {preset_id} updated successfully")
                return True
            else:
                logger.warning(f"User {telegram_id} | Failed to update aspect ratio for style preset {preset_id}")
                return False
        except Exception as e:
            logger.error(f"User {telegram_id} | Error updating aspect ratio: {e}", exc_info=True)
            return False
