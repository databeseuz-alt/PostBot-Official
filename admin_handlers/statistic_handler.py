#--- START OF FILE statistic_handler.py ---
import io
from datetime import datetime, timedelta, timezone
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from aiogram import F, Router, types, Bot
from aiogram.types import BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

from admin_handlers.admin_handler import IsAdmin
from xdata_handlers import config
from xdata_handlers.database import (
    get_detailed_user_stats, get_new_users_stats_extended,
    get_posts_stats, get_language_distribution, get_daily_stats_for_graph,
    get_active_users_by_period, get_total_errors_count, get_activity_heatmap_for_last_24h,
    get_now # YANGI IMPORT
)
from admin_handlers.xinline_keyboard import get_stats_menu_keyboard

statistic_router = Router()

#==================================================
# --- Y O R D A M CH I   F U N K S I Y A L A R   V A   K L A V I A T U R A L A R ---
#==================================================

def _get_navigation_keyboard():
    """Statistika bo'limi uchun navigatsiya klaviaturasini yaratadi."""
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Asosiy panel", callback_data="admin:back_to_main_menu")
    builder.button(text="◀️ Ortga", callback_data="admin:stats_menu")
    builder.adjust(2)
    return builder.as_markup()


#==================================================
# --- S T A T I S T I K A   B O' L I M I   A S O S I Y   M E N Y U S I ---
#==================================================

@statistic_router.callback_query(F.data == "admin:stats_menu", IsAdmin())
async def admin_stats_menu_handler(callback: types.CallbackQuery):
    """Statistika bo'limining asosiy menyusini ko'rsatadi."""
    text = "📊 Statistika bo'limi. Kerakli ma'lumot turini tanlang:"
    keyboard = get_stats_menu_keyboard()

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)

    await callback.answer()


#==================================================
# --- U M U M I Y   S T A T I S T I K A N I   K O' R S A T I SH ---
#==================================================

async def _format_stats_text(
    detailed_stats: dict,
    new_user_stats: dict,
    posts_stats: dict,
    lang_dist: dict,
    active_users: dict,
    total_errors: int,
    heatmap: str,
    current_time: datetime
) -> str:
    """Statistika ma'lumotlaridan formatlangan matn yaratadi."""
    # Vaqtni to'g'ridan-to'g'ri formatlaymiz
    time_str = current_time.strftime('%d.%m.%Y %H:%M')
    status_line = f" <b>( {time_str} )</b>"

    lang_block_parts = ["<b>🏴 Tillar boʻyicha taqsimot:</b>"]

    lang_map = {
        'uzl': 'UZ 🇺🇿', 'uzk': 'ЎЗ 🇺🇿', 'ru': 'RU 🇷🇺', 'en': 'EN 🇬🇧',
        'kz': 'KZ 🇰🇿', 'az': 'AZ 🇦🇿', 'tr': 'TR 🇹🇷', 'kg': 'KG 🇰🇬',
        None: 'Noma\'lum'
    }

    active_langs = {lang: data for lang, data in lang_dist.items() if data.get('count', 0) > 0}

    if active_langs:
        for lang_code, data in active_langs.items():
            lang_name = lang_map.get(lang_code, lang_code)
            percentage = int(data['percentage'])
            lang_block_parts.append(f"  - {lang_name} : {data['count']} ta ({percentage}%)")
    else:
        lang_block_parts.append("Tillar bo'yicha ma'lumot yo'q.")

    lang_text = "\n".join(lang_block_parts)

    return (
        f"<b>📊 Bot Statistikasi</b>\n\n"
        f"<b>👥 Jami foydalanuvchilar:</b> {detailed_stats.get('total', 0)} ta{status_line}\n\n"
        f"<b>📈 Yangi a'zolar:</b>\n"
        f"  - Bugun: {new_user_stats.get('daily', 0)} ta\n"
        f"  - Shu hafta: {new_user_stats.get('weekly', 0)} ta\n"
        f"  - Shu oy: {new_user_stats.get('monthly', 0)} ta\n\n"
        f"<b>🏃‍♂️ Faol a'zolar:</b>\n"
        f"  - bugun: {active_users.get('daily', 0)} ta\n"
        f"  - shu hafta: {active_users.get('weekly', 0)} ta\n"
        f"  - shu Oy: {active_users.get('monthly', 0)} ta\n\n"
        f"{lang_text}\n\n"
        f"<b>✍️ Yaratilgan postlar:</b>\n"
        f"  - Jami: {posts_stats.get('total', 0)} ta\n"
        f"  - Bugun: {posts_stats.get('daily', 0)} ta\n"
        f"  - Shu hafta: {posts_stats.get('weekly', 0)} ta\n"
        f"  - Shu oy: {posts_stats.get('monthly', 0)} ta\n\n"
        f"<b>🕒 Bugungi eng faol vaqt:</b>\n"
        f"  - {heatmap}\n\n"
        f"<b>⚙️ Tizim holati:</b>\n"
        f"  - Qayd etilgan xatolar: {total_errors} ta"
    )


