from aiogram.utils.keyboard import ReplyKeyboardBuilder, KeyboardButton, InlineKeyboardBuilder, InlineKeyboardButton
from xdata_handlers.translator import get_text

async def get_main_menu(lang: str, user_id: int):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('new_post_btn', lang)))
    builder.add(KeyboardButton(text=get_text('edit_post_btn', lang)))

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_post_settings_kb(content_type: str, has_caption: bool = False, lang: str = 'uzl', is_editing: bool = False, is_paid: bool = False):
    builder = ReplyKeyboardBuilder()

    # Birinchi qator: 4 ta asosiy tugma
    builder.add(KeyboardButton(text=get_text('preview_btn', lang))) # Ko'rish
    builder.add(KeyboardButton(text=get_text('settings_btn', lang))) # Sozlamalar
    builder.add(KeyboardButton(text=get_text('get_buttons_btn', lang))) # Tugma

    # Dinamik tugma (Paid Media / Poll Settings / Location Settings)
    if content_type in ['photo', 'video', 'animation', 'paid_media']:
        paid_text = get_text('paid_media_enabled_btn', lang) if is_paid else get_text('paid_media_btn', lang)
        builder.add(KeyboardButton(text=paid_text))
    elif content_type == 'poll':
        builder.add(KeyboardButton(text=get_text('poll_settings_btn', lang)))
    elif content_type == 'location':
        builder.add(KeyboardButton(text=get_text('location_settings_btn', lang)))
    else:
        # Agar dinamik tugma bo'lmasa, Tahrirlash tugmasini bu yerga chiqaramiz
        builder.add(KeyboardButton(text=get_text('edit_content_btn', lang)))

    # Ikkinchi qator: 2 ta tugma
    # Agar Tahrirlash birinchi qatorda bo'lmasa, uni bu yerga qo'shamiz
    if content_type in ['photo', 'video', 'animation', 'poll', 'location', 'paid_media']:
        builder.add(KeyboardButton(text=get_text('edit_content_btn', lang)))

    # Tayyor / Tasdiqlash
    if is_editing:
        builder.add(KeyboardButton(text=get_text('edit_confirm_btn', lang)))
    else:
        builder.add(KeyboardButton(text=get_text('done_btn', lang)))

    # Bekor qilish tugmasi (oxirida)
    builder.add(KeyboardButton(text=get_text('cancel_btn', lang)))

    # Layout: 4, 3 (chunki Cancel ham bor) - User 4, 2 deganida birinchi qatorda 4 ta bo'lishini nazarda tutgan
    # 7 ta tugma bo'lsa: 4, 2, 1 ko'rinishida chiqadi
    builder.adjust(4, 2, 1)

    return builder.as_markup(resize_keyboard=True)


def get_media_settings_kb(lang: str, has_spoiler: bool = False, show_caption_above: bool = False, has_caption: bool = True, content_type: str = 'photo'):
    """Media sozlamalari uchun klaviatura - faqat 2 ta media sozlamasi va Watermark"""
    builder = ReplyKeyboardBuilder()
    
    # 1. Caption position (Yuqoriga/Pastga)
    if has_caption and content_type in ['photo', 'video', 'animation', 'paid_media']:
        position_text = get_text('position_above_btn', lang) if show_caption_above else get_text('position_below_btn', lang)
        builder.add(KeyboardButton(text=position_text))
    
    # 2. Spoiler
    if content_type in ['photo', 'video', 'animation']:
        spoiler_text = get_text('spoiler_enabled_btn', lang) if has_spoiler else get_text('spoiler_btn', lang)
        builder.add(KeyboardButton(text=spoiler_text))
    
    # 3. Watermark
    builder.add(KeyboardButton(text=get_text('watermark_btn', lang)))
    
    # 4. Orqaga
    builder.add(KeyboardButton(text=get_text('back_btn', lang)))
    
    # Layout: 2, 2
    builder.adjust(2, 2)
        
    return builder.as_markup(resize_keyboard=True)



