"""
Style Manager Service
"""
import logging
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.crud import (
    create_style_preset,
    get_user_style_presets,
    get_style_preset_by_id,
    update_style_preset,
    delete_style_preset,
    count_user_active_presets
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
        try:
            count = await count_user_active_presets(session, user_id)
            if count >= settings.MAX_SAVED_STYLES:
                return {"success": False, "error": f"Limit reached ({settings.MAX_SAVED_STYLES})"}
            
            style_data = {
                "product_name": product_name,
                "aspect_ratio": aspect_ratio,
                "prompts": styles
            }
            
            preset = await create_style_preset(session, user_id, name, style_data)
            logger.info(f"Saved style '{name}' for user {user_id}")
            return {"success": True, "preset_id": preset.id, "error": None}
            
        except Exception as e:
            logger.error(f"Error saving style: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_user_styles(session: AsyncSession, user_id: int) -> List[Dict]:
        try:
            presets = await get_user_style_presets(session, user_id)
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
            logger.error(f"Error getting styles: {e}", exc_info=True)
            return []
    
    @staticmethod
    async def apply_style(session: AsyncSession, user_id: int, preset_id: int) -> Optional[Dict]:
        try:
            preset = await get_style_preset_by_id(session, preset_id, user_id)
            if not preset: return None
            return {
                "product_name": preset.style_data["product_name"],
                "aspect_ratio": preset.style_data["aspect_ratio"],
                "styles": preset.style_data["prompts"]
            }
        except Exception as e:
            logger.error(f"Error applying style: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def delete_style(session: AsyncSession, user_id: int, preset_id: int) -> bool:
        try:
            return await delete_style_preset(session, preset_id, user_id)
        except Exception as e:
            logger.error(f"Error deleting style: {e}", exc_info=True)
            return False
            
    @staticmethod
    async def rename_style(session: AsyncSession, user_id: int, preset_id: int, new_name: str) -> bool:
        try:
            preset = await update_style_preset(session, preset_id, user_id, name=new_name)
            return bool(preset)
        except Exception as e:
            logger.error(f"Error renaming style: {e}", exc_info=True)
            return False
