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
    
    if content_type == 'poll':
        builder.add(KeyboardButton(text=get_text('poll_settings_btn', lang)))
    elif content_type == 'location':
        builder.add(KeyboardButton(text=get_text('location_settings_btn', lang)))
    else:
        builder.add(KeyboardButton(text=get_text('edit_content_btn', lang)))

    # Ikkinchi qator (faqat poll/location uchun qo'shimcha tahrirlash tugmasi)
    if content_type in ['poll', 'location']:
        builder.add(KeyboardButton(text=get_text('edit_content_btn', lang)))
    
    # Ikkinchi qator: Bekor qilish, Tayyor (tartib: avval bekor qilish, keyin tayyor)
    builder.add(KeyboardButton(text=get_text('cancel_btn', lang))) # Bekor qilish
    
    # Tayyor / Tasdiqlash
    if is_editing:
        builder.add(KeyboardButton(text=get_text('edit_confirm_btn', lang)))
    else:
        builder.add(KeyboardButton(text=get_text('done_btn', lang))) # Tayyor

    # Layout: 4, 2 (4 ta tugma birinchi qatorda, 2 ta tugma ikkinchi qatorda)
    builder.adjust(4, 2)

    return builder.as_markup(resize_keyboard=True)


def get_settings_menu_kb(lang: str):
    """Asosiy sozlamalar menyusi - Media va Watermark tugmalari (adjust 2)"""
    builder = ReplyKeyboardBuilder()
    
    # Media sozlamalari
    builder.add(KeyboardButton(text=get_text('media_settings_btn', lang)))
    
    # Watermark sozlamalari
    builder.add(KeyboardButton(text=get_text('watermark_btn', lang)))
    
    # Layout: 2 (2 ta tugma yonma-yon)
    builder.adjust(2)
    
    return builder.as_markup(resize_keyboard=True)


def get_media_settings_kb(lang: str, has_spoiler: bool = False, show_caption_above: bool = False, has_caption: bool = True, content_type: str = 'photo', is_paid: bool = False):
    """Media sozlamalari uchun klaviatura - layout 1, 2, 1"""
    builder = ReplyKeyboardBuilder()
    
    # 1-qator: Joylashuv (1 ta tugma)
    if has_caption and content_type in ['photo', 'video', 'animation', 'paid_media']:
        position_text = get_text('position_above_btn', lang) if show_caption_above else get_text('position_below_btn', lang)
    else:
        position_text = get_text('position_btn', lang)
    builder.add(KeyboardButton(text=position_text))
    
    # 2-qator: Pulli media va Spoiler (2 ta tugma)
    if content_type in ['photo', 'video', 'animation']:
        spoiler_text = get_text('spoiler_enabled_btn', lang) if has_spoiler else get_text('spoiler_btn', lang)
        builder.add(KeyboardButton(text=spoiler_text))
    
    if content_type in ['photo', 'video', 'animation', 'paid_media']:
        paid_text = get_text('paid_media_enabled_btn', lang) if is_paid else get_text('paid_media_btn', lang)
        builder.add(KeyboardButton(text=paid_text))
    
    # 3-qator: Orqaga (1 ta tugma)
    builder.add(KeyboardButton(text=get_text('back_btn', lang)))
    
    # Layout: 1, 2, 1
    builder.adjust(1, 2, 1)
        
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
