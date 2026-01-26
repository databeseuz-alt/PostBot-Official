#--- START OF FILE xinline_keyboard.py ---
from aiogram.utils.keyboard import InlineKeyboardBuilder
from xdata_handlers.translator import get_text
from xdata_handlers.database import get_guide_button_settings
from xdata_handlers import config

# =============================================================================
# --- K L A V I A T U R A   Y A R A T I SH ---
# =============================================================================

# =============================================================================
# SOZLAMALAR BO'LIMI UCHUN
# =============================================================================

async def build_main_settings_keyboard(lang: str, user_id: int):
    """Foydalanuvchi rolidan kelib chiqib, asosiy sozlamalar menyusini yaratadi."""
    builder = InlineKeyboardBuilder()
    if user_id in config.ADMIN_IDS:
        builder.button(text=get_text('btn_manage_visibility', lang), callback_data="settings:manage_visibility")
        builder.button(text=get_text('btn_edit_message', lang), callback_data="settings:edit_content")
        builder.adjust(1)
    else:
        settings = await get_guide_button_settings(user_id)
        if settings['user_enabled']:
            builder.button(text=get_text('btn_hide_guide', lang), callback_data="settings:toggle_user")
        else:
            builder.button(text=get_text('btn_show_guide', lang), callback_data="settings:toggle_user")
    return builder.as_markup()

async def build_visibility_management_keyboard(lang: str, user_id: int):
    """Admin uchun tugma ko'rinishini boshqarish menyusini yaratadi."""
    builder = InlineKeyboardBuilder()
    settings = await get_guide_button_settings(user_id)

    if settings['user_enabled']:
        builder.button(text=get_text('btn_hide_for_self', lang), callback_data="settings:toggle_user")
    else:
        builder.button(text=get_text('btn_show_for_self', lang), callback_data="settings:toggle_user")

    if settings['globally_enabled']:
        builder.button(text=get_text('btn_disable_for_all', lang), callback_data="settings:toggle_global")
    else:
        builder.button(text=get_text('btn_enable_for_all', lang), callback_data="settings:toggle_global")

    builder.button(text=get_text('btn_back', lang), callback_data="settings:back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def build_language_choice_keyboard(lang: str):
    """Admin uchun kontent o'rnatishda til tanlash menyusi."""
    builder = InlineKeyboardBuilder()
    builder.button(text="O'zbekcha 🇺🇿", callback_data="guide_lang:uz")
    builder.button(text="Русский 🇷🇺", callback_data="guide_lang:ru")
    builder.button(text="English 🇬🇧", callback_data="guide_lang:en")
    builder.button(text=get_text('btn_back', lang), callback_data="settings:back_to_main")
    builder.adjust(1)
    return builder.as_markup()

# =============================================================================
# REKLAMA BO'LIMI UCHUN
# =============================================================================

def get_ad_agreement_keyboard(lang: str):
    """Reklama shartlariga rozilik bildirish tugmasini yaratadi."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_accept', lang), callback_data="ad_agreement:accept")
    return builder.as_markup()

def get_reply_to_user_keyboard(user_id: int, lang: str = 'uz'):
    """Adminga yuborilgan reklama murojaati ostidagi javob berish tugmasi."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_reply', lang), callback_data=f"reply_ad:{user_id}")
    return builder.as_markup()

def get_reply_to_admin_keyboard(admin_id: int, lang: str = 'uz'):
    """Foydalanuvchiga kelgan javob ostidagi javob berish tugmasi."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_reply', lang), callback_data=f"reply_ad_to_admin:{admin_id}")
    return builder.as_markup()

# =============================================================================
# FIKR-MULOHAZA BO'LIMI UCHUN
# =============================================================================

def get_feedback_agreement_keyboard(lang: str):
    """Fikr-mulohaza shartlariga rozilik bildirish tugmasini yaratadi."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_accept', lang), callback_data="feedback_agreement:accept")
    return builder.as_markup()

def get_feedback_reply_to_user_keyboard(user_id: int, lang: str = 'uz'):
    """Adminga yuborilgan fikr-mulohaza ostidagi javob berish tugmasi."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_reply', lang), callback_data=f"reply_feedback:{user_id}")
    return builder.as_markup()

def get_feedback_reply_to_admin_keyboard(lang: str = 'uz'):
    """Foydalanuvchiga kelgan javob ostidagi javob berish tugmasi."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_reply', lang), callback_data="reply_feedback_to_admin:start")
    return builder.as_markup()

#--- END OF FILE xinline_keyboard.py ---
