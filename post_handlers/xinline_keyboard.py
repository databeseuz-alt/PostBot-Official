
from aiogram.types import InlineKeyboardButton
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Optional
from aiogram.filters.callback_data import CallbackData
from xdata_handlers.translator import get_text
from xdata_handlers.database import get_post_name

# Emoji to style mapping - used across multiple functions
EMOJI_STYLES = {
    '🟢': 'success',
    '🔴': 'danger',
    '🔵': 'primary',
    '⚪': None
}


def get_button_style(style_str: str) -> Optional[str]:
    """Convert string style to valid internal style string

    Supported: primary, success, danger
    """
    if not style_str:
        return None
    valid_styles = {'primary', 'positive', 'destructive', 'danger', 'success'}
    if style_str in valid_styles:
        if style_str == 'positive': return 'success'
        if style_str == 'destructive': return 'danger'
        return style_str
    return None

def get_style_emoji(style_str: str) -> str:
    """Get emoji representing the style"""
    emoji_map = {
        'success': '🟢',
        'danger': '🔴',
        'primary': '🔵'
    }
    return emoji_map.get(style_str, '')


def _extract_style_from_text(btn_text: str) -> tuple[str, Optional[str]]:
    """
    Extract style from button text based on emoji prefixes.
    Returns (cleaned_text, style) tuple.
    """
    style = None
    for emoji_char, estyle in EMOJI_STYLES.items():
        if btn_text.startswith(emoji_char + emoji_char):
            style = estyle
            btn_text = btn_text[len(emoji_char):]
            break
        elif btn_text.startswith(emoji_char):
            style = estyle
            btn_text = btn_text[len(emoji_char):].strip()
            break
    return btn_text, style


class PostSendCallbackFactory(CallbackData, prefix="post_send"):
    action: str
    post_code: Optional[str] = None
    channel_id: Optional[int] = None

class EditSendCallbackFactory(CallbackData, prefix="edit_send"):
    action: str
    post_code: str

class SavePostCallbackFactory(CallbackData, prefix="save_post"):
    action: str
    post_code: str

def generate_post_keyboard(buttons_matrix: Optional[List[List[Optional[Dict]]]] = None, lang: str = 'uzl'):
    """Tahrirlash uchun klaviatura (➕ va boshqaruvchi tugmalar bilan)"""
    builder = InlineKeyboardBuilder()
    if not buttons_matrix:
        builder.button(text=get_text('add_inline_btn', lang), callback_data="add:0:0")
        return builder.as_markup()

    has_real_buttons = any(any(btn and not btn.get('is_placeholder') for btn in row) for row in buttons_matrix)
    placeholder_text = "➕" if has_real_buttons else get_text('add_inline_btn', lang)

    for r_idx, row in enumerate(buttons_matrix):
        current_row_buttons = []
        for c_idx, btn in enumerate(row):
            if btn is None:
                continue
            if btn.get('is_placeholder'):
                current_row_buttons.append(InlineKeyboardButton(text=placeholder_text, callback_data=f"add:{r_idx}:{c_idx}"))
            else:
                btn_text, style = _extract_style_from_text(str(btn['text']))

                kwargs = {
                    'text': btn_text,
                    'callback_data': f"manage:{r_idx}:{c_idx}"
                }

                if style:
                    valid_style = get_button_style(style)
                    if valid_style:
                        kwargs['style'] = valid_style

                if btn.get('emoji_id'):
                    kwargs['icon_custom_emoji_id'] = btn['emoji_id']
                current_row_buttons.append(InlineKeyboardButton(**kwargs))
        if current_row_buttons:
            builder.row(*current_row_buttons)

    return builder.as_markup()

