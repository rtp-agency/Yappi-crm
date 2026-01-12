"""
Whitelist authentication middleware.
Only allows users from ADMIN_IDS to use the bot.
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from loguru import logger

from src.config.settings import get_settings


class WhitelistMiddleware(BaseMiddleware):
    """
    Middleware that checks if user is in the whitelist (ADMIN_IDS).
    Blocks all messages from unauthorized users.
    """

    def __init__(self):
        self.settings = get_settings()
        self.allowed_ids = self.settings.admin_ids_set
        logger.info(f"Whitelist middleware initialized. Allowed IDs: {self.allowed_ids}")

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Get user from event
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user is None:
            logger.warning("Event without user, blocking")
            return None

        # Check if user is in whitelist
        if user.id not in self.allowed_ids:
            logger.warning(f"Unauthorized access attempt from user {user.id} (@{user.username})")

            # Send rejection message only for Message events
            if isinstance(event, Message):
                await event.answer(
                    "⛔ Доступ запрещён.\n"
                    "Этот бот доступен только для администраторов."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Доступ запрещён", show_alert=True)

            return None

        # User is authorized, proceed
        return await handler(event, data)
