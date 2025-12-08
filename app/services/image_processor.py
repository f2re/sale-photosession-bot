"""
Image Processor Service
"""
import logging
import asyncio
from io import BytesIO
from typing import Dict, List
from PIL import Image
from aiogram import Bot

from app.database.models import User
from app.services.nanobanana import NanoBananaService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self):
        self.nanobanana = NanoBananaService()
    
    def _convert_webp_to_png(self, image_bytes: bytes) -> bytes:
        try:
            img = Image.open(BytesIO(image_bytes))
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')
            output = BytesIO()
            img.save(output, format='PNG', optimize=True)
            return output.getvalue()
        except Exception as e:
            logger.error(f"WebP conversion error: {e}")
            raise
    
    async def generate_photoshoot(
        self,
        product_image_bytes: bytes,
        styles: List[Dict],
        aspect_ratio: str,
        bot: Bot,
        user: User
    ) -> Dict:
        try:
            logger.info(f"Starting photoshoot for {user.telegram_id}")
            
            # Convert if needed
            try:
                img = Image.open(BytesIO(product_image_bytes))
                if img.format and img.format.upper() == 'WEBP':
                    product_image_bytes = self._convert_webp_to_png(product_image_bytes)
            except Exception as e:
                return {"success": False, "error": "Invalid image format"}
            
            tasks = [
                self._generate_single_variant(
                    product_image_bytes, s["prompt"], s["style_name"], aspect_ratio
                ) for s in styles
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            images = []
            successful_count = 0
            
            for i, (res, style) in enumerate(zip(results, styles)):
                if isinstance(res, Exception) or not res.get("success"):
                    err = str(res) if isinstance(res, Exception) else res.get("error")
                    images.append({
                        "success": False,
                        "style_name": style["style_name"],
                        "prompt": style["prompt"],
                        "error": err
                    })
                else:
                    images.append({
                        **res,
                        "style_name": style["style_name"],
                        "prompt": style["prompt"]
                    })
                    successful_count += 1
            
            if successful_count < 4:
                await NotificationService.notify_admins_processing_error(
                    bot, user.telegram_id, user.username, "NanoBanana",
                    f"Failed {4-successful_count}/4 images"
                )
            
            return {
                "success": successful_count > 0,
                "images": images,
                "successful_count": successful_count,
                "error": None if successful_count > 0 else "All generations failed"
            }
            
        except Exception as e:
            logger.error(f"Critical error: {e}", exc_info=True)
            return {"success": False, "error": "Internal processing error"}

    async def _generate_single_variant(self, img_bytes, prompt, style_name, ratio):
        try:
            return await self.nanobanana.generate_image(
                prompt=prompt, reference_image_bytes=img_bytes, aspect_ratio=ratio
            )
        except Exception as e:
            return {"success": False, "error": str(e)}