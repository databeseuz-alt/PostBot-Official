from aiogram import F, Router, types
from aiogram.filters import Filter
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

from xdata_handlers.database import get_connection, release_connection, get_bot_stats
from xdata_handlers import config
from admin_handlers.xinline_keyboard import get_statistics_keyboard
from admin_handlers.admin_handler import IsAdmin

statistics_router = Router()


def get_tashkent_datetime(utc_dt: datetime) -> datetime:
    """UTC vaqtni Toshkent vaqtiga (UTC+5) o'giradi."""
    if utc_dt is None:
        return None
    tashkent_offset = timedelta(hours=5)
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    tashkent_dt = utc_dt.astimezone(timezone(tashkent_offset))
    return tashkent_dt


def format_tashkent_datetime(dt: datetime) -> str:
    """Datetimeni DD.MM.YYYY HH:MM formatida qaytaradi (Toshkent vaqti)."""
    if dt is None:
        return "00.00.0000 00:00"
    # Agar dt date bo'lsa (vaqt yo'q), datetime ga o'giramiz
    if isinstance(dt, datetime):
        # UTC+5 vaqtga o'girish
        tashkent_dt = dt.astimezone(timezone(timedelta(hours=5)))
        return tashkent_dt.strftime("%d.%m.%Y %H:%M")
    # Agar faqat sana bo'lsa
    return dt.strftime("%d.%m.%Y")


async def get_total_users_count() -> tuple[int, datetime]:
    """Jami foydalanuvchilar sonini qaytaradi."""
    import asyncio
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Adminlarni chiqarib tashlaymiz
            admin_ids = config.ADMIN_IDS
            if admin_ids:
                admin_ids_str = ','.join('%s' for _ in admin_ids)
                cursor.execute(f"SELECT COUNT(*) FROM users WHERE user_id NOT IN ({admin_ids_str})", admin_ids)
            else:
                cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            return total_users, None
        except Exception as e:
            logger.error(f"Error getting total users count: {e}")
            return 0, None
        finally:
            if conn: release_connection(conn)
            
    return await asyncio.to_thread(_sync)


@statistics_router.callback_query(F.data == "admin:statistics_main", IsAdmin())
async def show_main_statistics(callback: types.CallbackQuery):
    """Asosiy statistikani ko'rsatadi."""
    from admin_handlers.xinline_keyboard import get_back_to_main_orqaga_keyboard
    
    try:
        stats = await get_bot_stats()
        
        # Hozirgi vaqtni formatlash
        current_time_str = "00.00.0000 00:00"
        if stats['current_time']:
            current_time_str = format_tashkent_datetime(stats['current_time'])
        
        # Formatlash (0 bilan, 00 emas)
        total_users = str(stats['total_users'])
        new_today = str(stats['new_today'])
        new_week = str(stats['new_week'])
        new_month = str(stats['new_month'])
        posts_today = str(stats.get('posts_today', 0))
        posts_week = str(stats.get('posts_week', 0))
        posts_month = str(stats.get('posts_month', 0))
        
        stats_text = (
            f"<b>📋 BOT STATISTIKASI :</b>\n\n"
            f"<b>👥 Jami Foydalanuvchilar: {total_users} ta ( {current_time_str} )</b>\n\n"
            f"<b>📈 Yangi a'zolar :</b>\n"
            f" <b>- bugun :</b> {new_today} ta\n"
            f" <b>- shu hafta :</b> {new_week} ta\n"
            f" <b>- shu oy :</b> {new_month} ta\n\n"
            f"<b>📝 Yangi postlar :</b>\n"
            f" <b>- bugun :</b> {posts_today} ta\n"
            f" <b>- shu hafta :</b> {posts_week} ta\n"
            f" <b>- shu oy :</b> {posts_month} ta"
        )
        
        await callback.message.edit_text(
            text=stats_text,
            reply_markup=get_back_to_main_orqaga_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Xato statistikani ko'rsatishda: {e}")
        await callback.message.edit_text(
            text="<b>📋 BOT STATISTIKASI :</b>\n\n"
            f"<b>👥 Jami Foydalanuvchilar: 0 ta (00.00.0000 00:00)</b>\n\n"
            f"<b>📈 Yangi a'zolar :</b>\n"
            f" <b>- bugun :</b> 0 ta\n"
            f" <b>- shu hafta :</b> 0 ta\n"
            f" <b>- shu oy :</b> 0 ta\n\n"
            f"<b>📝 Yaratilgan postlar :</b>\n"
            f" <b>- bugun :</b> 0 ta\n"
            f" <b>- shu hafta :</b> 0 ta\n"
            f" <b>- shu oy :</b> 0 ta",
            reply_markup=get_back_to_main_orqaga_keyboard()
        )
    
    await callback.answer()


@statistics_router.callback_query(F.data == "admin:statistics_menu", IsAdmin())
async def statistics_menu_handler(callback: types.CallbackQuery):
    """Statistika bo'limi menyusi."""
    await callback.message.edit_text(
        text="📊 Statistika bo'limi. Kerakli bo'limni tanlang:",
        reply_markup=get_statistics_keyboard()
    )
    await callback.answer()
