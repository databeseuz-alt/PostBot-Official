from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder, KeyboardButton, InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup
from xdata_handlers.translator import get_text

async def get_main_menu(lang: str, user_id: int):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('new_post_btn', lang)))
    builder.add(KeyboardButton(text=get_text('edit_post_btn', lang)))

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_post_settings_kb(content_type: str, has_caption: bool = False, lang: str = 'uzl', is_editing: bool = False, is_paid: bool = False):
    builder = ReplyKeyboardBuilder()

    builder.add(KeyboardButton(text=get_text('preview_btn', lang))) # Ko'rish
    builder.add(KeyboardButton(text=get_text('settings_btn', lang))) # Sozlamalar
    builder.add(KeyboardButton(text=get_text('get_buttons_btn', lang))) # Tugma

    
    builder.add(KeyboardButton(text=get_text('edit_content_btn', lang)))

    # For poll & text: add auto_signature and quiz buttons
    # For location: no auto_signature or quiz
    # For photo/video/paid_media: add auto_signature only if has_caption, always add media_settings and watermark
    # For audio/voice: no media_settings, no quiz
    # For document/animation: add media_settings
    if content_type == 'poll':
        builder.add(KeyboardButton(text=get_text('auto_signature_btn', lang)))
        builder.add(KeyboardButton(text=get_text('quiz_btn', lang)))
    elif content_type == 'text':
        builder.add(KeyboardButton(text=get_text('auto_signature_btn', lang)))
        builder.add(KeyboardButton(text=get_text('quiz_btn', lang)))
    elif content_type in ['photo', 'video', 'paid_media']:
        if has_caption:
            builder.add(KeyboardButton(text=get_text('auto_signature_btn', lang)))
        builder.add(KeyboardButton(text=get_text('media_settings_btn', lang)))
    elif content_type in ['audio', 'voice']:
        # Audio and voice: no media_settings, no quiz
        # With caption: add auto_signature
        if has_caption:
            builder.add(KeyboardButton(text=get_text('auto_signature_btn', lang)))
    elif content_type in ['document', 'animation']:
        # Document and animation: only one button in middle row
        # With caption: auto_signature, without caption: media_settings
        if has_caption:
            builder.add(KeyboardButton(text=get_text('auto_signature_btn', lang)))
        else:
            builder.add(KeyboardButton(text=get_text('media_settings_btn', lang)))

    # Watermark for photo, video, and paid_media only
    if content_type in ['photo', 'video', 'paid_media']:
        builder.add(KeyboardButton(text=get_text('watermark_btn', lang)))

    # Convert button for photo, video, paid_media, sticker and video_note
    if content_type in ['photo', 'video', 'paid_media', 'sticker', 'video_note']:
        builder.add(KeyboardButton(text=get_text('convert_btn', lang)))

    builder.add(KeyboardButton(text=get_text('cancel_btn', lang))) # Bekor qilish

    if is_editing:
        builder.add(KeyboardButton(text=get_text('edit_confirm_btn', lang)))
    else:
        builder.add(KeyboardButton(text=get_text('done_btn', lang))) # Tayyor

    # Adjust layout based on content type
    if content_type == 'poll':
        builder.adjust(4, 2, 2)
    elif content_type == 'location':
        builder.adjust(4, 2)
    elif content_type in ['photo', 'video', 'paid_media']:
        builder.adjust(4, 4, 2)
    elif content_type == 'text':
        builder.adjust(4, 2, 2)
    elif content_type in ['audio', 'voice']:
        builder.adjust(4, 2)
    elif content_type in ['document', 'animation']:
        builder.adjust(4, 1, 2)
    elif content_type == 'dice':
        builder.adjust(4, 2)
    elif content_type in ['sticker', 'video_note']:
        builder.adjust(4, 1, 2)
    else:
        builder.adjust(4, 2, 2)

    return builder.as_markup(resize_keyboard=True)

