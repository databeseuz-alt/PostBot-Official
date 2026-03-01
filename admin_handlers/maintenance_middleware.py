import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware, types
from aiogram.types import TelegramObject, Update
from xdata_handlers.database import is_maintenance_mode, get_user_language
from xdata_handlers.translator import get_text
from xdata_handlers import config

logger = logging.getLogger(__name__)

class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get('event_from_user')
        if not user or user.is_bot:
            return await handler(event, data)

        # Admins are exempt
        if user.id in config.ADMIN_IDS:
            return await handler(event, data)

        if await is_maintenance_mode():
            lang = await get_user_language(user.id)
            warning_text = get_text('maintenance_warning_msg', lang)
            
            # We check the event type to respond appropriately
            # Some events might not be Update (though usually they are in DP middleware)
            if isinstance(event, Update):
                if event.callback_query:
                    await event.callback_query.answer(warning_text, show_alert=True)
                    return
                elif event.message:
                    await event.message.answer(warning_text)
                    return
            
            # fallback if it's not a standard update but we have a way to respond
            # This part is just a safety measure
            return

        return await handler(event, data)
