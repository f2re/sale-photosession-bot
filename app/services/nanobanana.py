"""
NanoBanana Image Generation Service (via OpenRouter)
"""
import aiohttp
import base64
import logging
import time
from io import BytesIO
from typing import Dict
from PIL import Image

from app.config import settings
from app.utils.prompt_logger import PromptLogger
from app.utils.api_retry import image_api_retry
logger = logging.getLogger(__name__)


def translate_api_error_to_russian(error_message: str) -> str:
    """
    Translate API error messages to user-friendly Russian messages.

    Args:
        error_message: Raw error message from API

    Returns:
        User-friendly Russian error message
    """
    error_lower = error_message.lower()

    # Face detection error
    if "face" in error_lower or "person" in error_lower:
        return (
            "❌ На фото обнаружено лицо человека.\n\n"
            "⚠️ Требования к фото:\n"
            "• Фотографируйте только товар\n"
            "• Без людей и лиц на фото\n"
            "• Товар должен быть хорошо виден\n"
            "• Используйте чистый фон\n\n"
            "Пожалуйста, загрузите другое фото товара без людей."
        )

    # Product not visible
    if "not visible" in error_lower or "cannot see" in error_lower or "not clear" in error_lower:
        return (
            "❌ Товар недостаточно хорошо виден на фото.\n\n"
            "💡 Рекомендации:\n"
            "• Убедитесь, что товар в фокусе\n"
            "• Используйте хорошее освещение\n"
            "• Товар должен занимать большую часть кадра\n"
            "• Избегайте размытых фото\n\n"
            "Попробуйте сделать более качественное фото."
        )

    # Image quality issues
    if "quality" in error_lower or "resolution" in error_lower or "blur" in error_lower:
        return (
            "❌ Качество фото недостаточное.\n\n"
            "📸 Требования:\n"
            "• Минимум 512x512 пикселей\n"
            "• Фото должно быть четким, не размытым\n"
            "• Хорошее освещение\n"
            "• Формат: JPG, PNG или WEBP\n\n"
            "Загрузите фото лучшего качества."
        )

    # Too many objects
    if "multiple" in error_lower or "many objects" in error_lower or "crowded" in error_lower:
        return (
            "❌ На фото слишком много объектов.\n\n"
            "✅ Рекомендуем:\n"
            "• Фотографируйте один товар\n"
            "• Уберите лишние предметы из кадра\n"
            "• Используйте простой фон\n\n"
            "Пожалуйста, сделайте фото с одним товаром."
        )

    # Generic reference image error
    if "reference image" in error_lower:
        return (
            "❌ Не удалось обработать исходное фото.\n\n"
            "⚠️ Проверьте требования:\n"
            "• Фото только товара (без людей)\n"
            "• Хорошее качество и освещение\n"
            "• Товар хорошо виден\n"
            "• Чистый фон\n\n"
            "Попробуйте загрузить другое фото."
        )

    # Safety/moderation issues
    if "safety" in error_lower or "inappropriate" in error_lower or "policy" in error_lower:
        return (
            "❌ Фото не соответствует требованиям безопасности.\n\n"
            "Пожалуйста, используйте фото товаров, подходящих для коммерческого использования.\n\n"
            "Обратитесь в поддержку, если считаете это ошибкой."
        )

    # Default error
    return (
        "❌ Не удалось сгенерировать изображение.\n\n"
        "Возможные причины:\n"
        "• Фото не подходит для обработки\n"
        "• Попробуйте другое фото товара\n"
        "• Проверьте качество и освещение\n\n"
        "Если проблема повторяется, обратитесь в поддержку."
    )


class NonRetryableGenerationError(Exception):
    """Exception for errors that should not be retried (e.g. content policy violations)"""
    pass


