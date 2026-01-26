#--- START OF FILE xreply_keyboard.py ---

from aiogram.utils.keyboard import ReplyKeyboardBuilder, KeyboardButton
from xdata_handlers.translator import get_text
from xdata_handlers.database import get_guide_button_settings

#=============================================================================
# --- K L A V I A T U R A   Y A R A T I SH ---
#=============================================================================

async def get_main_menu(lang: str, user_id: int):
    """Asosiy menyu klaviaturasini shaxsiy sozlamalar bilan yaratadi."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('btn_create_post', lang)))
    builder.add(KeyboardButton(text=get_text('btn_edit_post', lang)))

    guide_settings = await get_guide_button_settings(user_id)
    if guide_settings['globally_enabled'] and guide_settings['user_enabled']:
        builder.add(KeyboardButton(text=get_text('btn_how_to_use', lang)))

    builder.add(KeyboardButton(text=get_text('btn_language_settings', lang)))

    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)


def get_post_settings_kb(content_type: str, has_caption: bool = False, lang: str = 'uzl'):
    """Postni sozlash menyusi klaviaturasini yaratadi."""
    builder = ReplyKeyboardBuilder()

    builder.add(KeyboardButton(text=get_text('btn_preview', lang)))

    # --- Y A N G I   M A N T I Q ---
    # Options tugmasini faqat matn mavjud bo'lganda qo'shamiz
    if content_type == 'text' or has_caption:
        builder.add(KeyboardButton(text=get_text('btn_options', lang)))

    builder.add(KeyboardButton(text=get_text('btn_get_buttons', lang)))
    builder.add(KeyboardButton(text=get_text('btn_edit_content', lang)))
    builder.add(KeyboardButton(text=get_text('btn_cancel_full', lang)))
    builder.add(KeyboardButton(text=get_text('btn_done', lang)))

    # Tugmalar soniga qarab klaviaturani moslashtiramiz
    if content_type == 'text' or has_caption:
        builder.adjust(4, 2) # 6 ta tugma
    else:
        builder.adjust(3, 2) # 5 ta tugma

    return builder.as_markup(resize_keyboard=True)


def get_post_done_menu(lang: str):
    """Post saqlangandan keyingi menyu klaviaturasini yaratadi."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('btn_create_another', lang)))
    builder.add(KeyboardButton(text=get_text('btn_back', lang)))

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_cancel_kb(lang: str):
    """Jarayonni bekor qilish uchun umumiy klaviatura."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('btn_cancel', lang)))
    return builder.as_markup(resize_keyboard=True)


def get_button_creation_cancel_kb(lang: str):
    """Faqat tugma yaratish jarayonini bekor qilish uchun klaviatura."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('btn_back_from_button', lang)))
    return builder.as_markup(resize_keyboard=True)


def get_save_cancel_kb(lang: str):
    """Post saqlash jarayonida bekor qilish uchun ortga tugmasi."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('btn_back_from_save', lang)))
    return builder.as_markup(resize_keyboard=True)


def get_save_cancelled_kb(lang: str):
    """Post saqlash bekor qilinganda ko'rsatiladigan klaviatura."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('btn_create_another', lang)))
    builder.add(KeyboardButton(text=get_text('btn_back', lang)))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_cancel_only_kb(lang: str):
    """Faqat bekor qilish tugmasi."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('btn_cancel', lang)))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

#--- END OF FILE xreply_keyboard.py ---
