from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from xdata_handlers.translator import get_text
from xdata_handlers import config

def get_main_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Statistika", callback_data="admin:statistics_menu")
    builder.button(text="🚫 Bloklangan", callback_data="admin:blocked_users_menu")
    builder.button(text="📢 Reklama", callback_data="admin:send_ad_start")
    builder.button(text="📢 Kanal ulash", callback_data="admin:channel_menu")
    builder.button(text="💾 Ma'lumotlar", callback_data="admin:export_menu_period")
    builder.button(text="⚙️ sozlamalar", callback_data="admin:settings_main_menu")

    builder.adjust(2, 2, 2)
    return builder.as_markup()

def get_settings_menu_keyboard():
    """Sozlamalar bo'limi uchun klaviatura."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏷 Bot nomi", callback_data="admin:bot_name_lang_select")
    builder.button(text="📝 Buyruqlar", callback_data="admin:bot_commands_lang_select")
    builder.button(text="ℹ️ description", callback_data="admin:bot_desc_lang_select")
    builder.button(text="👤 Tarjimai hol", callback_data="admin:bot_bio_lang_select")
    builder.button(text="🔙 Admin paneliga qaytish", callback_data="admin:back_to_main_menu")
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def get_no_commands_keyboard(mode: str = "commands", text: str = "Buyruq"):
    """Ma'lumot mavjud bo'lmaganda chiqadigan klaviatura (1, 2 adjust)."""
    builder = InlineKeyboardBuilder()
    builder.button(text=f"➕ {text} qo'shish", callback_data=f"admin:bot_{mode}_start:all")
    builder.button(text="🔙 Admin paneli", callback_data="admin:back_to_main_menu")
    builder.button(text="🔙 Orqaga", callback_data="admin:settings_main_menu")
    builder.adjust(1, 2)
    return builder.as_markup()

def get_commands_input_nav_keyboard(mode: str = "commands"):
    """Buyruq/Bio/Desc kiritish jarayonidagi navigatsiya (2 adjust)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Asosiy panel", callback_data="admin:back_to_main_menu")
    builder.button(text="🔙 Orqaga", callback_data=f"admin:bot_{mode}_lang_select")
    builder.adjust(2)
    return builder.as_markup()

def get_language_selection_keyboard(has_global: bool = True, mode: str = "commands"):
    """Tillar ro'yxatini chiqaruvchi klaviatura."""
    import os
    from xdata_handlers.translator import BASE_DIR
    locales_dir = os.path.join(BASE_DIR, "language_packs")
    builder = InlineKeyboardBuilder()
    
    LANG_MAP = {
        'uz': '🇺🇿 UZ',
        'en': '🇬🇧 EN',
        'ru': '🇷🇺 RU',
        'ar': '🇸🇦 AR',
        'az': '🇦🇿 AZ',
        'de': '🇩🇪 DE',
        'es': '🇪🇸 ES',
        'fr': '🇫🇷 FR',
        'it': '🇮🇹 IT',
        'kg': '🇰🇬 KG',
        'kz': '🇰🇿 KZ',
        'tj': '🇹🇯 TJ',
        'tk': '🇹🇲 TK',
        'tr': '🇹🇷 TR'
    }
    
    try:
        if os.path.exists(locales_dir):
            added_langs = set()
            for file in os.listdir(locales_dir):
                if file.endswith(".json"):
                    lang_code = file[:-5]
                    
                    if lang_code in ['uzl', 'uzk']:
                        lang_code = 'uz'
                        
                    if lang_code not in added_langs:
                        text = LANG_MAP.get(lang_code, lang_code.upper())
                        builder.button(text=text, callback_data=f"admin:bot_{mode}_start:{lang_code}")
                        added_langs.add(lang_code)
    except Exception as e:
        pass
        
    if has_global:
        builder.button(text="🌐 Default", callback_data=f"admin:bot_{mode}_start:all")
    
    builder.button(text="🔙 Asosiy panel", callback_data="admin:back_to_main_menu")
    builder.button(text="🔙 Orqaga", callback_data="admin:settings_main_menu")
    
    if has_global:
        builder.adjust(5, 5, 5, 2)
    else:
        builder.adjust(5, 5, 2)
        
    return builder.as_markup()


def get_statistics_keyboard():
    """Statistika bo'limi uchun klaviatura."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Asosiy statistika", callback_data="admin:statistics_main")
    builder.button(text="📊 Grafika", callback_data="admin:statistics_graphic")
    builder.button(text="🔙 Admin paneliga qaytish", callback_data="admin:back_to_main_menu")
    
    builder.adjust(2, 1)
    return builder.as_markup()

def get_back_to_main_orqaga_keyboard():
    """Asosiy statistika ko'rsatilganda 2 ta tugma: Asosiy panel va Orqaga."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Asosiy panel", callback_data="admin:back_to_main_menu")
    builder.button(text="🔙 Orqaga", callback_data="admin:statistics_menu")
    
    builder.adjust(2)
    return builder.as_markup()

def get_user_data_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="💾 Ma'lumotlar bazasi", callback_data="admin:export_menu_period")
    builder.button(text="🔎 User qidirish", callback_data="admin:search_user_start")
    builder.button(text="✉️ Xabar yuborish", callback_data="admin:direct_message_start")
    builder.button(text="🔙 Admin paneliga qaytish", callback_data="admin:back_to_main_menu")
    builder.adjust(2, 1, 1)
    return builder.as_markup()