class NanoBananaService:
    """Service for generating images via OpenRouter"""

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.IMAGE_MODEL # e.g., google/gemini-2.0-flash-001 or similar capable of image output
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    async def _make_generation_request(self, payload: dict, headers: dict) -> dict:
        """
        Make generation API request - used by retry handler.

        Args:
            payload: API request payload
            headers: Request headers

        Returns:
            API response dictionary

        Raises:
            aiohttp.ClientError: On API errors
            NonRetryableGenerationError: On fatal errors (policy, safety, etc)
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    # Validate response has images
                    choices = result.get('choices', [])
                    if not choices:
                        raise aiohttp.ClientError("No choices in API response")

                    message = choices[0].get('message', {})
                    images = message.get('images', [])

                    if not images:
                        # Get content for error analysis
                        content = message.get('content', '')
                        
                        # Check for fatal errors that shouldn't be retried
                        content_lower = content.lower()
                        fatal_keywords = ["person", "face", "safety", "policy", "inappropriate", "unable to generate"]
                        if any(k in content_lower for k in fatal_keywords):
                            logger.warning(f"Generation refused (fatal): {content[:200]}")
                            raise NonRetryableGenerationError(content)
                            
                        logger.error(f"No images in response. Content: ```\n{content[:500]}\n```")
                        raise aiohttp.ClientError(f"No images generated. API response: {content[:200]}")

                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"API Error: {response.status} - {error_text}")
                    
                    # Check for fatal errors in 400/500 responses too
                    error_lower = error_text.lower()
                    fatal_keywords = ["person", "face", "safety", "policy", "inappropriate"]
                    if any(k in error_lower for k in fatal_keywords):
                         raise NonRetryableGenerationError(f"API rejection: {error_text[:200]}")
                         
                    raise aiohttp.ClientError(f"API returned status {response.status}: {error_text[:200]}")


    async def generate_image(
        self,
        prompt: str,
        reference_image_bytes: bytes,
        aspect_ratio: str,
        strength: float = 0.75
    ) -> Dict:
        """
        Generate image based on prompt and reference image

        Args:
            prompt: Detailed prompt
            reference_image_bytes: Original product image
            aspect_ratio: Target aspect ratio (e.g. "1:1")
            strength: Control strength (0.0 to 1.0)

        Returns:
            {
                "success": bool,
                "image_bytes": Optional[bytes],
                "error": Optional[str]
            }
        """
        start_time = time.time()
        system_prompt = None
        full_user_prompt = None
        success = False
        error_msg = None
        image_size_kb = None
        style_name = "unknown"

        try:
            # Extract style name from prompt if it contains style_name pattern
            style_name = prompt[:50] if len(prompt) > 50 else prompt

            # Convert reference image to base64
            base64_image = base64.b64encode(reference_image_bytes).decode('utf-8')

            # Determine mime type
            try:
                img = Image.open(BytesIO(reference_image_bytes))
                img_format = img.format.lower() if img.format else 'jpeg'
                mime_type = f"image/{img_format}"
            except:
                mime_type = "image/jpeg"

            # Prepare request headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://sale-photo.app-studio.online/",
                "X-Title": "Product Photoshoot Bot"
            }

            # Construct system prompt for image generation
            system_prompt = (
                "You are an advanced AI photographer specializing in product photography. "
                "Generate a photorealistic product image based on the user's prompt and the provided reference image. "
                "\n\nCRITICAL REQUIREMENTS - PRODUCT PRESERVATION:\n"
                "- PRESERVE the product's EXACT shape, form, and proportions\n"
                "- PRESERVE the product's EXACT colors, tones, and color palette\n"
                "- PRESERVE the product's EXACT texture, materials, and surface details\n"
                "- PRESERVE all unique features, labels, decorations, and craftsmanship\n"
                "- For handmade items: maintain ALL craft details, imperfections, and authentic character\n"
                "\nWHAT YOU CAN CHANGE:\n"
                "- Camera angle and perspective\n"
                "- Lighting direction, intensity, and quality\n"
                "- Background and environment\n"
                "- Product position and placement\n"
                "- Surrounding props and elements\n"
                "\nThe product must remain recognizable and identical to the reference image. "
                "Only the photography context changes, never the product itself."
            )

            full_user_prompt = (
                f"Generate a professional product photograph based on this style description: {prompt}\n\n"
                f"CRITICAL: Use the reference image as the EXACT product to photograph. "
                f"DO NOT modify the product's shape, color, texture, or any details. "
                f"The product must look IDENTICAL to the reference - only change the photography setup (angle, lighting, background, position). "
                f"For handmade items, preserve all craft features and unique characteristics. "
                f"Focus on professional composition and lighting while keeping the product unchanged."
            )

            # Convert aspect ratio to format accepted by API
            aspect_ratio_param = aspect_ratio if ":" in aspect_ratio else "1:1"
            logger.info(f"Using aspect_ratio for generation: {aspect_ratio_param} (original: {aspect_ratio})")

            # Payload for chat completion with image output
            payload = {
                "model": self.model,
                "modalities": ["text", "image"],
                "image_config": {
                    "aspect_ratio": aspect_ratio_param
                },
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": full_user_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ]
            }

            logger.info(f"Sending generation request to {self.model}...")

            # Use retry mechanism for resilient API calls
            result = await image_api_retry.execute_with_retry(
                self._make_generation_request,
                payload,
                headers
            )

            # Extract image from response (validation already done in _make_generation_request)
            message = result['choices'][0]['message']
            images = message['images']
            first_image = images[0]
            image_url_obj = first_image.get('image_url', {})
            data_url = image_url_obj.get('url', '')

            # Extract base64 data and decode
            if data_url.startswith('data:image/'):
                try:
                    base64_data = data_url.split(',', 1)[1]
                    image_bytes = base64.b64decode(base64_data)
                    image_size_kb = len(image_bytes) / 1024
                    success = True
                    logger.info(f"Successfully generated image: {image_size_kb:.1f} KB")
                    return {"success": True, "image_bytes": image_bytes, "error": None}
                except Exception as e:
                    logger.error(f"Failed to decode base64 image: {e}")
                    error_msg = f"Failed to decode image: {str(e)}"
                    return {"success": False, "image_bytes": None, "error": error_msg}
            else:
                error_msg = "Invalid image data URL format"
                logger.error(error_msg)
                return {"success": False, "image_bytes": None, "error": error_msg}

        except Exception as e:
            logger.error(f"Generation error: {e}", exc_info=True)
            error_msg = str(e)

            # Translate API errors to user-friendly Russian messages
            if "No images generated" in error_msg or "No choices" in error_msg:
                russian_error = translate_api_error_to_russian("No images in response")
            else:
                russian_error = translate_api_error_to_russian(error_msg)

            return {"success": False, "image_bytes": None, "error": russian_error}

        finally:
            # Log prompt and response for analytics
            duration_ms = (time.time() - start_time) * 1000
            try:
                PromptLogger.log_image_generation(
                    product_description="Product from reference image",
                    style_name=style_name,
                    style_prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    system_prompt=system_prompt if system_prompt else "",
                    full_user_prompt=full_user_prompt if full_user_prompt else "",
                    success=success,
                    error=error_msg,
                    duration_ms=duration_ms,
                    image_size_kb=image_size_kb
                )
            except Exception as log_err:
                logger.error(f"Failed to log image generation prompt: {log_err}")


    async def test_connection(self) -> bool:
        # Simple test
        return True
