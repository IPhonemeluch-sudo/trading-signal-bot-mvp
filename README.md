# trading-signal-bot-mvp

Минимальный Telegram-бот на Python с polling-режимом. Бот принимает текстовые сообщения и фотографии; для фотографий выполняется OCR через Tesseract с языками `eng+rus`.

## Импорт в Replit

1. Откройте Replit и выберите **Create → Import from GitHub**.
2. Вставьте URL репозитория:

   https://github.com/IPhonemeluch-sudo/trading-signal-bot-mvp

3. Импортируйте ветку `main`.
4. Файл запуска находится в `bot/main.py`; команда запуска уже прописана в `.replit`.

## Secrets / Environment variables

Добавьте в Replit Secrets:

- `TELEGRAM_TOKEN` — токен от BotFather; не публикуйте его.
- `ADMIN_ID` — Telegram ID администратора, например `5378044435`.
- `LANG` — язык интерфейса, по умолчанию `ru`.
- `RETENTION_HOURS` — срок хранения данных в часах, по умолчанию `24`.

## OCR без Tesseract

Переменная `DISABLE_OCR` необязательна:

- `DISABLE_OCR=0` — бот пытается распознать текст на фото.
- `DISABLE_OCR=1` — OCR отключён, фото принимается без распознавания.

Если в среде Replit системный Tesseract не установлен, бот всё равно запускается. При отправке фото он сообщит, что OCR недоступен, и продолжит работать. Это не приводит к остановке процесса.

## Проверка в Telegram

- `/start` — проверить запуск бота.
- `/myid` — получить свой Telegram ID.
- Текстовое сообщение — проверить обработчик текста.
- Фотография с текстом — проверить OCR или безопасную обработку ошибки, если Tesseract недоступен.

## Локальный запуск


Скопируйте пример переменных окружения и установите зависимости:

```bash
cp .env.example .env
python -m pip install -r bot/requirements.txt
python bot/main.py
```

## Docker

Dockerfile устанавливает Tesseract и русский языковой пакет:

```bash
docker build -t trading-signal-bot ./bot
docker run --env-file .env trading-signal-bot
```

Настоящий токен храните только в переменных окружения или Replit Secrets.
