from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from xdata_handlers.translator import get_text
from xdata_handlers.database import (
    get_user_language, get_user_post_settings, update_user_post_settings
)
from post_handlers.xinline_keyboard import get_ai_assistant_keyboard

settings_router = Router()


@settings_router.message(Command("settings"))
async def command_settings_handler(message: types.Message):
    """Asosiy sozlamalar menyusini ko'rsatadi."""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    from post_handlers.xinline_keyboard import create_settings_main_keyboard
    
    await message.answer(
        get_text('settings_menu_msg', lang),
        reply_markup=create_settings_main_keyboard(lang=lang)
    )




@settings_router.callback_query(F.data == "settings_timezone")
async def settings_timezone_menu(callback: types.CallbackQuery):
    lang = await get_user_language(callback.from_user.id)
    text = "🌎 <b>Vaqt mintaqasi</b>\n\nHozirgi vaqt mintaqasi <code>Asia/Tashkent</code> qilib o'rnatilgan."
    
    from post_handlers.xinline_keyboard import create_timezone_keyboard
    await callback.message.edit_text(text, reply_markup=create_timezone_keyboard(lang=lang), parse_mode="HTML")
    await callback.answer()

@settings_router.callback_query(F.data == "change_timezone_alphabet")
async def settings_change_timezone_alphabet(callback: types.CallbackQuery):
    lang = await get_user_language(callback.from_user.id)
    text = "Mamlakat nomi qaysi harf bilan boshlanishini tanlang:"
    
    from post_handlers.xinline_keyboard import create_timezone_alphabet_keyboard
    await callback.message.edit_text(text, reply_markup=create_timezone_alphabet_keyboard(lang=lang))
    await callback.answer()

@settings_router.callback_query(F.data == "back_to_settings_main")
async def settings_back_to_main(callback: types.CallbackQuery):
    lang = await get_user_language(callback.from_user.id)
    from post_handlers.xinline_keyboard import create_settings_main_keyboard
    await callback.message.edit_text(
        get_text('settings_menu_msg', lang),
        reply_markup=create_settings_main_keyboard(lang=lang)
    )
    await callback.answer()


@settings_router.callback_query(F.data == "settings_ai_assistant")
async def settings_ai_assistant_menu(callback: types.CallbackQuery):
    """AI assistant menyusini ko'rsatadi."""
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    user_settings = await get_user_post_settings(user_id)
    is_enabled = user_settings.get('ai_assistant_enabled', False)
    
    await callback.message.edit_text(
        "🤖 <b>AI-assistent sozlamalari</b>",
        reply_markup=get_ai_assistant_keyboard(is_enabled, lang=lang),
        parse_mode="HTML"
    )
    await callback.answer()

@settings_router.callback_query(F.data == "toggle_ai_assistant")
async def settings_toggle_ai_assistant(callback: types.CallbackQuery):
    """AI assistant tugmasini yoqish/o'chirish."""
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    user_settings = await get_user_post_settings(user_id)
    current_state = user_settings.get('ai_assistant_enabled', False)
    new_state = not current_state
    
    await update_user_post_settings(
        user_id=user_id,
        parse_mode='HTML',
        ai_assistant_enabled=new_state
    )
    
    if new_state:
        alert_text = get_text('ai_assistant_alert_msg', lang)
    else:
        alert_text = "AI-assistent o'chirildi."
    
    await callback.answer(alert_text, show_alert=True)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_ai_assistant_keyboard(new_state, lang=lang)
    )


# Watermark sozlamalari olib tashlandi - endi faqat post yaratish menyusida

