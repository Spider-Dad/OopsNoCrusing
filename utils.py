"""
Общие утилиты для бота OopsNoCursing
"""

import asyncio
import logging
from constants import RETRY_COUNT, RETRY_DELAY, BOT_RETRY_DELAY

logger = logging.getLogger(__name__)

async def retry_on_timeout_gif(func, *args, **kwargs):
    """Функция для повторных попыток выполнения при таймауте (для gif_service)"""
    for attempt in range(RETRY_COUNT):
        try:
            return await func(*args, **kwargs)
        except (asyncio.TimeoutError, Exception) as e:
            if attempt == RETRY_COUNT - 1:
                logger.error(f"Все попытки получения GIF исчерпаны: {e}")
                return None
            logger.warning(f"Ошибка при попытке {attempt + 1}/{RETRY_COUNT}: {e}, повтор через {RETRY_DELAY} сек...")
            await asyncio.sleep(RETRY_DELAY)

async def retry_on_timeout_bot(func, *args, **kwargs):
    """Функция для повторных попыток выполнения при таймауте (для bot)"""
    for attempt in range(RETRY_COUNT):
        try:
            return await func(*args, **kwargs)
        except asyncio.TimeoutError:
            if attempt == RETRY_COUNT - 1:
                raise
            logger.warning(f"Таймаут при попытке {attempt + 1}/{RETRY_COUNT}, повтор через {BOT_RETRY_DELAY} сек...")
            await asyncio.sleep(BOT_RETRY_DELAY)