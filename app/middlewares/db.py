import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from app.database import get_db

logger = logging.getLogger(__name__)


class DbSessionMiddleware(BaseMiddleware):
    """
    Database session middleware with proper error handling and monitoring.
    Ensures sessions are properly committed/rolled back and closed.
    """
    def __init__(self):
        self._active_sessions = 0
        self._max_sessions = 0
        self._total_requests = 0

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        db = get_db()
        if db is None:
            raise RuntimeError("Database is not initialized")

        self._active_sessions += 1
        self._total_requests += 1
        self._max_sessions = max(self._max_sessions, self._active_sessions)

        try:
            async with db.get_session() as session:
                data["session"] = session
                result = await handler(event, data)

                # Ensure any pending changes are committed
                if session.in_transaction():
                    await session.commit()

                return result

        except Exception as e:
            # Log error with session info for debugging
            logger.error(
                f"Handler error (active sessions: {self._active_sessions}): {e}",
                exc_info=True
            )
            raise

        finally:
            self._active_sessions -= 1

            # Periodic logging for monitoring
            if self._total_requests % 100 == 0:
                logger.info(
                    f"Session stats: "
                    f"total={self._total_requests}, "
                    f"active={self._active_sessions}, "
                    f"peak={self._max_sessions}"
                )

    def get_stats(self) -> Dict:
        """Get middleware statistics for monitoring"""
        return {
            "active_sessions": self._active_sessions,
            "max_concurrent_sessions": self._max_sessions,
            "total_requests": self._total_requests
        }
