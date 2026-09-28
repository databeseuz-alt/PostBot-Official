from aiogram import F, Router, types
from aiogram.filters import Filter
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

from xdata_handlers.database import get_total_users_count, get_bot_stats
from admin_handlers.admin_handler import IsAdmin
from admin_handlers.xinline_keyboard import get_statistics_keyboard

statistics_router = Router()

def format_tashkent_datetime(dt: datetime) -> str:
    """Datetimeni DD.MM.YYYY HH:MM formatida qaytaradi (Toshkent vaqti)."""
    if dt is None:
        return "00.00.0000 00:00"
    if isinstance(dt, datetime):
        tashkent_dt = dt.astimezone(timezone(timedelta(hours=5)))
        return tashkent_dt.strftime("%d.%m.%Y %H:%M")
    return str(dt)

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
