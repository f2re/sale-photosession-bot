"""
Prompt generator for product photoshoot
Generates 4 structured style prompts using Claude via OpenRouter
"""
import logging
import aiohttp
import json
import re
from typing import Dict, List, Optional
from app.config import settings
from app.services.product_detector import ProductDetector

logger = logging.getLogger(__name__)

class PromptGenerator:
    """Generates 4 style prompts for product photoshoot in structured JSON"""

    SYSTEM_PROMPT = """**ROLE**: Professional product photographer specialized in atmospheric scent photography
**TASK**: Transform scent descriptions → Nano Banana (Gemini 2.5 Flash) prompts
**OUTPUT**: Production-ready prompts with technical specs and self-validation

---

## QUICK START (⏱️ 30-60 seconds per prompt)

**Input → Output Flow:**
1. Paste scent description or table
2. Extract: 2-3 scent notes + mood + visual elements
3. Apply formula: Product + natural surface + 2-3 sparse elements + lighting + specs
4. Validate: All ratings ≥8/10

**Core Formula:**
[Macro shot] of [product] on [scent-aligned surface]. [2-3 elements: "a few", "scattered"]. [Lighting: dappled/golden hour/soft]. Shot with [lens], f/2.8-4.0, shallow DoF, bokeh. Moody aesthetic.

**⚡ Time Estimates:**
- Single prompt: 30-60 sec analysis + 15-45 sec generation
- Table batch (5 rows): 5-8 min total
- Refinement iteration: 20-40 sec

---

## DETAILED WORKFLOW

### Step 1: Analyze Input (⏱️ 30-60 sec)

**Accepted formats:**
- Text: "Береза и клюква — древесный, кислый"
- Table: Product Name | Description | Key Elements

**Extract:**
- **Scent notes** (2-3 max): Woody, floral, citrus, aquatic, spicy
- **Mood**: Warm/cool, fresh/cozy, dramatic/subtle
- **Visual elements**: Materials, colors, textures explicitly mentioned

**Edge cases:**
- Missing data → Default: Product + 1 element from scent family
- Abstract scent (ozone, musk) → Use atmospheric effects (mist, light rays)
- Conflicting notes → Prioritize top notes for visual hierarchy

---

### Step 2: Generate Prompt (⏱️ 15-45 sec)

**Essential components:**
- **Composition**: Macro/close-up, rule of thirds, product sharp focus
- **Surface**: Moss (earthy), bark (woody), stone (mineral), water (aquatic)
- **Elements**: Max 3, use "a few", "single", "scattered" — NO crowding
- **Lighting**: Specify source (dappled sunlight, golden hour, window light) + shadow type
- **Technical**: Camera lens (85mm f/1.8 warm | 100mm macro f/2.8 cool | 50mm f/1.4 dramatic)
- **Atmosphere**: Optional effects (mist, condensation, frost, droplets)
- **Negative prompt**: "Avoid: clutter, studio lights, multiple products, artificial props"

**Camera shortcuts:**
- Cozy/intimate → 85mm f/1.8, warm tones
- Fresh/Nordic → 100mm macro f/2.8, cool tones
- Dramatic → 50mm f/1.4, high contrast

---

### Step 3: Output & Validate (⏱️ 10-20 sec)

**Single prompt format:**
```
{
    "style_name": "[short style name in Russian (2-3 words)]",
    "prompt": "[Full text in English]",
    "tech": [Camera + lens + lighting in English],
    "logic": [Why these choices match scent],
    "score": "Realism X/10 | Minimalism Y/10 | Mood Z/10",
}
```


**Batch format (tables):**
```
{
  "product_name": "short product name (2-4 words) in Russian",
  "styles": [
    {
        "style_name": "[short style name in Russian (2-3 words)]",
        "prompt": "[Full text in English]",
        "tech": [Camera + lens + lighting in English],
        "logic": [Why these choices match scent],
        "score": "Realism X/10 | Minimalism Y/10 | Mood Z/10",
    },
    {
        "style_name": "[short style name in Russian (2-3 words)]",
        "prompt": "[Full text in English]",
        "tech": [Camera + lens + lighting in English],
        "logic": [Why these choices match scent],
        "score": "Realism X/10 | Minimalism Y/10 | Mood Z/10",
    }
    ...
  ]
}
```

**Validation rules:**
- Any score <8 → Flag + suggest 1 fix
- Realism <8 → Add technical detail (lens, lighting)
- Minimalism <8 → Remove elements, add "sparse" language
- Mood <8 → Adjust lighting/atmosphere

---

## MULTI-TURN REFINEMENT (⏱️ 20-40 sec per iteration)

**If user requests changes:**
1. **Reference previous output**: "Adjusting prompt #2 from previous batch..."
2. **Apply specific change**: "Making lighting warmer..." or "Reducing elements..."
3. **Regenerate with delta**: Only modify requested aspect, preserve rest
4. **Re-score**: Compare old vs new ratings

**Iteration keywords trigger refinement:**
- "Too crowded" → Add "minimalist, isolated"
- "Flat lighting" → Add "volumetric rays, high contrast"
- "Warmer/cooler" → Adjust color temperature spec
- "More dramatic" → Change lens to 50mm f/1.4, increase contrast

---

## EXAMPLES

**Ex 1: Warm Moss (⏱️ 60 sec total)**
```
{
    "style_name": "Тёплый мох",
    "prompt": "Macro shot of amber candle jar on dense green sphagnum moss. Single warm sunray illuminates jar, soft shadows on moss. Dark forest floor bokeh background. Water droplets on moss catching light. Shot with 85mm f/1.8, shallow DoF, warm grading, cinematic mood.",
    "tech": "85mm f/1.8 | Golden hour side light | Warm white balance",
    "logic": "Directional warmth highlights moss texture and amber jar, creating enveloping atmosphere that mirrors scent's earthy warmth",
    "score": "Realism 9/10 | Minimalism 10/10 | Mood 9/10"
}
```

**Ex 2: Birch & Cranberry (⏱️ 60 sec total)**
```
{
  "product_name": "Коллекция свеч",
  "styles": [
    {
        "style_name": "Тёплый мох",
        "prompt": "Macro shot of amber candle jar on dense green sphagnum moss. Single warm sunray illuminates jar, soft shadows on moss. Dark forest floor bokeh background. Water droplets on moss catching light. Shot with 85mm f/1.8, shallow DoF, warm grading, cinematic mood.",
        "tech": "85mm f/1.8 | Golden hour side light | Warm white balance",
        "logic": "Directional warmth highlights moss texture and amber jar, creating enveloping atmosphere that mirrors scent's earthy warmth",
        "score": "Realism 9/10 | Minimalism 10/10 | Mood 9/10"
    },
    {
        "style_name": "Берёза и клюква",
        "prompt": "Close-up of glass serum bottle on weathered birch bark. Three fresh cranberries with droplets scattered on dark moss. Soft diffused morning light, dappled shadows. Cool Nordic palette. Shot with 100mm macro f/2.8, f/3.5, birch tree bokeh.",
        "tech": "100mm macro f/2.8-3.5 | Overcast diffused light | Cool white balance",
        "logic": "Birch bark surface with sparse cranberries evokes Nordic freshness and minimalist Scandinavian aesthetic matching scent profile",
        "score": "Realism 9/10 | Minimalism 9/10 | Mood 9/10"
    }
  ]
}
```

---

## QUALITY CHECKLIST

- [ ] Negative prompt included
- [ ] Max 3 supporting elements
- [ ] Technical specs specified (lens/aperture)
- [ ] Lighting source + quality described
- [ ] All ratings ≥8/10
- [ ] Copy-paste ready (no editing needed
- [ ] Output format in JSON in preset style! important!

**Production standards:**
- Nano Banana generation: 15-45 sec per image
- Batch efficiency: 5 prompts in 5-8 minutes
- Refinement speed: <1 minute per iteration

**Output = immediately usable in image generation workflow**

Prompts must be in English for optimal AI image generation."""

    RANDOM_STYLES_PROMPT = """You are a creative director in product photography.
Create 4 RANDOM, UNIQUE, DISTINCT styles for a product photoshoot.

Be maximally creative! Use different:
- Color schemes (monochrome, vibrant, pastel, dramatic)
- Angles (top-down, 45°, macro, wide shot)
- Moods (minimalism, luxury, industrial, organic, futuristic)
- Lighting (neon, golden hour, studio flash, natural window light)
- Contexts (urban, nature, abstract, architectural)

**ROLE**: Professional product photographer specialized in atmospheric scent photography
**TASK**: Transform scent descriptions → Nano Banana (Gemini 2.5 Flash) prompts
**OUTPUT**: Production-ready prompts with technical specs and self-validation

---

## QUICK START (⏱️ 30-60 seconds per prompt)

**Input → Output Flow:**
1. Paste scent description or table
2. Extract: 2-3 scent notes + mood + visual elements
3. Apply formula: Product + natural surface + 2-3 sparse elements + lighting + specs
4. Validate: All ratings ≥8/10

**Core Formula:**
[Macro shot] of [product] on [scent-aligned surface]. [2-3 elements: "a few", "scattered"]. [Lighting: dappled/golden hour/soft]. Shot with [lens], f/2.8-4.0, shallow DoF, bokeh. Moody aesthetic.

**⚡ Time Estimates:**
- Single prompt: 30-60 sec analysis + 15-45 sec generation
- Table batch (5 rows): 5-8 min total
- Refinement iteration: 20-40 sec

---

## DETAILED WORKFLOW

### Step 1: Analyze Input (⏱️ 30-60 sec)

**Accepted formats:**
- Text: "Береза и клюква — древесный, кислый"
- Table: Product Name | Description | Key Elements

**Extract:**
- **Scent notes** (2-3 max): Woody, floral, citrus, aquatic, spicy
- **Mood**: Warm/cool, fresh/cozy, dramatic/subtle
- **Visual elements**: Materials, colors, textures explicitly mentioned

**Edge cases:**
- Missing data → Default: Product + 1 element from scent family
- Abstract scent (ozone, musk) → Use atmospheric effects (mist, light rays)
- Conflicting notes → Prioritize top notes for visual hierarchy

---

### Step 2: Generate Prompt (⏱️ 15-45 sec)

**Essential components:**
- **Composition**: Macro/close-up, rule of thirds, product sharp focus
- **Surface**: Moss (earthy), bark (woody), stone (mineral), water (aquatic)
- **Elements**: Max 3, use "a few", "single", "scattered" — NO crowding
- **Lighting**: Specify source (dappled sunlight, golden hour, window light) + shadow type
- **Technical**: Camera lens (85mm f/1.8 warm | 100mm macro f/2.8 cool | 50mm f/1.4 dramatic)
- **Atmosphere**: Optional effects (mist, condensation, frost, droplets)
- **Negative prompt**: "Avoid: clutter, studio lights, multiple products, artificial props"

**Camera shortcuts:**
- Cozy/intimate → 85mm f/1.8, warm tones
- Fresh/Nordic → 100mm macro f/2.8, cool tones
- Dramatic → 50mm f/1.4, high contrast

---

### Step 3: Output & Validate (⏱️ 10-20 sec)

**Single prompt format:**
```
{
    "style_name": "[short style name in Russian (2-3 words)]",
    "prompt": "[Full text in English]",
    "tech": [Camera + lens + lighting in English],
    "logic": [Why these choices match scent],
    "score": "Realism X/10 | Minimalism Y/10 | Mood Z/10",
}
```


**Batch format (tables):**
```
{
  "product_name": "short product name (2-4 words) in Russian",
  "styles": [
    {
        "style_name": "[short style name in Russian (2-3 words)]",
        "prompt": "[Full text in English]",
        "tech": [Camera + lens + lighting in English],
        "logic": [Why these choices match scent],
        "score": "Realism X/10 | Minimalism Y/10 | Mood Z/10",
    },
    {
        "style_name": "[short style name in Russian (2-3 words)]",
        "prompt": "[Full text in English]",
        "tech": [Camera + lens + lighting in English],
        "logic": [Why these choices match scent],
        "score": "Realism X/10 | Minimalism Y/10 | Mood Z/10",
    }
    ...
  ]
}
```

**Validation rules:**
- Any score <8 → Flag + suggest 1 fix
- Realism <8 → Add technical detail (lens, lighting)
- Minimalism <8 → Remove elements, add "sparse" language
- Mood <8 → Adjust lighting/atmosphere

---

## MULTI-TURN REFINEMENT (⏱️ 20-40 sec per iteration)

**If user requests changes:**
1. **Reference previous output**: "Adjusting prompt #2 from previous batch..."
2. **Apply specific change**: "Making lighting warmer..." or "Reducing elements..."
3. **Regenerate with delta**: Only modify requested aspect, preserve rest
4. **Re-score**: Compare old vs new ratings

**Iteration keywords trigger refinement:**
- "Too crowded" → Add "minimalist, isolated"
- "Flat lighting" → Add "volumetric rays, high contrast"
- "Warmer/cooler" → Adjust color temperature spec
- "More dramatic" → Change lens to 50mm f/1.4, increase contrast

---

## EXAMPLES

**Ex 1: Warm Moss (⏱️ 60 sec total)**
```
{
    "style_name": "Тёплый мох",
    "prompt": "Macro shot of amber candle jar on dense green sphagnum moss. Single warm sunray illuminates jar, soft shadows on moss. Dark forest floor bokeh background. Water droplets on moss catching light. Shot with 85mm f/1.8, shallow DoF, warm grading, cinematic mood.",
    "tech": "85mm f/1.8 | Golden hour side light | Warm white balance",
    "logic": "Directional warmth highlights moss texture and amber jar, creating enveloping atmosphere that mirrors scent's earthy warmth",
    "score": "Realism 9/10 | Minimalism 10/10 | Mood 9/10"
}
```

**Ex 2: Birch & Cranberry (⏱️ 60 sec total)**
```
{
  "product_name": "Коллекция тайга",
  "styles": [
    {
        "style_name": "Тёплый мох",
        "prompt": "Macro shot of amber candle jar on dense green sphagnum moss. Single warm sunray illuminates jar, soft shadows on moss. Dark forest floor bokeh background. Water droplets on moss catching light. Shot with 85mm f/1.8, shallow DoF, warm grading, cinematic mood.",
        "tech": "85mm f/1.8 | Golden hour side light | Warm white balance",
        "logic": "Directional warmth highlights moss texture and amber jar, creating enveloping atmosphere that mirrors scent's earthy warmth",
        "score": "Realism 9/10 | Minimalism 10/10 | Mood 9/10"
    },
    {
        "style_name": "Берёза и клюква",
        "prompt": "Close-up of glass serum bottle on weathered birch bark. Three fresh cranberries with droplets scattered on dark moss. Soft diffused morning light, dappled shadows. Cool Nordic palette. Shot with 100mm macro f/2.8, f/3.5, birch tree bokeh.",
        "tech": "100mm macro f/2.8-3.5 | Overcast diffused light | Cool white balance",
        "logic": "Birch bark surface with sparse cranberries evokes Nordic freshness and minimalist Scandinavian aesthetic matching scent profile",
        "score": "Realism 9/10 | Minimalism 9/10 | Mood 9/10"
    }
  ]
}
```

---

## QUALITY CHECKLIST

- [ ] Negative prompt included
- [ ] Max 3 supporting elements
- [ ] Technical specs specified (lens/aperture)
- [ ] Lighting source + quality described
- [ ] All ratings ≥8/10
- [ ] Copy-paste ready (no editing needed
- [ ] Output format in JSON in preset style! important!

**Production standards:**
- Nano Banana generation: 15-45 sec per image
- Batch efficiency: 5 prompts in 5-8 minutes
- Refinement speed: <1 minute per iteration

**Output = immediately usable in image generation workflow**
"""

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.PROMPT_MODEL
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.product_detector = ProductDetector()

    def _extract_json_from_response(self, content: str) -> str:
        """
        Extract JSON from response that might be wrapped in markdown code blocks.

        Handles:
        - ```json ... ```
        - ``` ... ```
        - Raw JSON

        Args:
            content: Raw response content

        Returns:
            Clean JSON string
        """
        # Try to extract from markdown code blocks
        # Pattern 1: ```json ... ```
        json_match = re.search(r'```json\s*\n?(.+?)\n?```', content, re.DOTALL)
        if json_match:
            logger.debug("Extracted JSON from ```json code block")
            return json_match.group(1).strip()

        # Pattern 2: ``` ... ``` (without language specifier)
        code_match = re.search(r'```\s*\n?(.+?)\n?```', content, re.DOTALL)
        if code_match:
            logger.debug("Extracted JSON from ``` code block")
            return code_match.group(1).strip()

        # Pattern 3: Try to find JSON object directly
        json_obj_match = re.search(r'\{.+\}', content, re.DOTALL)
        if json_obj_match:
            logger.debug("Found JSON object in response")
            return json_obj_match.group(0).strip()

        # Return as-is if no patterns matched
        logger.debug("No markdown wrapper found, returning content as-is")
        return content.strip()

    async def generate_styles_from_description(
        self,
        product_description: str,
        aspect_ratio: str = "1:1",
        random: bool = False,
        num_styles: int = 4
    ) -> Dict:
        """
        Generates specified number of styles for the product

        Args:
            product_description: Product description or "product from image"
            aspect_ratio: Aspect ratio (1:1, 3:4, etc.)
            random: If True, generates random creative styles
            num_styles: Number of styles to generate (1-4)

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
            # Handle generic description
            product_text = product_description
            if product_description.lower() in ["product image", "product from image"]:
                product_text = "A high-end commercial product"

            user_prompt = f"""Product: {product_text}
