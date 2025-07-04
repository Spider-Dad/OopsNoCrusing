"""
Модуль для работы с различными API для получения GIF-изображений
"""

import os
import aiohttp
import logging
import random
from typing import Optional, Tuple
from dotenv import load_dotenv

from constants import (
    PROFANITY_RESPONSES, CAT_CAPTIONS, YESNO_API_URL, CATAAS_API_URL,
    FORCE_NO_PARAM, ERROR_THRESHOLD
)
from utils import retry_on_timeout_gif

# Загрузка переменных окружения
load_dotenv()

# Выбор API для получения GIF
API_SOURCE = os.getenv('API_SOURCE', 'yesno').lower()

# Счетчик ошибок для каждого API
api_error_count = {
    'yesno': 0,
    'cataas': 0
}

async def get_gif_url() -> Tuple[Optional[str], str]:
    """
    Получает URL GIF-изображения с выбранного API

    Returns:
        Tuple[Optional[str], str]: (URL GIF-изображения или None в случае ошибки, название использованного API)
    """
    # Повторно считываем переменную окружения для уверенности
    api_source = os.getenv('API_SOURCE', 'yesno').lower()

    # Проверяем счетчик ошибок и переключаем API если нужно
    if api_error_count[api_source] >= ERROR_THRESHOLD:
        api_source = 'yesno' if api_source == 'cataas' else 'cataas'
        logging.warning(f"Переключение на API {api_source} из-за превышения порога ошибок")
        api_error_count[api_source] = 0  # Сбрасываем счетчик для нового API

    logging.info(f"Используемый API источник: {api_source} (глобальная переменная API_SOURCE={API_SOURCE})")

    if api_source == 'cataas':
        logging.info("Выбран источник CATAAS (котики)")
        gif_url = await get_cat_gif()
        if gif_url is None:
            api_error_count['cataas'] += 1
            logging.warning(f"Ошибка при получении GIF от cataas. Счетчик ошибок: {api_error_count['cataas']}")
            # Пробуем получить GIF от yesno
            gif_url = await get_yesno_gif()
            return gif_url, 'yesno'
        return gif_url, 'cataas'
    else:
        logging.info("Выбран источник YESNO (по умолчанию)")
        gif_url = await get_yesno_gif()
        if gif_url is None:
            api_error_count['yesno'] += 1
            logging.warning(f"Ошибка при получении GIF от yesno. Счетчик ошибок: {api_error_count['yesno']}")
            # Пробуем получить GIF от cataas
            gif_url = await get_cat_gif()
            return gif_url, 'cataas'
        return gif_url, 'yesno'

async def get_yesno_gif() -> Optional[str]:
    """
    Получает URL GIF-изображения с API yesno.wtf

    Returns:
        URL GIF-изображения или None в случае ошибки
    """
    async def _get_gif():
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(YESNO_API_URL + FORCE_NO_PARAM) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('image')
                else:
                    logging.error(f"yesno API вернул статус: {response.status}")
                    return None

    return await retry_on_timeout_gif(_get_gif)

async def get_cat_gif() -> Optional[str]:
    """
    Получает URL GIF-изображения с API cataas.com (Cat as a service)

    Returns:
        URL GIF-изображения или None в случае ошибки
    """
    try:
        # Используем базовый URL без добавления текста
        url = CATAAS_API_URL

        # Добавляем случайный параметр, чтобы избежать кеширования Telegram
        random_param = f"?r={random.randint(1, 100000)}"
        url = url + random_param

        async def _get_gif():
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return url
                    logging.error(f"cataas API вернул статус: {response.status}")
                    return None

        return await retry_on_timeout_gif(_get_gif)

    except Exception as e:
        logging.error(f"Ошибка при подготовке URL для cataas API: {e}")
        return None

def get_caption(api_source: str = None) -> str:
    """
    Возвращает подпись в зависимости от выбранного API

    Args:
        api_source: Название API, которое использовалось для получения GIF

    Returns:
        Строка с подписью для GIF
    """
    if api_source == 'cataas':
        return random.choice(CAT_CAPTIONS)
    return random.choice(PROFANITY_RESPONSES)