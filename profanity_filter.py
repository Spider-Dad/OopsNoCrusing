"""
Модуль для фильтрации нецензурной лексики с использованием данных из Викисловаря
"""

import os
import json
import logging
import re
import aiohttp
from bs4 import BeautifulSoup
from typing import Set, List, Optional

# Путь к файлу с кешированным списком нецензурных слов
CACHE_FILE = "bad_words_cache.json"

# URL категории матерных выражений на Викисловаре
WIKTIONARY_URL = "https://ru.wiktionary.org/wiki/Категория:Матерные_выражения/ru"

# Список базовых нецензурных слов на случай если не удастся получить данные из Викисловаря
FALLBACK_BAD_WORDS = {
    "бля", "блять", "ебать", "хуй", "пизда", "сука", "пидор", "пидр", "мудак", "долбоёб",
    "еблан", "дебил", "хер", "хрен", "залупа", "манда", "шлюха", "ебало", "жопа",
    "пиздец", "ебаный", "нахуй", "нахер", "похуй"
}

async def fetch_bad_words_from_wiktionary() -> Set[str]:
    """
    Получает список нецензурных слов из Викисловаря.

    Returns:
        Set[str]: Множество нецензурных слов
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(WIKTIONARY_URL) as response:
                if response.status != 200:
                    logging.error(f"Ошибка при получении страницы Викисловаря: {response.status}")
                    return FALLBACK_BAD_WORDS

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Находим все ссылки в категории матерных выражений
                bad_words = set()
                category_members = soup.select("div.mw-category a")

                for link in category_members:
                    word = link.text.strip().lower()
                    bad_words.add(word)

                    # Добавляем вариации слова без знаков препинания
                    clean_word = re.sub(r'[^\w\s]', '', word)
                    if clean_word:
                        bad_words.add(clean_word)

                # Если список оказался пустым, используем резервный список
                if not bad_words:
                    logging.warning("Не удалось получить список слов из Викисловаря, используем стандартный набор")
                    return FALLBACK_BAD_WORDS

                # Добавляем еще несколько часто используемых слов, которые могут отсутствовать в категории
                bad_words.update(FALLBACK_BAD_WORDS)

                return bad_words

    except Exception as e:
        logging.error(f"Ошибка при парсинге Викисловаря: {e}")
        return FALLBACK_BAD_WORDS

async def load_or_update_bad_words() -> Set[str]:
    """
    Загружает список нецензурных слов из кеша или обновляет его из Викисловаря.

    Returns:
        Set[str]: Множество нецензурных слов
    """
    # Проверяем наличие кеш-файла
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                return set(cache_data)
        except Exception as e:
            logging.error(f"Ошибка при чтении кеш-файла: {e}")

    # Если кеш-файла нет или произошла ошибка, получаем данные из Викисловаря
    bad_words = await fetch_bad_words_from_wiktionary()

    # Сохраняем полученные данные в кеш
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(bad_words), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка при сохранении кеш-файла: {e}")

    return bad_words

# Глобальная переменная для хранения списка нецензурных слов
BAD_WORDS = FALLBACK_BAD_WORDS

async def initialize_bad_words():
    """
    Инициализирует глобальный список нецензурных слов при запуске приложения.
    """
    global BAD_WORDS
    BAD_WORDS = await load_or_update_bad_words()
    logging.info(f"Загружено {len(BAD_WORDS)} нецензурных слов")

def contains_profanity(text: str) -> bool:
    """
    Проверяет содержит ли текст нецензурную лексику.

    Args:
        text: Проверяемый текст

    Returns:
        True если содержит нецензурную лексику, иначе False
    """
    if not text:
        return False

    # Приводим текст к нижнему регистру и разбиваем на слова
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)

    # Проверяем каждое слово на вхождение в список нецензурных слов
    for word in words:
        if word in BAD_WORDS:
            return True

    # Проверяем вхождение корней слов (для обхода склонений)
    for bad_word in BAD_WORDS:
        if len(bad_word) > 3 and bad_word in text_lower:
            return True

    return False