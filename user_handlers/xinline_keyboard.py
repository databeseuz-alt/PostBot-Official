from aiogram.utils.keyboard import InlineKeyboardBuilder
from xdata_handlers.translator import get_text
from xdata_handlers import config



async def build_main_settings_keyboard(lang: str, user_id: int):
    """Foydalanuvchi rolidan kelib chiqib, asosiy sozlamalar menyusini yaratadi."""
    builder = InlineKeyboardBuilder()
    if user_id in config.ADMIN_IDS:
        builder.button(text="⚙️ Tugmani Boshqarish", callback_data="settings:manage_visibility")
        builder.button(text="📝 Xabarni Tahrirlash", callback_data="settings:edit_content")
        builder.adjust(1)
    return builder.as_markup()





def get_reply_to_user_keyboard(user_id: int, lang: str = 'uzl'):
    """Adminga yuborilgan reklama murojaati ostidagi javob berish tugmasi."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('reply_btn', lang), callback_data=f"reply_ad:{user_id}")
    return builder.as_markup()

def get_reply_to_admin_keyboard(admin_id: int, lang: str = 'uzl'):
    """Foydalanuvchiga kelgan javob ostidagi javob berish tugmasi."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('reply_btn', lang), callback_data=f"reply_ad_to_admin:{admin_id}")
    return builder.as_markup()



def get_feedback_reply_to_user_keyboard(user_id: int, lang: str = 'uzl'):
    """Adminga yuborilgan fikr-mulohaza ostidagi javob berish tugmasi."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('reply_btn', lang), callback_data=f"reply_feedback:{user_id}")
    return builder.as_markup()

def get_feedback_reply_to_admin_keyboard(lang: str = 'uzl'):
    """Foydalanuvchiga kelgan javob ostidagi javob berish tugmasi."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('reply_btn', lang), callback_data="reply_feedback_to_admin:start")
    return builder.as_markup()

