"""
Main entry point for the bot.
Run: python -m src.main
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from src.bot.bot import create_bot, create_dispatcher
from src.services.sheets.client import get_sheets_client


async def on_startup():
    """Actions on bot startup."""
    logger.info("Bot starting...")

    # Initialize Google Sheets client
    client = get_sheets_client()
    await client.initialize()
    logger.info("Google Sheets client ready")


async def on_shutdown():
    """Actions on bot shutdown."""
    logger.info("Bot shutting down...")

    # Close Google Sheets client
    client = get_sheets_client()
    await client.close()


async def main():
    """Main function."""
    # Configure logging
    logger.add(
        "logs/bot_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )

    # Create bot and dispatcher
    bot = create_bot()
    dp = create_dispatcher()

    # Register startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Starting bot polling...")

    try:
        # Start polling
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