def get_position_kb(lang: str, current_position: str = 'below'):
    """Joylashuv tugmasi - toggle tugma sifatida"""
    builder = ReplyKeyboardBuilder()

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

def get_single_button_kb(text: str) -> ReplyKeyboardMarkup:
    """Bitta tugmali klaviatura yaratish uchun umumiy funksiya."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=text))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def get_cancel_kb(lang: str):
    """Bekor qilish tugmasi bilan klaviatura."""
    return get_single_button_kb(get_text('cancel_btn', lang))

def get_back_button_kb(lang: str):
    """Orqaga tugmasi bilan klaviatura."""
    return get_single_button_kb(get_text('back_btn', lang))

# Asosiy funksiyalarga aliaslar (mavjud kod bilan moslik uchun)
get_button_creation_cancel_kb = get_back_button_kb
get_save_cancel_kb = get_back_button_kb
get_cancel_only_kb = get_cancel_kb

def get_save_cancelled_kb(lang: str):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('cr_another_post_btn', lang)))
    builder.add(KeyboardButton(text=get_text('back_btn', lang)))
    builder.adjust(2)
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

    # Media types that don't support captions
    media_without_caption = ('video_note', 'sticker', 'location', 'voice', 'dice', 'poll')
    
    # Only show delete buttons if content_type supports caption AND has caption
    if content_type != 'text' and has_caption and content_type not in media_without_caption:
        builder.add(KeyboardButton(text=get_text('delete_media_btn', lang)))
        builder.add(KeyboardButton(text=get_text('delete_text_btn', lang)))

    builder.add(KeyboardButton(text=get_text('back_btn', lang)))

    builder.adjust(2, 1) if (content_type != 'text' and has_caption and content_type not in media_without_caption) else builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def get_reactions_selection_kb(lang: str):
    builder = ReplyKeyboardBuilder()

    builder.add(KeyboardButton(text="👍 / 👎"))

    emojis = [
        "👍", "👎", "❤️", "🔥", "🥰",
        "👏", "😁", "🤔", "🤯", "😱",
        "🤬", "😢", "🎉", "🤩", "🤮",
        "💩", "🙏", "👌", "🕊", "🤡",
        "🥱", "🥴", "😍", "🐳", "❤️‍🔥"
    ]

    for emoji in emojis:
        builder.add(KeyboardButton(text=emoji))

    builder.add(KeyboardButton(text=get_text('back_btn', lang)))

    builder.adjust(1, 5, 5, 5, 5, 5, 1)

    return builder.as_markup(resize_keyboard=True)

def get_watermark_settings_kb(lang: str, is_enabled: bool = False):
    """Watermark sozlamalari uchun klaviatura"""
    builder = ReplyKeyboardBuilder()

    if is_enabled:
        toggle_text = get_text('watermark_disable_btn', lang)
    else:
        toggle_text = get_text('watermark_enable_btn', lang)
    builder.add(KeyboardButton(text=toggle_text))

    builder.add(KeyboardButton(text=get_text('watermark_text_btn', lang)))

    builder.add(KeyboardButton(text=get_text('watermark_position_btn', lang)))

    builder.add(KeyboardButton(text=get_text('back_btn', lang)))

    builder.adjust(3, 1)
    return builder.as_markup(resize_keyboard=True)

def get_quiz_settings_kb(lang: str):
    """Viktorina sozlamalari uchun inline klaviatura"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    # First row: 2 buttons
    builder.add(InlineKeyboardButton(text=get_text('quiz_add_option_btn', lang), callback_data='quiz_add_option'))
    builder.add(InlineKeyboardButton(text=get_text('quiz_correct_answer_btn', lang), callback_data='quiz_correct_answer'))
    
    # Second row: 1 button
    builder.add(InlineKeyboardButton(text=get_text('quiz_anonymous_btn', lang), callback_data='quiz_anonymous'))
    
    builder.adjust(2, 1)
    return builder.as_markup()
