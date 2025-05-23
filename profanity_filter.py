"""
Модуль для фильтрации нецензурной лексики с использованием данных из Викисловаря через API MediaWiki
"""

import os
import json
import logging
import re
import aiohttp
from typing import Set, List, Optional, Dict, Any, Union
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# Определение директории данных в зависимости от окружения
if ENVIRONMENT.lower() == 'production':
    DATA_DIR = '/data'
else:
    DATA_DIR = 'data'

# Путь к файлу с кешированным списком нецензурных слов
CACHE_FILE = os.path.join(DATA_DIR, "bad_words_cache.json")

# URL API MediaWiki Викисловаря
MEDIAWIKI_API_URL = "https://ru.wiktionary.org/w/api.php"

# Название категории с матерными выражениями
CATEGORY_NAME = "Категория:Матерные_выражения/ru"

# Список базовых нецензурных слов на случай если не удастся получить данные из Викисловаря
FALLBACK_BAD_WORDS = {
    "бля", "блять", "ебать", "хуй", "пизда", "сука", "пидор", "пидр", "мудак", "долбоёб",
    "еблан", "дебил", "хер", "хрен", "залупа", "манда", "шлюха", "ебало", "жопа",
    "пиздец", "ебаный", "нахуй", "нахер", "похуй", "горит пизда", "дать в еблетку",
    "дать пизды", "дать по ебалу", "дать по пизде мешалкой", "девятый хуй без соли доедать",
    "дневальный! подай станок ебальный!", "до пизды", "а поебаться тебе не завернуть?",
    "а сто хуёв — большая куча?", "ап-хуй", "архипиздрит", "ахуй", "ахуилард",
    # Добавляем составные слова с корнем "еб/ёб"
    "свиноеб", "свиноёб", "мудоеб", "мудоёб", "говноеб", "говноёб", "дебилоеб", "дебилоёб",
    "хуеплет", "хуёплет", "членосос", "хуесос", "хуёсос"
}

# Словарь для добавления вариаций словоформ, которые может не содержать API
ADDITIONAL_WORD_FORMS = {
    "еба": ["ебал", "ебать", "ебу", "ебет", "ебаный", "ебанутый", "ебанько"],
    "хуй": ["хуя", "хуем", "хуями", "хуёв"],
    "пизд": ["пизда", "пизды", "пизде", "пиздец", "пиздой"],
    "хер": ["хера", "херово", "херня", "хером"],
    "бля": ["блять", "бляди", "блядь", "бляха"],
    "залуп": ["залупа", "залупой", "залупиться"]
}

def normalize_yo(text: str) -> str:
    """
    Заменяет букву 'ё' на 'е' для нормализации текста

    Args:
        text: Исходный текст

    Returns:
        Текст с замененными 'ё' на 'е'
    """
    return text.replace('ё', 'е')

def generate_yo_variants(word: str) -> Set[str]:
    """
    Генерирует варианты слова с заменой 'е' на 'ё' во всех возможных сочетаниях

    Args:
        word: Исходное слово

    Returns:
        Множество вариантов слова
    """
    if 'е' not in word and 'ё' not in word:
        return {word}

    variants = {word}

    # Если в слове есть 'ё', добавляем вариант с заменой на 'е'
    if 'ё' in word:
        variants.add(normalize_yo(word))

    # Если в слове есть 'е', генерируем варианты с заменой на 'ё'
    if 'е' in word:
        # Находим все позиции буквы 'е' в слове
        positions = [i for i, char in enumerate(word) if char == 'е']

        # Генерируем все возможные комбинации замен
        for i in range(1, 2**len(positions)):
            new_word = list(word)
            for j, pos_bit in enumerate(bin(i)[2:].zfill(len(positions))):
                if pos_bit == '1':
                    pos = positions[j]
                    new_word[pos] = 'ё'
            variants.add(''.join(new_word))

    return variants

