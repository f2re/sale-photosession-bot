"""
NanoBanana Image Generation Service (via OpenRouter)
"""
import aiohttp
import base64
import logging
from io import BytesIO
from typing import Dict
from PIL import Image

from app.config import settings

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


class NanoBananaService:
    """Service for generating images via OpenRouter"""

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.IMAGE_MODEL # e.g., google/gemini-2.0-flash-001 or similar capable of image output
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

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
        try:
            # Convert reference image to base64
            base64_image = base64.b64encode(reference_image_bytes).decode('utf-8')

            # Determine mime type
            try:
                img = Image.open(BytesIO(reference_image_bytes))
                img_format = img.format.lower() if img.format else 'jpeg'
                mime_type = f"image/{img_format}"
            except:
                mime_type = "image/jpeg"

            # Prepare request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://sale-photo.app-studio.online/",
                "X-Title": "Product Photoshoot Bot"
            }

            # Construct system prompt for image generation
            system_prompt = (
                "You are an advanced AI photographer. "
                "Generate a photorealistic product image based on the user's prompt and the provided reference image. "
                "Maintain the product's identity and key features strictly. "
                "Follow the requested style, lighting, and composition."
            )

            # Convert aspect ratio to format accepted by API (e.g., "1:1" -> "1:1")
            aspect_ratio_param = aspect_ratio if ":" in aspect_ratio else "1:1"
            logger.info(f"Using aspect_ratio for generation: {aspect_ratio_param} (original: {aspect_ratio})")

            # Payload for chat completion with image output
            # Using image_config for Gemini 2.5 Flash as per OpenRouter documentation
            payload = {
                "model": self.model,
                "modalities": ["text", "image"],  # Required for image generation
                "image_config": {
                    "aspect_ratio": aspect_ratio_param  # Correct parameter structure for Gemini
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
                                "text": f"Generate an image of this product based on this description: {prompt}. "
                                        f"Keep the product look consistent with the reference. "
                                        f"Maintain high quality and professional composition."
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
            logger.debug(payload)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        result = await response.json()

                        # Extract image from response
                        # OpenRouter returns images in the message.images field
                        # Response format:
                        # {
                        #   "choices": [{
                        #     "message": {
                        #       "role": "assistant",
                        #       "content": "...",
                        #       "images": [{
                        #         "type": "image_url",
                        #         "image_url": {
                        #           "url": "data:image/png;base64,..."
                        #         }
                        #       }]
                        #     }
                        #   }]
                        # }

                        choices = result.get('choices', [])
                        if not choices:
                            return {"success": False, "image_bytes": None, "error": "No output from API"}

                        message = choices[0].get('message', {})
                        images = message.get('images', [])

                        # Check if we have images in the response
                        if images and len(images) > 0:
                            # Extract the first image
                            first_image = images[0]
                            image_url_obj = first_image.get('image_url', {})
                            data_url = image_url_obj.get('url', '')

                            # data_url format: "data:image/png;base64,iVBORw0KGgo..."
                            if data_url.startswith('data:image/'):
                                # Extract base64 data after the comma
                                try:
                                    base64_data = data_url.split(',', 1)[1]
                                    image_bytes = base64.b64decode(base64_data)
                                    return {"success": True, "image_bytes": image_bytes, "error": None}
                                except Exception as e:
                                    logger.error(f"Failed to decode base64 image: {e}")
                                    return {"success": False, "image_bytes": None, "error": f"Failed to decode image: {str(e)}"}
                            else:
                                return {"success": False, "image_bytes": None, "error": "Invalid image data URL format"}

                        # No images in response
                        content = message.get('content', '')
                        logger.error(f"No images in response. Content: {content[:200]}")
                        logger.debug(f"Full response: {result}")

                        # Translate error to Russian for user
                        russian_error = translate_api_error_to_russian(content)
                        return {"success": False, "image_bytes": None, "error": russian_error}

                    else:
                        error_text = await response.text()
                        logger.error(f"API Error: {response.status} - {error_text}")
                        return {"success": False, "image_bytes": None, "error": f"API Error: {response.status}"}

        except Exception as e:
            logger.error(f"Generation error: {e}", exc_info=True)
            return {"success": False, "image_bytes": None, "error": str(e)}

    async def test_connection(self) -> bool:
        # Simple test
        return True
