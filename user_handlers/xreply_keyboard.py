#--- START OF FILE xreply_keyboard.py ---
from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder, KeyboardButton
from xdata_handlers.translator import get_text

# =============================================================================
# --- K L A V I A T U R A   Y A R A T I SH ---
# =============================================================================

def get_back_kb(lang: str) -> types.ReplyKeyboardMarkup:
    """"Ortga" tugmasini yaratuvchi funksiya."""
    builder = ReplyKeyboardBuilder()
    builder.button(text=get_text('btn_back', lang))
    return builder.as_markup(resize_keyboard=True)

def get_cancel_kb(lang: str) -> types.ReplyKeyboardMarkup:
    """"Bekor qilish" tugmasini yaratuvchi funksiya."""
    builder = ReplyKeyboardBuilder()
    builder.button(text=get_text('btn_cancel', lang))
    return builder.as_markup(resize_keyboard=True)
#--- END OF FILE xreply_keyboard.py ---
