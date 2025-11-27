#--- START OF FILE xinline_keyboard.py ---
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

# =============================================================================
# --- K L A V I A T U R A   Y A R A T I SH ---
# =============================================================================

# --- ASOSIY ADMIN PANELI UCHUN ---

def get_main_admin_keyboard():
    builder = InlineKeyboardBuilder()
    # YANGILANDI: `callback_data` yangi menyuga yo'naltirildi
    builder.button(text="📊 bot statistika", callback_data="admin:stats_menu")
    builder.button(text="🚫 bloklanganlar", callback_data="admin:blocked_users_menu")
    builder.button(text="📢 Reklama yuborish", callback_data="admin:send_ad_start")
    builder.button(text="📢 Kanalni ulash", callback_data="admin:channel_menu")
    builder.button(text="ℹ️ foydalanuvchi ma'lumotlari bazasi", callback_data="admin:user_data_menu")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

# --- YANGI BO'LIM: STATISTIKA MENYUSI UCHUN ---

def get_stats_menu_keyboard():
    """Statistika bo'limining asosiy menyusini yaratadi."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Umumiy statistika", callback_data="admin:stats_show_general")
    builder.button(text="📈 Grafika", callback_data="admin:stats_show_graph")
    builder.button(text="◀️ Admin paneliga qaytish", callback_data="admin:back_to_main_menu")
    builder.adjust(2, 1)
    return builder.as_markup()

# --- FOYDALANUVCHI MA'LUMOTLARI BO'LIMI UCHUN ---

def get_user_data_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="💾 Ma'lumotlar bazasi", callback_data="admin:export_menu_period")
    builder.button(text="🔎 User qidirish", callback_data="admin:search_user_start")
    builder.button(text="◀️ Admin paneliga qaytish", callback_data="admin:back_to_main_menu")
    builder.adjust(2, 1)
    return builder.as_markup()

def get_export_period_keyboard():
    """Ma'lumotlarni eksport qilish uchun vaqt oralig'ini tanlash klaviaturasi."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Barcha foydalanuvchi ma'lumoti", callback_data="admin:export_type_menu:all")
    builder.button(text="Oylik", callback_data="admin:export_type_menu:monthly")
    builder.button(text="Haftalik", callback_data="admin:export_type_menu:weekly")
    builder.button(text="Kunlik", callback_data="admin:export_type_menu:daily")
    builder.button(text="◀️ Asosiy panel", callback_data="admin:back_to_main_menu")
    builder.button(text="◀️ Ortga", callback_data="admin:user_data_menu")
    builder.adjust(1, 3, 2)
    return builder.as_markup()

def get_export_type_keyboard(period: str):
    """Ma'lumotlarni eksport qilish uchun ma'lumot turini tanlash klaviaturasi."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Barcha foydalanuvchi ro'yxati", callback_data=f"admin:export_do:{period}:full_list")
    builder.button(text="Faqat post yaratganlar", callback_data=f"admin:export_do:{period}:post_creators")
    builder.button(text="Foydalanuvchi sozlamalari", callback_data=f"admin:export_do:{period}:user_settings")
    builder.button(text="◀️ Asosiy panel", callback_data="admin:back_to_main_menu")
    builder.button(text="◀️ Ortga", callback_data="admin:export_menu_period")
    builder.adjust(3, 2)
    return builder.as_markup()

# --- USER QIDIRISH BO'LIMI UCHUN YANGI KLAVIATURALAR ---

def get_user_search_start_keyboard():
    """User qidirishni boshlash uchun navigatsiya klaviaturasi."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Asosiy panel", callback_data="admin:back_to_main_menu"),
        InlineKeyboardButton(text="◀️ Ortga", callback_data="admin:user_data_menu")
    )
    return builder.as_markup()

