"""
Модуль для работы с различными API для получения GIF-изображений
"""

import os
import aiohttp
import logging
import random
from typing import Optional
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Выбор API для получения GIF
API_SOURCE = os.getenv('API_SOURCE', 'yesno').lower()

# URL API для получения случайных GIF
YESNO_API_URL = "https://yesno.wtf/api"
CATAAS_API_URL = "https://cataas.com/cat/gif"

# Возможные подписи к котикам
CAT_CAPTIONS = [
    "Не матерись - гладь котика!",
    "Кот не одобряет твои выражения",
    "Мяу! На кошачьем это значит: 'Не ругайся!'",
    "Вместо мата - погладь кота",
    "Котики против мата!",
    "Мурррр... нет ругательствам!",
    "Этот котик моет свои ушки, а ты помой свой язык!"
]

# Принудительно получать "no" GIF для yesno API
FORCE_NO_PARAM = "?force=no"

async def get_gif_url() -> Optional[str]:
    """
    Получает URL GIF-изображения с выбранного API

    Returns:
        URL GIF-изображения или None в случае ошибки
    """
    if API_SOURCE == 'cataas':
        return await get_cat_gif()
    else:  # По умолчанию используем yesno API
        return await get_yesno_gif()

async def get_yesno_gif() -> Optional[str]:
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
                    logging.error(f"yesno API вернул статус: {response.status}")
                    return None
    except Exception as e:
        logging.error(f"Ошибка при запросе к yesno API: {e}")
        return None

async def get_cat_gif() -> Optional[str]:
    """
    Получает URL GIF-изображения с API cataas.com (Cat as a service)

    Returns:
        URL GIF-изображения или None в случае ошибки
    """
    try:
        # Используем прямой URL к GIF с котиками
        # API cataas.com возвращает картинку напрямую, не JSON
        caption = random.choice(CAT_CAPTIONS)
        # Добавляем текст к GIF с котиком если это нужно
        # text_params = f"/says/{caption}?fontSize=25&fontColor=white"

        # Возвращаем полный URL для использования в боте
        return CATAAS_API_URL
    except Exception as e:
        logging.error(f"Ошибка при подготовке URL для cataas API: {e}")
        return None

def get_caption() -> str:
    """
    Возвращает подпись в зависимости от выбранного API

    Returns:
        Строка с подписью для GIF
    """
    if API_SOURCE == 'cataas':
        return random.choice(CAT_CAPTIONS)
    return None