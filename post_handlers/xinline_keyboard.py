#--- START OF FILE xinline_keyboard.py ---

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Optional
from aiogram.filters.callback_data import CallbackData

#=============================================================================
# --- K L A V I A T U R A   Y A R A T I SH ---
#=============================================================================

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

#--- END OF FILE xinline_keyboard.py ---
