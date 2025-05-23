# Бот-фильтр нецензурной лексики

Бот для Telegram, который отслеживает сообщения в чате и при обнаружении нецензурной лексики отправляет GIF-изображение в ответ с одним из случайных вариантов текста.

## Пример

Рабочая версия бота доступна в Telegram: [@OopsNoCursingBot](https://t.me/OopsNoCursingBot)

Добавьте бота в свою группу, чтобы он отслеживал сообщения с нецензурной лексикой и реагировал на них.

## Особенности

- Мониторинг сообщений в чате на наличие нецензурной лексики
- Фильтрация нецензурной лексики с использованием словаря из Викисловаря
- Получение полного списка слов из категории "Матерные выражения/ru" через API MediaWiki
- Поддержка пагинации для обработки всех страниц категории
- Корректная обработка взаимозаменяемых букв "е" и "ё" в нецензурных словах
- Кеширование списка нецензурных слов для быстрой работы
- Выбор источника GIF-изображений для ответа:
  - API yesno.wtf (анимации "да"/"нет")
  - API cataas.com (анимации с котиками)
- Разнообразные текстовые ответы на нецензурную лексику
- Ограничение доступа к административным командам только для администратора бота

## Установка

1. Клонируйте репозиторий:
```
git clone <url-репозитория>
cd <имя-папки>
```

2. Создайте директорию для постоянных данных:
```
mkdir data
```

3. Создайте виртуальное окружение и активируйте его:
```
python -m venv venv
# Для Windows
venv\Scripts\activate
# Для Linux/Mac
source venv/bin/activate
```

4. Установите зависимости:
```
pip install -r requirements.txt
```

5. Создайте файл `.env` на основе `.env.example` и добавьте необходимые переменные:
```
# Токен вашего Telegram бота
BOT_TOKEN=ваш_токен_бота

# Telegram ID администратора бота
ADMIN_ID=ваш_telegram_id

# Среда выполнения: development или production
# development - локальные пути к файлам, production - абсолютные пути (/data)
ENVIRONMENT=development

# API источник для ответных GIF: yesno или cataas
# yesno - GIF с ответами да/нет, cataas - GIF с котиками
API_SOURCE=yesno
```

Токен можно получить у [@BotFather](https://t.me/BotFather) в Telegram.
Узнать свой Telegram ID можно с помощью бота [@userinfobot](https://t.me/userinfobot).

## Запуск

```
python bot.py
```

При первом запуске бот автоматически загрузит список нецензурных слов из Викисловаря через API MediaWiki и сохранит его в файл `/data/bad_words_cache.json`.

## Деплой на Amvera

Бот развернут на сервисе [Amvera](https://amvera.ru/). Если вы хотите использовать этот сервис для деплоя:

1. Зарегистрируйтесь на платформе Amvera
2. Создайте новый проект и подключите ваш репозиторий GitHub
3. Убедитесь, что в корне проекта есть файл `amvera.yml` с правильной конфигурацией:
   ```yaml
   meta:
     environment: python
     toolchain:
       name: pip
       version: 3.11
   build:
     requirementsPath: requirements.txt
   run:
     scriptName: bot.py
     persistenceMount: /data
     containerPort: 80
   ```
4. В настройках проекта на Amvera добавьте переменную окружения `ENVIRONMENT=production`
5. **Важно**: При запуске в режиме `production` бот будет использовать абсолютные пути к файлам в директории `/data/`.

Если вы используете другой сервис для деплоя, следуйте его документации для настройки постоянного хранилища данных.

## Команды бота

### Основные команды
- `/start` или `/help` - информация о боте и доступных командах

### Команды администратора (доступны только для пользователя с ID, указанным в переменной ADMIN_ID)
- `/update_words` - обновить список нецензурных слов из Викисловаря
- `/force_update` - принудительно обновить словарь с удалением кеш-файла
- `/add_word [слово]` - добавить новое слово в словарь нецензурной лексики (вместе с вариациями букв е/ё)
- `/debug` - показать информацию о текущем словаре (количество слов и примеры)
- `/check_env` - проверить текущие значения переменных окружения
- `/test [текст]` - проверить, содержит ли текст нецензурную лексику и отобразить причину срабатывания фильтра
- `/test_yo [слово]` - показать все варианты слова с заменой е/ё и проверить их на нецензурность с указанием причины

## Обработка букв "е" и "ё"

Бот автоматически распознает слова, содержащие нецензурную лексику, независимо от использования букв "е" или "ё". Например, слова "свиноеб" и "свиноёб" будут одинаково определены как нецензурные. Это достигается благодаря:

1. Генерации вариантов слов с различными комбинациями букв "е" и "ё"
2. Нормализации текста для сравнения (замена "ё" на "е")
3. Многоуровневой проверке слов и их корней

## Структура проекта

- `bot.py` - основной файл бота
- `profanity_filter.py` - модуль фильтрации нецензурной лексики с использованием API MediaWiki
- `gif_service.py` - модуль для получения GIF через API
- `requirements.txt` - зависимости проекта
- `.env.example` - пример файла с переменными окружения
- `amvera.yml` - конфигурационный файл для деплоя на Amvera
- `.gitignore` - список файлов, исключенных из системы контроля версий
- `data/` - директория для постоянного хранения данных (не включается в репозиторий)
  - `bot.log` - файл логов работы бота
  - `bad_words_cache.json` - кеш со списком нецензурных слов

> **Примечание:** Файлы `bot.log` и `bad_words_cache.json` создавать не обязательно - они будут созданы автоматически при первом запуске бота. Достаточно только создать директорию `data`.

## Лицензия

MIT