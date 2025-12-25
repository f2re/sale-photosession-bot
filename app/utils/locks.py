"""
User processing locks to prevent concurrent image processing with automatic cleanup
"""
import asyncio
import time
import logging
from typing import Dict, Set
from collections import defaultdict
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class UserProcessingLock:
    """
    Manages locks for user image processing to prevent concurrent requests.
    Features automatic cleanup of stale locks to prevent memory leaks.
    """
    def __init__(self, cleanup_interval: int = 300):
        """
        Initialize lock manager with automatic cleanup.

        Args:
            cleanup_interval: Time in seconds between cleanup cycles (default: 5 minutes)
        """
        self._locks: Dict[int, asyncio.Lock] = {}
        self._processing: Set[int] = set()
        self._main_lock = asyncio.Lock()

        # Tracking for automatic cleanup
        self._lock_timestamps: Dict[int, float] = defaultdict(float)
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()

    async def _cleanup_old_locks(self):
        """
        Remove locks that haven't been used recently.
        Prevents memory leaks from accumulated lock objects.
        """
        now = time.time()

        # Only cleanup periodically
        if now - self._last_cleanup < self._cleanup_interval:
            return

        async with self._main_lock:
            to_remove = [
                user_id for user_id, ts in self._lock_timestamps.items()
                if (now - ts > self._cleanup_interval
                    and user_id not in self._processing)
            ]

            for user_id in to_remove:
                if user_id in self._locks and not self._locks[user_id].locked():
                    del self._locks[user_id]
                    del self._lock_timestamps[user_id]

            self._last_cleanup = now

            if to_remove:
                logger.info(
                    f"Lock cleanup: removed {len(to_remove)} stale locks. "
                    f"Active locks: {len(self._locks)}, processing: {len(self._processing)}"
                )

    @asynccontextmanager
    async def acquire(self, user_id: int):
        """
        Acquire lock for user image processing with automatic cleanup.

        Args:
            user_id: Telegram user ID

        Raises:
            RuntimeError: If user already has a processing request
        """
        # Periodic cleanup of stale locks
        await self._cleanup_old_locks()

        async with self._main_lock:
            # Check if user is already processing
            if user_id in self._processing:
                raise RuntimeError("Already processing image for this user")

            # Get or create lock for this user
            if user_id not in self._locks:
                self._locks[user_id] = asyncio.Lock()

            lock = self._locks[user_id]
            self._processing.add(user_id)
            self._lock_timestamps[user_id] = time.time()

        try:
            async with lock:
                yield
        finally:
            async with self._main_lock:
                self._processing.discard(user_id)
                self._lock_timestamps[user_id] = time.time()

                # Immediate cleanup if lock is unused
                if user_id in self._locks and user_id not in self._processing:
                    if not self._locks[user_id].locked():
                        del self._locks[user_id]
                        # Keep timestamp for a bit to track usage patterns
                        # Will be removed in periodic cleanup

    def is_processing(self, user_id: int) -> bool:
        """Check if user is currently processing an image"""
        return user_id in self._processing

    def get_stats(self) -> Dict:
        """Get lock manager statistics for monitoring"""
        return {
            "active_locks": len(self._locks),
            "processing_users": len(self._processing),
            "tracked_users": len(self._lock_timestamps),
            "cleanup_interval": self._cleanup_interval,
            "time_since_cleanup": time.time() - self._last_cleanup
        }


# Global instance
user_processing_lock = UserProcessingLock()