# Eski get_position_kb funksiyasini o'chiramiz yoki yangi versiyaga almashtiramiz
def get_position_kb(lang: str, current_position: str = 'below'):
    """Joylashuv tugmasi - toggle tugma sifatida"""
    builder = ReplyKeyboardBuilder()
    
    # Faqat bitta joylashuv tugmasi
    if current_position == 'above':
        next_position_text = get_text('position_below_btn', lang)
    else:
        next_position_text = get_text('position_above_btn', lang)
    
    builder.add(KeyboardButton(text=next_position_text))
    builder.add(KeyboardButton(text=get_text('back_btn', lang)))
    
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_post_done_menu(lang: str):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('cr_another_post_btn', lang)))
    builder.add(KeyboardButton(text=get_text('back_btn', lang)))

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_cancel_kb(lang: str):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('cancel_btn', lang)))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_button_creation_cancel_kb(lang: str):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('back_btn', lang)))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_save_cancel_kb(lang: str):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('back_btn', lang)))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_save_cancelled_kb(lang: str):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('cr_another_post_btn', lang)))
    builder.add(KeyboardButton(text=get_text('back_btn', lang)))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_cancel_only_kb(lang: str):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('cancel_btn', lang)))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_button_type_kb(lang: str):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('url_type_btn', lang)))
    builder.add(KeyboardButton(text=get_text('text_type_btn', lang)))
    builder.add(KeyboardButton(text=get_text('reactions_btn', lang)))
    builder.add(KeyboardButton(text=get_text('back_btn', lang)))
    builder.adjust(3, 1)
    return builder.as_markup(resize_keyboard=True)


def get_cancel_reply_kb(lang: str, ai_assistant_enabled: bool = True):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('cancel_btn', lang)))
    if ai_assistant_enabled:
        builder.add(KeyboardButton(text=get_text('ai_assistant_btn', lang)))
        builder.adjust(2)
    else:
        builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def get_edit_content_kb(post_data: dict, lang: str):
    builder = ReplyKeyboardBuilder()
    
    content_type = post_data.get('content_type', 'text')
    has_caption = bool(post_data.get('caption'))
    has_text = bool(post_data.get('text'))

    if content_type != 'text' and has_caption:
        builder.add(KeyboardButton(text=get_text('delete_media_btn', lang)))
        builder.add(KeyboardButton(text=get_text('delete_text_btn', lang)))
    
    builder.add(KeyboardButton(text=get_text('back_btn', lang)))
    
    builder.adjust(2, 1) if (content_type != 'text' and has_caption) else builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_reactions_selection_kb(lang: str):
    builder = ReplyKeyboardBuilder()
    
    # 1. Preset button
    builder.add(KeyboardButton(text="👍 / 👎"))
    
    # 2. Emoji grid
    emojis = [
        "👍", "👎", "❤️", "🔥", "🥰",
        "👏", "😁", "🤔", "🤯", "😱",
        "🤬", "😢", "🎉", "🤩", "🤮",
        "💩", "🙏", "👌", "🕊", "🤡",
        "🥱", "🥴", "😍", "🐳", "❤️‍🔥"
    ]
    
    for emoji in emojis:
        builder.add(KeyboardButton(text=emoji))
        
    # 3. Back button
    builder.add(KeyboardButton(text=get_text('back_btn', lang)))
    
    # Layout: 1 (top), 5x5 (grid), 1 (back)
    builder.adjust(1, 5, 5, 5, 5, 5, 1)
    
    return builder.as_markup(resize_keyboard=True)


def get_watermark_settings_kb(lang: str, is_enabled: bool = False):
    """Watermark sozlamalari uchun klaviatura"""
    builder = ReplyKeyboardBuilder()
    
    # Toggle tugmasi
    if is_enabled:
        toggle_text = get_text('watermark_disable_btn', lang)
    else:
        toggle_text = get_text('watermark_enable_btn', lang)
    builder.add(KeyboardButton(text=toggle_text))
    
    # Matn sozlash
    builder.add(KeyboardButton(text=get_text('watermark_text_btn', lang)))
    
    # Joylashuv
    builder.add(KeyboardButton(text=get_text('watermark_position_btn', lang)))
    
    # Orqaga
    builder.add(KeyboardButton(text=get_text('back_btn', lang)))
    
    builder.adjust(3, 1)
    return builder.as_markup(resize_keyboard=True)
