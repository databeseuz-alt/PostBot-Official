#--- START OF FILE errorlog_handler.py ---
import logging
import traceback
from aiogram import Router, types
from aiogram.exceptions import TelegramAPIError

# Proksi xatoliklarini aniqlash uchun importlar
from aiohttp.client_exceptions import (
    ClientProxyConnectionError,
    ClientConnectorError,
    ClientHttpProxyError
)

from xdata_handlers.database import log_user_error

error_router = Router()

@error_router.errors()
async def error_handler(exception: types.ErrorEvent):
    """
    Barcha kutilmagan xatoliklarni ushlab oladi, log yozadi va bazaga saqlaydi.
    Proksi bilan bog'liq xatoliklarni e'tiborsiz qoldiradi.
    """
    # Proksi yoki tarmoq bilan bog'liq xatoliklarni tekshiramiz
    if isinstance(exception.exception, (ClientProxyConnectionError, ClientConnectorError, ClientHttpProxyError)):
        logging.warning("Proksi yoki tarmoq xatoligi yuz berdi, logga yozilmaydi: %s", exception.exception)
        # Xatolikni qayta ishlangan deb belgilaymiz va keyingi bosqichga o'tkazmaymiz
        return True

    # Boshqa barcha xatoliklar uchun to'liq log yozamiz
    logging.error("Dispatcherda kutilmagan xatolik yuz berdi: %s", exception.exception, exc_info=True)

    # Xatolik matnini tayyorlaymiz
    error_trace = traceback.format_exc()
    error_message = f"Exception: {exception.exception}\n\nTraceback:\n{error_trace}"

    # Foydalanuvchi ID sini olishga harakat qilamiz
    user_id = None
    if exception.update.message and exception.update.message.from_user:
        user_id = exception.update.message.from_user.id
    elif exception.update.callback_query and exception.update.callback_query.from_user:
        user_id = exception.update.callback_query.from_user.id
    elif exception.update.inline_query and exception.update.inline_query.from_user:
        user_id = exception.update.inline_query.from_user.id

    # Xatolikni bazaga yozamiz
    try:
        # Matn uzunligini cheklaymiz, chunki bazadagi ustun chegaralangan bo'lishi mumkin
        await log_user_error(user_id=user_id, error_text=error_message[:4000])
    except Exception as db_error:
        logging.error(f"Xatolikni bazaga yozishda xatolik yuz berdi: {db_error}")

    # Agar Telegram API bilan bog'liq xato bo'lsa, bu odatda botning o'zi bilan bog'liq emas
    # (masalan, foydalanuvchi botni bloklagan). Bunday xatoliklarni qayta ishlashni
    # aiogramning o'ziga qo'yib beramiz.
    if isinstance(exception.exception, TelegramAPIError):
        return False

    # Boshqa barcha xatoliklar uchun True qaytaramiz (qayta ishlangan deb belgilaymiz)
    return True
#--- END OF FILE errorlog_handler.py ---
