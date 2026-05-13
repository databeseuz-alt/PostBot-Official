from aiogram.types import InlineKeyboardButton
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Optional
from aiogram.filters.callback_data import CallbackData
from xdata_handlers.translator import get_text
from xdata_handlers.database import get_post_name

EMOJI_STYLES = {
    '🟢': 'success',
    '🔴': 'danger',
    '🔵': 'primary',
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
    original_text = btn_text
    for emoji_char, estyle in EMOJI_STYLES.items():
        if btn_text.startswith(emoji_char + emoji_char):
            style = estyle
            btn_text = btn_text[len(emoji_char):]
            break
        elif btn_text.startswith(emoji_char):
            style = estyle
            btn_text = btn_text[len(emoji_char):].strip()
            break
    # Agar matn bo'sh qolsa (faqat emoji yuborilgan bo'lsa), asl emoji ni qoldir
    if not btn_text and style:
        btn_text = original_text
    return btn_text, style


class PostSendCallbackFactory(CallbackData, prefix="post_send"):
    action: str
    post_code: Optional[str] = None
    channel_id: Optional[int] = None

class EditSendCallbackFactory(CallbackData, prefix="edit_send"):
    action: str
    post_code: Optional[str] = None

class SavePostCallbackFactory(CallbackData, prefix="save_post"):
    action: str
    post_code: Optional[str] = None

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
                elif btn.get('type') == 'ad_poll':
                    action = btn.get('action', 'none')
                    kwargs['callback_data'] = f"ad_poll:{action}"
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

def generate_final_keyboard(buttons_matrix: Optional[List[List[Optional[Dict]]]] = None, post_code: str = 'none'):
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
                    kwargs['callback_data'] = f"track_click:{post_code}:text_btn:{db_id}"
                elif btn.get('type') == 'reaction':
                    kwargs['text'] = f"{btn_text} 0"
                    reaction_text = btn.get('text', '👍')
                    kwargs['callback_data'] = f"track_click:{post_code}:reaction:{reaction_text}"
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


async def get_post_management_keyboard(post_code: str, lang: str = 'uzl'):
    """
    Post saqlangandan keyin 'Saqlash' yoki 'Tahrirlash' tugmalarini yaratadi.
    Agar postda nom bo'lsa -> 'Tahrirlash', aks holda -> 'Saqlash'
    """
    if not post_code:
        return None
    
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

def create_settings_main_keyboard(lang: str = 'uzl', timezone_str: str = "Tashkent (00:00)"):
    """Asosiy sozlamalar menyusi."""
    builder = InlineKeyboardBuilder()
    # Row 1: Interfeys & Taxrirchilar
    builder.row(
        InlineKeyboardButton(text="⌨️ Interfeys", callback_data="settings_interface"),
        InlineKeyboardButton(text="👥 Taxrirchilar", callback_data="settings_editors")
    )
    # Row 2: Vaqt mintaqasi
    builder.row(InlineKeyboardButton(text=f"🕒 Vaqt mintaqasi: {timezone_str}", callback_data="settings_timezone"))
    # Row 3: mybots
    builder.row(InlineKeyboardButton(text="📢 mybots", callback_data="settings_mybots"))
    # Row 4: Post Shablonlari
    builder.row(InlineKeyboardButton(text="📂 Post Shablonlari", callback_data="settings_templates"))
    # Row 5: Yangi kanal / guruh
    builder.row(InlineKeyboardButton(text="➕ Yangi kanal / guruh", callback_data="settings_add_channel"))
    
    return builder.as_markup()

def create_settings_interface_keyboard(settings: dict, lang: str = 'uzl', expanded: bool = False):
    """Interfeys sozlamalari menyusi."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📂 Papkalar", callback_data="settings_folders"))
    builder.row(InlineKeyboardButton(text="📢 Kanallar", callback_data="settings_channel_list_conf"))
    builder.row(InlineKeyboardButton(text="📝 Post Tahrirlash", callback_data="settings_post_edit"))
    
    if expanded:
        def get_cb(key):
            return "✅" if settings.get(key) else "⬜️"
            
        builder.row(InlineKeyboardButton(text=f"{get_cb('conf_publish')} Nashrni tasdiqlash", callback_data="set_iface:conf_publish"))
        builder.row(InlineKeyboardButton(text=f"{get_cb('auto_select_chan')} Kanalni avtomatik tanlash", callback_data="set_iface:auto_select_chan"))
        builder.row(InlineKeyboardButton(text=f"{get_cb('hide_bottom_menu')} Pastki menyuni yashirish", callback_data="set_iface:hide_bottom_menu"))
        builder.row(InlineKeyboardButton(text=f"{get_cb('markdown_mode')} Markdown", callback_data="set_iface:markdown_mode"))
        
        builder.row(
            InlineKeyboardButton(text="← Orqaga", callback_data="back_to_settings_main"),
            InlineKeyboardButton(text="Yopish ↑", callback_data="settings_interface_collapse")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="← Orqaga", callback_data="back_to_settings_main"),
            InlineKeyboardButton(text="Ko'proq ↓", callback_data="settings_interface_expand")
        )
    
    return builder.as_markup()

def create_settings_channel_list_conf_keyboard(lang: str = 'uzl'):
    """Kanal ro'yxati sozlamalari."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⇅ Kanal tartibi", callback_data="settings_channel_sort"))
    builder.row(InlineKeyboardButton(text="Sahifadagi kanallar soni: 20", callback_data="settings_channels_per_page"))
    builder.row(InlineKeyboardButton(text="← Orqaga", callback_data="settings_interface"))
    return builder.as_markup()

def create_settings_folders_keyboard(lang: str = 'uzl'):
    """Papkalar sozlamalari."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="← Orqaga", callback_data="settings_interface"))
    return builder.as_markup()

def create_settings_post_edit_keyboard(settings: dict, lang: str = 'uzl'):
    """Post tahrirlash sozlamalari (Checkboxes)."""
    builder = InlineKeyboardBuilder()
    
    # Checkbox logic
    def get_cb(key):
        return "✅" if settings.get(key) else "⬜️"

    options = [
        ("Guruhli tahrirlash", "edit_bulk", "edit_bulk_timer"),
        ("Avto-o'chirish taymeri", "edit_auto_del", "edit_auto_del"),
        ("Mahkamlash", "edit_pin", "edit_silent"),
        ("Ovozni o'chirish", "edit_silent", "edit_silent"),
        ("Himoya qilish", "edit_protect", "edit_reply"),
        ("Javob berish", "edit_reply", "edit_reply"),
        ("Izohlarni o'chirish", "edit_no_comments", "edit_ai"),
        ("AI yordamchisi", "edit_ai", "edit_ai"),
        ("Qayta joylash", "edit_repost", "edit_replace_url"),
        ("Havolani almashtirish", "edit_replace_url", "edit_replace_url"),
        ("Manba krediti", "edit_credit", "edit_restore_tpl"),
        ("Shablonni tiklash", "edit_restore_tpl", "edit_restore_tpl")
    ]
    
    # The image shows 2 columns
    # image_20 shows:
    # Guruhli tahrirlash | Avto-o'chirish taymeri
    # Mahkamlash         | Ovozni o'chirish
    # Himoya qilish      | Javob berish
    # Izohlarni o'chirish| AI yordamchisi
    # Qayta joylash      | Havolani almashtirish
    # Manba krediti      | Shablonni tiklash

    # Let's map them properly
    rows = [
        [("Guruhli tahrirlash", "edit_bulk"), ("Avto-o'chirish taymeri", "edit_auto_del")],
        [("Mahkamlash", "edit_pin"), ("Ovozni o'chirish", "edit_silent")],
        [("Himoya qilish", "edit_protect"), ("Javob berish", "edit_reply")],
        [("Izohlarni o'chirish", "edit_no_comments"), ("AI yordamchisi", "edit_ai")],
        [("Qayta joylash", "edit_repost"), ("Havolani almashtirish", "edit_replace_url")],
        [("Manba krediti", "edit_credit"), ("Shablonni tiklash", "edit_restore_tpl")]
    ]

    for row in rows:
        btn_row = []
        for text, key in row:
            cb = get_cb(key)
            btn_row.append(InlineKeyboardButton(text=f"{cb} {text}", callback_data=f"set_edit:{key}"))
        builder.row(*btn_row)

    builder.row(InlineKeyboardButton(text="← Orqaga", callback_data="settings_interface"))
    return builder.as_markup()

def get_media_settings_inline_kb(lang: str, has_spoiler: bool = False, is_paid: bool = False, show_caption_above: bool = False, has_caption: bool = True, content_type: str = 'photo', paid_price: int = 1):
    """Media sozlamalari uchun inline klaviatura"""
    builder = InlineKeyboardBuilder()

    if has_caption and content_type in ['photo', 'video', 'animation', 'paid_media']:
        position_text = get_text('position_above_btn', lang) if show_caption_above else get_text('position_below_btn', lang)
        builder.button(text=position_text, callback_data="media_toggle_position")

    if content_type in ['photo', 'video', 'animation', 'paid_media']:
        paid_text = get_text('paid_media_enabled_btn', lang) if is_paid else get_text('paid_media_btn', lang)
        builder.button(text=paid_text, callback_data="media_toggle_paid")

    if content_type in ['photo', 'video', 'animation', 'paid_media']:
        if is_paid:
            price_text = get_text('media_price_btn', lang)
            builder.button(text=price_text, callback_data="media_set_price")
        else:
            spoiler_text = get_text('spoiler_enabled_btn', lang) if has_spoiler else get_text('spoiler_btn', lang)
            builder.button(text=spoiler_text, callback_data="media_toggle_spoiler")

    # Layout hisoblash
    rows = []
    if has_caption and content_type in ['photo', 'video', 'animation', 'paid_media']:
        rows.append(1)  # position
    if content_type in ['photo', 'video', 'animation', 'paid_media']:
        rows.append(2)  # paid + spoiler/price
    builder.adjust(*rows)

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
        InlineKeyboardButton(text=get_text('btn_color_green', lang), callback_data="btn_color:success", style="success"),
        InlineKeyboardButton(text=get_text('btn_color_blue', lang), callback_data="btn_color:primary", style="primary"),
        InlineKeyboardButton(text=get_text('btn_color_red', lang), callback_data="btn_color:danger", style="danger")
    )
    return builder.as_markup()

def get_print_settings_keyboard(lang: str = 'uzl', post_code: str = None, print_settings: dict = None):
    """Chop etish sozlamalari uchun inline klaviatura."""
    builder = InlineKeyboardBuilder()
    ps = print_settings or {}
    pc = post_code or 'none'

    # Jimjitlik rejimi
    if ps.get('silent_mode'):
        builder.button(text=get_text('print_silent_enabled_btn', lang), callback_data=f"print:{pc}:silent")
    else:
        builder.button(text=get_text('print_silent_btn', lang), callback_data=f"print:{pc}:silent")

    # Kontent himoyasi
    if ps.get('protect_content'):
        builder.button(text=get_text('print_protect_enabled_btn', lang), callback_data=f"print:{pc}:protect")
    else:
        builder.button(text=get_text('print_protect_btn', lang), callback_data=f"print:{pc}:protect")

    # Avtomatik pin
    if ps.get('auto_pin'):
        builder.button(text=get_text('print_pin_enabled_btn', lang), callback_data=f"print:{pc}:pin")
    else:
        builder.button(text=get_text('print_pin_btn', lang), callback_data=f"print:{pc}:pin")

    # Javob berish (reply)
    reply_text = get_text('print_reply_btn', lang)
    if ps.get('reply_to_message_id'):
        reply_text += " ✅"
    builder.button(text=reply_text, callback_data=f"print:{pc}:reply")

    # Avto o'chirish
    auto_del_text = get_text('print_auto_delete_btn', lang)
    if ps.get('delete_timer_seconds'):
        auto_del_text += " ✅"
    builder.button(text=auto_del_text, callback_data=f"print:{pc}:auto_delete")

    # Izohlar
    if ps.get('comments_enabled'):
        builder.button(text=get_text('print_comments_enabled_btn', lang), callback_data=f"print:{pc}:comments")
    else:
        builder.button(text=get_text('print_comments_btn', lang), callback_data=f"print:{pc}:comments")

    # Orqaga
    builder.button(text=get_text('back_btn', lang), callback_data=f"print:{pc}:back")

    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()

def get_settings_menu_inline_kb(lang: str, content_type: str = 'text'):
    """Asosiy sozlamalar menyusi - kelajakda qo'shimcha sozlamalar uchun"""
    builder = InlineKeyboardBuilder()
    
    # Empty menu - no quiz functionality
    return builder.as_markup()

def get_auto_signature_settings_kb(signature_settings: dict, lang: str = 'uzl'):
    """Avto imzo sozlamalari uchun klaviatura - soddalashtirilgan"""
    builder = InlineKeyboardBuilder()

    enabled = signature_settings.get('enabled', False)

    # Tahrirlash tugmasi
    builder.button(text="✍️ tahrirlash", callback_data="auto_sig_edit_text")

    # Yoqish/o'chirish tugmasi - faqat holatni ko'rsatadi
    if enabled:
        builder.button(text="✅ yoqilgan", callback_data="auto_sig_toggle")
    else:
        builder.button(text="❌ o'chirilgan", callback_data="auto_sig_toggle")

    builder.adjust(2)

    return builder.as_markup()


def get_auto_signature_back_kb(lang: str = 'uzl'):
    """Avto imzo matnini kiritishdan keyin qaytish tugmasi"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 orqaga", callback_data="auto_sig_settings")
    return builder.as_markup()


def get_auto_signature_cancel_kb(lang: str = 'uzl'):
    """Yangi imzo qo'shishni bekor qilish tugmasi"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data="auto_sig_cancel_new")
    return builder.as_markup()
    