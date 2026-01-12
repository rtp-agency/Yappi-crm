"""
Bot initialization and configuration.
"""
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from src.config.settings import get_settings
from src.bot.middlewares.auth import WhitelistMiddleware
from src.bot.handlers import start, orders


def create_bot() -> Bot:
    """Create and configure bot instance."""
    settings = get_settings()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    return bot


def create_dispatcher() -> Dispatcher:
    """Create and configure dispatcher with all routers and middlewares."""
    dp = Dispatcher(storage=MemoryStorage())

    # Register whitelist middleware
    dp.message.middleware(WhitelistMiddleware())
    dp.callback_query.middleware(WhitelistMiddleware())

    # Register routers
    dp.include_router(start.router)
    dp.include_router(orders.router)

    logger.info("Dispatcher configured with routers and middlewares")

    return dp
