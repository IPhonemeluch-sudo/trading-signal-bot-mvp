import asyncio
import io
import logging
import os
import re
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv
from PIL import Image
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

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
DISABLE_OCR = os.getenv("DISABLE_OCR", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


@dataclass
class TradingSignal:
    symbol: str
    side: str
    entry: float
    stop_loss: float
    take_profits: List[float]


NUMBER = r"(\d+(?:[.,]\d+)?)"
SIDE_RE = re.compile(r"\b(BUY|SELL|LONG|SHORT|ПОКУПКА|ПРОДАЖА|ЛОНГ|ШОРТ)\b", re.I)

# Labels are intentionally kept separate from the number expression so that
# "SL: 64000" and "стоп-лосс 64000" are handled identically.
ENTRY_RE = re.compile(
    rf"\b(?:entry|вход|цена(?:\s+входа)?|price)\b\s*[:=\-]?\s*{NUMBER}",
    re.I,
)
STOP_RE = re.compile(
    rf"\b(?:sl|stop[\s-]*loss|stop|стоп[\s-]*лосс|стоп)\b\s*[:=\-]?\s*{NUMBER}",
    re.I,
)
TP_RE = re.compile(
    rf"\b(?:tp\d*|take[\s-]*profit|тейк[\s-]*профит|цель)"
    rf"(?:\s+\d+\s*(?=[:=\-]))?"
    rf"\s*[:=\-]?\s*{NUMBER}",
    re.I,
)


def number(value: str) -> float:
    """Convert common signal number formats to float."""
    return float(value.replace(",", "."))


def find_symbol(text: str, side_match: re.Match[str]) -> Optional[str]:
    """Find a ticker near the side, preferring common quote-currency suffixes."""
    before_side = text[: side_match.start()]
    after_side = text[side_match.end() :]
    candidates = re.findall(r"\b[A-Z][A-Z0-9]{2,14}\b", before_side + " " + after_side)
    ignored = {
        "BUY",
        "SELL",
        "LONG",
        "SHORT",
        "ENTRY",
        "PRICE",
        "STOP",
        "LOSS",
        "TAKE",
        "PROFIT",
        "TP",
        "SL",
    }
    candidates = [item for item in candidates if item not in ignored]
    if not candidates:
        return None
    quote_suffixes = ("USDT", "USDC", "USD", "BTC", "ETH", "EUR")
    return next(
        (candidate for candidate in candidates if candidate.endswith(quote_suffixes)),
        candidates[0],
    )


def parse_signal(text: str) -> TradingSignal:
    """Parse a signal with a symbol, direction, entry, SL and at least one TP.

    Supported examples:
      BTCUSDT BUY Entry: 65000 SL: 64000 TP1: 67000 TP2: 68000
      ETHUSDT LONG
      Вход: 3500 Стоп: 3400 Цель 1: 3700
    """
    side_match = SIDE_RE.search(text)
    if not side_match:
        raise ValueError("не найдено направление BUY/SELL или LONG/SHORT")

    symbol = find_symbol(text.upper(), side_match)
    if not symbol:
        raise ValueError("не найден тикер, например BTCUSDT")

    raw_side = side_match.group(1).upper()
    side = "BUY / LONG" if raw_side in {"BUY", "LONG", "ПОКУПКА", "ЛОНГ"} else "SELL / SHORT"

    entry_match = ENTRY_RE.search(text)
    if not entry_match:
        # Many channels omit the "Entry" label:
        # "BTCUSDT BUY 65000 SL 64000 TP 67000".
        # In that case use the first number after the direction and before SL/TP.
        after_side = text[side_match.end() :]
        risk_label = re.search(
            r"\b(?:sl|stop[\s-]*loss|stop|стоп[\s-]*лосс|стоп|"
            r"tp\d*|take[\s-]*profit|тейк[\s-]*профит|цель)\b",
            after_side,
            re.I,
        )
        entry_area = after_side[: risk_label.start()] if risk_label else after_side
        fallback_entry = re.search(NUMBER, entry_area)
        if fallback_entry:
            entry_match = fallback_entry
    stop_match = STOP_RE.search(text)
    take_profits = [number(match.group(1)) for match in TP_RE.finditer(text)]

    missing = []
    if not entry_match:
        missing.append("Entry")
    if not stop_match:
        missing.append("SL")
    if not take_profits:
        missing.append("TP")
    if missing:
        raise ValueError("не хватает полей: " + ", ".join(missing))

    return TradingSignal(
        symbol=symbol,
        side=side,
        entry=number(entry_match.group(1)),
        stop_loss=number(stop_match.group(1)),
        take_profits=take_profits,
    )


def format_price(value: float) -> str:
    return f"{value:g}"


def format_signal(signal: TradingSignal) -> str:
    targets = "\n".join(
        f"  TP{i}: {format_price(target)}"
        for i, target in enumerate(signal.take_profits, start=1)
    )
    return (
        "✅ Сигнал распознан\n\n"
        f"Инструмент: {signal.symbol}\n"
        f"Направление: {signal.side}\n"
        f"Вход: {format_price(signal.entry)}\n"
        f"Стоп-лосс: {format_price(signal.stop_loss)}\n"
        f"Тейк-профиты:\n{targets}"
    )


def signal_help() -> str:
    return (
        "Не удалось распознать сигнал. Отправьте его в формате:\n\n"
        "BTCUSDT BUY\n"
        "Entry: 65000\n"
        "SL: 64000\n"
        "TP1: 67000\n"
        "TP2: 68000"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    await update.message.reply_text(
        "Бот запущен. Отправьте торговый сигнал или фотографию. "
        "Для проверки своего ID используйте /myid."
    )


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    user_id = update.effective_user.id
    admin_note = " Вы назначены администратором." if user_id == ADMIN_ID else ""
    await update.message.reply_text(f"Ваш Telegram ID: {user_id}.{admin_note}")


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    if DISABLE_OCR:
        await update.message.reply_text(
            "OCR отключён (DISABLE_OCR=1). Фото получено, но распознавание текста "
            "в текущем режиме не выполняется."
        )
        return

    try:
        telegram_file = await update.message.photo[-1].get_file()
        photo_bytes = await telegram_file.download_as_bytearray()

        with Image.open(io.BytesIO(photo_bytes)) as image:
            try:
                import pytesseract
            except Exception:
                logger.exception("pytesseract import failed")
                await update.message.reply_text(
                    "OCR временно недоступен: пакет pytesseract не установлен."
                )
                return

            text = await asyncio.to_thread(
                pytesseract.image_to_string,
                image,
                lang="eng+rus",
            )

        text = text.strip()
        if not text:
            await update.message.reply_text("На фото не удалось распознать текст.")
            return

        try:
            signal = parse_signal(text)
        except ValueError:
            await update.message.reply_text(
                f"Распознанный текст:\n{text}\n\n{signal_help()}"
            )
            return
        await update.message.reply_text(format_signal(signal))
    except Exception:
        logger.exception("Error processing photo")
        await update.message.reply_text(
            "Не удалось обработать фото. Проверьте качество изображения и попробуйте ещё раз."
        )


async def text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    try:
        signal = parse_signal(update.message.text)
    except ValueError as exc:
        # If it looks like a signal but is incomplete, explain what is missing.
        if SIDE_RE.search(update.message.text):
            await update.message.reply_text(f"Сигнал неполный: {exc}.\n\n{signal_help()}")
        else:
            await update.message.reply_text(signal_help())
        return

    await update.message.reply_text(format_signal(signal))


def create_application(token: str) -> Application:
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("myid", myid))
    application.add_handler(MessageHandler(filters.PHOTO, photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
    return application


async def start_app_async(app: Application) -> None:
    await app.initialize()
    await app.start()
    await app.updater.start_polling()


async def stop_app_async(app: Application) -> None:
    try:
        await app.updater.stop()
    except Exception:
        logger.exception("Error stopping polling")
    try:
        await app.stop()
    except Exception:
        logger.exception("Error stopping app")
    try:
        await app.shutdown()
    except Exception:
        logger.exception("Error during app shutdown")


async def main_async() -> None:
    raw = os.getenv("TOKENS", "").strip()
    tokens = [token.strip() for token in raw.split(",") if token.strip()]
    if not tokens and TELEGRAM_TOKEN:
        tokens = [TELEGRAM_TOKEN]
    if not tokens:
        raise RuntimeError(
            "No TOKENS or TELEGRAM_TOKEN set. Set TOKENS (comma-separated) "
            "or TELEGRAM_TOKEN."
        )

    logger.info("Starting %d bot(s) | ocr_disabled=%s", len(tokens), DISABLE_OCR)
    apps: List[Application] = []
    for token in tokens:
        try:
            app = create_application(token)
            await start_app_async(app)
            apps.append(app)
            logger.info("Started bot for token prefix=%s...", token[:8])
        except Exception:
            logger.exception("Failed to start bot for token prefix=%s", token[:8])

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutdown signal received")
    finally:
        for app in apps:
            await stop_app_async(app)


if __name__ == "__main__":
    asyncio.run(main_async())