@statistic_router.callback_query(F.data == "admin:stats_show_general", IsAdmin())
async def admin_general_stats_handler(callback: types.CallbackQuery, bot: Bot):
    """
    Ma'lumotlar bazasidan joriy statistikani oladi va foydalanuvchiga yuboradi.
    """
    await callback.answer("⏳ Ma'lumotlar yuklanmoqda...", show_alert=False)

    detailed_stats = await get_detailed_user_stats(admin_ids=config.ADMIN_IDS)
    new_user_stats = await get_new_users_stats_extended(admin_ids=config.ADMIN_IDS)
    posts_stats = await get_posts_stats(admin_ids=config.ADMIN_IDS)
    lang_dist = await get_language_distribution(admin_ids=config.ADMIN_IDS)
    active_users = await get_active_users_by_period(admin_ids=config.ADMIN_IDS)
    total_errors = await get_total_errors_count()
    heatmap = await get_activity_heatmap_for_last_24h(admin_ids=config.ADMIN_IDS)

    # Hozirgi Toshkent vaqtini olamiz
    current_tashkent_time = get_now()

    text = await _format_stats_text(
        detailed_stats, new_user_stats, posts_stats, lang_dist,
        active_users, total_errors, heatmap, current_tashkent_time
    )

    keyboard = _get_navigation_keyboard()

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)


#==================================================
# --- G R A F I K A N I   Y A R A T I SH   V A   Y U B O R I SH ---
#==================================================

async def create_stats_graph(daily_stats: list, title: str) -> io.BytesIO:
    """Matplotlib yordamida statistika grafigini yaratadi."""
    current_year = get_now().year
    dates_str = [item['date'] for item in daily_stats]
    dates = [datetime.strptime(f"{d}.{current_year}", "%d.%m.%Y") for d in dates_str]

    new_users = [item['new_users'] for item in daily_stats]
    new_posts = [item['new_posts'] for item in daily_stats]

    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(15, 8))

    ax.plot(dates, new_users, marker='o', linestyle='-', label='Yangi foydalanuvchilar', color='#4CAF50', markersize=5)
    ax.plot(dates, new_posts, marker='s', linestyle='--', label='Yangi postlar', color='#2196F3', markersize=5)

    ax.set_title(title, fontsize=16, color='white', pad=20)
    ax.set_ylabel('Soni', color='white', fontsize=12)
    ax.tick_params(axis='x', rotation=45, colors='white', labelsize=10)
    ax.tick_params(axis='y', colors='white', labelsize=10)
    ax.legend(facecolor='#2c2c2c', edgecolor='white', labelcolor='white')
    ax.grid(True, linestyle='--', alpha=0.3)

    # X o'qini har bir kunni ko'rsatadigan qilib sozlash
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    fig.autofmt_xdate(ha='right')

    # Y o'qini butun sonlarda ko'rsatish
    max_val = max(max(new_users), max(new_posts)) if new_users or new_posts else 1
    step = max(1, int(np.ceil(max_val / 10)))
    ax.yaxis.set_major_locator(plt.MultipleLocator(step))

    # Y o'qining pastki chegarasiga kichik bo'sh joy qo'shish (80% tushirish)
    ax.set_ylim(bottom=-0.02 * max(1, max_val))

    # X o'qining chegaralariga kichik bo'sh joy qo'shish
    ax.set_xlim(dates[0] - timedelta(days=0.5), dates[-1] + timedelta(days=0.5))

    fig.tight_layout(pad=3.0)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close(fig)
    return buf

@statistic_router.callback_query(F.data == "admin:stats_show_graph", IsAdmin())
async def admin_graph_stats_handler(callback: types.CallbackQuery):
    await callback.answer("📈 Grafika yaratilmoqda...", show_alert=False)

    daily_stats = await get_daily_stats_for_graph(days=30)
    if not daily_stats or len(daily_stats) < 2:
        await callback.message.answer("Grafika yaratish uchun ma'lumotlar yetarli emas.")
        return

    graph_buffer = await create_stats_graph(daily_stats, "Oxirgi 30 kunlik statistika")
    photo_file = BufferedInputFile(graph_buffer.read(), filename="stats_graph.png")

    keyboard = _get_navigation_keyboard()

    try:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=photo_file,
            caption="📊 oxirgi 30 kunlik faollik grafigi.",
            reply_markup=keyboard
        )
    except TelegramBadRequest:
        await callback.message.answer_photo(
            photo=photo_file,
            caption="📊 oxirgi 30 kunlik faollik grafigi.",
            reply_markup=keyboard
        )
#--- END OF FILE statistic_handler.py ---
