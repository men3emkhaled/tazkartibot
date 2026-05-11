"""
Tazkarti Booking Bot - Entry Point.
Bot 2: Handles ticket booking for users via Telegram.
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from booking_bot.config import BOOKING_BOT_TOKEN, ADMIN_TELEGRAM_ID
from booking_bot.bot.handlers import router
from booking_bot.db.operations import init_booking_db

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Run on bot startup."""
    logger.info("🚀 Booking Bot starting...")

    # Initialize database
    if not init_booking_db():
        logger.error("❌ Failed to initialize database!")
        sys.exit(1)

    # Notify admin
    if ADMIN_TELEGRAM_ID:
        try:
            await bot.send_message(
                ADMIN_TELEGRAM_ID,
                "🚀 بوت الحجز شغال دلوقتي!\n"
                "هيبعتلك الـ Captchas هنا لما حد يحجز."
            )
        except Exception as e:
            logger.warning(f"⚠️ Could not notify admin: {e}")

    logger.info("✅ Booking Bot ready!")


async def on_shutdown(bot: Bot):
    """Run on bot shutdown."""
    logger.info("👋 Booking Bot shutting down...")
    if ADMIN_TELEGRAM_ID:
        try:
            await bot.send_message(ADMIN_TELEGRAM_ID, "🛑 بوت الحجز اتوقف.")
        except Exception:
            pass


async def main():
    """Main entry point."""
    if not BOOKING_BOT_TOKEN:
        logger.error("❌ BOOKING_BOT_TOKEN not set in .env!")
        sys.exit(1)

    if not ADMIN_TELEGRAM_ID:
        logger.error("❌ ADMIN_TELEGRAM_ID not set in .env!")
        sys.exit(1)

    # Create bot and dispatcher
    bot = Bot(
        token=BOOKING_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=None),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register router
    dp.include_router(router)

    # Register startup/shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Start polling
    logger.info("🤖 Starting polling...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
