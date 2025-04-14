"""
Эхо-бот с фильтрацией нецензурной лексики.
При обнаружении нецензурной лексики отправляет GIF-изображение в ответ.
"""

import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ContentType

from profanity_filter import contains_profanity, initialize_bad_words
from gif_service import get_gif_url

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение токена из переменных окружения
API_TOKEN = os.getenv('BOT_TOKEN')

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Инициализация списка нецензурных слов
async def on_startup(dp):
    await initialize_bad_words()
    logging.info("Бот запущен и готов к работе")

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """
    Обработчик команд /start и /help
    """
    await message.reply("Привет!\nЯ эхо-бот с функцией фильтрации нецензурной лексики.\n"
                       "Если ты напишешь плохие слова, я отправлю тебе GIF.")

@dp.message_handler(commands=['update_words'])
async def update_bad_words(message: types.Message):
    """
    Обработчик команды обновления списка нецензурных слов
    """
    # Проверяем, что команда вызвана из чата администратора
    if message.from_user.id == message.chat.id:  # Это личный чат с ботом
        await message.reply("Обновляю список нецензурных слов из Викисловаря...")
        await initialize_bad_words()
        await message.reply("Список обновлен!")
    else:
        await message.reply("Эта команда доступна только в личном чате с ботом.")

@dp.message_handler(content_types=ContentType.TEXT)
async def echo_message(message: types.Message):
    """
    Обработчик текстовых сообщений
    Реагирует только на сообщения с нецензурной лексикой
    """
    text = message.text

    # Проверяем текст на наличие нецензурной лексики
    if contains_profanity(text):
        # Получаем URL GIF из API
        gif_url = await get_gif_url()

        if gif_url:
            # Отправляем GIF в ответ на сообщение с нецензурной лексикой
            await message.reply_animation(
                animation=gif_url,
                caption="Пожалуйста, не используйте нецензурную лексику! 🙏"
            )
        else:
            # Если не удалось получить GIF, отправляем текстовое сообщение
            await message.reply("Пожалуйста, не используйте нецензурную лексику! 🙏")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)