def generate_preview_keyboard(buttons_matrix: Optional[List[List[Optional[Dict]]]] = None):
    """Oldindan ko'rish uchun klaviatura"""
    builder = InlineKeyboardBuilder()
    if not buttons_matrix:
        return None

    for row in buttons_matrix:
        current_row_buttons = []
        for btn in row:
            if btn and not btn.get('is_placeholder'):
                btn_text, style = _extract_style_from_text(str(btn['text']))

                kwargs = {'text': btn_text}

                if btn.get('type') == 'text_btn':
                    db_id = btn.get('db_id', '0')
                    kwargs['callback_data'] = f"text_btn_preview:{db_id}"
                elif btn.get('type') == 'reaction':
                    kwargs['text'] = f"{btn_text} 0"
                    kwargs['callback_data'] = "reaction_preview"
                else:
                    kwargs['url'] = btn.get('url', 'https://t.me')

                if style:
                    valid_style = get_button_style(style)
                    if valid_style:
                        kwargs['style'] = valid_style

                if btn.get('emoji_id'):
                    kwargs['icon_custom_emoji_id'] = btn['emoji_id']
                current_row_buttons.append(InlineKeyboardButton(**kwargs))
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
                btn_text, style = _extract_style_from_text(str(btn['text']))

                kwargs = {'text': btn_text}

                if btn.get('type') == 'text_btn':
                    db_id = btn.get('db_id', '0')
                    kwargs['callback_data'] = f"text_btn:{db_id}"
                elif btn.get('type') == 'reaction':
                    kwargs['text'] = f"{btn_text} 0"
                    reaction_text = btn.get('text', '👍')
                    kwargs['callback_data'] = f"reaction:{reaction_text}"
                else:
                    kwargs['url'] = btn.get('url', 'https://t.me')

                if style:
                    valid_style = get_button_style(style)
                    if valid_style:
                        kwargs['style'] = valid_style

                if btn.get('emoji_id'):
                    kwargs['icon_custom_emoji_id'] = btn['emoji_id']
                current_row_buttons.append(InlineKeyboardButton(**kwargs))
        if current_row_buttons:
            builder.row(*current_row_buttons)

    if not builder.export():
        return None

    return builder.as_markup()

def create_post_options_keyboard(content_type: str, lang: str = 'uzl'):
    """Postning qo'shimcha sozlamalari uchun asosiy menyu."""
    return None

async def get_post_management_keyboard(post_code: str, lang: str = 'uzl'):
    """
    Post saqlangandan keyin 'Saqlash' yoki 'Tahrirlash' tugmalarini yaratadi.
    Agar postda nom bo'lsa -> 'Tahrirlash', aks holda -> 'Saqlash'
    """
    builder = InlineKeyboardBuilder()

    post_name = await get_post_name(post_code)

    if post_name:
        builder.button(
            text=get_text('edit_post_btn', lang),
            callback_data=SavePostCallbackFactory(action="edit_save_menu", post_code=post_code).pack()
        )
    else:
        builder.button(
            text=get_text('save_btn', lang), 
            callback_data=SavePostCallbackFactory(action="start_save", post_code=post_code).pack()
        )

    builder.button(
        text=get_text('send_btn', lang),
        callback_data=PostSendCallbackFactory(action="start_sending", post_code=post_code).pack()
    )
    builder.button(
        text=get_text('print_settings_btn', lang),
        callback_data=f"print:{post_code}:menu"
    )
    builder.adjust(2, 2)
    return builder.as_markup()

def get_post_save_edit_keyboard(post_code: str, lang: str = 'uzl'):
    """
    'Tahrirlash' tugmasi bosilganda chiqadigan menyu:
    [ Qayta nomlash ] [ O'chirish ]
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text('rename_btn', lang),
        callback_data=SavePostCallbackFactory(action="rename", post_code=post_code).pack()
    )
    builder.button(
        text=get_text('delete_btn', lang),
        callback_data=SavePostCallbackFactory(action="delete_name", post_code=post_code).pack()
    )
    builder.adjust(2)
    return builder.as_markup()

def get_send_timing_keyboard(post_code: str, channel_id: int, lang: str = 'uzl'):
    """Kanal tanlagandan keyin: Hozir yuborish yoki Rejalashtirish."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text('send_now_btn', lang),
        callback_data=PostSendCallbackFactory(action="confirm_prompt", post_code=post_code, channel_id=channel_id).pack()
    )
    builder.button(
        text=get_text('schedule_btn', lang),
        callback_data=PostSendCallbackFactory(action="schedule_for_channel", post_code=post_code, channel_id=channel_id).pack()
    )
    builder.adjust(2)
    return builder.as_markup()

