"""
Image Processor Service
"""
import logging
import asyncio
import aiohttp
import base64
from io import BytesIO
from typing import Dict, List
from PIL import Image
from aiogram import Bot

from app.database.models import User
from app.services.nanobanana import NanoBananaService
from app.services.notification_service import NotificationService
from app.config import settings

logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self):
        self.nanobanana = NanoBananaService()
        self.openrouter_api_key = settings.OPENROUTER_API_KEY
        self.vision_model = "google/gemini-2.0-flash-exp:free"  # Fast and free vision model
    
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
    
    async def analyze_product_image(self, image_bytes: bytes) -> Dict:
        """
        Analyze product image using vision API to extract product details.
        
        Args:
            image_bytes: Product image bytes
            
        Returns:
            {
                "success": bool,
                "product_description": str,  # Detailed description
                "error": Optional[str]
            }
        """
        try:
            logger.info("Starting product image analysis with vision API")
            
            # Convert image to base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # Detect image format
            image = Image.open(BytesIO(image_bytes))
            image_format = image.format.lower() if image.format else 'jpeg'
            mime_type = f"image/{image_format}"
            
            # Prepare request
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://t.me/@SalePhotosession_bot",
                "X-Title": "Product Photoshoot Bot"
            }
            
            # Product analysis prompt
            analysis_prompt = """Analyze this product image and provide a detailed description.

Extract:
1. **Product Type**: What is this product? (e.g., perfume bottle, candle, skincare jar, watch, shoes, etc.)
2. **Key Features**: Shape, size, materials, colors, textures
3. **Brand/Style**: Premium/budget, modern/vintage, minimalist/ornate
4. **Notable Details**: Labels, decorations, unique characteristics

Provide a CONCISE description in 2-3 sentences that captures the essence of the product for professional photoshoot planning.

Example format:
"A premium amber glass candle jar with minimalist black label. The product has a cylindrical shape with visible wax texture and appears to be a luxury home fragrance item. Clean, modern aesthetic with natural materials."

Your description:"""
            
            payload = {
                "model": self.vision_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": analysis_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.3,  # Low temperature for consistent analysis
                "max_tokens": 300
            }
            
            logger.info(f"Sending product analysis request to vision API (model: {self.vision_model})")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Extract description from response
                        description = result['choices'][0]['message']['content'].strip()
                        
                        logger.info(f"Product analysis successful: {description[:100]}...")
                        
                        return {
                            "success": True,
                            "product_description": description,
                            "error": None
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Vision API error: {response.status} - {error_text}")
                        
                        # Fallback to generic description
                        return {
                            "success": False,
                            "product_description": "A high-end commercial product",
                            "error": f"API error: {response.status}"
                        }
                        
        except Exception as e:
            logger.error(f"Error analyzing product image: {e}", exc_info=True)
            
            # Fallback to generic description
            return {
                "success": False,
                "product_description": "A high-end commercial product",
                "error": str(e)
            }
    
    async def generate_photoshoot(
        self,
        product_image_bytes: bytes,
        styles: List[Dict],
        aspect_ratio: str,
        bot: Bot,
        user: User,
        progress_message=None
    ) -> Dict:
        try:
            logger.info(f"Starting photoshoot for user {user.telegram_id} with aspect_ratio: {aspect_ratio}, styles: {len(styles)}")

            # Convert if needed
            try:
                img = Image.open(BytesIO(product_image_bytes))
                if img.format and img.format.upper() == 'WEBP':
                    logger.info("Converting WEBP to PNG")
                    product_image_bytes = self._convert_webp_to_png(product_image_bytes)
            except Exception as e:
                logger.error(f"Image format validation failed: {e}")
                return {"success": False, "error": "Invalid image format"}

            total_styles = len(styles)

            # Update progress: preparing request
            if progress_message:
                try:
                    await progress_message.edit_text(
                        f"📤 Отправляю запросы на генерацию {total_styles} изображений...\n"
                        f"⏳ Ожидайте, это займет около минуты"
                    )
                except Exception as e:
                    logger.warning(f"Failed to update progress message: {e}")

            # Generate all style variations in parallel
            tasks = [
                self._generate_single_variant(
                    product_image_bytes, s["prompt"], s["style_name"], aspect_ratio
                ) for s in styles
            ]

            logger.info(f"Generating {total_styles} style variations in parallel")

            # Update progress: waiting for results
            if progress_message:
                try:
                    await progress_message.edit_text(
                        f"🎨 Генерация изображений в процессе...\n"
                        f"🔄 Обрабатываю {total_styles} стилей\n"
                        f"⏳ ~1 мин"
                    )
                except Exception as e:
                    logger.warning(f"Failed to update progress message: {e}")

            results = await asyncio.gather(*tasks, return_exceptions=True)

            images = []
            successful_count = 0

            for i, (res, style) in enumerate(zip(results, styles)):
                if isinstance(res, Exception):
                    logger.error(f"Style {i+1} ({style['style_name']}) failed with exception: {res}")
                    images.append({
                        "success": False,
                        "style_name": style["style_name"],
                        "prompt": style["prompt"],
                        "error": str(res)
                    })
                elif not res.get("success"):
                    logger.warning(f"Style {i+1} ({style['style_name']}) failed: {res.get('error')}")
                    images.append({
                        "success": False,
                        "style_name": style["style_name"],
                        "prompt": style["prompt"],
                        "error": res.get("error")
                    })
                else:
                    logger.info(f"Style {i+1} ({style['style_name']}) generated successfully")
                    images.append({
                        **res,
                        "style_name": style["style_name"],
                        "prompt": style["prompt"]
                    })
                    successful_count += 1

            # Update progress: generation complete
            if progress_message:
                try:
                    await progress_message.edit_text(
                        f"✅ Генерация завершена!\n"
                        f"📊 Получено изображений: {successful_count} из {total_styles}\n"
                        f"⏳ Отправляю результаты..."
                    )
                except Exception as e:
                    logger.warning(f"Failed to update progress message: {e}")

            logger.info(f"Photoshoot completed: {successful_count}/{total_styles} successful")

            # Notify admins if there were failures
            if successful_count < total_styles:
                await NotificationService.notify_admins_processing_error(
                    bot, user.telegram_id, user.username, "NanoBanana",
                    f"Failed {total_styles-successful_count}/{total_styles} images"
                )
            
            return {
                "success": successful_count > 0,
                "images": images,
                "successful_count": successful_count,
                "error": None if successful_count > 0 else "All generations failed"
            }
            
        except Exception as e:
            logger.error(f"Critical error in generate_photoshoot: {e}", exc_info=True)
            return {"success": False, "error": "Internal processing error"}

    async def _generate_single_variant(self, img_bytes, prompt, style_name, ratio):
        """
        Generate single image variant using NanoBanana API.
        
        Args:
            img_bytes: Product image bytes
            prompt: Style prompt
            style_name: Style name for logging
            ratio: Aspect ratio
            
        Returns:
            Result dict with success, image_bytes, and error fields
        """
        try:
            logger.info(f"Generating '{style_name}' with ratio {ratio}")
            return await self.nanobanana.generate_image(
                prompt=prompt, 
                reference_image_bytes=img_bytes, 
                aspect_ratio=ratio
            )
        except Exception as e:
            logger.error(f"Failed to generate '{style_name}': {e}", exc_info=True)
            return {"success": False, "error": str(e)}