def get_user_search_result_keyboard(posts: list):
    """User qidiruvi natijasi uchun klaviatura (yaratilgan postlar bilan)."""
    builder = InlineKeyboardBuilder()
    if posts:
        for post_code in posts:
            builder.button(text=f"{post_code}", callback_data=f"admin:review_post:{post_code}")
        builder.adjust(3)

    builder.row(
        InlineKeyboardButton(text="◀️ Asosiy panel", callback_data="admin:back_to_main_menu"),
        InlineKeyboardButton(text="◀️ Ortga", callback_data="admin:user_data_menu")
    )
    return builder.as_markup()

# --- BLOKLASH BO'LIMI UCHUN ---

def get_blocked_users_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Foydalanuvchini bloklash", callback_data="admin:block_user_start")
    builder.button(text="📋 Bloklanganlar ro'yxati", callback_data="admin:show_blocked_list")
    builder.button(text="◀️ Admin paneliga qaytish", callback_data="admin:back_to_main_menu")
    builder.adjust(2, 1)
    return builder.as_markup()

async def get_blocked_list_view_keyboard(admin_ids: list, adjust_size: int = 3):
    from xdata_handlers.database import get_blocked_users_with_info
    blocked_users = await get_blocked_users_with_info(admin_ids=admin_ids)
    builder = InlineKeyboardBuilder()

    if blocked_users:
        for user in blocked_users:
            display_name = user.get('full_name') or f"Noma'lum ({user['user_id']})"
            builder.button(text=f"❌ {display_name}", callback_data=f"admin:unblock_confirm:{user['user_id']}")
        builder.adjust(adjust_size)

    builder.row(
        InlineKeyboardButton(text="◀️ Asosiy panel", callback_data="admin:back_to_main_menu"),
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:blocked_users_menu")
    )
    return builder.as_markup()

def get_unblock_confirmation_keyboard(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, blokdan chiqarilsin", callback_data=f"admin:unblock_do:{user_id}")
    builder.button(text="❌ Yo'q, qolsin", callback_data="admin:show_blocked_list")
    builder.adjust(2)
    return builder.as_markup()

# --- REKLAMA BO'LIMI UCHUN ---

def generate_ad_edit_keyboard(buttons_matrix: list | None = None):
    builder = InlineKeyboardBuilder()
    if not buttons_matrix:
        builder.button(text="➕", callback_data="ad:add:0:0")
        return builder.as_markup()

    for r_idx, row in enumerate(buttons_matrix):
        current_row_buttons = []
        for c_idx, btn in enumerate(row):
            if btn.get('is_placeholder'):
                current_row_buttons.append(InlineKeyboardButton(text="➕", callback_data=f"ad:add:{r_idx}:{c_idx}"))
            else:
                current_row_buttons.append(InlineKeyboardButton(text=f"{btn['text']}", callback_data=f"ad:manage:{r_idx}:{c_idx}"))
        if current_row_buttons:
            builder.row(*current_row_buttons)
    return builder.as_markup()

# --- KANAL BOSHQARUVI BO'LIMI UCHUN ---

def get_channel_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Kanal qo'shish", callback_data="admin:channel_add_start")
    builder.button(text="📋 Ulangan kanallar", callback_data="admin:channel_show_list")
    builder.button(text="◀️ Admin paneliga qaytish", callback_data="admin:back_to_main_menu")
    builder.adjust(2, 1)
    return builder.as_markup()

async def get_channel_list_keyboard():
    from xdata_handlers.database import get_all_required_channels
    builder = InlineKeyboardBuilder()
    channels = await get_all_required_channels()

    text = "Hozirda majburiy a'zolik uchun birorta ham kanal ulanmagan."
    if channels:
        text = "Ulangan kanallar ro'yxati (o'chirish uchun bosing):"
        for channel in channels:
            title = channel.get('title', "Noma'lum")
            channel_id = channel.get('id')
            builder.button(text=f"❌ {title[:40]}", callback_data=f"admin:channel_remove:{channel_id}")
        builder.adjust(3)

    builder.row(
        InlineKeyboardButton(text="◀️ Asosiy panel", callback_data="admin:back_to_main_menu"),
        InlineKeyboardButton(text="◀️ Ortga", callback_data="admin:channel_menu")
    )
    return builder.as_markup(), text
#--- END OF FILE xinline_keyboard.py ---
