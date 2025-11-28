#--- START OF FILE xinline_keyboard.py ---
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Optional
from aiogram.filters.callback_data import CallbackData

# =============================================================================
# --- K L A V I A T U R A   Y A R A T I SH ---
# =============================================================================

class PostSettingsCallbackFactory(CallbackData, prefix="post_settings"):
    action: str
    value: Optional[str] = None

class PostSendCallbackFactory(CallbackData, prefix="post_send"):
    action: str
    post_code: Optional[str] = None
    channel_id: Optional[int] = None

class EditSendCallbackFactory(CallbackData, prefix="edit_send"):
    action: str
    post_code: str

def generate_post_keyboard(buttons_matrix: Optional[List[List[Optional[Dict]]]] = None):
    """Tahrirlash uchun klaviatura (➕ va boshqaruvchi tugmalar bilan)"""
    builder = InlineKeyboardBuilder()
    if not buttons_matrix:
        builder.button(text="➕", callback_data="add:0:0")
        return builder.as_markup()

    for r_idx, row in enumerate(buttons_matrix):
        current_row_buttons = []
        for c_idx, btn in enumerate(row):
            if btn is None:
                continue
            if btn.get('is_placeholder'):
                current_row_buttons.append(InlineKeyboardButton(text="➕", callback_data=f"add:{r_idx}:{c_idx}"))
            else:
                current_row_buttons.append(InlineKeyboardButton(
                    text=f"{btn['text']}",
                    callback_data=f"manage:{r_idx}:{c_idx}"
                ))
        if current_row_buttons:
            builder.row(*current_row_buttons)

    return builder.as_markup()


def generate_preview_keyboard(buttons_matrix: Optional[List[List[Optional[Dict]]]] = None):
    """Oldindan ko'rish uchun klaviatura (faqat URL bilan ishlaydigan tugmalar)"""
    builder = InlineKeyboardBuilder()
    if not buttons_matrix:
        return None

    for row in buttons_matrix:
        current_row_buttons = []
        for btn in row:
            if btn and not btn.get('is_placeholder'):
                current_row_buttons.append(InlineKeyboardButton(text=btn['text'], url=btn['url']))
        if current_row_buttons:
            builder.row(*current_row_buttons)

    if not builder.export():
        return None

    return builder.as_markup()


def generate_final_keyboard(buttons_matrix: Optional[List[List[Optional[Dict]]]] = None):
    """Inline rejim uchun yakuniy klaviatura (tahrirlash tugmalarisiz)"""
    builder = InlineKeyboardBuilder()
    if not buttons_matrix:
        return None

    for row in buttons_matrix:
        current_row_buttons = []
        for btn in row:
            if btn and not btn.get('is_placeholder'):
                current_row_buttons.append(InlineKeyboardButton(text=btn['text'], url=btn['url']))
        if current_row_buttons:
            builder.row(*current_row_buttons)

    if not builder.export():
        return None

    return builder.as_markup()

def create_post_options_keyboard(content_type: str, has_caption: bool, current_parse_mode: Optional[str], url_preview_disabled: bool):
    """Postning qo'shimcha sozlamalari uchun asosiy menyu."""
    builder = InlineKeyboardBuilder()
    button_count = 0

    if content_type == 'text' or has_caption:
        builder.button(
            text="✍️ Matn formati",
            callback_data=PostSettingsCallbackFactory(action="show_parse_mode").pack()
        )
        button_count += 1

    if content_type == 'text':
        builder.button(
            text="🔗 URL Preview",
            callback_data=PostSettingsCallbackFactory(action="show_url_preview").pack()
        )
        button_count += 1

    if button_count > 1:
        builder.adjust(2)
    else:
        builder.adjust(1)

    return builder.as_markup()

def create_post_parse_mode_keyboard(current_mode: Optional[str], show_back_button: bool = True):
    """Matn formatini tanlash klaviaturasi."""
    builder = InlineKeyboardBuilder()

    modes_order = [
        ("MarkdownV2", "Markdown"),
        ("HTML", "HTML")
    ]

    for mode_value, mode_name in modes_order:
        text = f"🔹 {mode_name}" if current_mode == mode_value else mode_name
        builder.button(
            text=text,
            callback_data=PostSettingsCallbackFactory(action="set_parse_mode", value=mode_value).pack()
        )

    if show_back_button:
        builder.button(text="◀️ Ortga", callback_data=PostSettingsCallbackFactory(action="back_to_options").pack())
        builder.adjust(2, 1)
    else:
        builder.adjust(2)

    return builder.as_markup()

def create_post_url_preview_keyboard(is_disabled: bool):
    """URL oldindan ko'rishni yoqish/o'chirish klaviaturasi."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Yoqish" if is_disabled else "🔹 ✅ Yoqish",
        callback_data=PostSettingsCallbackFactory(action="set_url_preview", value="false").pack()
    )
    builder.button(
        text="❌ O'chirish" if not is_disabled else "🔹 ❌ O'chirish",
        callback_data=PostSettingsCallbackFactory(action="set_url_preview", value="true").pack()
    )
    builder.button(text="◀️ Ortga", callback_data=PostSettingsCallbackFactory(action="back_to_options").pack())
    builder.adjust(2, 1)
    return builder.as_markup()

#=============================================================================
# POSTNI BOSHQARISH VA YUBORISH UCHUN KLAviATURALAR
#=============================================================================

def get_post_management_keyboard(post_code: str):
    """Post saqlangandan keyin 'Saqlash' va 'Yuborish' tugmalarini yaratadi."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Saqlash", callback_data=f"save_post:{post_code}")
    builder.button(
        text="Yuborish",
        callback_data=PostSendCallbackFactory(action="start_sending", post_code=post_code).pack()
    )
    builder.adjust(2)
    return builder.as_markup()