def get_export_period_keyboard():
    """Ma'lumotlarni eksport qilish uchun vaqt oralig'ini tanlash klaviaturasi."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Barcha foydalanuvchi ma'lumoti", callback_data="admin:export_type_menu:all")
    builder.button(text="Oylik", callback_data="admin:export_type_menu:monthly")
    builder.button(text="Haftalik", callback_data="admin:export_type_menu:weekly")
    builder.button(text="Kunlik", callback_data="admin:export_type_menu:daily")
    builder.button(text="🔙 Asosiy panel", callback_data="admin:back_to_main_menu")
    builder.button(text="🔙 Ortga", callback_data="admin:user_data_menu")
    builder.adjust(1, 3, 2)
    return builder.as_markup()

def get_export_type_keyboard(period: str):
    """Ma'lumotlarni eksport qilish uchun ma'lumot turini tanlash klaviaturasi."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Barcha foydalanuvchi ro'yxati", callback_data=f"admin:export_do:{period}:full_list")
    builder.button(text="Faqat post yaratganlar", callback_data=f"admin:export_do:{period}:post_creators")
    builder.button(text="Foydalanuvchi sozlamalari", callback_data=f"admin:export_do:{period}:user_settings")
    builder.button(text="🔙 Asosiy panel", callback_data="admin:back_to_main_menu")
    builder.button(text="🔙 Ortga", callback_data="admin:export_menu_period")
    builder.adjust(3, 2)
    return builder.as_markup()

def get_user_search_start_keyboard():
    """User qidirishni boshlash uchun navigatsiya klaviaturasi."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Asosiy panel", callback_data="admin:back_to_main_menu"),
        InlineKeyboardButton(text="🔙 Ortga", callback_data="admin:user_data_menu")
    )
    return builder.as_markup()

def get_user_profile_actions_keyboard(user_id: int, is_blocked: bool):
    """Foydalanuvchi profili uchun amallar klaviaturasi."""
    builder = InlineKeyboardBuilder()

    builder.button(text="✉️ Xabar yozish", callback_data=f"admin:dm_from_profile:{user_id}")

    if is_blocked:
        builder.button(text="✅ Blokdan chiqarish", callback_data=f"admin:unblock_from_profile:{user_id}")
    else:
        builder.button(text="🚫 Bloklash", callback_data=f"admin:block_from_profile:{user_id}")

    builder.adjust(2)

    builder.row(
        InlineKeyboardButton(text="🔙 Asosiy panel", callback_data="admin:back_to_main_menu"),
        InlineKeyboardButton(text="🔙 Ortga", callback_data="admin:search_user_start")
    )
    return builder.as_markup()

def get_blocked_users_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Foydalanuvchini bloklash", callback_data="admin:block_user_start")
    builder.button(text="📋 Bloklanganlar ro'yxati", callback_data="admin:show_blocked_list")
    builder.button(text="🔙 Admin paneliga qaytish", callback_data="admin:back_to_main_menu")
    builder.adjust(2, 1)
    return builder.as_markup()

async def get_blocked_list_view_keyboard(admin_ids: list, adjust_size: int = 3):
    from xdata_handlers.database import get_blocked_users_with_info
    blocked_users = await get_blocked_users_with_info(admin_ids=admin_ids)
    builder = InlineKeyboardBuilder()

    if blocked_users:
        for user in blocked_users:
            display_name = user.get('nickname') or f"Noma'lum ({user['user_id']})"
            builder.button(text=f"❌ {display_name}", callback_data=f"admin:view_blocked_user:{user['user_id']}")
        builder.adjust(adjust_size)

    builder.row(
        InlineKeyboardButton(text="🔙 Asosiy panel", callback_data="admin:back_to_main_menu"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:blocked_users_menu")
    )
    return builder.as_markup()

def get_blocked_user_detail_keyboard(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔓 Blokdan chiqarish", callback_data=f"admin:unblock_confirm:{user_id}")
    builder.button(text="🔙 Orqaga", callback_data="admin:show_blocked_list")
    builder.adjust(2)
    return builder.as_markup()

def get_unblock_confirmation_keyboard(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, blokdan chiqarilsin", callback_data=f"admin:unblock_do:{user_id}")
    builder.button(text="❌ Yo'q, qolsin", callback_data=f"admin:view_blocked_user:{user_id}")
    builder.adjust(2)
    return builder.as_markup()

def generate_ad_edit_keyboard(buttons_matrix: list | None = None):
    builder = InlineKeyboardBuilder()
    if not buttons_matrix:
        builder.button(text=get_text('add_inline_btn', 'uzl'), callback_data="ad:add:0:0")
        return builder.as_markup()

    has_real_buttons = any(any(btn and not btn.get('is_placeholder') for btn in row) for row in buttons_matrix)

    placeholder_text = "➕" if has_real_buttons else get_text('add_inline_btn', 'uzl')

    for r_idx, row in enumerate(buttons_matrix):
        current_row_buttons = []
        for c_idx, btn in enumerate(row):
            if btn.get('is_placeholder'):
                current_row_buttons.append(InlineKeyboardButton(text=placeholder_text, callback_data=f"ad:add:{r_idx}:{c_idx}"))
            else:
                current_row_buttons.append(InlineKeyboardButton(text=f"{btn['text']}", callback_data=f"ad:manage:{r_idx}:{c_idx}"))
        if current_row_buttons:
            builder.row(*current_row_buttons)
    return builder.as_markup()

def get_channel_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Kanal qo'shish", callback_data="admin:channel_add_start")
    builder.button(text="📋 Ulangan kanallar", callback_data="admin:channel_show_list")
    builder.button(text="🔙 Admin paneliga qaytish", callback_data="admin:back_to_main_menu")
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
        InlineKeyboardButton(text="🔙 Asosiy panel", callback_data="admin:back_to_main_menu"),
        InlineKeyboardButton(text="🔙 Ortga", callback_data="admin:channel_menu")
    )
    return builder.as_markup(), text
