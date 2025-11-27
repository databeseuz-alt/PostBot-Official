#--- START OF FILE statsmiddleware.py ---
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from xdata_handlers import database

class UserActivityMiddleware(BaseMiddleware):
    """
    Bu middleware har bir kiruvchi update'dan foydalanuvchi faolligini
    ushlab qoladi va ma'lumotlar bazasiga yozib boradi.
    Shuningdek, foydalanuvchining usernamesini ham yangilab turadi.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # data lug'atidan 'event_from_user' kalitini topishga harakat qilamiz.
        # Bu kalit aiogram tomonidan deyarli barcha foydalanuvchi bilan bog'liq
        # event'larga avtomatik qo'shiladi.
        user: User | None = data.get('event_from_user')

        # Agar user obyekti mavjud bo'lsa (ya'ni, bu foydalanuvchidan kelgan so'rov bo'lsa)
        if user:
            # Ma'lumotlar bazasidagi funksiyani chaqirib, faollikni qayd etamiz
            # va usernamesini yangilaymiz.
            await database.record_user_activity(user_id=user.id, username=user.username)

        # Middleware o'z ishini tugatgach, event'ni keyingi handler'larga o'tkazib yuboradi.
        return await handler(event, data)
#--- END OF FILE statsmiddleware.py ---
