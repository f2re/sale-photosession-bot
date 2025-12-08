Отлично! Теперь создам полный переработанный план с учётом всех требований.

# План разработки Product Photoshoot Bot v2.0

## Обновлённая архитектура с NanoBanana и управлением стилями

### Ключевые изменения

1. **Единый промпт для генерации 4 стилей** - структурированный JSON ответ
2. **Интерфейс выбора пропорций и стилей** - через inline клавиатуры
3. **Случайные стили для вдохновения** - генератор разнообразных стилей
4. **Интеграция NanoBanana API** - вместо OpenRouter для генерации изображений
5. **Сохранение пользовательских стилей** - до 4 стилей с названиями
6. **FSM (Finite State Machine)** - для управления многошаговым процессом

***

## Структура проекта (обновлённая)

```
product-photoshoot-bot/
├── bot.py
├── alembic/
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── bot.py
│   ├── config.py                    # ✅ Скопировать + модифицировать
│   ├── database/
│   │   ├── __init__.py              # ✅ Скопировать
│   │   ├── models.py                # 🔄 Скопировать + ДОБАВИТЬ StylePreset
│   │   └── crud.py                  # 🔄 Скопировать + ДОБАВИТЬ CRUD для стилей
│   ├── handlers/
│   │   ├── __init__.py              # 🔄 Модифицировать
│   │   ├── user.py                  # 🔄 СУЩЕСТВЕННАЯ модификация
│   │   ├── style_management.py      # ⭐ НОВЫЙ файл
│   │   ├── admin.py                 # ✅ Скопировать + тексты
│   │   ├── payment.py               # ✅ Скопировать + тексты
│   │   ├── support.py               # ✅ Скопировать + тексты
│   │   ├── batch_processing.py      # 🔄 Адаптировать
│   │   └── common.py                # ✅ Скопировать
│   ├── keyboards/
│   │   ├── __init__.py
│   │   ├── inline.py                # 🔄 ДОБАВИТЬ новые клавиатуры
│   │   └── reply.py                 # ✅ Скопировать
│   ├── middlewares/
│   │   ├── __init__.py              # ✅ Скопировать
│   │   └── db.py                    # ✅ Скопировать
│   ├── services/
│   │   ├── __init__.py
│   │   ├── prompt_generator.py      # ⭐ НОВЫЙ - единый JSON промпт
│   │   ├── nanobanana.py            # ⭐ НОВЫЙ - API NanoBanana
│   │   ├── image_processor.py       # 🔄 Переработать под новый флоу
│   │   ├── style_manager.py         # ⭐ НОВЫЙ - управление стилями
│   │   ├── yookassa.py              # ✅ Скопировать
│   │   ├── notification_service.py  # ✅ Скопировать + тексты
│   │   ├── payment_checker.py       # ✅ Скопировать
│   │   └── yandex_metrika.py        # ✅ Скопировать
│   ├── utils/
│   │   ├── __init__.py
│   │   └── helpers.py               # ✅ Скопировать
│   └── states.py                    # ⭐ НОВЫЙ - FSM состояния
├── requirements.txt                 # 🔄 ДОБАВИТЬ зависимости
├── Dockerfile                       # ✅ Скопировать
├── docker-compose.yml               # ✅ Скопировать + имена
├── .env.example                     # 🔄 ДОБАВИТЬ новые переменные
└── README.md                        # 🔄 Переписать
```

***

## Детальный план файлов

### 1. Config (`app/config.py`)