async def get_all_words_in_category() -> Set[str]:
    """
    Получить все слова в категории "Матерные выражения/ru" используя API MediaWiki
    и прямой парсинг HTML страниц

    Returns:
        Set[str]: Множество слов из категории
    """
    logging.info("Начинаю получение слов из категории...")
    words = set()
    processed_urls = set()  # Для отслеживания уже обработанных URL

    # Метод 1: Прямой парсинг HTML страниц с пагинацией
    try:
        async with aiohttp.ClientSession() as session:
            # Начинаем с первой страницы
            base_url = f"https://ru.wiktionary.org/wiki/{CATEGORY_NAME}"
            url = base_url

            # Также проверим альтернативный формат URL
            alt_base_url = "https://ru.wiktionary.org/w/index.php?title=Категория:Матерные_выражения/ru"

            # Обрабатываем первую страницу
            await process_category_page(session, url, words)
            processed_urls.add(url)

            # Пробуем найти следующие страницы
            next_url = await get_next_page_url(session, url)
            while next_url is not None:
                full_url = next_url
                if not full_url.startswith('http'):
                    full_url = f"https://ru.wiktionary.org{next_url}"

                # Проверяем, не обрабатывали ли мы уже этот URL
                if full_url in processed_urls:
                    logging.warning(f"URL уже был обработан, прерываем: {full_url}")
                    break

                processed_urls.add(full_url)
                await process_category_page(session, full_url, words)
                next_url = await get_next_page_url(session, full_url)

            # Если не нашли следующие страницы обычным способом,
            # попробуем обработать страницы с параметрами pagefrom явно
            if len(processed_urls) <= 2:
                # Пробуем явно указать параметры пагинации
                pagefrom_params = [
                    "&pagefrom=испиздить%0Aиспиздить#mw-pages",
                    "&pagefrom=отпиздеться#mw-pages",
                    "&pagefrom=хуёвина+с+морковиной%0Aхуёвина+с+морковино#mw-pages"
                ]

                for param in pagefrom_params:
                    page_url = f"{alt_base_url}{param}"
                    if page_url not in processed_urls:
                        processed_urls.add(page_url)
                        await process_category_page(session, page_url, words)

                # И также проверим pageuntil параметры
                pageuntil_params = [
                    "&pageuntil=испиздить%0Aиспиздить#mw-pages",
                    "&pageuntil=ебанье%0Aебанье#mw-pages"
                ]

                for param in pageuntil_params:
                    page_url = f"{alt_base_url}{param}"
                    if page_url not in processed_urls:
                        processed_urls.add(page_url)
                        await process_category_page(session, page_url, words)

            logging.info(f"Обработано {len(processed_urls)} страниц категории")

    except Exception as e:
        logging.error(f"Ошибка при получении слов напрямую из HTML: {e}")

    # Метод 2: Через API MediaWiki
    try:
        api_words = await fetch_via_api_method()
        words.update(api_words)
        logging.info(f"Через API получено {len(api_words)} слов")
    except Exception as e:
        logging.error(f"Ошибка при получении слов через API MediaWiki: {e}")

    # Добавляем словоформы для лучшего обнаружения
    word_forms = set()
    for word in words:
        word_forms.update(generate_word_forms(word))

    words.update(word_forms)

    # Если не удалось получить ни одного слова, возвращаем базовый набор
    if not words:
        logging.warning("Не удалось получить список слов, возвращаю базовый набор")
        words = FALLBACK_BAD_WORDS
    else:
        # Всегда добавляем базовый набор для надежности
        words.update(FALLBACK_BAD_WORDS)

    logging.info(f"Всего получено {len(words)} уникальных нецензурных слов и их форм")

    # Логируем несколько примеров слов для проверки
    sample = list(words)[:20] if len(words) > 20 else list(words)
    logging.info(f"Примеры слов: {', '.join(sample)}")

    return words

async def process_category_page(session: aiohttp.ClientSession, url: str, words: Set[str]) -> None:
    """
    Извлекает слова из страницы категории
    """
    logging.info(f"Обрабатываю страницу категории: {url}")
    async with session.get(url) as response:
        if response.status != 200:
            logging.error(f"Ошибка при получении страницы: {response.status}")
            return

        html = await response.text()

        # Извлекаем слова из HTML
        # Ищем блок с id="mw-pages"
        mw_pages_pattern = re.compile(r'<div id="mw-pages"[^>]*>(.*?)<noscript>', re.DOTALL)
        pages_match = mw_pages_pattern.search(html)

        if pages_match:
            pages_content = pages_match.group(1)

            # Поиск всех ссылок внутри блока категории
            link_pattern = re.compile(r'<a href="[^"]+" title="([^"]+)"[^>]*>(?:[^<]+)</a>')
            for match in link_pattern.finditer(pages_content):
                title = match.group(1)
                if ":" not in title and "Категория:" not in title:  # Пропускаем подкатегории
                    # Добавляем оригинальное слово
                    word = title.lower()
                    words.add(word)

                    # Добавляем вариации с ё/е
                    words.update(generate_yo_variants(word))

                    # Добавляем вариацию без знаков препинания
                    clean_word = re.sub(r'[^\w\s]', '', word)
                    if clean_word:
                        words.add(clean_word)
                        words.update(generate_yo_variants(clean_word))

            logging.info(f"Найдено {len(words)} слов на данный момент")

