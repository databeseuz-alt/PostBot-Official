#--- START OF FILE xreply_keyboard.py ---
from aiogram.utils.keyboard import ReplyKeyboardBuilder, KeyboardButton
from xdata_handlers.translator import get_text

# =============================================================================
# --- K L A V I A T U R A   Y A R A T I SH ---
# =============================================================================

def get_ad_post_settings_kb(web_preview_disabled: bool = False):
    """Reklama postini sozlash menyusi klaviaturasini yaratadi."""
    builder = ReplyKeyboardBuilder()
    preview_text = "Preview: OFF" if web_preview_disabled else "Preview: ON"

    builder.add(KeyboardButton(text="👁️‍🗨️ Preview"))
    builder.add(KeyboardButton(text=preview_text))
    builder.add(KeyboardButton(text="🔡 Get Buttons"))
    builder.add(KeyboardButton(text="✏️ Edit Content"))
    builder.add(KeyboardButton(text="❌ Cancel"))
    builder.add(KeyboardButton(text="✅ Done"))

    builder.adjust(4, 2)
    return builder.as_markup(resize_keyboard=True)


def get_admin_back_kb():
    """Admin panelidagi holatlardan ortga qaytish uchun klaviatura."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="◀️ Ortga (Admin panel)"))
    return builder.as_markup(resize_keyboard=True)

def get_cancel_kb(lang: str):
    """Jarayonni bekor qilish uchun umumiy klaviatura."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('btn_cancel', lang)))
    return builder.as_markup(resize_keyboard=True)

def get_ad_back_kb():
    """Reklama tugmasini yaratish jarayonidan ortga qaytish uchun klaviatura."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="◀️ Ortga"))
    return builder.as_markup(resize_keyboard=True)
#--- END OF FILE xreply_keyboard.py ---
