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
    # Повторно считываем переменную окружения для уверенности
    api_source = os.getenv('API_SOURCE', 'yesno').lower()

    logging.info(f"Используемый API источник: {api_source} (глобальная переменная API_SOURCE={API_SOURCE})")

    if api_source == 'cataas':
        logging.info("Выбран источник CATAAS (котики)")
        return await get_cat_gif()
    else:
        logging.info("Выбран источник YESNO (по умолчанию)")
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
        # Выбираем случайную подпись для котика
        caption = random.choice(CAT_CAPTIONS)

        # С вероятностью 50% добавляем текст к изображению котика
        if random.choice([True, False]):
            # Используем API для добавления текста на изображение
            # Заменяем пробелы на %20 для URL
            caption_encoded = caption.replace(" ", "%20")
            text_params = f"/says/{caption_encoded}?fontSize=20&color=white"
            url = CATAAS_API_URL + text_params
        else:
            url = CATAAS_API_URL

        # Добавляем случайный параметр, чтобы избежать кеширования Telegram
        random_param = f"?r={random.randint(1, 100000)}"
        if "?" in url:
            # Если уже есть параметры, добавляем через &
            return url + f"&r={random.randint(1, 100000)}"
        else:
            return url + random_param

    except Exception as e:
        logging.error(f"Ошибка при подготовке URL для cataas API: {e}")
        return None

def get_caption() -> str:
    """
    Возвращает подпись в зависимости от выбранного API

    Returns:
        Строка с подписью для GIF
    """
    # Согласованно используем ту же переменную, что и в get_gif_url
    api_source = os.getenv('API_SOURCE', 'yesno').lower()

    if api_source == 'cataas':
        return random.choice(CAT_CAPTIONS)
    return None