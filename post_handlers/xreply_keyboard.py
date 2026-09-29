from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder, KeyboardButton, InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup
from xdata_handlers.translator import get_text
from post_handlers.custom_emojis import EMOJI_CREATE, EMOJI_CHANNEL, EMOJI_EDIT, clean_btn_text

class AwaitableInlineKeyboardMarkup(types.InlineKeyboardMarkup):
    def __await__(self):
        async def _identity():
            return self
        return _identity().__await__()

def get_main_menu(lang: str, user_id: int = 0):
    builder = InlineKeyboardBuilder()
    builder.button(
        text=clean_btn_text(get_text('new_post_btn', lang)),
        callback_data="main:new_post",
        icon_custom_emoji_id=EMOJI_CREATE
    )
    builder.button(
        text=clean_btn_text(get_text('my_channels_btn', lang)),
        callback_data="main:my_channels",
        icon_custom_emoji_id=EMOJI_CHANNEL
    )
    builder.button(
        text=clean_btn_text(get_text('edit_post_btn', lang)),
        callback_data="main:edit_post",
        icon_custom_emoji_id=EMOJI_EDIT
    )
    builder.button(text=get_text('statistic_btn', lang), callback_data="main:statistic")
    builder.button(text=get_text('schedule_list_btn', lang), callback_data="main:schedule_list")

    builder.adjust(3, 2)
    markup = builder.as_markup()
    return AwaitableInlineKeyboardMarkup(inline_keyboard=markup.inline_keyboard)

def get_post_settings_kb(content_type: str, has_caption: bool = False, lang: str = 'uzl', is_editing: bool = False, is_paid: bool = False):
    builder = ReplyKeyboardBuilder()

    # 1-qator: asosiy tugmalar (4 ta)
    builder.add(KeyboardButton(text=get_text('preview_btn', lang)))  # Ko'rish
    builder.add(KeyboardButton(text=get_text('settings_btn', lang)))  # Sozlamalar
    builder.add(KeyboardButton(text=get_text('get_buttons_btn', lang)))  # Tugma
    builder.add(KeyboardButton(text=get_text('edit_content_btn', lang)))  # Tahrirlash

    # 2-qator: auto_signature, media, watermark, aqlli sozlamalar
    row2_buttons = 0
    
    # auto_signature - text, photo, video, document, audio, voice (agar caption mavjud)
    if content_type in ['text', 'photo', 'video', 'document', 'audio', 'voice']:
        if has_caption or content_type == 'text':
            builder.add(KeyboardButton(text=get_text('auto_signature_btn', lang)))
            row2_buttons += 1
    
    # media_settings - photo, video, animation, paid_media
    if content_type in ['photo', 'video', 'animation', 'paid_media']:
        builder.add(KeyboardButton(text=get_text('media_settings_btn', lang)))
        row2_buttons += 1

    # watermark - faqat photo uchun
    if content_type == 'photo':
        builder.add(KeyboardButton(text=get_text('watermark_btn', lang)))
        row2_buttons += 1
        
    builder.add(KeyboardButton(text="⚙️ Aqlli sozlamalar"))
    row2_buttons += 1
    
    # 3-qator: bekor qilish va tayyor (2 ta)
    builder.add(KeyboardButton(text=get_text('cancel_btn', lang)))
    builder.add(KeyboardButton(text=get_text('done_btn', lang)))

    # Adjust layout: dynamic based on row 2 button count
    if row2_buttons > 0:
        builder.adjust(4, row2_buttons, 2)
    else:
        builder.adjust(4, 2)

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

def get_turbo_done_menu(lang: str):
    builder = ReplyKeyboardBuilder()
    exit_text = get_text('exit_turbo_mode_btn', lang)
    back_text = get_text('back_btn', lang)
    builder.add(KeyboardButton(text=exit_text))
    builder.add(KeyboardButton(text=back_text))
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
    media_without_caption = ('video_note', 'sticker', 'location', 'voice', 'dice')
    
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

