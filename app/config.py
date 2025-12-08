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
    
    # OpenRouter API (for prompt generation via Claude)
    OPENROUTER_API_KEY: str
    PROMPT_MODEL: str = "anthropic/claude-3.5-sonnet"  # For generating prompts
    IMAGE_MODEL: str = "google/gemini-2.0-flash-001" # Using Gemini 2.0 Flash for image generation via OpenRouter/NanoBanana
    
    # YooKassa
    YOOKASSA_SHOP_ID: str
    YOOKASSA_SECRET_KEY: str
    YOOKASSA_RETURN_URL: str = "https://t.me/your_product_bot"
    
    # Packages
    PACKAGE_1_NAME: str = "Стартовый"
    PACKAGE_1_PHOTOSHOOTS: int = 3  # photoshoots (each = 4 photos)
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
    
    # Photoshoot Settings
    FREE_PHOTOSHOOTS_COUNT: int = 2  # Free photoshoots for new users
    PHOTOS_PER_PHOTOSHOOT: int = 4  # Photos per photoshoot
    MAX_SAVED_STYLES: int = 4  # Max saved styles
    
    # Aspect Ratios
    AVAILABLE_ASPECT_RATIOS: List[str] = [
        "1:1",    # Square (Instagram)
        "3:4",    # Vertical (Stories)
        "4:3",    # Horizontal
        "16:9",   # Wide (YouTube)
        "9:16"    # Vertical (TikTok)
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
    REFERRAL_REWARD_START: int = 1  # photoshoots rewarded when referral clicks start
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
        """Photoshoot packages"""
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