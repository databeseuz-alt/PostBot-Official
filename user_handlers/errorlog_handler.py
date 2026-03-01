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

logger = logging.getLogger(__name__)
error_router = Router()

@error_router.errors()
async def error_handler(exception: types.ErrorEvent):
    """
    Barcha kutilmagan xatoliklarni ushlab oladi, log yozadi va bazaga saqlaydi.
    Proksi bilan bog'liq xatoliklarni e'tiborsiz qoldiradi.
    """
    if isinstance(exception.exception, (ClientProxyConnectionError, ClientConnectorError, ClientHttpProxyError)):
        return True

    error_trace = traceback.format_exc()
    error_message = f"Exception: {exception.exception}\n\nTraceback:\n{error_trace}"

    user_id = None
    if exception.update.message and exception.update.message.from_user:
        user_id = exception.update.message.from_user.id
    elif exception.update.callback_query and exception.update.callback_query.from_user:
        user_id = exception.update.callback_query.from_user.id
    elif exception.update.inline_query and exception.update.inline_query.from_user:
        user_id = exception.update.inline_query.from_user.id

    # Logging xatoni log faylga yozish
    logger.error(f"Xatolik yuz berdi | User ID: {user_id} | Exception: {exception.exception}", exc_info=True)

    try:
        await log_user_error(user_id=user_id, error_text=error_message[:4000])
    except Exception:
        pass

    if isinstance(exception.exception, TelegramAPIError):
        return False

    return True
