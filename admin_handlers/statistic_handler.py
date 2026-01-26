#--- START OF FILE admin_handlers/statistic_handler.py ---
from aiogram import F, Router, types
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramBadRequest

from admin_handlers.admin_handler import IsAdmin
from xdata_handlers import config
from xdata_handlers.database import (
    get_detailed_user_stats, get_new_users_stats_extended,
    get_posts_stats, get_language_distribution, get_daily_stats_for_graph,
    get_active_users_by_period, get_total_errors_count, get_activity_heatmap_for_last_24h,
    get_weekly_activity, get_daily_hours_activity, get_post_formats, get_button_stats,
    get_now
)
from admin_handlers.xinline_keyboard import (
    get_stats_menu_keyboard, get_graphics_menu_keyboard, 
    get_users_stats_keyboard, get_posts_stats_keyboard, 
    get_back_navigation_keyboard
)
from admin_handlers.stat_drawer import StatDrawer

statistic_router = Router()
drawer = StatDrawer()

#==================================================
# --- S T A T I S T I K A   B O' L I M I   A S O S I Y   M E N Y U S I ---
#==================================================

@statistic_router.callback_query(F.data == "admin:stats_menu", IsAdmin())
async def admin_stats_menu_handler(callback: types.CallbackQuery):
    """Statistika bo'limining asosiy menyusini (2-1) ko'rsatadi."""
    text = "📊 <b>Statistika bo'limi</b>\n\nKerakli bo'limni tanlang:"
    keyboard = get_stats_menu_keyboard()

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)
    except Exception:
        # Rasm bo'lsa edit qilib bo'lmaydi, o'chirib yozish kerak
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)

    await callback.answer()

#==================================================
# --- 1. U M U M I Y   M A T N L I   S T A T I S T I K A ---
#==================================================

async def _format_stats_text(
    detailed_stats: dict,
    new_user_stats: dict,
    posts_stats: dict,
    lang_dist: dict,
    active_users: dict,
    total_errors: int,
    current_time
) -> str:
    """Statistika ma'lumotlaridan formatlangan matn yaratadi."""
    time_str = current_time.strftime('%d.%m.%Y %H:%M')
    status_line = f" <b>( {time_str} )</b>"

    lang_block_parts = ["<b>🏴 Tillar boʻyicha taqsimot:</b>"]
    lang_map = {
        'uzl': 'UZ 🇺🇿', 'uzk': 'ЎЗ 🇺🇿', 'ru': 'RU 🇷🇺', 'en': 'EN 🇬🇧',
        'kz': 'KZ 🇰🇿', 'az': 'AZ 🇦🇿', 'tr': 'TR 🇹🇷', 'kg': 'KG 🇰🇬',
        'tj': 'TJ 🇹🇯', 'tk': 'TK 🇹🇲',
        None: 'Noma\'lum'
    }

    # lang_dist endi oddiy lug'at {lang: count}
    total_lang_users = sum(lang_dist.values())
    
    if lang_dist:
        for lang_code, count in lang_dist.items():
            lang_name = lang_map.get(lang_code, lang_code)
            percentage = int((count / total_lang_users) * 100) if total_lang_users > 0 else 0
            lang_block_parts.append(f"  - {lang_name} : {count} ta ({percentage}%)")
    else:
        lang_block_parts.append("Tillar bo'yicha ma'lumot yo'q.")

    lang_text = "\n".join(lang_block_parts)

    return (
        f"<b>📊 Bot Statistikasi</b>\n\n"
        f"<b>👥 Jami foydalanuvchilar:</b> {detailed_stats.get('total_users', 0)} ta{status_line}\n\n"
        f"<b>📈 Yangi a'zolar:</b>\n"
        f"  - Bugun: {new_user_stats.get('daily', 0)} ta\n"
        f"  - Shu hafta: {new_user_stats.get('weekly', 0)} ta\n"
        f"  - Shu oy: {new_user_stats.get('monthly', 0)} ta\n\n"
        f"<b>🏃‍♂️ Faol a'zolar:</b>\n"
        f"  - Bugun: {active_users.get('daily', 0)} ta\n"
        f"  - Shu hafta: {active_users.get('weekly', 0)} ta\n"
        f"  - Shu oy: {active_users.get('monthly', 0)} ta\n\n"
        f"{lang_text}\n\n"
        f"<b>✍️ Yaratilgan postlar:</b>\n"
        f"  - Jami: {posts_stats.get('total', 0)} ta\n"
        f"  - Bugun: {posts_stats.get('daily', 0)} ta\n"
        f"  - Shu hafta: {posts_stats.get('weekly', 0)} ta\n"
        f"  - Shu oy: {posts_stats.get('monthly', 0)} ta\n\n"
        f"<b>⚙️ Tizim holati:</b>\n"
        f"  - Qayd etilgan xatolar: {total_errors} ta"
    )

