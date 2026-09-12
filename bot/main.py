import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def env_int(name: str, default: int) -> int:
    value = os.getenv(name, str(default)).strip()
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
ADMIN_ID = env_int("ADMIN_ID", 0)
LANG = os.getenv("LANG", "ru").strip() or "ru"
RETENTION_HOURS = env_int("RETENTION_HOURS", 24)
DISABLE_OCR = os.getenv("DISABLE_OCR", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    await update.message.reply_text(
        "Бот запущен. Отправьте торговый сигнал или фотографию.
"
        "Для проверки своего ID используйте /myid."
    )


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    user_id = update.effective_user.id
    admin_note = "
Вы назначены администратором." if user_id == ADMIN_ID else ""
    await update.message.reply_text(f"Ваш Telegram ID: {user_id}{admin_note}")


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if DISABLE_OCR:
        await update.message.reply_text(
            "OCR отключён (DISABLE_OCR=1). Фото получено, но распознавание текста "
            "в текущем режиме не выполняется."
        )
        return
    await update.message.reply_text(
        "OCR пока не подключён в этом MVP. Отправьте текстовый сигнал сообщением."
    )


async def text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "Сообщение получено. Обработка торговых сигналов будет добавлена следующим шагом."
    )


def main() -> None:
    if not TELEGRAM_TOKEN:
        raise RuntimeError(
            "TELEGRAM_TOKEN is not set. Add it to Replit Secrets or the environment."
        )

    logger.info(
        "Starting polling | lang=%s | admin_id=%s | retention_hours=%s | ocr_disabled=%s",
        LANG,
        ADMIN_ID,
        RETENTION_HOURS,
        DISABLE_OCR,
    )

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("myid", myid))
    application.add_handler(MessageHandler(filters.PHOTO, photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
