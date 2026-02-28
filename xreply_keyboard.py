from aiogram.utils.keyboard import ReplyKeyboardBuilder, KeyboardButton
from xdata_handlers.translator import get_text


def get_ad_post_settings_kb():
    """Reklama postini sozlash menyusi klaviaturasini yaratadi."""
    builder = ReplyKeyboardBuilder()

    builder.add(KeyboardButton(text="👁️ Ko'rish"))
    builder.add(KeyboardButton(text="🔢 Tugmalar"))
    builder.add(KeyboardButton(text="✏️ Postni tahrirlash"))
    builder.add(KeyboardButton(text="❌ Bekor qilish"))
    builder.add(KeyboardButton(text="✅ Tayyor"))

    builder.adjust(3, 2)
    return builder.as_markup(resize_keyboard=True)


def get_admin_back_kb():
    """Admin panelidagi holatlardan ortga qaytish uchun klaviatura."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Bekor qilish"))
    return builder.as_markup(resize_keyboard=True)

def get_ad_edit_content_kb(has_media_and_text: bool = False):
    """Edit content uchun klaviatura - media va matn birga bo'lsa qo'shimcha tugmalar bilan."""
    builder = ReplyKeyboardBuilder()
    
    if has_media_and_text:
        builder.add(KeyboardButton(text="🗑️ Mediani o'chirish"))
        builder.add(KeyboardButton(text="🗑️ Matnni o'chirish"))
        builder.add(KeyboardButton(text="🔙 Orqaga"))
        builder.adjust(2, 1)
    else:
        builder.add(KeyboardButton(text="🔙 Orqaga"))
    
    return builder.as_markup(resize_keyboard=True)

def get_cancel_kb(lang: str):
    """Jarayonni bekor qilish uchun umumiy klaviatura."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('cancel_btn', lang)))
    return builder.as_markup(resize_keyboard=True)

def get_ad_back_kb():
    """Reklama tugmasini yaratish jarayonidan ortga qaytish uchun klaviatura."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔙 Ortga"))
    return builder.as_markup(resize_keyboard=True)
