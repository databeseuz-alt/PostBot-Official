from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder, KeyboardButton
from xdata_handlers.translator import get_text


def get_back_kb(lang: str) -> types.ReplyKeyboardMarkup:
    """"Ortga" tugmasini yaratuvchi funksiya."""
    builder = ReplyKeyboardBuilder()
    builder.button(text=get_text('back_btn', lang))
    return builder.as_markup(resize_keyboard=True)

def get_cancel_kb(lang: str) -> types.ReplyKeyboardMarkup:
    """"Bekor qilish" tugmasini yaratuvchi funksiya."""
    builder = ReplyKeyboardBuilder()
    builder.button(text=get_text('cancel_btn', lang))
    return builder.as_markup(resize_keyboard=True)
