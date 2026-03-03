"""
Avto Imzo (Auto Signature) handler'lari
Foydalanuvchilar uchun avtomatik imzo funksiyasi
"""

from aiogram import Router, F, types
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from xdata_handlers.translator import get_text
from xdata_handlers.database import (
    get_user_auto_signature,
    toggle_auto_signature,
    update_auto_signature_text,
    update_auto_signature_position,
    toggle_auto_signature_newline
)
from post_handlers.xinline_keyboard import (
    get_auto_signature_settings_kb,
    get_auto_signature_back_kb,
    create_settings_main_keyboard
)

router = Router()


class AutoSignatureState(StatesGroup):
    """Avto imzo matnini kiritish uchun state"""
    enter_text = State()


def _normalize_lang(lang_code: str) -> str:
    """Til kodini normalize qiladi"""
    if not lang_code:
        return 'uzl'
    lang = lang_code[:2].lower()
    valid_langs = ['uz', 'ru', 'en', 'ar', 'az', 'de', 'es', 'fr', 'it', 'kg', 'kz', 'tj', 'tk', 'tr']
    if lang not in valid_langs:
        return 'uzl'
    return 'uzl' if lang == 'uz' else lang


def _build_settings_text(settings: dict, lang: str) -> str:
    """Sozlamalar matnini yaratadi"""
    enabled_text = "✅ Yoniq" if settings['enabled'] else "❌ Ochiq"
    position_text = "Post yuqorisida" if settings['position'] == 'top' else "Post pastida"
    newline_text = "✅ Ha" if settings['newline'] else "❌ Yo'q"
    
    text = get_text('auto_signature_title', lang)
    text += f"\n\n{get_text('auto_signature_info', lang)}"
    text += f"\n\n<b>Imzo:</b> {settings['text'] or '—'}"
    text += f"\n<b>Holat:</b> {enabled_text}"
    text += f"\n<b>Joylashuv:</b> {position_text}"
    text += f"\n<b>Yangi qator:</b> {newline_text}"
    return text


@router.callback_query(F.data == "auto_sig_settings")
async def show_auto_signature_settings(callback: CallbackQuery):
    """Avto imzo sozlamalari menyusini ko'rsatadi"""
    lang = _normalize_lang(callback.from_user.language_code)
    user_id = callback.from_user.id
    
    # Foydalanuvchi sozlamalarini olish
    settings = await get_user_auto_signature(user_id)
    
    # Xabar matnini yaratish
    text = _build_settings_text(settings, lang)
    
    # Klaviaturani olish
    keyboard = get_auto_signature_settings_kb(settings, lang)
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        # Agar tahrirlash mumkin bo'lmasa, yangi xabar yuborish
        await callback.message.answer(text, reply_markup=keyboard)
    
    await callback.answer()


@router.callback_query(F.data == "auto_sig_toggle")
async def toggle_auto_signature_handler(callback: CallbackQuery):
    """Avto imzoni yoqish/o'chirish"""
    lang = _normalize_lang(callback.from_user.language_code)
    user_id = callback.from_user.id
    
    # Holatni o'zgartirish
    new_state = await toggle_auto_signature(user_id)
    
    # Yangilangan sozlamalarni olish
    settings = await get_user_auto_signature(user_id)
    
    # Xabar matnini yangilash
    text = _build_settings_text(settings, lang)
    keyboard = get_auto_signature_settings_kb(settings, lang)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    
    # Alert ko'rsatish
    if new_state:
        await callback.answer(get_text('auto_signature_enabled', lang))
    else:
        await callback.answer(get_text('auto_signature_disabled', lang))


@router.callback_query(F.data == "auto_sig_edit_text")
async def start_edit_signature_text(callback: CallbackQuery, state: FSMContext):
    """Imzo matnini o'zgartirishni boshlaydi"""
    lang = _normalize_lang(callback.from_user.language_code)
    
    # State'ga o'tish
    await state.set_state(AutoSignatureState.enter_text)
    
    text = get_text('auto_signature_enter_text', lang)
    keyboard = get_auto_signature_back_kb(lang)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.message(AutoSignatureState.enter_text)
async def save_signature_text(message: Message, state: FSMContext):
    """Foydalanuvchi kiritgan imzo matnini saqlaydi"""
    lang = _normalize_lang(message.from_user.language_code)
    
    user_id = message.from_user.id
    text = message.text
    
    # Matnni saqlash
    await update_auto_signature_text(user_id, text)
    
    # State'ni tozalash
    await state.clear()
    
    # Yangilangan sozlamalarni olish
    settings = await get_user_auto_signature(user_id)
    
    # Xabar matnini yaratish
    response_text = _build_settings_text(settings, lang)
    keyboard = get_auto_signature_settings_kb(settings, lang)
    
    await message.answer(response_text, reply_markup=keyboard)
    
    # Saqlanganligi haqida xabar
    await message.answer(get_text('auto_signature_text_saved', lang))


@router.callback_query(F.data == "auto_sig_position")
async def change_signature_position(callback: CallbackQuery):
    """Imzo joylashuvini o'zgartirish (top <-> bottom)"""
    lang = _normalize_lang(callback.from_user.language_code)
    user_id = callback.from_user.id
    
    # Hozirgi sozlamalarni olish
    settings = await get_user_auto_signature(user_id)
    
    # Joylashuvni o'zgartirish
    new_position = 'bottom' if settings['position'] == 'top' else 'top'
    await update_auto_signature_position(user_id, new_position)
    
    # Yangilangan sozlamalarni olish
    settings = await get_user_auto_signature(user_id)
    
    # Xabar matnini yangilash
    text = _build_settings_text(settings, lang)
    keyboard = get_auto_signature_settings_kb(settings, lang)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer(get_text('auto_signature_position_saved', lang))


@router.callback_query(F.data == "auto_sig_newline")
async def toggle_newline_setting(callback: CallbackQuery):
    """Yangi qator sozlamasini o'zgartirish"""
    lang = _normalize_lang(callback.from_user.language_code)
    user_id = callback.from_user.id
    
    # Sozlamani o'zgartirish
    new_state = await toggle_auto_signature_newline(user_id)
    
    # Yangilangan sozlamalarni olish
    settings = await get_user_auto_signature(user_id)
    
    # Xabar matnini yangilash
    text = _build_settings_text(settings, lang)
    keyboard = get_auto_signature_settings_kb(settings, lang)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    
    # Alert ko'rsatish
    if new_state:
        await callback.answer(get_text('auto_signature_newline_enabled', lang))
    else:
        await callback.answer(get_text('auto_signature_newline_disabled', lang))


@router.callback_query(F.data == "settings_back")
async def back_to_settings(callback: CallbackQuery):
    """Asosiy sozlamalar menyusiga qaytish"""
    lang = _normalize_lang(callback.from_user.language_code)
    
    keyboard = create_settings_main_keyboard(lang)
    
    await callback.message.edit_text(
        get_text('settings_menu_msg', lang),
        reply_markup=keyboard
    )
    await callback.answer()