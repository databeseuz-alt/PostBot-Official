from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware

from aiogram.types import TelegramObject, Message

import logging

logger = logging.getLogger(__name__)

from xdata_handlers.database import add_or_update_user
from xdata_handlers import config

class StatsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get('event_from_user')
        chat = data.get('event_chat')

        if user and user.is_bot:
            if isinstance(event, Message):
                await event.answer("🤖 Botlar botdan foydalanishi mumkin emas!")
            return

        if not user or not chat or chat.type != 'private':
            return await handler(event, data)

        # Adminlarni statistikadan chetlashtirish
        if config.ADMIN_IDS and user.id in config.ADMIN_IDS:
            return await handler(event, data)
            
        await add_or_update_user(user_id=user.id, nickname=user.full_name, username=user.username)

        return await handler(event, data)