**Источник:** [photo-portrait-bot/app/config.py](https://github.com/f2re/photo-portrait-bot/blob/main/app/config.py)

**Модификации:**

```python
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str
    BOT_USERNAME: str
    ADMIN_IDS: str
    
    # Database
    DATABASE_URL: Optional[str] = None
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "product_photoshoot_bot"
    DB_USER: str = "product_user"
    DB_PASSWORD: str = ""
    
    # ⭐ НОВОЕ: OpenRouter для промптов (Claude)
    OPENROUTER_API_KEY: str
    PROMPT_MODEL: str = "anthropic/claude-3.5-sonnet"  # Для генерации промптов
    
    # YooKassa
    YOOKASSA_SHOP_ID: str
    YOOKASSA_SECRET_KEY: str
    YOOKASSA_RETURN_URL: str = "https://t.me/your_product_bot"
    
    # ⭐ НОВОЕ: Пакеты (адаптировать под товарную съемку)
    PACKAGE_1_NAME: str = "Стартовый"
    PACKAGE_1_PHOTOSHOOTS: int = 3  # фотосессий (каждая = 4 фото)
    PACKAGE_1_PRICE: int = 299
    
    PACKAGE_2_NAME: str = "Бизнес"
    PACKAGE_2_PHOTOSHOOTS: int = 10
    PACKAGE_2_PRICE: int = 799
    
    PACKAGE_3_NAME: str = "Профессиональный"
    PACKAGE_3_PHOTOSHOOTS: int = 30
    PACKAGE_3_PRICE: int = 1999
    
    PACKAGE_4_NAME: str = "Безлимитный"
    PACKAGE_4_PHOTOSHOOTS: int = 100
    PACKAGE_4_PRICE: int = 4999
    
    # ⭐ НОВОЕ: Настройки фотосессий
    FREE_PHOTOSHOOTS_COUNT: int = 2  # Бесплатных фотосессий для новых
    PHOTOS_PER_PHOTOSHOOT: int = 4  # Фото в одной фотосессии
    MAX_SAVED_STYLES: int = 4  # Максимум сохранённых стилей
    
    # ⭐ НОВОЕ: Доступные пропорции
    AVAILABLE_ASPECT_RATIOS: List[str] = [
        "1:1",    # Квадрат (Instagram)
        "3:4",    # Вертикаль (Stories)
        "4:3",    # Горизонталь
        "16:9",   # Широкий (YouTube)
        "9:16"    # Вертикальный (TikTok)
    ]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Yandex Metrika (optional)
    YANDEX_METRIKA_COUNTER_ID: Optional[str] = None
    YANDEX_METRIKA_TOKEN: Optional[str] = None
    METRIKA_GOAL_START: str = "start_bot"
    METRIKA_GOAL_FIRST_PHOTOSHOOT: str = "first_photoshoot"
    METRIKA_GOAL_PURCHASE: str = "purchase"
    METRIKA_UPLOAD_INTERVAL: int = 3600
    
    # Referral Program
    REFERRAL_REWARD_START: int = 1  # фотосессий при старте реферала
    REFERRAL_REWARD_PURCHASE_PERCENT: int = 10
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def admin_ids_list(self) -> List[int]:
        return [int(id.strip()) for id in self.ADMIN_IDS.split(",") if id.strip()]
    
    @property
    def packages_config(self) -> List[dict]:
        """Пакеты фотосессий"""
        return [
            {
                "name": self.PACKAGE_1_NAME,
                "photoshoots_count": self.PACKAGE_1_PHOTOSHOOTS,
                "price_rub": self.PACKAGE_1_PRICE
            },
            {
                "name": self.PACKAGE_2_NAME,
                "photoshoots_count": self.PACKAGE_2_PHOTOSHOOTS,
                "price_rub": self.PACKAGE_2_PRICE
            },
            {
                "name": self.PACKAGE_3_NAME,
                "photoshoots_count": self.PACKAGE_3_PHOTOSHOOTS,
                "price_rub": self.PACKAGE_3_PRICE
            },
            {
                "name": self.PACKAGE_4_NAME,
                "photoshoots_count": self.PACKAGE_4_PHOTOSHOOTS,
                "price_rub": self.PACKAGE_4_PRICE
            }
        ]
    
    @property
    def is_metrika_enabled(self) -> bool:
        return bool(self.YANDEX_METRIKA_COUNTER_ID and self.YANDEX_METRIKA_TOKEN)

settings = Settings()
```

***

### 2. Database Models (`app/database/models.py`)

**Источник:** [photo-portrait-bot/app/database/models.py](https://github.com/f2re/photo-portrait-bot/blob/main/app/database/models.py)

**Модификации:** ДОБАВИТЬ новую модель StylePreset

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# ✅ User - скопировать из исходника БЕЗ изменений
class User(Base):
    __tablename__ = "users"
    # ... (весь код из photo-portrait-bot/app/database/models.py)

# ✅ Payment - скопировать из исходника БЕЗ изменений
class Payment(Base):
    __tablename__ = "payments"
    # ... (весь код из photo-portrait-bot)

# 🔄 ProcessedImage - МОДИФИЦИРОВАТЬ: добавить поля
class ProcessedImage(Base):
    __tablename__ = "processed_images"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    telegram_file_id = Column(String, nullable=True)
    
    # ⭐ НОВОЕ: добавить информацию о стиле
    style_name = Column(String, nullable=True)  # Название стиля
    prompt_used = Column(Text, nullable=True)   # Использованный промпт
    aspect_ratio = Column(String, nullable=True) # Пропорции (1:1, 3:4 и т.д.)
    
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    user = relationship("User", back_populates="processed_images")

# ⭐ НОВАЯ МОДЕЛЬ: StylePreset
class StylePreset(Base):
    """Сохранённые пользовательские стили"""
    __tablename__ = "style_presets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Название стиля (задаёт пользователь)
    name = Column(String(100), nullable=False)  # напр. "Минимализм белый фон"
    
    # Параметры стиля (JSON)
    style_data = Column(JSON, nullable=False)
    # Структура style_data:
    # {
    #     "product_name": "...",
    #     "aspect_ratio": "1:1",
    #     "prompts": [
    #         {"style": "...", "prompt": "..."},
    #         {"style": "...", "prompt": "..."},
    #         {"style": "...", "prompt": "..."},
    #         {"style": "...", "prompt": "..."}
    #     ]
    # }
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationship
    user = relationship("User", back_populates="style_presets")

# Обновить User модель: добавить relationships
# В классе User добавить:
# processed_images = relationship("ProcessedImage", back_populates="user")
# style_presets = relationship("StylePreset", back_populates="user")
```

***

### 3. Database CRUD (`app/database/crud.py`)

**Источник:** [photo-portrait-bot/app/database/crud.py](https://github.com/f2re/photo-portrait-bot/blob/main/app/database/crud.py)

**Действие:** Скопировать весь файл + ДОБАВИТЬ функции для StylePreset

```python
# ✅ Скопировать все существующие CRUD функции из исходника

# ⭐ ДОБАВИТЬ в конец файла:

async def create_style_preset(
    session: AsyncSession,
    user_id: int,
    name: str,
    style_data: dict
) -> StylePreset:
    """Создать сохранённый стиль"""
    preset = StylePreset(
        user_id=user_id,
        name=name,
        style_data=style_data
    )
    session.add(preset)
    await session.commit()
    await session.refresh(preset)
    return preset

async def get_user_style_presets(
    session: AsyncSession,
    user_id: int,
    active_only: bool = True
) -> List[StylePreset]:
    """Получить все стили пользователя"""
    query = select(StylePreset).where(StylePreset.user_id == user_id)
    if active_only:
        query = query.where(StylePreset.is_active == True)
    query = query.order_by(StylePreset.created_at.desc())
    result = await session.execute(query)
    return result.scalars().all()

async def get_style_preset_by_id(
    session: AsyncSession,
    preset_id: int,
    user_id: int
) -> Optional[StylePreset]:
    """Получить стиль по ID"""
    query = select(StylePreset).where(
        StylePreset.id == preset_id,
        StylePreset.user_id == user_id,
        StylePreset.is_active == True
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def update_style_preset(
    session: AsyncSession,
    preset_id: int,
    user_id: int,
    name: Optional[str] = None,
    style_data: Optional[dict] = None
) -> Optional[StylePreset]:
    """Обновить стиль"""
    preset = await get_style_preset_by_id(session, preset_id, user_id)
    if not preset:
        return None
    
    if name:
        preset.name = name
    if style_data:
        preset.style_data = style_data
    
    await session.commit()
    await session.refresh(preset)
    return preset

async def delete_style_preset(
    session: AsyncSession,
    preset_id: int,
    user_id: int
) -> bool:
    """Удалить стиль (мягкое удаление)"""
    preset = await get_style_preset_by_id(session, preset_id, user_id)
    if not preset:
        return False
    
    preset.is_active = False
    await session.commit()
    return True

async def count_user_active_presets(
    session: AsyncSession,
    user_id: int
) -> int:
    """Подсчитать активные стили пользователя"""
    query = select(func.count(StylePreset.id)).where(
        StylePreset.user_id == user_id,
        StylePreset.is_active == True
    )
    result = await session.execute(query)
    return result.scalar() or 0
```

***

### 4. FSM States (`app/states.py`) - ⭐ НОВЫЙ ФАЙЛ

```python
"""FSM состояния для многошагового процесса создания фотосессии"""
from aiogram.fsm.state import State, StatesGroup

class PhotoshootStates(StatesGroup):
    """Состояния процесса создания фотосессии"""
    
    # Ожидание загрузки фото товара
    waiting_for_product_photo = State()
    
    # Выбор пропорций
    selecting_aspect_ratio = State()
    
    # Выбор стилей (анализ / случайные / свои)
    selecting_styles_method = State()
    
    # Просмотр предложенных стилей и выбор
    reviewing_suggested_styles = State()
    
    # Генерация фотосессии
    generating_photoshoot = State()
    
    # Сохранение стиля
    saving_style_name = State()

class StyleManagementStates(StatesGroup):
    """Состояния управления стилями"""
    
    # Просмотр сохранённых стилей
    viewing_saved_styles = State()
    
    # Редактирование названия стиля
    editing_style_name = State()
```

***

### 5. Prompt Generator (`app/services/prompt_generator.py`) - ⭐ НОВЫЙ

```python
"""
Генератор промптов для фотосессии товара
Возвращает структурированный JSON с 4 стилями
"""
import logging
import aiohttp
import json
from typing import Dict, List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class PromptGenerator:
    """Генерирует 4 промпта для фотосессии товара в структурированном JSON"""
    
    SYSTEM_PROMPT = """Ты - эксперт в product photography и creative direction.
Твоя задача - проанализировать товар и создать 4 уникальных, профессиональных 
промпта для генерации фотографий в разных стилях.

ВАЖНО: Ответ ДОЛЖЕН быть валидным JSON следующей структуры:
{
  "product_name": "краткое название товара (2-4 слова)",
  "styles": [
    {
      "style_name": "краткое название стиля (2-3 слова на русском)",
      "prompt": "детальный промпт на английском для генерации"
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

4 стиля ДОЛЖНЫ быть максимально разными:
1. Lifestyle / In-use (товар в использовании, естественная среда)
2. Studio / Clean (студийная съемка, чистый фон, акцент на детали)
3. Interior / Context (товар в интерьере, атмосфера)
4. Creative / Artistic (креативная концепция, художественный подход)

Каждый prompt должен содержать:
- Описание композиции и ракурса
- Освещение (natural, studio, dramatic, soft и т.д.)
- Цветовую палитру и mood
- Технические параметры (camera, lens, aperture)
- Детали окружения

Промпты на английском для оптимальной работы с image generation AI."""

    RANDOM_STYLES_PROMPT = """Ты - креативный директор в product photography.
Создай 4 СЛУЧАЙНЫХ, УНИКАЛЬНЫХ, НЕ ПОХОЖИХ друг на друга стиля для фотосессии товара.

Будь максимально креативным! Используй разные:
- Цветовые схемы (монохром, vibrant, pastel, dramatic)
- Ракурсы (top-down, 45°, macro, wide shot)
- Настроения (минимализм, luxury, industrial, organic, futuristic)
- Освещение (neon, golden hour, studio flash, natural window light)
- Контексты (urban, nature, abstract, architectural)

ВАЖНО: Ответ в том же JSON формате:
{
  "product_name": "краткое название товара",
  "styles": [
    {"style_name": "название стиля", "prompt": "детальный промпт"},
    ...4 стиля...
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
        Генерирует 4 стиля для товара
        
        Args:
            product_description: Описание товара
            aspect_ratio: Пропорции (1:1, 3:4, и т.д.)
            random: Если True - генерирует случайные креативные стили
            
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
            user_prompt = f"""Товар: {product_description}
Пропорции фото: {aspect_ratio}

{"Создай 4 СЛУЧАЙНЫХ, максимально РАЗНЫХ и КРЕАТИВНЫХ стиля!" if random else "Создай 4 классических профессиональных стиля для этого товара."}

Верни результат СТРОГО в JSON формате."""

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
                "response_format": {"type": "json_object"}  # Требуем JSON
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
                        
                        # Парсим JSON
                        try:
                            data = json.loads(content)
                            
                            # Валидация структуры
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
        """Валидация JSON структуры"""
        if not isinstance(data, dict):
            return False
        
        if "product_name" not in data or "styles" not in data:
            return False
        
        if not isinstance(data["styles"], list) or len(data["styles"]) != 4:
            return False
        
        for style in data["styles"]:
            if not isinstance(style, dict):
                return False
            if "style_name" not in style or "prompt" not in style:
                return False
        
        return True
    
    def _fallback_response(self, product: str, aspect_ratio: str) -> Dict:
        """Fallback если генерация не удалась"""
        logger.warning("Using fallback prompts")
        
        return {
            "success": True,
            "product_name": product[:30],
            "styles": [
                {
                    "style_name": "Lifestyle",
                    "prompt": f"Professional lifestyle product photography of {product}, in use by person, natural environment, warm natural lighting, candid moment, aspect ratio {aspect_ratio}, shot on Canon EOS R5, 50mm f/1.8, shallow depth of field, authentic feel, high-end commercial quality"
                },
                {
                    "style_name": "Студийная съемка",
                    "prompt": f"Clean studio product shot of {product}, pure white background, professional studio lighting setup with softboxes, sharp focus on every detail, ultra high resolution 8k, aspect ratio {aspect_ratio}, Sony A7IV, 85mm f/1.4 macro, minimal shadows, e-commerce photography, product catalog quality"
                },
                {
                    "style_name": "Интерьер",
                    "prompt": f"{product} elegantly placed in modern minimalist interior, natural window light creating soft shadows, contemporary home setting, aspect ratio {aspect_ratio}, architectural photography style, Fujifilm GFX 100S, 35mm f/2, ambient atmosphere, lifestyle magazine quality"
                },
                {
                    "style_name": "Креативная",
                    "prompt": f"Creative conceptual photography of {product}, artistic composition with dynamic angles, vibrant color palette, dramatic studio lighting, aspect ratio {aspect_ratio}, fashion editorial style, Phase One XF, 80mm f/2.8, cinematic mood, advertising campaign quality, bold visual statement"
                }
            ],
            "error": None
        }
```

***

### 7. Style Manager (`app/services/style_manager.py`) - ⭐ НОВЫЙ

```python
"""
Управление пользовательскими стилями
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
    """Управление сохранёнными стилями пользователя"""
    
    @staticmethod
    async def save_style(
        session: AsyncSession,
        user_id: int,
        name: str,
        product_name: str,
        aspect_ratio: str,
        styles: List[Dict]
    ) -> Dict:
        """
        Сохранить новый стиль
        
        Args:
            session: DB сессия
            user_id: ID пользователя
            name: Название стиля (от пользователя)
            product_name: Название товара
            aspect_ratio: Пропорции
            styles: Список из 4 стилей [{"style_name": "...", "prompt": "..."}, ...]
            
        Returns:
            {"success": bool, "preset_id": int, "error": Optional[str]}
        """
        try:
            # Проверяем лимит
            count = await count_user_active_presets(session, user_id)
            if count >= settings.MAX_SAVED_STYLES:
                return {
                    "success": False,
                    "preset_id": None,
                    "error": f"Достигнут лимит сохранённых стилей ({settings.MAX_SAVED_STYLES})"
                }
            
            # Формируем данные стиля
            style_data = {
                "product_name": product_name,
                "aspect_ratio": aspect_ratio,
                "prompts": styles
            }
            
            # Сохраняем
            preset = await create_style_preset(
                session=session,
                user_id=user_id,
                name=name,
                style_data=style_data
            )
            
            logger.info(f"Saved new style preset '{name}' for user {user_id}")
            
            return {
                "success": True,
                "preset_id": preset.id,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error saving style: {e}", exc_info=True)
            return {
                "success": False,
                "preset_id": None,
                "error": str(e)
            }
    
    @staticmethod
    async def get_user_styles(
        session: AsyncSession,
        user_id: int
    ) -> List[Dict]:
        """
        Получить все стили пользователя
        
        Returns:
            [{"id": int, "name": str, "product_name": str, "aspect_ratio": str, "created_at": datetime}, ...]
        """
        try:
            presets = await get_user_style_presets(session, user_id)
            
            return [
                {
                    "id": preset.id,
                    "name": preset.name,
                    "product_name": preset.style_data.get("product_name", "Unknown"),
                    "aspect_ratio": preset.style_data.get("aspect_ratio", "1:1"),
                    "created_at": preset.created_at
                }
                for preset in presets
            ]
            
        except Exception as e:
            logger.error(f"Error getting user styles: {e}", exc_info=True)
            return []
    
    @staticmethod
    async def apply_style(
        session: AsyncSession,
        user_id: int,
        preset_id: int
    ) -> Optional[Dict]:
        """
        Применить сохранённый стиль
        
        Returns:
            {
                "product_name": str,
                "aspect_ratio": str,
                "styles": [{"style_name": "...", "prompt": "..."}, ...]
            }
        """
        try:
            preset = await get_style_preset_by_id(session, preset_id, user_id)
            if not preset:
                return None
            
            return {
                "product_name": preset.style_data["product_name"],
                "aspect_ratio": preset.style_data["aspect_ratio"],
                "styles": preset.style_data["prompts"]
            }
            
        except Exception as e:
            logger.error(f"Error applying style: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def delete_style(
        session: AsyncSession,
        user_id: int,
        preset_id: int
    ) -> bool:
        """Удалить стиль"""
        try:
            success = await delete_style_preset(session, preset_id, user_id)
            if success:
                logger.info(f"Deleted style preset {preset_id} for user {user_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error deleting style: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def rename_style(
        session: AsyncSession,
        user_id: int,
        preset_id: int,
        new_name: str
    ) -> bool:
        """Переименовать стиль"""
        try:
            preset = await update_style_preset(
                session=session,
                preset_id=preset_id,
                user_id=user_id,
                name=new_name
            )
            
            if preset:
                logger.info(f"Renamed style preset {preset_id} to '{new_name}'")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error renaming style: {e}", exc_info=True)
            return False
```

***

### 8. Image Processor (`app/services/image_processor.py`) - 🔄 СУЩЕСТВЕННАЯ МОДИФИКАЦИЯ

**Источник:** [photo-portrait-bot/app/services/image_processor.py](https://github.com/f2re/photo-portrait-bot/blob/main/app/services/image_processor.py)

**Действие:** Переписать логику под новый флоу

```python
"""
Процессор изображений для фотосессии товаров
Координирует генерацию 4 вариантов через NanoBanana
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
    """Обработка изображений товаров для фотосессии"""
    
    def __init__(self):
        self.nanobanana = NanoBananaService()
    
    def _convert_webp_to_png(self, image_bytes: bytes) -> bytes:
        """Конвертация WebP в PNG (из исходника БЕЗ ИЗМЕНЕНИЙ)"""
        # ... (скопировать из photo-portrait-bot/app/services/image_processor.py)
        pass
    
    async def generate_photoshoot(
        self,
        product_image_bytes: bytes,
        styles: List[Dict],
        aspect_ratio: str,
        bot: Bot,
        user: User
    ) -> Dict:
        """
        Генерирует фотосессию из 4 изображений
        
        Args:
            product_image_bytes: Исходное фото товара
            styles: Список из 4 стилей [{"style_name": "...", "prompt": "..."}, ...]
            aspect_ratio: Пропорции (1:1, 3:4, и т.д.)
            bot: Бот для уведомлений
            user: Пользователь
            
        Returns:
            {
                "success": bool,
                "images": [
                    {
                        "success": bool,
                        "image_bytes": Optional[bytes],
                        "style_name": str,
                        "prompt": str,
                        "error": Optional[str]
                    },
                    ... (4 шт)
                ],
                "successful_count": int,
                "error": Optional[str]
            }
        """
        try:
            logger.info(f"Starting photoshoot generation for user {user.telegram_id}")
            
            # Валидация и конвертация входного изображения
            try:
                img = Image.open(BytesIO(product_image_bytes))
                width, height = img.size
                original_format = img.format
                logger.info(f"Input image: {width}x{height}, format: {original_format}")
                
                # Конвертируем WebP если нужно
                if original_format and original_format.upper() == 'WEBP':
                    logger.info("Converting WebP to PNG...")
                    product_image_bytes = self._convert_webp_to_png(product_image_bytes)
                    
            except Exception as e:
                logger.error(f"Invalid image format: {e}")
                return {
                    "success": False,
                    "images": [],
                    "successful_count": 0,
                    "error": "Неподдерживаемый формат изображения"
                }
            
            # Генерируем 4 изображения ПАРАЛЛЕЛЬНО
            tasks = [
                self._generate_single_variant(
                    product_image_bytes,
                    style["prompt"],
                    style["style_name"],
                    aspect_ratio
                )
                for style in styles
            ]
            
            # Ждём все результаты
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Обрабатываем результаты
            images = []
            successful_count = 0
            
            for i, (result, style) in enumerate(zip(results, styles)):
                if isinstance(result, Exception):
                    logger.error(f"Generation {i+1} failed: {result}")
                    images.append({
                        "success": False,
                        "image_bytes": None,
                        "style_name": style["style_name"],
                        "prompt": style["prompt"],
                        "error": str(result)
                    })
                else:
                    images.append({
                        **result,
                        "style_name": style["style_name"],
                        "prompt": style["prompt"]
                    })
                    if result["success"]:
                        successful_count += 1
            
            logger.info(f"Photoshoot completed: {successful_count}/4 images generated successfully")
            
            # Уведомляем админов если были ошибки
            if successful_count < 4:
                failed_styles = [
                    img["style_name"] 
                    for img in images 
                    if not img["success"]
                ]
                await NotificationService.notify_admins_processing_error(
                    bot=bot,
                    user_telegram_id=user.telegram_id,
                    username=user.username,
                    service_name="NanoBanana",
                    error_message=f"Failed to generate {4-successful_count} images: {', '.join(failed_styles)}"
                )
            
            return {
                "success": successful_count > 0,  # Успех если хотя бы 1 изображение
                "images": images,
                "successful_count": successful_count,
                "error": None if successful_count > 0 else "Не удалось сгенерировать ни одного изображения"
            }
            
        except Exception as e:
            logger.error(f"Critical error in generate_photoshoot: {e}", exc_info=True)
            
            # Уведомляем админов
            await NotificationService.notify_admins_processing_error(
                bot=bot,
                user_telegram_id=user.telegram_id,
                username=user.username,
                service_name="ImageProcessor",
                error_message=str(e)
            )
            
            return {
                "success": False,
                "images": [],
                "successful_count": 0,
                "error": "Произошла критическая ошибка. Мы уже работаем над исправлением."
            }
    
    async def _generate_single_variant(
        self,
        product_image_bytes: bytes,
        prompt: str,
        style_name: str,
        aspect_ratio: str
    ) -> Dict:
        """Генерирует одно изображение"""
        try:
            logger.info(f"Generating '{style_name}' variant...")
            
            result = await self.nanobanana.generate_image(
                prompt=prompt,
                reference_image_bytes=product_image_bytes,
                aspect_ratio=aspect_ratio,
                strength=0.75  # Баланс между оригиналом и промптом
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating '{style_name}': {e}")
            return {
                "success": False,
                "image_bytes": None,
                "error": str(e)
            }
    
    async def test_service(self) -> bool:
        """Тест подключения к NanoBanana"""
        return await self.nanobanana.test_connection()
```

***

### 9. Keyboards (`app/keyboards/inline.py`) - 🔄 ДОБАВИТЬ новые клавиатуры

**Источник:** [photo-portrait-bot/app/keyboards/](https://github.com/f2re/photo-portrait-bot/tree/main/app/keyboards)

**Действие:** Скопировать существующие + ДОБАВИТЬ новые

```python
"""
Inline клавиатуры
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict
from app.config import settings

# ✅ Скопировать все существующие функции из исходника

# ⭐ ДОБАВИТЬ новые клавиатуры:

def get_aspect_ratio_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора пропорций"""
    builder = InlineKeyboardBuilder()
    
    ratios = {
        "1:1": "□ Квадрат (Instagram)",
        "3:4": "▭ Вертикаль (Stories)",
        "4:3": "▭ Горизонталь",
        "16:9": "▬ Широкий (YouTube)",
        "9:16": "▮ Вертикальный (TikTok)"
    }
    
    for ratio, label in ratios.items():
        builder.button(
            text=label,
            callback_data=f"aspect_ratio:{ratio}"
        )
    
    builder.adjust(1)  # По 1 кнопке в ряд
    return builder.as_markup()


def get_style_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора метода стилей"""
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="🎨 Проанализировать товар",
        callback_data="styles:analyze"
    )
    builder.button(
        text="🎲 Случайные стили",
        callback_data="styles:random"
    )
    builder.button(
        text="📁 Мои сохранённые стили",
        callback_data="styles:saved"
    )
    builder.button(
        text="🔙 Назад",
        callback_data="back_to_ratio"
    )
    
    builder.adjust(1)
    return builder.as_markup()


def get_style_preview_keyboard(can_save: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура после предпросмотра стилей"""
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="✅ Создать фотосессию",
        callback_data="confirm_generation"
    )
    builder.button(
        text="🔄 Другие случайные стили",
        callback_data="styles:random"
    )
    
    if can_save:
        builder.button(
            text="💾 Сохранить этот стиль",
            callback_data="save_style"
        )
    
    builder.button(
        text="🔙 Назад",
        callback_data="back_to_style_selection"
    )
    
    builder.adjust(1)
    return builder.as_markup()


def get_saved_styles_keyboard(styles: List[Dict]) -> InlineKeyboardMarkup:
    """Клавиатура со списком сохранённых стилей"""
    builder = InlineKeyboardBuilder()
    
    for style in styles:
        # Название + превью товара и пропорций
        text = f"{style['name']} ({style['aspect_ratio']})"
        builder.button(
            text=text,
            callback_data=f"apply_style:{style['id']}"
        )
    
    builder.button(
        text="🔙 Назад",
        callback_data="back_to_style_selection"
    )
    
    builder.adjust(1)
    return builder.as_markup()


def get_style_management_keyboard(preset_id: int) -> InlineKeyboardMarkup:
    """Клавиатура управления конкретным стилем"""
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="✏️ Переименовать",
        callback_data=f"rename_style:{preset_id}"
    )
    builder.button(
        text="🗑 Удалить",
        callback_data=f"delete_style:{preset_id}"
    )
    builder.button(
        text="🔙 Назад к списку",
        callback_data="styles:saved"
    )
    
    builder.adjust(2, 1)
    return builder.as_markup()


def get_post_generation_keyboard(has_balance: bool) -> InlineKeyboardMarkup:
    """Клавиатура после генерации фотосессии"""
    builder = InlineKeyboardBuilder()
    
    if has_balance:
        builder.button(
            text="🎨 Создать ещё фотосессию",
            callback_data="new_photoshoot"
        )
    else:
        builder.button(
            text="💳 Купить пакет",
            callback_data="buy_package"
        )
    
    builder.button(
        text="📁 Мои стили",
        callback_data="manage_styles"
    )
    builder.button(
        text="ℹ️ Мой профиль",
        callback_data="profile"
    )
    
    builder.adjust(1)
    return builder.as_markup()


def get_confirm_save_style_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение сохранения стиля"""
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="✅ Да, сохранить",
        callback_data="confirm_save_style"
    )
    builder.button(
        text="❌ Отмена",
        callback_data="cancel_save_style"
    )
    
    builder.adjust(2)
    return builder.as_markup()
```

***

### 10. User Handler (`app/handlers/user.py`) - 🔄 СУЩЕСТВЕННАЯ МОДИФИКАЦИЯ

**Источник:** [photo-portrait-bot/app/handlers/user.py](https://github.com/f2re/photo-portrait-bot/blob/main/app/handlers/user.py)

**Действие:** Переписать основной флоу обработки фото

```python
"""
Пользовательские обработчики
"""
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.states import PhotoshootStates
from app.keyboards.inline import (
    get_aspect_ratio_keyboard,
    get_style_selection_keyboard,
    get_style_preview_keyboard,
    get_saved_styles_keyboard,
    get_post_generation_keyboard,
    get_confirm_save_style_keyboard
)
from app.services.prompt_generator import PromptGenerator
from app.services.image_processor import ImageProcessor
from app.services.style_manager import StyleManager
from app.database.crud import (
    get_or_create_user,
    update_user_images_count,
    create_processed_image
)
from app.config import settings

logger = logging.getLogger(__name__)
router = Router()

prompt_generator = PromptGenerator()
image_processor = ImageProcessor()

# ✅ СКОПИРОВАТЬ /start handler из исходника с изменёнными текстами

@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext):
    """Команда /start"""
    # ... (логика из исходника, изменить тексты на товарную тематику)
    
    welcome_text = """
🎨 <b>Добро пожаловать в Product Photoshoot Bot!</b>

Я помогу создать профессиональную фотосессию вашего товара в разных стилях! 📸

<b>Как это работает:</b>
1️⃣ Загрузите фото товара
2️⃣ Выберите пропорции изображений
3️⃣ Выберите стили съемки (или создайте случайные!)
4️⃣ Получите 4 профессиональных фото в разных стилях

У вас есть <b>{free_count} бесплатных фотосессий</b> для начала! 🎁

Просто отправьте фото товара, чтобы начать! 📷
"""
    
    # ... (остальная логика из исходника)


@router.message(F.photo | F.document, StateFilter(None))
async def handle_product_photo(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot
):
    """Обработка загруженного фото товара"""
    try:
        # Получаем пользователя
        user = await get_or_create_user(
            session=session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        # Проверяем баланс
        if user.images_remaining <= 0:
            await message.answer(
                "😔 У вас закончились фотосессии!\n\n"
                "Купите пакет, чтобы продолжить:",
                reply_markup=get_buy_packages_keyboard()
            )
            return
        
        # Скачиваем фото
        if message.photo:
            file_id = message.photo[-1].file_id  # Максимальное качество
            file = await bot.get_file(file_id)
        else:  # document
            file_id = message.document.file_id
            file = await bot.get_file(file_id)
        
        # Загружаем байты
        photo_bytes = await bot.download_file(file.file_path)
        photo_data = photo_bytes.read()
        
        # Сохраняем в состояние
        await state.update_data(
            product_image_bytes=photo_data,
            product_image_file_id=file_id
        )
        
        # Переходим к выбору пропорций
        await message.answer(
            "✅ Фото товара получено!\n\n"
            "Теперь выберите пропорции для фотосессии:",
            reply_markup=get_aspect_ratio_keyboard()
        )
        
        await state.set_state(PhotoshootStates.selecting_aspect_ratio)
        
    except Exception as e:
        logger.error(f"Error handling product photo: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при загрузке фото. Попробуйте снова."
        )


@router.callback_query(F.data.startswith("aspect_ratio:"))
async def select_aspect_ratio(
    callback: CallbackQuery,
    state: FSMContext
):
    """Выбор пропорций"""
    await callback.answer()
    
    aspect_ratio = callback.data.split(":")[1]
    
    # Сохраняем
    await state.update_data(aspect_ratio=aspect_ratio)
    
    # Показываем методы выбора стиля
    await callback.message.edit_text(
        f"✅ Выбраны пропорции: <b>{aspect_ratio}</b>\n\n"
        "Теперь выберите, как создать стили для фотосессии:",
        reply_markup=get_style_selection_keyboard()
    )
    
    await state.set_state(PhotoshootStates.selecting_styles_method)


@router.callback_query(F.data == "styles:analyze")
async def analyze_product_styles(
    callback: CallbackQuery,
    state: FSMContext
):
    """Анализ товара и генерация подходящих стилей"""
    await callback.answer()
    
    # Показываем процесс
    msg = await callback.message.edit_text(
        "🔍 Анализирую товар и подбираю подходящие стили...\n\n"
        "⏳ Это займёт 10-15 секунд"
    )
    
    # Получаем данные из состояния
    data = await state.get_data()
    aspect_ratio = data["aspect_ratio"]
    
    # Генерируем стили
    result = await prompt_generator.generate_styles_from_description(
        product_description="product from uploaded image",  # Можно добавить распознавание
        aspect_ratio=aspect_ratio,
        random=False
    )
    
    if not result["success"]:
        await msg.edit_text(
            "❌ Не удалось сгенерировать стили. Попробуйте ещё раз или выберите случайные стили.",
            reply_markup=get_style_selection_keyboard()
        )
        return
    
    # Сохраняем стили в состояние
    await state.update_data(
        product_name=result["product_name"],
        styles=result["styles"]
    )
    
    # Показываем предпросмотр стилей
    styles_text = _format_styles_preview(result["styles"])
    
    await msg.edit_text(
        f"✨ <b>Предложенные стили для вашего товара:</b>\n\n"
        f"📦 Товар: <b>{result['product_name']}</b>\n"
        f"📐 Пропорции: <b>{aspect_ratio}</b>\n\n"
        f"{styles_text}\n\n"
        f"Выберите действие:",
        reply_markup=get_style_preview_keyboard(can_save=True)
    )
    
    await state.set_state(PhotoshootStates.reviewing_suggested_styles)


@router.callback_query(F.data == "styles:random")
async def generate_random_styles(
    callback: CallbackQuery,
    state: FSMContext
):
    """Генерация случайных креативных стилей"""
    await callback.answer()
    
    msg = await callback.message.edit_text(
        "🎲 Генерирую случайные креативные стили для вдохновения...\n\n"
        "⏳ Это займёт 10-15 секунд"
    )
    
    data = await state.get_data()
    aspect_ratio = data["aspect_ratio"]
    
    # Генерируем СЛУЧАЙНЫЕ стили
    result = await prompt_generator.generate_styles_from_description(
        product_description="product from uploaded image",
        aspect_ratio=aspect_ratio,
        random=True  # ⭐ Случайная генерация
    )
    
    if not result["success"]:
        await msg.edit_text(
            "❌ Не удалось сгенерировать стили. Попробуйте ещё раз.",
            reply_markup=get_style_selection_keyboard()
        )
        return
    
    # Сохраняем
    await state.update_data(
        product_name=result["product_name"],
        styles=result["styles"]
    )
    
    styles_text = _format_styles_preview(result["styles"])
    
    await msg.edit_text(
        f"🎨 <b>Случайные креативные стили:</b>\n\n"
        f"📦 Товар: <b>{result['product_name']}</b>\n"
        f"📐 Пропорции: <b>{aspect_ratio}</b>\n\n"
        f"{styles_text}\n\n"
        f"Не понравилось? Можете сгенерировать ещё раз! 🎲",
        reply_markup=get_style_preview_keyboard(can_save=True)
    )
    
    await state.set_state(PhotoshootStates.reviewing_suggested_styles)


@router.callback_query(F.data == "styles:saved")
async def show_saved_styles(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """Показать сохранённые стили"""
    await callback.answer()
    
    user_id = callback.from_user.id
    
    # Получаем стили из БД
    styles = await StyleManager.get_user_styles(session, user_id)
    
    if not styles:
        await callback.message.edit_text(
            "📁 У вас пока нет сохранённых стилей.\n\n"
            "Создайте фотосессию и сохраните понравившийся стиль!",
            reply_markup=get_style_selection_keyboard()
        )
        return
    
    # Показываем список
    styles_list = "\n".join([
        f"{i+1}. <b>{s['name']}</b> ({s['aspect_ratio']}) - {s['product_name']}"
        for i, s in enumerate(styles)
    ])
    
    await callback.message.edit_text(
        f"📁 <b>Ваши сохранённые стили ({len(styles)}/{settings.MAX_SAVED_STYLES}):</b>\n\n"
        f"{styles_list}\n\n"
        f"Выберите стиль для применения:",
        reply_markup=get_saved_styles_keyboard(styles)
    )


@router.callback_query(F.data.startswith("apply_style:"))
async def apply_saved_style(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """Применить сохранённый стиль"""
    await callback.answer()
    
    preset_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    # Загружаем стиль из БД
    style_data = await StyleManager.apply_style(session, user_id, preset_id)
    
    if not style_data:
        await callback.answer("❌ Стиль не найден", show_alert=True)
        return
    
    # Сохраняем в состояние
    await state.update_data(
        product_name=style_data["product_name"],
        aspect_ratio=style_data["aspect_ratio"],
        styles=style_data["styles"]
    )
    
    styles_text = _format_styles_preview(style_data["styles"])
    
    await callback.message.edit_text(
        f"✅ <b>Применён сохранённый стиль</b>\n\n"
        f"📦 Товар: <b>{style_data['product_name']}</b>\n"
        f"📐 Пропорции: <b>{style_data['aspect_ratio']}</b>\n\n"
        f"{styles_text}\n\n"
        f"Готовы создать фотосессию?",
        reply_markup=get_style_preview_keyboard(can_save=False)  # Уже сохранён
    )
    
    await state.set_state(PhotoshootStates.reviewing_suggested_styles)


@router.callback_query(F.data == "confirm_generation")
async def generate_photoshoot(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot
):
    """Генерация фотосессии"""
    await callback.answer()
    
    # Получаем пользователя
    user = await get_or_create_user(
        session=session,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username
    )
    
    # Проверяем баланс (1 фотосессия = 4 фото = 4 кредита или настраиваемо)
    photoshoots_cost = 1  # Можно настроить
    if user.images_remaining < photoshoots_cost:
        await callback.message.edit_text(
            "😔 Недостаточно фотосессий для генерации!\n\n"
            "Купите пакет:",
            reply_markup=get_buy_packages_keyboard()
        )
        return
    
    # Показываем прогресс
    progress_msg = await callback.message.edit_text(
        "🎨 Создаю вашу фотосессию...\n\n"
        "⏳ Генерирую 4 профессиональных фото\n"
        "Это может занять 1-2 минуты"
    )
    
    # Получаем данные
    data = await state.get_data()
    product_image_bytes = data["product_image_bytes"]
    styles = data["styles"]
    aspect_ratio = data["aspect_ratio"]
    product_name = data["product_name"]
    
    # Генерируем фотосессию
    result = await image_processor.generate_photoshoot(
        product_image_bytes=product_image_bytes,
        styles=styles,
        aspect_ratio=aspect_ratio,
        bot=bot,
        user=user
    )
    
    if not result["success"] or result["successful_count"] == 0:
        await progress_msg.edit_text(
            f"❌ Не удалось создать фотосессию.\n\n"
            f"Ошибка: {result.get('error', 'Unknown error')}\n\n"
            f"Попробуйте ещё раз или свяжитесь с поддержкой."
        )
        return
    
    # Списываем кредиты
    await update_user_images_count(session, user.id, -photoshoots_cost)
    
    # Отправляем фотоальбом
    media_group = []
    for i, img_data in enumerate(result["images"]):
        if img_data["success"]:
            # Создаём InputMediaPhoto
            caption = f"<b>{img_data['style_name']}</b>" if i == 0 else None
            media_group.append(
                InputMediaPhoto(
                    media=img_data["image_bytes"],
                    caption=caption
                )
            )
            
            # Сохраняем в БД
            await create_processed_image(
                session=session,
                user_id=user.id,
                telegram_file_id=None,  # Будет после отправки
                style_name=img_data["style_name"],
                prompt_used=img_data["prompt"],
                aspect_ratio=aspect_ratio
            )
    
    # Удаляем прогресс
    await progress_msg.delete()
    
    # Отправляем альбом
    if media_group:
        await callback.message.answer_media_group(media_group)
        
        await callback.message.answer(
            f"✅ <b>Фотосессия готова!</b>\n\n"
            f"📸 Создано: {result['successful_count']}/4 фото\n"
            f"📦 Товар: {product_name}\n"
            f"📐 Пропорции: {aspect_ratio}\n\n"
            f"💰 Осталось фотосессий: <b>{user.images_remaining - photoshoots_cost}</b>",
            reply_markup=get_post_generation_keyboard(
                has_balance=(user.images_remaining - photoshoots_cost) > 0
            )
        )
    
    # Сохраняем данные для возможного сохранения стиля
    await state.update_data(last_generated=True)
    await state.set_state(PhotoshootStates.generating_photoshoot)


@router.callback_query(F.data == "save_style")
async def initiate_save_style(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """Начать сохранение стиля"""
    await callback.answer()
    
    user_id = callback.from_user.id
    
    # Проверяем лимит
    count = await StyleManager.get_user_styles(session, user_id)
    if len(count) >= settings.MAX_SAVED_STYLES:
        await callback.answer(
            f"❌ Достигнут лимит сохранённых стилей ({settings.MAX_SAVED_STYLES})\n\n"
            "Удалите старый стиль, чтобы сохранить новый.",
            show_alert=True
        )
        return
    
    await callback.message.answer(
        "💾 <b>Сохранение стиля</b>\n\n"
        "Введите название для этого стиля (например: \"Минимализм белый фон\"):"
    )
    
    await state.set_state(PhotoshootStates.saving_style_name)


@router.message(StateFilter(PhotoshootStates.saving_style_name))
async def save_style_with_name(
    message: Message,
    state: FSMContext,
    session: AsyncSession
):
    """Сохранение стиля с именем"""
    style_name = message.text.strip()
    
    if len(style_name) > 100:
        await message.answer(
            "❌ Название слишком длинное (макс. 100 символов). Попробуйте короче:"
        )
        return
    
    # Получаем данные стиля
    data = await state.get_data()
    
    # Сохраняем в БД
    result = await StyleManager.save_style(
        session=session,
        user_id=message.from_user.id,
        name=style_name,
        product_name=data["product_name"],
        aspect_ratio=data["aspect_ratio"],
        styles=data["styles"]
    )
    
    if result["success"]:
        await message.answer(
            f"✅ Стиль <b>\"{style_name}\"</b> успешно сохранён!\n\n"
            f"Теперь вы можете использовать его снова в разделе \"Мои сохранённые стили\".",
            reply_markup=get_post_generation_keyboard(has_balance=True)
        )
    else:
        await message.answer(
            f"❌ Не удалось сохранить стиль: {result['error']}"
        )
    
    await state.clear()


def _format_styles_preview(styles: list) -> str:
    """Форматирование превью стилей"""
    text = ""
    for i, style in enumerate(styles, 1):
        text += f"{i}. <b>{style['style_name']}</b>\n"
        # Показываем короткое превью промпта
        prompt_preview = style['prompt'][:80] + "..." if len(style['prompt']) > 80 else style['prompt']
        text += f"   <i>{prompt_preview}</i>\n\n"
    return text

# ✅ СКОПИРОВАТЬ остальные handlers из исходника (профиль, помощь, и т.д.)
```

***

### 11. Style Management Handler (`app/handlers/style_management.py`) - ⭐ НОВЫЙ

```python
"""
Управление сохранёнными стилями
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession

from app.states import StyleManagementStates
from app.services.style_manager import StyleManager
from app.keyboards.inline import get_style_management_keyboard, get_saved_styles_keyboard
from app.config import settings

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "manage_styles")
async def show_style_management(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Показать управление стилями"""
    await callback.answer()
    
    user_id = callback.from_user.id
    styles = await StyleManager.get_user_styles(session, user_id)
    
    if not styles:
        await callback.message.edit_text(
            "📁 У вас пока нет сохранённых стилей.\n\n"
            "Создайте фотосессию и сохраните понравившийся стиль!"
        )
        return
    
    styles_list = ""
    for i, s in enumerate(styles, 1):
        styles_list += (
            f"{i}. <b>{s['name']}</b>\n"
            f"   📦 {s['product_name']} | 📐 {s['aspect_ratio']}\n"
            f"   📅 {s['created_at'].strftime('%d.%m.%Y')}\n\n"
        )
    
    await callback.message.edit_text(
        f"📁 <b>Управление стилями ({len(styles)}/{settings.MAX_SAVED_STYLES})</b>\n\n"
        f"{styles_list}"
        "Выберите стиль:",
        reply_markup=get_saved_styles_keyboard(styles)
    )


@router.callback_query(F.data.startswith("delete_style:"))
async def delete_style(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Удалить стиль"""
    preset_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    success = await StyleManager.delete_style(session, user_id, preset_id)
    
    if success:
        await callback.answer("✅ Стиль удалён", show_alert=True)
        # Обновляем список
        await show_style_management(callback, session)
    else:
        await callback.answer("❌ Не удалось удалить стиль", show_alert=True)


@router.callback_query(F.data.startswith("rename_style:"))
async def initiate_rename_style(
    callback: CallbackQuery,
    state: FSMContext
):
    """Начать переименование"""
    await callback.answer()
    
    preset_id = int(callback.data.split(":")[1])
    
    await state.update_data(renaming_preset_id=preset_id)
    await state.set_state(StyleManagementStates.editing_style_name)
    
    await callback.message.answer(
        "✏️ Введите новое название для стиля:"
    )


@router.message(StateFilter(StyleManagementStates.editing_style_name))
async def rename_style_confirm(
    message: Message,
    state: FSMContext,
    session: AsyncSession
):
    """Подтверждение переименования"""
    new_name = message.text.strip()
    
    if len(new_name) > 100:
        await message.answer(
            "❌ Название слишком длинное (макс. 100 символов)"
        )
        return
    
    data = await state.get_data()
    preset_id = data["renaming_preset_id"]
    
    success = await StyleManager.rename_style(
        session,
        message.from_user.id,
        preset_id,
        new_name
    )
    
    if success:
        await message.answer(f"✅ Стиль переименован в <b>\"{new_name}\"</b>")
    else:
        await message.answer("❌ Не удалось переименовать стиль")
    
    await state.clear()
```

***

### 12. Requirements.txt - 🔄 ДОБАВИТЬ зависимости

```txt
# Существующие (из исходника)
asyncpg
aiogram==3.4.1
sqlalchemy==2.0.25
asyncpg==0.29.0
alembic==1.13.1
aiohttp==3.9.1
python-dotenv==1.0.0
pillow==10.2.0
pydantic==2.5.3
pydantic-settings==2.1.0
redis==5.0.1
numpy==1.26.3
scikit-learn==1.3.2
yookassa==3.0.0
```

Всё остальное уже покрыто существующими зависимостями!

***

### 13. .env.example - 🔄 ОБНОВИТЬ

```env
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token
BOT_USERNAME=your_bot_username
ADMIN_IDS=123456789,987654321

# Database
DATABASE_URL=postgresql+asyncpg://product_user:password@localhost:5432/product_photoshoot_bot
# OR use individual components:
DB_HOST=localhost
DB_PORT=5432
DB_NAME=product_photoshoot_bot
DB_USER=product_user
DB_PASSWORD=your_password

# OpenRouter API (для генерации промптов через Claude)
OPENROUTER_API_KEY=your_openrouter_api_key
PROMPT_MODEL=anthropic/claude-3.5-sonnet

# YooKassa Payments
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
YOOKASSA_RETURN_URL=https://t.me/your_product_bot

# Packages Configuration
PACKAGE_1_NAME=Стартовый
PACKAGE_1_PHOTOSHOOTS=3
PACKAGE_1_PRICE=299

PACKAGE_2_NAME=Бизнес
PACKAGE_2_PHOTOSHOOTS=10
PACKAGE_2_PRICE=799

PACKAGE_3_NAME=Профессиональный
PACKAGE_3_PHOTOSHOOTS=30
PACKAGE_3_PRICE=1999

PACKAGE_4_NAME=Безлимитный
PACKAGE_4_PHOTOSHOOTS=100
PACKAGE_4_PRICE=4999

# Settings
FREE_PHOTOSHOOTS_COUNT=2
PHOTOS_PER_PHOTOSHOOT=4
MAX_SAVED_STYLES=4
LOG_LEVEL=INFO

# Yandex Metrika (optional)
YANDEX_METRIKA_COUNTER_ID=
YANDEX_METRIKA_TOKEN=
METRIKA_GOAL_START=start_bot
METRIKA_GOAL_FIRST_PHOTOSHOOT=first_photoshoot
METRIKA_GOAL_PURCHASE=purchase
METRIKA_UPLOAD_INTERVAL=3600

# Referral Program
REFERRAL_REWARD_START=1
REFERRAL_REWARD_PURCHASE_PERCENT=10
```

***

## Итоговый User Flow

```
1. Пользователь отправляет фото товара
   ↓
2. Бот предлагает выбрать пропорции (1:1, 3:4, 4:3, 16:9, 9:16)
   ↓
3. Выбор метода стилей:
   a) 🎨 Проанализировать товар → Claude генерирует 4 подходящих стиля
   b) 🎲 Случайные стили → Claude генерирует 4 креативных случайных стиля
   c) 📁 Мои сохранённые → Применить ранее сохранённый стиль
   ↓
4. Превью стилей:
   - Показываются 4 стиля с названиями и промптами
   - Можно сгенерировать другие случайные (🔄)
   - Можно сохранить этот набор (💾)
   ↓
5. Подтверждение → ✅ Создать фотосессию
   ↓
6. Генерация:
   - 4 запроса в NanoBanana API параллельно
   - Каждый запрос: reference_image + unique_prompt + aspect_ratio
   ↓
7. Результат:
   - Фотоальбом из 4 изображений
   - Подписи со стилями
   - Списание 1 фотосессии (настраиваемо)
   ↓
8. Post-generation:
   - 🎨 Создать ещё
   - 💾 Сохранить стиль (если ещё не сохранён)
   - 📁 Управление стилями
```

***
