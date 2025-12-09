import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from alembic.config import Config
from alembic import command

from app.config import settings
from app.database import init_db
from app.handlers import user, admin, payment, support, batch_processing, style_management
from app.services.yandex_metrika import periodic_metrika_upload
from app.middlewares import DbSessionMiddleware

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


async def notify_admins(message: str):
    """Notify admins about critical errors"""
    try:
        # Create a temporary bot instance just for sending this message
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        for admin_id in settings.admin_ids_list:
            try:
                await bot.send_message(chat_id=admin_id, text=message)
                logger.info(f"Admin {admin_id} notified about error.")
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
        await bot.session.close()
    except Exception as e:
        logger.error(f"Failed to initialize bot for notification: {e}")


def run_migrations():
    """Run Alembic migrations"""
    logger.info("Running database migrations...")
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise e


async def main():
    """Main bot function"""
    # Initialize database
    logger.info("Initializing database...")
    db = init_db(settings.database_url)

    # Note: Tables are created via Alembic migrations (run_migrations)
    # create_tables() is kept as a fallback or for specific dev setups, 
    # but strictly speaking shouldn't be needed if migrations run.
    # We'll leave it in a try/except but it might be redundant.
    try:
        await db.create_tables()
        logger.info("Database tables check/creation passed")
    except Exception as e:
        logger.error(f"Database table check failed (might be handled by migrations): {e}")
        # We don't return here, assuming migrations might have worked or it's a non-critical check failure
    
    # Synchronize packages from config to database
    try:
        from app.database.crud import sync_packages_from_config
        async with db.get_session() as session:
            await sync_packages_from_config(session, settings.packages_config)
        logger.info("Packages synchronized successfully")
    except Exception as e:
        logger.error(f"Failed to synchronize packages: {e}")
        # Don't return - continue even if packages sync fails

    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register middleware
    dp.update.middleware(DbSessionMiddleware())

    # Register routers
    # IMPORTANT: batch_processing must be registered BEFORE user router
    # to handle media groups (albums) before single images
    dp.include_router(batch_processing.router)
    dp.include_router(style_management.router)
    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(payment.router)
    dp.include_router(support.router)

    # Start background task for periodic Metrika upload
    metrika_upload_task = None
    if settings.is_metrika_enabled:
        metrika_upload_task = asyncio.create_task(
            periodic_metrika_upload(db.get_session)
        )
        logger.info(
            f"Metrika upload task started. "
            f"Events will be uploaded every {settings.METRIKA_UPLOAD_INTERVAL}s"
        )
    else:
        logger.info("Metrika upload task skipped (Metrika is disabled)")

    logger.info("Bot started successfully")
    
    # Notify admins about startup
    # await notify_admins("✅ Bot started successfully") # Optional, might be spammy on restart loops

    try:
        # Start polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Cancel background task on shutdown
        if metrika_upload_task:
            metrika_upload_task.cancel()
            try:
                await metrika_upload_task
            except asyncio.CancelledError:
                logger.info("Metrika upload task cancelled")
        await bot.session.close()


if __name__ == "__main__":
    try:
        # Run migrations before starting the async loop
        run_migrations()
        
        # Start the bot
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
        try:
            asyncio.run(notify_admins(f"🚨 <b>BOT CRITICAL ERROR</b> 🚨\n\n<pre>{str(e)}</pre>"))
        except Exception as notify_error:
            logger.error(f"Failed to send error notification: {notify_error}")
        sys.exit(1)