def get_edit_send_keyboard(post_code: str):
    """Postni tahrirlash yoki yuborishni tanlash klaviaturasi."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📝 Tahrirlash",
        callback_data=EditSendCallbackFactory(action="edit", post_code=post_code).pack()
    )
    builder.button(
        text="↗️ Yuborish",
        callback_data=PostSendCallbackFactory(action="start_sending", post_code=post_code).pack()
    )
    builder.adjust(2)
    return builder.as_markup()

def get_channel_list_keyboard(channels: list[dict], post_code: str):
    """Foydalanuvchi kanallari ro'yxatini post yuborish uchun yaratadi."""
    builder = InlineKeyboardBuilder()
    for channel in channels:
        builder.button(
            text=channel['channel_name'],
            callback_data=PostSendCallbackFactory(
                action="select_channel",
                post_code=post_code,
                channel_id=channel['channel_id']
            ).pack()
        )
    builder.adjust(3)
    return builder.as_markup()

def get_send_confirmation_keyboard(post_code: str, channel_id: int):
    """Postni yuborishni tasdiqlash klaviaturasini yaratadi."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Yo'q ❌",
        callback_data=PostSendCallbackFactory(action="start_sending", post_code=post_code).pack()
    )
    builder.button(
        text="Ha ✅",
        callback_data=PostSendCallbackFactory(
            action="confirm_send",
            post_code=post_code,
            channel_id=channel_id
        ).pack()
    )
    builder.adjust(2)
    return builder.as_markup()

def get_add_channel_prompt_keyboard():
    """Foydalanuvchini kanal qo'shishga undovchi klaviatura."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Kanal qo'shish", callback_data="add_channel_redirect")
    return builder.as_markup()

# =============================================================================
# --- ADMIN PANELI KLAVIATURALARI ---
# =============================================================================

def get_main_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 bot statistika", callback_data="admin:stats_menu")
    builder.button(text="🚫 bloklanganlar", callback_data="admin:blocked_users_menu")
    builder.button(text="📢 Reklama yuborish", callback_data="admin:send_ad_start")
    builder.button(text="📢 Kanalni ulash", callback_data="admin:channel_menu")
    builder.button(text="ℹ️ foydalanuvchi ma'lumotlari bazasi", callback_data="admin:user_data_menu")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def get_stats_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Umumiy statistika", callback_data="admin:stats_show_general")
    builder.button(text="📈 Grafika", callback_data="admin:stats_show_graph")
    builder.button(text="◀️ Admin paneliga qaytish", callback_data="admin:back_to_main_menu")
    builder.adjust(2, 1)
    return builder.as_markup()

def get_user_data_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="💾 Ma'lumotlar bazasi", callback_data="admin:export_menu_period")
    builder.button(text="🔎 User qidirish", callback_data="admin:search_user_start")
    builder.button(text="◀️ Admin paneliga qaytish", callback_data="admin:back_to_main_menu")
    builder.adjust(2, 1)
    return builder.as_markup()

def get_export_period_keyboard():
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
    builder = InlineKeyboardBuilder()
    builder.button(text="Barcha foydalanuvchi ro'yxati", callback_data=f"admin:export_do:{period}:full_list")
    builder.button(text="Faqat post yaratganlar", callback_data=f"admin:export_do:{period}:post_creators")
    builder.button(text="Foydalanuvchi sozlamalari", callback_data=f"admin:export_do:{period}:user_settings")
    builder.button(text="◀️ Asosiy panel", callback_data="admin:back_to_main_menu")
    builder.button(text="◀️ Ortga", callback_data="admin:export_menu_period")
    builder.adjust(3, 2)
    return builder.as_markup()

def get_user_search_start_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Asosiy panel", callback_data="admin:back_to_main_menu"),
        InlineKeyboardButton(text="◀️ Ortga", callback_data="admin:user_data_menu")
    )
    return builder.as_markup()

# --- XATOLIK TUZATILGAN JOY ---
def get_user_search_result_keyboard(posts: list):
    """User qidiruvi natijasi uchun klaviatura (yaratilgan postlar bilan)."""
    builder = InlineKeyboardBuilder()
    if posts:
        for post in posts:
            # Post bu yerda lug'at (dict) ko'rinishida keladi: {'code': '...', 'name': '...'}
            code = post.get('code')
            name = post.get('name')
            
            # Tugma matniga nomini chiqaramiz (agar bo'lsa), bo'lmasa kodini
            btn_text = name if name else code
            # Agar nom juda uzun bo'lsa, qisqartiramiz
            if len(btn_text) > 20:
                btn_text = btn_text[:20] + "..."
            
            # Callback data ga esa faqat KODni beramiz
            builder.button(text=f"{btn_text}", callback_data=f"admin:review_post:{code}")
        builder.adjust(2)

    builder.row(
        InlineKeyboardButton(text="◀️ Asosiy panel", callback_data="admin:back_to_main_menu"),
        InlineKeyboardButton(text="◀️ Ortga", callback_data="admin:user_data_menu")
    )
    return builder.as_markup()

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

def get_channel_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Kanal qo'shish", callback_data="admin:channel_add_start")
    builder.button(text="📋 Ulangan kanallar", callback_data="admin:channel_show_list")
    builder.button(text="◀️ Admin paneliga qaytish", callback_data="admin:back_to_main_menu")
    builder.adjust(2, 1)
    return builder.as_markup()

async def get_channel_list_keyboard_admin():
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