def get_edit_send_keyboard(post_code: str, lang: str = 'uzl'):
    """Postni tahrirlash yoki yuborishni tanlash klaviaturasi."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text('edit_post_btn', lang),
        callback_data=EditSendCallbackFactory(action="edit", post_code=post_code).pack()
    )
    builder.button(
        text=get_text('send_confirm_btn', lang),
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

def get_send_confirmation_keyboard(post_code: str, channel_id: int, lang: str = 'uzl'):
    """Postni yuborishni tasdiqlash klaviaturasini yaratadi."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('no_btn', lang),
        callback_data=PostSendCallbackFactory(action="back_to_channels", post_code=post_code).pack()
    )
    builder.button(
        text=get_text('yes_btn', lang),
        callback_data=PostSendCallbackFactory(
            action="confirm_send",
            post_code=post_code,
            channel_id=channel_id
        ).pack()
    )
    builder.adjust(2)
    return builder.as_markup()

def get_add_channel_prompt_keyboard(lang: str = 'uzl'):
    """Foydalanuvchini kanal qo'shishga undovchi klaviatura."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('add_channel_btn', lang), callback_data="add_channel_redirect")
    return builder.as_markup()

def get_add_channel_with_post_keyboard(post_code: str, lang: str = 'uzl'):
    """Post yuborish vaqtida kanal yo'q bo'lsa, post kodi bilan kanal qo'shish tugmasi."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text('add_channel_post_btn', lang),
        callback_data=PostSendCallbackFactory(action="add_channel_with_post", post_code=post_code).pack()
    )
    return builder.as_markup()

class ButtonTypeCallbackFactory(CallbackData, prefix="btn_type"):
    type: str

def get_button_type_reply_kb(lang: str):
    """Tugma turini tanlash uchun reply klaviatura."""
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    from aiogram.types import KeyboardButton

    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('url_type_btn', lang)))
    builder.add(KeyboardButton(text=get_text('text_type_btn', lang)))
    builder.add(KeyboardButton(text=get_text('reactions_btn', lang)))
    builder.add(KeyboardButton(text=get_text('back_btn', lang)))
    builder.adjust(3, 1)
    return builder.as_markup(resize_keyboard=True)

def create_settings_main_keyboard(lang: str = 'uzl'):
    """Asosiy sozlamalar menyusi."""
    builder = InlineKeyboardBuilder()
    builder.button(text="vaqt mintaqasi: Toshkent (00:00)", callback_data="settings_timezone")
    builder.button(text=get_text('ai_assistant_btn', lang), callback_data="settings_ai_assistant")
    builder.adjust(1)
    return builder.as_markup()

def get_media_settings_inline_kb(lang: str, has_spoiler: bool = False, is_paid: bool = False, show_caption_above: bool = False, has_caption: bool = True, content_type: str = 'photo'):
    """Media sozlamalari uchun inline klaviatura - layout 1, 2, 1 (faqat caption bo'lsa joylashuv ko'rsatiladi)"""
    builder = InlineKeyboardBuilder()

    if has_caption and content_type in ['photo', 'video', 'animation', 'paid_media']:
        position_text = get_text('position_above_btn', lang) if show_caption_above else get_text('position_below_btn', lang)
        builder.button(text=position_text, callback_data="media_toggle_position")

    if content_type in ['photo', 'video', 'animation']:
        spoiler_text = get_text('spoiler_enabled_btn', lang) if has_spoiler else get_text('spoiler_btn', lang)
        builder.button(text=spoiler_text, callback_data="media_toggle_spoiler")

    if content_type in ['photo', 'video', 'animation', 'paid_media']:
        paid_text = get_text('paid_media_enabled_btn', lang) if is_paid else get_text('paid_media_btn', lang)
        builder.button(text=paid_text, callback_data="media_toggle_paid")

    builder.button(text=get_text('back_btn', lang), callback_data="back_to_settings_menu")

    if has_caption and content_type in ['photo', 'video', 'animation', 'paid_media']:
        builder.adjust(1, 2, 1)
    else:
        builder.adjust(2, 1)

    return builder.as_markup()

