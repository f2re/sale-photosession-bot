"""
Product Detection Service using Vision AI
"""
import aiohttp
import base64
import logging
from io import BytesIO
from typing import Dict, Optional
from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)

class ProductDetector:
    """Service for detecting and analyzing product from images using vision AI"""

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        # Use Gemini 2.0 Flash for cost-effective vision analysis
        # Cost: $0.10/M input, $0.40/M output (~$0.0011 per image)
        self.model = "google/gemini-2.0-flash-001"
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    async def detect_product(self, image_bytes: bytes) -> Dict:
        """
        Analyze product image and return detailed product description

        Args:
            image_bytes: Product image bytes

        Returns:
            {
                "success": bool,
                "product_type": str,  # e.g., "Shoes", "Watch", "Cosmetics"
                "product_name": str,  # e.g., "Premium Leather Sneakers"
                "description": str,   # Detailed description
                "category": str,      # e.g., "Fashion", "Electronics", "Beauty"
                "error": Optional[str]
            }
        """
        try:
            logger.info("Starting product detection from image...")

            # Convert image to base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')

            # Determine mime type
            try:
                img = Image.open(BytesIO(image_bytes))
                img_format = img.format.lower() if img.format else 'jpeg'
                mime_type = f"image/{img_format}"
            except:
                mime_type = "image/jpeg"

            # Prepare request headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://t.me/SalePhotosession_bot",
                "X-Title": "Product Photoshoot Bot"
            }

            # Detailed system prompt for product detection
            system_prompt = """You are a professional product analyst specializing in e-commerce and product photography.
Your task is to analyze product images and provide detailed, accurate product information.

IMPORTANT RULES:
- Identify the SPECIFIC product type (not just generic categories)
- Provide a concise, descriptive product name
- Give a detailed description including materials, style, features
- Categorize into one of: Fashion, Electronics, Beauty, Home, Food, Sports, Jewelry, Accessories, Other
- Be specific and accurate - if you see sneakers, say "Athletic Sneakers" not just "Shoes"
- Focus on what makes this product unique and marketable
- If multiple products are visible, focus on the main/primary product"""

            user_prompt = """Analyze this product image and provide detailed information in the following JSON format:

{
    "product_type": "Specific product type (e.g., 'Wireless Headphones', 'Leather Wallet', 'Face Cream') in Russian",
    "product_name": "Descriptive product name (e.g., 'Premium Over-Ear Wireless Headphones', 'Handcrafted Leather Bifold Wallet') in Russian",
    "description": "Detailed description including materials, style, features, color, distinctive characteristics",
    "category": "One of: Fashion, Electronics, Beauty, Home, Food, Sports, Jewelry, Accessories, Other"
}

Be specific, accurate, and focus on marketable product features that would be relevant for product photography."""

            # Payload for chat completion with vision
            payload = {
                "model": self.model,
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
                                "text": user_prompt
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
                "temperature": 0.3,  # Lower temperature for more consistent results
                "max_tokens": 500
            }

            logger.info(f"Sending product detection request to {self.model}...")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()

                        # Extract text response
                        choices = result.get('choices', [])
                        if not choices:
                            logger.error("No choices in API response")
                            return self._fallback_response("No response from API")

                        message = choices[0].get('message', {})
                        content = message.get('content', '').strip()

                        if not content:
                            logger.error("Empty content in API response")
                            return self._fallback_response("Empty response from API")

                        # Parse JSON response
                        try:
                            # Try to extract JSON from markdown code blocks if present
                            if '```json' in content:
                                content = content.split('```json')[1].split('```')[0].strip()
                            elif '```' in content:
                                content = content.split('```')[1].split('```')[0].strip()

                            import json
                            product_info = json.loads(content)

                            # Validate required fields
                            required_fields = ['product_type', 'product_name', 'description', 'category']
                            if not all(field in product_info for field in required_fields):
                                logger.warning(f"Missing required fields in response: {product_info}")
                                return self._fallback_response("Incomplete product information")

                            logger.info(f"Product detected: {product_info['product_type']} - {product_info['product_name']}")

                            return {
                                "success": True,
                                "product_type": product_info['product_type'],
                                "product_name": product_info['product_name'],
                                "description": product_info['description'],
                                "category": product_info['category'],
                                "error": None
                            }

                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON response: {e}")
                            logger.debug(f"Raw content: {content}")

                            # Fallback: use raw content as description
                            return {
                                "success": True,
                                "product_type": "Product",
                                "product_name": "Commercial Product",
                                "description": content[:500],  # Use first 500 chars as description
                                "category": "Other",
                                "error": None
                            }

                    else:
                        error_text = await response.text()
                        logger.error(f"API Error: {response.status} - {error_text}")
                        return self._fallback_response(f"API Error: {response.status}")

        except Exception as e:
            logger.error(f"Product detection error: {e}", exc_info=True)
            return self._fallback_response(str(e))

    def _fallback_response(self, error: str) -> Dict:
        """Return fallback response when detection fails"""
        logger.warning(f"Using fallback product detection. Error: {error}")
        return {
            "success": False,
            "product_type": "Premium Product",
            "product_name": "High-Quality Commercial Product",
            "description": "A premium commercial product requiring professional photography",
            "category": "Other",
            "error": error
        }

    async def test_connection(self) -> bool:
        """Test API connection"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://openrouter.ai/api/v1/models",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200
        except:
            return False
