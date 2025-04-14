"""
Эхо-бот с фильтрацией нецензурной лексики.
При обнаружении нецензурной лексики отправляет GIF-изображение в ответ.
"""

import logging
import os
import random
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ContentType, ParseMode

from profanity_filter import contains_profanity, initialize_bad_words
from gif_service import get_gif_url

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение токена и ID администратора из переменных окружения
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# Определение путей в зависимости от окружения
if ENVIRONMENT.lower() == 'production':
    DATA_DIR = '/data'
else:
    DATA_DIR = 'data'

# Преобразуем ID администратора в число, если он задан
ADMIN_ID = int(ADMIN_ID) if ADMIN_ID and ADMIN_ID.isdigit() else None

# Список сообщений для ответа на нецензурную лексику
PROFANITY_RESPONSES = [
    "Ой-ой, кажется, ваш ротик немножко 💩 засорился!",
    "Ваше сообщение было обработано цензурой. Результат: 🚫🤬→🎁 (вот вам гифка вместо мата).",
    "Замечено: 99% мата — это крик души. Вот вам гифка вместо терапии.",
    "Ваш комментарий был слишком 🧨 spicy 🧨 для этого чата. Охлаждаем.",
    "Вот вам гифка, пока вы вспоминаете, как говорить без мата. Как в детсаде!",
    "Чат записал это в \"Тетрадь позора\". Исправляемся?",
    "\"Сказано — не материться!\" (с) Капитан Очевидность."
]

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(DATA_DIR, "bot.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Вспомогательная функция для проверки прав администратора
def is_admin(user_id):
    """Проверяет, является ли пользователь администратором бота"""
    return ADMIN_ID and user_id == ADMIN_ID

# Текст справки
HELP_TEXT = """
*Бот-фильтр нецензурной лексики*

Этот бот отслеживает сообщения в чате на наличие нецензурной лексики и отправляет GIF-изображение в ответ.

*Доступные команды:*

*Основные команды:*
• `/start` или `/help` — показать эту справку

*Команды администратора:*
• `/update_words` — обновить список нецензурных слов из Викисловаря
• `/force_update` — принудительно обновить список слов с удалением кеша
• `/add_word [слово]` — добавить новое слово в список
• `/debug` — показать информацию о текущем списке

*Команды тестирования:*
• `/test [текст]` — проверить текст на наличие нецензурной лексики
• `/test_yo [слово]` — показать варианты слова с заменой е/ё

*Примечание:* Команды администратора доступны только для администратора бота.
"""

# Инициализация списка нецензурных слов
async def on_startup(dp):
    logger.info("Запуск бота и инициализация списка нецензурных слов...")
    await initialize_bad_words()
    logger.info("Бот запущен и готов к работе")

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """
    Обработчик команд /start и /help
    """
    await message.reply(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(commands=['update_words'])
async def update_bad_words(message: types.Message):
    """
    Обработчик команды обновления списка нецензурных слов (только для администратора)
    """
    if not is_admin(message.from_user.id):
        await message.reply("⚠️ У вас нет прав администратора для выполнения этой команды.")
        return

    await message.reply("Обновляю список нецензурных слов из Викисловаря...")
    await initialize_bad_words()
    await message.reply("✅ Список обновлен!")

@dp.message_handler(commands=['force_update'])
async def force_update_words(message: types.Message):
    """
    Принудительное обновление списка слов с удалением кеша (только для администратора)
    """
    if not is_admin(message.from_user.id):
        await message.reply("⚠️ У вас нет прав администратора для выполнения этой команды.")
        return

    from profanity_filter import CACHE_FILE
    import os

    await message.reply("Начинаю принудительное обновление списка...")

    # Удаляем кеш-файл если он существует
    if os.path.exists(CACHE_FILE):
        try:
            os.remove(CACHE_FILE)
            await message.reply(f"Кеш-файл {CACHE_FILE} удален.")
        except Exception as e:
            await message.reply(f"Ошибка при удалении кеш-файла: {e}")

    # Запускаем обновление
    await initialize_bad_words()

    from profanity_filter import BAD_WORDS
    count = len(BAD_WORDS)
    await message.reply(f"✅ Список принудительно обновлен! Загружено {count} слов.")

@dp.message_handler(commands=['debug'])
async def debug_info(message: types.Message):
    """
    Отладочная информация (только для администратора)
    """
    if not is_admin(message.from_user.id):
        await message.reply("⚠️ У вас нет прав администратора для выполнения этой команды.")
        return

    from profanity_filter import BAD_WORDS
    count = len(BAD_WORDS)
    sample = list(BAD_WORDS)[:10] if count > 10 else list(BAD_WORDS)

    debug_text = f"📊 *Информация о списке:*\n\n" \
                f"• Количество слов: {count}\n" \
                f"• Примеры слов: {', '.join(sample)}"

    await message.reply(debug_text, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(commands=['test'])
async def test_filter(message: types.Message):
    """
    Тестирование фильтра на конкретных словах (только для администратора)
    """
    if not is_admin(message.from_user.id):
        await message.reply("⚠️ У вас нет прав администратора для выполнения этой команды.")
        return

    if not message.get_args():
        await message.reply("Использование: `/test [слово или фраза для проверки]`", parse_mode=ParseMode.MARKDOWN)
        return

    test_text = message.get_args()
    result = contains_profanity(test_text)

    if result:
        await message.reply(f"✅ Текст «{test_text}» содержит нецензурную лексику")
    else:
        await message.reply(f"❌ Текст «{test_text}» не содержит нецензурную лексику")

@dp.message_handler(commands=['test_yo'])
async def test_yo_variations(message: types.Message):
    """
    Тестирование фильтра на слова с буквами е/ё (только для администратора)
    """
    if not is_admin(message.from_user.id):
        await message.reply("⚠️ У вас нет прав администратора для выполнения этой команды.")
        return

    if not message.get_args():
        await message.reply("Использование: `/test_yo [слово с буквой е или ё]`", parse_mode=ParseMode.MARKDOWN)
        return

    test_word = message.get_args().strip()

    # Импортируем функции из модуля profanity_filter
    from profanity_filter import generate_yo_variants, contains_profanity

    # Получаем варианты слова с е/ё
    variants = generate_yo_variants(test_word)

    # Проверяем каждый вариант на нецензурность
    results = []
    for variant in variants:
        is_profane = contains_profanity(variant)
        status = "✅ нецензурное" if is_profane else "❌ обычное"
        results.append(f"• `{variant}` — {status}")

    # Формируем ответное сообщение
    response = f"🔄 *Варианты слова '{test_word}' с заменой е/ё:*\n\n"
    response += "\n".join(results)

    await message.reply(response, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(commands=['add_word'])
async def add_bad_word(message: types.Message):
    """
    Добавление слова в список нецензурной лексики (только для администратора)
    """
    if not is_admin(message.from_user.id):
        await message.reply("⚠️ У вас нет прав администратора для выполнения этой команды.")
        return

    args = message.get_args()
    if not args:
        await message.reply("Использование: `/add_word [слово для добавления]`", parse_mode=ParseMode.MARKDOWN)
        return

    word = args.strip().lower()

    # Импортируем необходимые функции и переменные
    from profanity_filter import BAD_WORDS, CACHE_FILE, generate_yo_variants
    import json

    # Добавляем слово и его вариации
    new_words = generate_yo_variants(word)
    words_count_before = len(BAD_WORDS)

    # Обновляем глобальный список
    BAD_WORDS.update(new_words)

    # Сохраняем обновленный список в кеш
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(BAD_WORDS), f, ensure_ascii=False, indent=2)

        added_count = len(BAD_WORDS) - words_count_before
        await message.reply(f"✅ Слово «{word}» и {added_count-1} его вариаций успешно добавлены в список.\n"
                           f"Всего слов в списке: {len(BAD_WORDS)}")

    except Exception as e:
        await message.reply(f"❌ Произошла ошибка при сохранении: {e}")

@dp.message_handler(content_types=ContentType.TEXT)
async def process_message(message: types.Message):
    """
    Обработчик текстовых сообщений
    Реагирует только на сообщения с нецензурной лексикой
    """
    text = message.text

    # Проверяем текст на наличие нецензурной лексики
    logger.debug(f"Проверка сообщения: {text}")
    if contains_profanity(text):
        logger.info(f"Обнаружена нецензурная лексика в сообщении: {text}")

        # Получаем URL GIF из API
        gif_url = await get_gif_url()

        if gif_url:
            # Выбираем случайное сообщение из списка
            caption = random.choice(PROFANITY_RESPONSES)

            # Отправляем GIF в ответ на сообщение с нецензурной лексикой
            await message.reply_animation(
                animation=gif_url,
                caption=caption
            )
        else:
            # Если не удалось получить GIF, отправляем текстовое сообщение
            await message.reply(random.choice(PROFANITY_RESPONSES))
    else:
        logger.debug("Нецензурная лексика не обнаружена")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)