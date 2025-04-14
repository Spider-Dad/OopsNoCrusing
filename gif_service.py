"""
Модуль для работы с API yesno.wtf для получения GIF-изображений
"""

import aiohttp
import logging
from typing import Optional

# URL API для получения случайных GIF
YESNO_API_URL = "https://yesno.wtf/api"

# Принудительно получать "no" GIF (как в примере)
FORCE_NO_PARAM = "?force=no"

async def get_gif_url() -> Optional[str]:
    """
    Получает URL GIF-изображения с API yesno.wtf

    Returns:
        URL GIF-изображения или None в случае ошибки
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(YESNO_API_URL + FORCE_NO_PARAM) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('image')
                else:
                    logging.error(f"API вернул статус: {response.status}")
                    return None
    except Exception as e:
        logging.error(f"Ошибка при запросе к API: {e}")
        return None