async def get_next_page_url(session: aiohttp.ClientSession, current_url: str) -> Optional[str]:
    """
    Извлекает URL следующей страницы из текущей страницы категории.
    Обрабатывает параметры pagefrom и pageuntil в URL.
    """
    async with session.get(current_url) as response:
        if response.status != 200:
            return None

        html = await response.text()

        # Сначала ищем ссылки навигации в блоке "mw-pages"
        navigation_pattern = re.compile(r'<div id="mw-pages".*?(?:Следующая страница|Предыдущая страница|следующие\s+\d+).*?</div>', re.DOTALL)
        nav_match = navigation_pattern.search(html)

        if not nav_match:
            logging.warning("Не найден блок навигации на странице")
            return None

        nav_content = nav_match.group(0)

        # Ищем ссылку на следующую страницу (тексты могут быть разными)
        next_links_pattern = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(?:Следующая страница|следующие\s+\d+|просмотреть следующие)</a>')
        next_matches = list(next_links_pattern.finditer(nav_content))

        if next_matches:
            next_url = next_matches[-1].group(1)  # Берем последнюю найденную ссылку
            next_url = next_url.replace("&amp;", "&")  # Исправляем экранирование амперсанда
            logging.info(f"Найдена ссылка на следующую страницу: {next_url}")
            return next_url

        return None

async def fetch_via_api_method() -> Set[str]:
    """
    Получает слова с использованием стандартного MediaWiki API
    """
    bad_words = set()
    cmcontinue = None

    async with aiohttp.ClientSession() as session:
        while True:
            params = {
                "action": "query",
                "format": "json",
                "list": "categorymembers",
                "cmtitle": CATEGORY_NAME,
                "cmlimit": 500,
                "cmtype": "page", # Только страницы, без подкатегорий
                "cmprop": "title" # Только заголовки
            }

            if cmcontinue:
                params["cmcontinue"] = cmcontinue

            async with session.get(MEDIAWIKI_API_URL, params=params) as response:
                if response.status != 200:
                    break

                try:
                    data = await response.json()

                    # Вывод полного ответа для отладки
                    logging.debug(f"API response: {json.dumps(data, ensure_ascii=False, indent=2)}")

                    if "query" in data and "categorymembers" in data["query"]:
                        members = data["query"]["categorymembers"]
                        for member in members:
                            title = member.get("title", "").lower()
                            if ":" not in title:
                                # Добавляем оригинальное слово
                                bad_words.add(title)

                                # Добавляем вариации с ё/е
                                bad_words.update(generate_yo_variants(title))

                                # Очищаем слово от знаков препинания
                                clean_word = re.sub(r'[^\w\s]', '', title)
                                if clean_word:
                                    bad_words.add(clean_word)
                                    bad_words.update(generate_yo_variants(clean_word))

                        logging.info(f"Через API получено {len(members)} слов")

                    # Проверяем наличие продолжения
                    if "continue" in data and "cmcontinue" in data["continue"]:
                        cmcontinue = data["continue"]["cmcontinue"]
                    else:
                        break
                except Exception as e:
                    logging.error(f"Ошибка при обработке ответа API: {e}")
                    break

    return bad_words

def generate_word_forms(word: str) -> Set[str]:
    """
    Генерирует дополнительные словоформы для слова
    """
    forms = set()
    word = word.lower()

    # Добавляем само слово
    forms.add(word)

    # Добавляем варианты с ё/е
    forms.update(generate_yo_variants(word))

    # Проверяем на совпадение с корнями в словаре дополнительных форм
    for root, variants in ADDITIONAL_WORD_FORMS.items():
        if root in word:
            forms.update(variants)
            # Для каждого варианта добавляем его вариации с ё/е
            for variant in variants:
                forms.update(generate_yo_variants(variant))

    # Генерируем простые склонения
    if len(word) > 3:
        if word.endswith('ть'):
            # Глагольные формы
            base = word[:-2]
            verb_forms = [
                f"{base}л", f"{base}ла", f"{base}ло", f"{base}ли",
                f"{base}ю", f"{base}ет", f"{base}ем", f"{base}ете", f"{base}ут",
                f"{base}нный", f"{base}нная", f"{base}нное", f"{base}нные"
            ]
            forms.update(verb_forms)
            # Для каждой формы добавляем варианты с ё/е
            for verb_form in verb_forms:
                forms.update(generate_yo_variants(verb_form))

        elif word.endswith('а'):
            # Склонения существительных женского рода
            base = word[:-1]
            noun_forms = [
                f"{base}у", f"{base}е", f"{base}ой", f"{base}ы"
            ]
            forms.update(noun_forms)
            # Для каждой формы добавляем варианты с ё/е
            for noun_form in noun_forms:
                forms.update(generate_yo_variants(noun_form))

        elif word.endswith('й'):
            # Склонения прилагательных
            base = word[:-1]
            adj_forms = [
                f"{base}я", f"{base}е", f"{base}ю", f"{base}м",
                f"{base}его", f"{base}ему"
            ]
            forms.update(adj_forms)
            # Для каждой формы добавляем варианты с ё/е
            for adj_form in adj_forms:
                forms.update(generate_yo_variants(adj_form))

    return forms

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
                logging.info(f"Загружено {len(cache_data)} слов из кеш-файла")
                return set(cache_data)
        except Exception as e:
            logging.error(f"Ошибка при чтении кеш-файла: {e}")

    # Если кеш-файла нет или произошла ошибка, получаем данные из Викисловаря
    bad_words = await get_all_words_in_category()

    # Сохраняем полученные данные в кеш
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(bad_words), f, ensure_ascii=False, indent=2)
            logging.info(f"Сохранено {len(bad_words)} слов в кеш-файл")
        return bad_words
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

