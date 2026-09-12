# trading-signal-bot-mvp

Минимальный Telegram-бот на Python с polling-режимом. В текущем MVP OCR отключён, поэтому для запуска в Replit системный Tesseract не требуется.

## Запуск в Replit

В Secrets / Environment variables добавьте:

- TELEGRAM_TOKEN — токен от BotFather (не публикуйте его)
- ADMIN_ID — 5378044435
- LANG — ru
- RETENTION_HOURS — 24
- DISABLE_OCR — 1

Файл .replit уже содержит команду запуска:

pip install -r bot/requirements.txt && python bot/main.py

После запуска проверьте в Telegram:

- /start — проверка запуска бота;
- /myid — получение своего Telegram ID;
- фото — бот ответит, что OCR отключён.

## Локальный запуск

cp .env.example .env
python -m pip install -r bot/requirements.txt
python bot/main.py

Настоящий токен храните только в переменных окружения или Secrets.
