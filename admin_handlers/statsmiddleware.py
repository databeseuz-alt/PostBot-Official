from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from xdata_handlers import database

class UserActivityMiddleware(BaseMiddleware):
    """
    Bu middleware har bir kiruvchi update'dan foydalanuvchi faolligini
    ushlab qoladi va ma'lumotlar bazasiga yozib boradi.
    Shuningdek, foydalanuvchining username va nickname'ni ham yangilab turadi.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User | None = data.get('event_from_user')

        if user:
            # Foydalanuvchi username yoki first_name bo'lsa, uni nickname sifatida ishlatamiz
            nickname = user.username or user.first_name
            await database.record_user_activity(user_id=user.id, username=user.username, nickname=nickname)

        return await handler(event, data)
