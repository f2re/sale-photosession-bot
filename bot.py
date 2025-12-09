import logging
import sys
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.handlers import get_routers
from app.database import init_db
from app.middlewares import DbSessionMiddleware

# Configure detailed logging with proper formatting
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True  # Force reconfiguration of root logger
)

# Set up logger for this module
logger = logging.getLogger(__name__)

# Ensure all aiogram loggers are visible
logging.getLogger("aiogram").setLevel(logging.INFO)
logging.getLogger("aiogram.event").setLevel(logging.INFO)

# Flush stdout immediately (important for Docker)
sys.stdout.reconfigure(line_buffering=True)

async def main():
    """Main entry point"""
    try:
        logger.info("="*60)
        logger.info("Starting Product Photoshoot Bot...")
        logger.info(f"Log level: {settings.LOG_LEVEL}")
        logger.info(f"Bot username: {settings.BOT_USERNAME}")
        logger.info("="*60)
        
        # Initialize Bot and Dispatcher
        logger.info("Initializing bot and dispatcher...")
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        dp = Dispatcher()
        logger.info("✓ Bot and dispatcher initialized")

        # Register middlewares
        logger.info("Registering middlewares...")
        dp.update.middleware(DbSessionMiddleware())
        logger.info("✓ Middlewares registered")

        # Include routers
        logger.info("Including routers...")
        routers = get_routers()
        dp.include_routers(*routers)
        logger.info(f"✓ {len(routers)} routers included")

        # Initialize database
        logger.info("Initializing database...")
        logger.info(f"Database URL: {settings.database_url.split('@')[-1]}")  # Hide credentials
        database = init_db(settings.database_url)
        logger.info("✓ Database initialized")

        # Delete webhook to ensure polling works
        logger.info("Removing webhook and dropping pending updates...")
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✓ Webhook removed")

        # Get bot info
        bot_info = await bot.get_me()
        logger.info(f"Bot info: @{bot_info.username} (ID: {bot_info.id})")
        
        # Start polling
        logger.info("="*60)
        logger.info("🚀 Bot is now running and polling for updates...")
        logger.info("Press Ctrl+C to stop")
        logger.info("="*60)
        
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )
        
    except Exception as e:
        logger.critical(f"Fatal error during bot startup: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("="*60)
        logger.info("Bot stopped by user")
        logger.info("="*60)
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
