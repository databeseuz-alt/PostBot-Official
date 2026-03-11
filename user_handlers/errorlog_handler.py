import traceback
import logging
from aiogram import Router, types
from aiogram.exceptions import TelegramAPIError

from aiohttp.client_exceptions import (
    ClientProxyConnectionError,
    ClientConnectorError,
    ClientHttpProxyError
)

from xdata_handlers.database import log_user_error

# Logging sozlamalari
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

error_router = Router()

@error_router.errors()
async def error_handler(exception: types.ErrorEvent):
    """
    Barcha kutilmagan xatoliklarni ushlab oladi, log yozadi va bazaga saqlaydi.
    Proksi bilan bog'liq xatoliklarni e'tiborsiz qoldiradi.
    """
    # Proxy bilan bog'liq xatoliklarni WARNING sifatida loglash
    if isinstance(exception.exception, (ClientProxyConnectionError, ClientConnectorError, ClientHttpProxyError)):
        logger.warning(f"[PROXY ERROR] Proxy xatosi - e'tiborsiz qoldirildi: {exception.exception}")
        return True

    user_id = None
    if exception.update.message and exception.update.message.from_user:
        user_id = exception.update.message.from_user.id
    elif exception.update.callback_query and exception.update.callback_query.from_user:
        user_id = exception.update.callback_query.from_user.id
    elif exception.update.inline_query and exception.update.inline_query.from_user:
        user_id = exception.update.inline_query.from_user.id

    # Asosiy xatolikni ERROR sifatida loglash
    error_trace = traceback.format_exc()
    error_message = f"Exception: {exception.exception}\n\nTraceback:\n{error_trace}"
    
    # Serverni loglarida ko'rsatish
    logger.error(f"[XATOLIK] Foydalanuvchi: {user_id} | Xatolik: {exception.exception}")
    logger.debug(f"[XATOLIK DETAL] Traceback:\n{error_trace}")

    try:
        await log_user_error(user_id=user_id, error_text=error_message[:4000])
        logger.info(f"[DB SAQLANDI] Foydalanuvchi {user_id} uchun xatolik bazaga saqlandi")
    except Exception as e:
        logger.error(f"[DB XATOLIK] Xatolikni bazaga saqlashda xato: {e}")

    # Telegram API xatoliklarni WARNING sifatida loglash
    if isinstance(exception.exception, TelegramAPIError):
        logger.warning(f"[TELEGRAM API ERROR] {exception.exception}")
        return False

    logger.info("[XATOLIK QAYTA ISHLANDI] Xatolik muvaffaqiyatli qayta ishlandi")
    return True
