"""
Prompt generator for product photoshoot
Generates 4 structured style prompts using Claude via OpenRouter
"""
import logging
import aiohttp
import json
from typing import Dict, List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class PromptGenerator:
    """Generates 4 style prompts for product photoshoot in structured JSON"""
    
    SYSTEM_PROMPT = """You are an expert in product photography and creative direction.
Your task is to analyze the product description and create 4 unique, professional
prompts for generating product photography in different styles.

IMPORTANT: The response MUST be valid JSON with the following structure:
{
  "product_name": "short product name (2-4 words)",
  "styles": [
    {
      "style_name": "short style name in Russian (2-3 words)",
      "prompt": "detailed prompt in English for image generation"
    },
    {
      "style_name": "...",
      "prompt": "..."
    },
    {
      "style_name": "...",
      "prompt": "..."
    },
    {
      "style_name": "...",
      "prompt": "..."
    }
  ]
}

The 4 styles MUST be distinctly different:
1. Lifestyle / In-use (product in use, natural environment)
2. Studio / Clean (studio shot, clean background, focus on details)
3. Interior / Context (product in interior, atmosphere)
4. Creative / Artistic (creative concept, artistic approach)

Each prompt must contain:
- Composition and angle description
- Lighting (natural, studio, dramatic, soft, etc.)
- Color palette and mood
- Technical specs (camera, lens, aperture)
- Environment details

Prompts must be in English for optimal AI image generation."""

    RANDOM_STYLES_PROMPT = """You are a creative director in product photography.
Create 4 RANDOM, UNIQUE, DISTINCT styles for a product photoshoot.

Be maximally creative! Use different:
- Color schemes (monochrome, vibrant, pastel, dramatic)
- Angles (top-down, 45°, macro, wide shot)
- Moods (minimalism, luxury, industrial, organic, futuristic)
- Lighting (neon, golden hour, studio flash, natural window light)
- Contexts (urban, nature, abstract, architectural)

IMPORTANT: Response must be in the same JSON format:
{
  "product_name": "short product name",
  "styles": [
    {"style_name": "style name (Russian)", "prompt": "detailed prompt (English)"},
    ...4 styles...
  ]
}"""

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.PROMPT_MODEL
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
    
    async def generate_styles_from_description(
        self,
        product_description: str,
        aspect_ratio: str = "1:1",
        random: bool = False
    ) -> Dict:
        """
        Generates 4 styles for the product
        
        Args:
            product_description: Product description or "product from image"
            aspect_ratio: Aspect ratio (1:1, 3:4, etc.)
            random: If True, generates random creative styles
            
        Returns:
            {
                "success": bool,
                "product_name": str,
                "styles": [
                    {"style_name": "...", "prompt": "..."},
                    ...
                ],
                "error": Optional[str]
            }
        """
        try:
            user_prompt = f"""Product: {product_description}
Aspect Ratio: {aspect_ratio}

{"Create 4 RANDOM, maximally DIFFERENT and CREATIVE styles!" if random else "Create 4 classic professional styles for this product."}

Return result STRICTLY in JSON format."""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://product-photoshoot-bot.com",
                "X-Title": "Product Photoshoot Bot"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": self.RANDOM_STYLES_PROMPT if random else self.SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                "temperature": 0.9 if random else 0.7,
                "max_tokens": 2000,
                "response_format": {"type": "json_object"}
            }
            
            logger.info(f"Generating {'random' if random else 'analyzed'} styles for: {product_description[:50]}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        
                        # Parse JSON
                        try:
                            data = json.loads(content)
                            
                            # Validate structure
                            if not self._validate_response(data):
                                raise ValueError("Invalid JSON structure")
                            
                            logger.info(f"Successfully generated styles for: {data.get('product_name', 'unknown')}")
                            
                            return {
                                "success": True,
                                "product_name": data["product_name"],
                                "styles": data["styles"],
                                "error": None
                            }
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON response: {e}")
                            logger.debug(f"Response content: {content}")
                            return self._fallback_response(product_description, aspect_ratio)
                    
                    else:
                        error_text = await response.text()
                        logger.error(f"API error: {response.status} - {error_text}")
                        return self._fallback_response(product_description, aspect_ratio)
                        
        except Exception as e:
            logger.error(f"Error generating styles: {e}", exc_info=True)
            return self._fallback_response(product_description, aspect_ratio)
    
    def _validate_response(self, data: dict) -> bool:
        """Validate JSON structure"""
        if not isinstance(data, dict): return False
        if "product_name" not in data or "styles" not in data: return False
        if not isinstance(data["styles"], list) or len(data["styles"]) != 4: return False
        
        for style in data["styles"]:
            if not isinstance(style, dict): return False
            if "style_name" not in style or "prompt" not in style: return False
        
        return True
    
    def _fallback_response(self, product: str, aspect_ratio: str) -> Dict:
        """Fallback if generation fails"""
        logger.warning("Using fallback prompts")
        
        return {
            "success": True,
            "product_name": "Product",
            "styles": [
                {
                    "style_name": "Lifestyle",
                    "prompt": f"Professional lifestyle product photography, in use by person, natural environment, warm natural lighting, candid moment, aspect ratio {aspect_ratio}, shot on Canon EOS R5, 50mm f/1.8, shallow depth of field, authentic feel, high-end commercial quality"
                },
                {
                    "style_name": "Студийная",
                    "prompt": f"Clean studio product shot, pure white background, professional studio lighting setup with softboxes, sharp focus on every detail, ultra high resolution 8k, aspect ratio {aspect_ratio}, Sony A7IV, 85mm f/1.4 macro, minimal shadows, e-commerce photography, product catalog quality"
                },
                {
                    "style_name": "Интерьер",
                    "prompt": f"Product elegantly placed in modern minimalist interior, natural window light creating soft shadows, contemporary home setting, aspect ratio {aspect_ratio}, architectural photography style, Fujifilm GFX 100S, 35mm f/2, ambient atmosphere, lifestyle magazine quality"
                },
                {
                    "style_name": "Креативная",
                    "prompt": f"Creative conceptual photography, artistic composition with dynamic angles, vibrant color palette, dramatic studio lighting, aspect ratio {aspect_ratio}, fashion editorial style, Phase One XF, 80mm f/2.8, cinematic mood, advertising campaign quality, bold visual statement"
                }
            ],
            "error": None
        }