@statistic_router.callback_query(F.data == "admin:stats:general_text", IsAdmin())
async def show_general_text_stats(callback: types.CallbackQuery):
    await callback.answer("⏳ Ma'lumotlar yuklanmoqda...")

    # Yangi database funksiyalaridan foydalanamiz
    # Lekin eski formatga mos kelishi uchun ularni chaqiramiz
    # get_detailed_user_stats yangi formatda, lekin bizga keragi ichida bor
    detailed_stats = await get_detailed_user_stats(config.ADMIN_IDS)
    
    # Qolganlari uchun eski funksiyalarni database.py da qoldirdik yoki yangilarini moslaymiz
    new_user_stats = await get_new_users_stats_extended(config.ADMIN_IDS)
    posts_stats = await get_posts_stats(config.ADMIN_IDS)
    lang_dist = await get_language_distribution(config.ADMIN_IDS)
    active_users = await get_active_users_by_period(config.ADMIN_IDS)
    total_errors = await get_total_errors_count()
    
    current_time = get_now()

    text = await _format_stats_text(
        detailed_stats, new_user_stats, posts_stats, lang_dist,
        active_users, total_errors, current_time
    )

    # Ortga tugmasi asosiy statistika menyusiga qaytaradi
    keyboard = get_back_navigation_keyboard("admin:stats_menu")

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)

#==================================================
# --- 2. G R A F I K A   B O' L I M I (MENYUSI) ---
#==================================================

@statistic_router.callback_query(F.data == "admin:stats:graphics_menu", IsAdmin())
async def show_graphics_menu(callback: types.CallbackQuery):
    text = "📈 <b>Grafika bo'limi</b>\n\nQanday turdagi grafikani ko'rmoqchisiz?"
    keyboard = get_graphics_menu_keyboard()
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

#==================================================
# --- 3. D A S H B O A R D ---
#==================================================

@statistic_router.callback_query(F.data == "admin:stats:dashboard", IsAdmin())
async def show_dashboard_handler(callback: types.CallbackQuery):
    await callback.answer("📊 Dashboard yuklanmoqda...")
    stats = await get_detailed_user_stats(config.ADMIN_IDS)
    image_buffer = drawer.draw_dashboard(stats)
    photo_file = BufferedInputFile(image_buffer.read(), filename="dashboard.png")
    
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_file,
        caption="📊 <b>Asosiy Dashboard</b>",
        reply_markup=get_back_navigation_keyboard("admin:stats:graphics_menu")
    )

#==================================================
# --- 4. A ' Z O L A R   B O' L I M I ---
#==================================================

@statistic_router.callback_query(F.data == "admin:stats:users_menu", IsAdmin())
async def show_users_menu(callback: types.CallbackQuery):
    text = "👥 <b>A'zolar statistikasi</b>\n\nQaysi davr yoki turni ko'rmoqchisiz?"
    keyboard = get_users_stats_keyboard()
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

@statistic_router.callback_query(F.data == "admin:stats:users:monthly", IsAdmin())
async def show_users_monthly(callback: types.CallbackQuery):
    await callback.answer("Grafik chizilmoqda...")
    dates, users, _ = await get_daily_stats_for_graph(30)
    image_buffer = drawer.draw_line_chart("👥 Yangi a'zolar (30 kun)", dates, users)
    photo_file = BufferedInputFile(image_buffer.read(), filename="users_monthly.png")
    
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_file,
        caption="📈 <b>30 kunlik a'zolar o'sishi</b>",
        reply_markup=get_back_navigation_keyboard("admin:stats:users_menu")
    )