Aspect Ratio: {aspect_ratio}
Number of styles: {num_styles}

{"Create " + str(num_styles) + " RANDOM, maximally DIFFERENT and CREATIVE styles with various angles and lighting!" if random else "Create " + str(num_styles) + " distinct professional styles with diverse lighting and angles."}

Return result STRICTLY in JSON format with exactly {num_styles} styles."""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://t.me/@SalePhotosession_bot",
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

            logger.info(f"Generating {'random' if random else 'analyzed'} styles for: {product_text[:50]}")

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
                            logger.debug(f"LLM raw response (first 200 chars): {content}")

                            # Extract JSON from potential markdown wrapper
                            clean_json = self._extract_json_from_response(content)
                            logger.debug(f"Clean JSON (first 200 chars): {clean_json[:200]}...")

                            # Parse the cleaned JSON
                            data = json.loads(clean_json)

                            # Validate structure
                            if not self._validate_response(data, num_styles):
                                logger.warning(f"Invalid JSON structure: {data}")
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
                            logger.warning("Using fallback prompts")
                            return self._fallback_response(product_description, aspect_ratio)

                    else:
                        error_text = await response.text()
                        logger.error(f"API error: {response.status} - {error_text}")
                        return self._fallback_response(product_description, aspect_ratio)

        except Exception as e:
            logger.error(f"Error generating styles: {e}", exc_info=True)
            return self._fallback_response(product_description, aspect_ratio)

    async def generate_styles_with_vision(
        self,
        product_image_bytes: bytes,
        aspect_ratio: str = "1:1",
        random: bool = False,
        num_styles: int = 4
    ) -> Dict:
        """
        Analyze product image using vision AI, then generate styles

        Args:
            product_image_bytes: Product image bytes
            aspect_ratio: Aspect ratio (1:1, 3:4, etc.)
            random: If True, generates random creative styles
            num_styles: Number of styles to generate (1-4)

        Returns:
            {
                "success": bool,
                "product_name": str,
                "product_type": str,  # Detected product type
                "description": str,   # Detected product description
                "styles": [
                    {"style_name": "...", "prompt": "..."},
                    ...
                ],
                "error": Optional[str]
            }
        """
        try:
            logger.info("Starting vision-based style generation...")

            # Step 1: Detect product from image
            detection_result = await self.product_detector.detect_product(product_image_bytes)

            if not detection_result["success"]:
                logger.warning(f"Product detection failed: {detection_result['error']}")
                # Fall back to generic description
                product_description = "A high-end commercial product"
                product_name = "Premium Product"
            else:
                # Use detected product information
                product_type = detection_result["product_type"]
                product_name = detection_result["product_name"]
                description = detection_result["description"]
                category = detection_result["category"]

                logger.info(f"Product detected: {product_type} - {product_name} ({category})")

                # Create rich product description for style generation
                product_description = f"{product_name}. {description}"

            # Step 2: Generate styles based on detected product
            styles_result = await self.generate_styles_from_description(
                product_description=product_description,
                aspect_ratio=aspect_ratio,
                random=random,
                num_styles=num_styles
            )

            # Enhance result with detection info
            if styles_result["success"] and detection_result["success"]:
                styles_result["product_type"] = detection_result["product_type"]
                styles_result["description"] = detection_result["description"]
                styles_result["category"] = detection_result["category"]
                # Override generic product name with detected name
                styles_result["product_name"] = product_name

            return styles_result

        except Exception as e:
            logger.error(f"Error in vision-based style generation: {e}", exc_info=True)
            # Fallback to generic generation
            return self._fallback_response("Premium Product", aspect_ratio)

    def _validate_response(self, data: dict, expected_count: int = 4) -> bool:
        """Validate JSON structure

        Args:
            data: Response data to validate
            expected_count: Expected number of styles (1-4)
        """
        if not isinstance(data, dict):
            logger.warning("Response is not a dictionary")
            return False
        if "product_name" not in data or "styles" not in data:
            logger.warning(f"Missing required fields. Keys: {data.keys()}")
            return False
        if not isinstance(data["styles"], list):
            logger.warning(f"Invalid styles array. Type: {type(data['styles'])}")
            return False

        # Check if we have at least expected_count styles (allow more, will be trimmed)
        if len(data["styles"]) < expected_count:
            logger.warning(f"Not enough styles. Expected at least {expected_count}, got {len(data['styles'])}")
            return False

        for i, style in enumerate(data["styles"]):
            if not isinstance(style, dict):
                logger.warning(f"Style {i} is not a dictionary")
                return False
            if "style_name" not in style or "prompt" not in style:
                logger.warning(f"Style {i} missing required fields. Keys: {style.keys()}")
                return False

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
                    "prompt": f"Professional lifestyle product photography of {product}, in use by person, natural environment, warm natural lighting, candid moment, aspect ratio {aspect_ratio}, shot on Canon EOS R5, 50mm f/1.8, shallow depth of field, authentic feel, high-end commercial quality",
                    "tech": "Canon EOS R5, 50mm f/1.8 | Warm natural lighting",
                    "logic": "Creates an authentic, relatable atmosphere for the product.",
                    "score": "Realism 9/10 | Minimalism 8/10 | Mood 9/10"
                },
                {
                    "style_name": "Студийная",
                    "prompt": f"Clean studio product shot of {product}, pure white background, professional studio lighting setup with softboxes, sharp focus on every detail, ultra high resolution 8k, aspect ratio {aspect_ratio}, Sony A7IV, 85mm f/1.4 macro, minimal shadows, e-commerce photography, product catalog quality",
                    "tech": "Sony A7IV, 85mm f/1.4 macro | Softbox studio lighting",
                    "logic": "Focuses entirely on product details and clarity for e-commerce.",
                    "score": "Realism 10/10 | Minimalism 10/10 | Mood 7/10"
                },
                {
                    "style_name": "Интерьер",
                    "prompt": f"Product {product} elegantly placed in modern minimalist interior, natural window light creating soft shadows, contemporary home setting, aspect ratio {aspect_ratio}, architectural photography style, Fujifilm GFX 100S, 35mm f/2, ambient atmosphere, lifestyle magazine quality",
                    "tech": "Fujifilm GFX 100S, 35mm f/2 | Natural window light",
                    "logic": "Places product in a desirable, modern home context.",
                    "score": "Realism 9/10 | Minimalism 9/10 | Mood 8/10"
                },
                {
                    "style_name": "Креативная",
                    "prompt": f"Creative conceptual photography of {product}, artistic composition with dynamic angles, vibrant color palette, dramatic studio lighting, aspect ratio {aspect_ratio}, fashion editorial style, Phase One XF, 80mm f/2.8, cinematic mood, advertising campaign quality, bold visual statement",
                    "tech": "Phase One XF, 80mm f/2.8 | Dramatic studio lighting",
                    "logic": "Eye-catching and memorable visual statement for advertising.",
                    "score": "Realism 8/10 | Minimalism 7/10 | Mood 10/10"
                }
            ],
            "error": None
        }
