Короткие инструкции по запуску бота в Replit

1) Импорт репозитория
- В Replit: Create → Import from GitHub → вставьте URL репозитория: https://github.com/IPhonemeluch-sudo/trading-signal-bot-mvp

2) Настройка Secrets (в правой панели — Environment variables)
- TELEGRAM_TOKEN = <ваш токен от BotFather>
- ADMIN_ID = 5378044435
- LANG = ru
- RETENTION_HOURS = 24
- DISABLE_OCR = 1    # ОБЯЗАТЕЛЬНО: отключает попытки использовать системный Tesseract в Replit

3) Команда запуска (в .replit уже указано)
- Replit автоматически выполнит: pip install -r bot/requirements.txt && python bot/main.py

4) Тестирование
- Нажмите Run в Replit и наблюдайте логи.
- В Telegram отправьте /start и /myid — бот должен ответить.
- При отправке фото бот вернёт сообщение, что OCR отключён (если DISABLE_OCR=1).

Примечания
- НЕ храните TELEGRAM_TOKEN в публичном репозитории. Всегда используйте Replit Secrets.
- Если в будущем захотите включить OCR — переносите бот на хост с системным tesseract (Railway/VPS/Render) и снимайте DISABLE_OCR.