@statistic_router.callback_query(F.data == "admin:stats:users:weekly", IsAdmin())
async def show_users_weekly(callback: types.CallbackQuery):
    await callback.answer("Grafik chizilmoqda...")
    labels, values = await get_weekly_activity(config.ADMIN_IDS)
    image_buffer = drawer.draw_bar_chart("📅 Haftalik faollik", labels, values)
    photo_file = BufferedInputFile(image_buffer.read(), filename="users_weekly.png")
    
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_file,
        caption="📅 <b>Hafta kunlari bo'yicha faollik</b>",
        reply_markup=get_back_navigation_keyboard("admin:stats:users_menu")
    )

@statistic_router.callback_query(F.data == "admin:stats:users:hourly", IsAdmin())
async def show_users_hourly(callback: types.CallbackQuery):
    await callback.answer("Grafik chizilmoqda...")
    labels, values = await get_daily_hours_activity(config.ADMIN_IDS)
    image_buffer = drawer.draw_bar_chart("🕒 Kunlik faollik soatlari", labels, values)
    photo_file = BufferedInputFile(image_buffer.read(), filename="users_hourly.png")
    
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_file,
        caption="🕒 <b>Soatlar bo'yicha faollik</b>",
        reply_markup=get_back_navigation_keyboard("admin:stats:users_menu")
    )

#==================================================
# --- 5. T I L L A R   B O' L I M I ---
#==================================================

@statistic_router.callback_query(F.data == "admin:stats:langs_menu", IsAdmin())
async def show_langs_stats(callback: types.CallbackQuery):
    await callback.answer("Grafik chizilmoqda...")
    data = await get_language_distribution(config.ADMIN_IDS)
    image_buffer = drawer.draw_pie_chart("🌍 Tillar taqsimoti", data)
    photo_file = BufferedInputFile(image_buffer.read(), filename="langs_pie.png")
    
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_file,
        caption="🌍 <b>Foydalanuvchilar tili</b>",
        reply_markup=get_back_navigation_keyboard("admin:stats:graphics_menu")
    )

#==================================================
# --- 6. P O S T L A R   B O' L I M I ---
#==================================================

@statistic_router.callback_query(F.data == "admin:stats:posts_menu", IsAdmin())
async def show_posts_menu(callback: types.CallbackQuery):
    text = "📝 <b>Postlar statistikasi</b>\n\nQaysi ma'lumotni ko'rmoqchisiz?"
    keyboard = get_posts_stats_keyboard()
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

@statistic_router.callback_query(F.data == "admin:stats:posts:monthly", IsAdmin())
async def show_posts_monthly(callback: types.CallbackQuery):
    await callback.answer("Grafik chizilmoqda...")
    dates, _, posts = await get_daily_stats_for_graph(30)
    image_buffer = drawer.draw_line_chart("📝 Yaratilgan postlar (30 kun)", dates, posts)
    photo_file = BufferedInputFile(image_buffer.read(), filename="posts_monthly.png")
    
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_file,
        caption="📈 <b>30 kunlik postlar statistikasi</b>",
        reply_markup=get_back_navigation_keyboard("admin:stats:posts_menu")
    )

@statistic_router.callback_query(F.data == "admin:stats:posts:formats", IsAdmin())
async def show_posts_formats(callback: types.CallbackQuery):
    await callback.answer("Grafik chizilmoqda...")
    data = await get_post_formats(config.ADMIN_IDS)
    image_buffer = drawer.draw_pie_chart("📄 Post formatlari", data)
    photo_file = BufferedInputFile(image_buffer.read(), filename="posts_formats.png")
    
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_file,
        caption="📄 <b>Post turlari</b>",
        reply_markup=get_back_navigation_keyboard("admin:stats:posts_menu")
    )

@statistic_router.callback_query(F.data == "admin:stats:posts:buttons", IsAdmin())
async def show_posts_buttons(callback: types.CallbackQuery):
    await callback.answer("Grafik chizilmoqda...")
    data = await get_button_stats(config.ADMIN_IDS)
    image_buffer = drawer.draw_bar_chart("🔘 Tugmalar ishlatilishi", list(data.keys()), list(data.values()))
    photo_file = BufferedInputFile(image_buffer.read(), filename="posts_buttons.png")
    
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_file,
        caption="🔘 <b>Postlarda tugmalar soni</b>",
        reply_markup=get_back_navigation_keyboard("admin:stats:posts_menu")
    )
#--- END OF FILE admin_handlers/statistic_handler.py ---
