"""
Эхо-бот с фильтрацией нецензурной лексики.
При обнаружении нецензурной лексики отправляет GIF-изображение в ответ.
"""

import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ContentType

from profanity_filter import contains_profanity
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

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """
    Обработчик команд /start и /help
    """
    await message.reply("Привет!\nЯ эхо-бот с функцией фильтрации нецензурной лексики.\n"
                       "Если ты напишешь плохие слова, я отправлю тебе GIF.")

@dp.message_handler(content_types=ContentType.TEXT)
async def echo_message(message: types.Message):
    """
    Эхо всех текстовых сообщений
    Если сообщение содержит нецензурную лексику, отправляет GIF
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
                caption="Ой-ой, кажется, ваш ротик немножко 💩 засорился!"
            )
        else:
            # Если не удалось получить GIF, отправляем текстовое сообщение
            await message.reply("Ой-ой, кажется, ваш ротик немножко 💩 засорился!")
    else:
        # Эхо обычного сообщения
        await message.answer(text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)