def create_timezone_keyboard(lang: str = 'uzl'):
    """Vaqt mintaqasi uchun sozlamalar."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Vaqt mintaqasini o'zgartirish", callback_data="change_timezone_alphabet")
    builder.button(text="🔙 Orqaga", callback_data="back_to_settings_main")
    builder.adjust(1)
    return builder.as_markup()

def create_timezone_alphabet_keyboard(lang: str = 'uzl'):
    """Mamlakatni tanlash uchun harflar ro'yxati."""
    import string
    builder = InlineKeyboardBuilder()
    for letter in string.ascii_uppercase:
        builder.button(text=letter, callback_data=f"tz_letter:{letter}")

    builder.button(text="🔙 Orqaga", callback_data="settings_timezone")
    builder.adjust(5, 5, 5, 5, 5, 1, 1)
    return builder.as_markup()

def get_done_inline_keyboard(lang: str = 'uzl'):
    """Post saqlangandan keyin: [Chop etish sozlamalari] [Boshqa post yaratish] [Orqaga]"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('print_settings_btn', lang), callback_data="print_settings")
    builder.button(text=get_text('cr_another_post_btn', lang), callback_data="done_create_another")
    builder.button(text=get_text('back_btn', lang), callback_data="done_back")
    builder.adjust(1, 2)
    return builder.as_markup()

def get_cancel_inline_kb(lang: str = 'uzl'):
    """Jarayonni bekor qilish uchun inline klaviatura."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('cancel_btn', lang), callback_data="cancel_action")
    builder.button(text=get_text('ai_assistant_btn', lang), callback_data="ai_assistant")
    builder.adjust(2)
    return builder.as_markup()

def get_ai_assistant_keyboard(is_enabled: bool, lang: str = 'uzl'):
    """AI assistant tugmasini yoqish/o'chirish klaviaturasi."""
    builder = InlineKeyboardBuilder()
    check_mark = "✅" if is_enabled else "☑️"
    builder.button(
        text=f"{check_mark} Ai bilan yozish",
        callback_data="toggle_ai_assistant"
    )
    builder.button(text=get_text('back_btn', lang), callback_data="back_to_settings_main")
    builder.adjust(1)
    return builder.as_markup()

def get_button_color_keyboard(lang: str = 'uzl'):
    """Tugma rangini tanlash uchun inline klaviatura."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text('btn_color_default', lang), callback_data="btn_color:"),
        InlineKeyboardButton(text=get_text('btn_color_green', lang), callback_data="btn_color:success", style="success")
    )
    builder.row(
        InlineKeyboardButton(text=get_text('btn_color_blue', lang), callback_data="btn_color:primary", style="primary"),
        InlineKeyboardButton(text=get_text('btn_color_red', lang), callback_data="btn_color:danger", style="danger")
    )
    return builder.as_markup()

def get_print_settings_keyboard(lang: str = 'uzl', post_code: str = None):
    """Chop etish sozlamalari uchun inline klaviatura."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('print_delete_timer', lang), callback_data=f"print:{post_code or 'none'}:delete_timer")
    builder.button(text=get_text('back_btn', lang), callback_data=f"print:{post_code or 'none'}:back")
    builder.adjust(1, 1)
    return builder.as_markup()

def get_settings_menu_inline_kb(lang: str, content_type: str = 'text'):
    """Asosiy sozlamalar menyusi - Media va Watermark tugmalari (faqat media uchun)"""
    builder = InlineKeyboardBuilder()

    media_types = ['photo', 'video', 'audio', 'document', 'animation', 'voice', 'video_note', 'paid_media']
    has_media = content_type in media_types

    if has_media:
        builder.button(text=get_text('media_settings_btn', lang), callback_data="open_media_settings_menu")

        if content_type == 'photo':
            builder.button(text=get_text('watermark_btn', lang), callback_data="watermark_settings")
            builder.adjust(2)
        else:
            builder.adjust(1)

    return builder.as_markup()

def get_post_settings_inline_kb(content_type: str, has_caption: bool = False, lang: str = 'uzl', is_editing: bool = False, is_paid: bool = False):
    """Post sozlamalari uchun inline klaviatura - tugmalar olib tashlangan"""
    return None