def contains_profanity(text: str) -> tuple[bool, Optional[str]]:
    """
    Проверяет содержит ли текст нецензурную лексику.

    Args:
        text: Проверяемый текст

    Returns:
        Кортеж (результат, причина), где:
        - результат: True если содержит нецензурную лексику, иначе False
        - причина: строка с объяснением причины срабатывания или None, если нецензурная лексика не обнаружена
    """
    if not text:
        return False, None

    # Приводим текст к нижнему регистру
    text_lower = text.lower()

    # Также подготавливаем вариант текста с нормализованными 'ё' -> 'е'
    text_normalized = normalize_yo(text_lower)

    # Разбиваем на слова оба варианта текста
    words = re.findall(r'\b\w+\b', text_lower)
    words_normalized = re.findall(r'\b\w+\b', text_normalized)

    # Объединяем оба набора слов
    all_words = set(words + words_normalized)

    # 1. Проверяем каждое слово на вхождение в список нецензурных слов напрямую
    for word in all_words:
        if word in BAD_WORDS:
            reason = f"Обнаружено нецензурное слово: '{word}'"
            logging.info(reason)
            return True, reason

    # 2. Проверяем каждое слово с нормализацией ё->е
    for bad_word in BAD_WORDS:
        normalized_bad_word = normalize_yo(bad_word)
        for word in all_words:
            if word == normalized_bad_word or normalize_yo(word) == bad_word:
                reason = f"Обнаружено нецензурное слово (после нормализации): '{word}' -> '{bad_word}'"
                logging.info(reason)
                return True, reason

    # 3. Проверяем на вхождение фраз и словосочетаний (для составных выражений)
    for bad_word in BAD_WORDS:
        if len(bad_word) > 3 and ' ' in bad_word:
            # Для фраз проверяем как оригинал, так и нормализованную версию
            if bad_word in text_lower or bad_word in text_normalized:
                reason = f"Обнаружено нецензурное выражение: '{bad_word}'"
                logging.info(reason)
                return True, reason

            # Проверяем с нормализацией ё->е
            normalized_bad_word = normalize_yo(bad_word)
            if normalized_bad_word in text_lower or normalized_bad_word in text_normalized:
                reason = f"Обнаружено нецензурное выражение (после нормализации): '{bad_word}'"
                logging.info(reason)
                return True, reason

    # 4. Проверяем вхождение корней слов (для обхода склонений)
    for bad_word in BAD_WORDS:
        if len(bad_word) > 3 and ' ' not in bad_word:
            # Проверяем оригинальную версию плохого слова
            for check_text in [text_lower, text_normalized]:
                if bad_word in check_text:
                    # Проверяем, что это именно корень слова, а не часть другого слова
                    word_pattern = re.compile(f'\\b\\w*{re.escape(bad_word)}\\w*\\b')
                    match = word_pattern.search(check_text)
                    if match:
                        detected_word = match.group(0)
                        reason = f"Обнаружен корень нецензурного слова: '{detected_word}' содержит корень '{bad_word}'"
                        logging.info(reason)
                        return True, reason

            # Проверяем нормализованную версию плохого слова
            normalized_bad_word = normalize_yo(bad_word)
            for check_text in [text_lower, text_normalized]:
                if normalized_bad_word in check_text:
                    # Проверяем, что это именно корень слова, а не часть другого слова
                    word_pattern = re.compile(f'\\b\\w*{re.escape(normalized_bad_word)}\\w*\\b')
                    match = word_pattern.search(check_text)
                    if match:
                        detected_word = match.group(0)
                        reason = f"Обнаружен корень нецензурного слова (после нормализации): '{detected_word}' содержит корень '{bad_word}'"
                        logging.info(reason)
                        return True, reason

    # 5. Прямая проверка слов из текста на основе частей слов
    for word in all_words:
        if len(word) >= 4:  # Минимальная длина слова для проверки
            for bad_root in ["хуй", "пизд", "залуп"]:
                if bad_root in word:
                    reason = f"Обнаружен корень нецензурного слова в слове: '{word}' (корень: '{bad_root}')"
                    logging.info(reason)
                    return True, reason

    return False, None