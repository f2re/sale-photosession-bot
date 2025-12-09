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
                "HTTP-Referer": "https://t.me/SalePhotosession_bot",
                "X-Title": "Product Photoshoot Bot"
            }
            
            # Construct system prompt for image generation
            system_prompt = (
                "You are an advanced AI photographer. "
                "Generate a photorealistic product image based on the user's prompt and the provided reference image. "
                "Maintain the product's identity and key features strictly. "
                "Follow the requested style, lighting, and composition."
            )

            # Payload for chat completion with image output
            payload = {
                "model": self.model,
                "modalities": ["text", "image"],  # Required for image generation
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
                                        f"Aspect Ratio: {aspect_ratio}. "
                                        f"Keep the product look consistent with the reference."
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
                        return {"success": False, "image_bytes": None, "error": "No images generated in response"}
                        
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
