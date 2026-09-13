"""
Markazlashgan xatolik loglash moduli.

Barcha handlerlardagi except bloklari shu modul orqali xatoliklarni:
  1. Logger'ga to'liq traceback bilan yozadi
  2. Ixtiyoriy holda bazaga saqlaydi (log_user_error)
  3. Ixtiyoriy holda adminlarga xabar yuboradi

Foydalanish:
    from xdata_handlers.error_logger import log_bot_error

    try:
        ...
    except Exception as e:
        await log_bot_error("send_scheduled_post", e, user_id=user_id, notify_admin=True, bot=bot)
"""

import asyncio
import logging
import traceback

logger = logging.getLogger(__name__)


async def log_bot_error(
    context: str,
    exc: Exception | None = None,
    user_id: int | None = None,
    save_to_db: bool = False,
    notify_admin: bool = False,
    bot=None,
) -> None:
    """Xatolikni loglaydi, ixtiyoriy holda bazaga yozadi va adminlarga xabar beradi.

    Args:
        context: Xatolik qayerda yuz bergani (masalan "send_scheduled_post").
        exc: Ushlangan exception (bo'lmasa faqat context yoziladi).
        user_id: Foydalanuvchi ID (bazaga yozish va log uchun).
        save_to_db: Bazaga log_user_error orqali yozish.
        notify_admin: ADMIN_IDS ga qisqa xabar yuborish (bot kerak).
        bot: Adminlarga xabar yuborish uchun Bot obyekti.
    """
    error_text = f"{context}: {exc}" if exc else context
    log_line = f"[XATO] {error_text}"
    if user_id:
        log_line += f" | user_id={user_id}"
    if exc:
        tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
        logger.error(log_line + "\n" + "".join(tb))
    else:
        logger.error(log_line)

    if save_to_db and user_id:
        try:
            from xdata_handlers.database import log_user_error
            await log_user_error(user_id=user_id, error_text=error_text[:4000])
        except Exception as db_exc:
            logger.warning(f"[XATO] Xatolikni bazaga yozib bo'lmadi: {db_exc}")

    if notify_admin and bot:
        try:
            from xdata_handlers import config
            for admin_id in config.ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"🛑 <b>Botda xatolik!</b>\n\n"
                        f"📍 Joy: <code>{context}</code>\n"
                        f"❌ Xatolik: <code>{str(exc)[:500] if exc else 'noma\'lum'}</code>\n"
                        f"👤 Foydalanuvchi: <code>{user_id or '—'}</code>",
                        parse_mode="HTML",
                    )
                except Exception as send_exc:
                    logger.warning(f"[XATO] Admin ({admin_id}) ga xabar yuborib bo'lmadi: {send_exc}")
        except Exception as admin_exc:
            logger.warning(f"[XATO] Adminlarga xabar yuborishda xatolik: {admin_exc}")


def log_bot_error_sync(context: str, exc: Exception | None = None, user_id: int | None = None) -> None:
    """Sync kontekstlar (DB thread'lari, init funksiyalar) uchun soddalashtirilgan loglash."""
    error_text = f"{context}: {exc}" if exc else context
    prefix = f" | user_id={user_id}" if user_id else ""
    logger.error(f"[XATO] {error_text}{prefix}\n{traceback.format_exc() if exc else ''}")


def fire_and_forget(coro) -> None:
    """Running loop bo'lmasa ham xavfsiz tarzda task yaratadi (loglash uchun)."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        pass
