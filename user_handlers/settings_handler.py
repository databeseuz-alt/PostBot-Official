#--- START OF FILE settings_handler.py ---
import logging
from aiogram import F, Router, types, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from admin_handlers.admin_handler import IsAdmin
from xdata_handlers.translator import get_text
from xdata_handlers.database import (
    get_guide_content, get_guide_button_settings, toggle_user_guide_setting,
    set_guide_content, toggle_how_to_use_button, get_user_language
)
from xdata_handlers import config

# Yangi joylashuvlar
from admin_handlers.vadmin_states import AdminGuideSettings
from user_handlers.xinline_keyboard import (
    build_main_settings_keyboard, build_visibility_management_keyboard,
    build_language_choice_keyboard
)

settings_router = Router()

# =============================================================================
# ASOSIY HANDLERLAR ("/settings" va "Qo'llanma")
# =============================================================================

@settings_router.message(Command("settings"))
async def command_settings_handler(message: types.Message):
    # XATOLIK TUZATILDI: Asinxron funksiyalar 'await' bilan chaqirildi
    lang = await get_user_language(message.from_user.id)
    keyboard = await build_main_settings_keyboard(lang, message.from_user.id)
    await message.answer(get_text('settings_menu_title', lang), reply_markup=keyboard)

@settings_router.message(F.text.in_({
    get_text('btn_how_to_use', 'uz'), get_text('btn_how_to_use', 'ru'), get_text('btn_how_to_use', 'en')
}))
async def show_guide_content(message: types.Message):
    # XATOLIK TUZATILDI: Asinxron funksiyalar 'await' bilan chaqirildi
    lang = await get_user_language(message.from_user.id)
    content = await get_guide_content(lang)

    if not content:
        return await message.answer(get_text('guide_not_set_yet', lang))

    try:
        content_type = content.get('content_type')
        text_or_caption = content.get('text_or_caption')
        file_id = content.get('file_id')

        if content_type == 'text':
            await message.answer(text_or_caption)
        elif content_type == 'photo':
            await message.answer_photo(photo=file_id, caption=text_or_caption)
        elif content_type == 'video':
            await message.answer_video(video=file_id, caption=text_or_caption)
    except Exception as e:
        logging.error(f"Yo'riqnoma yuborishda xato: {e}")
        await message.answer(get_text('guide_not_set_yet', lang))

# =============================================================================
# CALLBACK HANDLERLARI (Sozlamalar menyusi uchun)
# =============================================================================

@settings_router.callback_query(F.data == "settings:back_to_main")
async def back_to_main_settings(callback: types.CallbackQuery):
    # XATOLIK TUZATILDI: Asinxron funksiyalar 'await' bilan chaqirildi
    lang = await get_user_language(callback.from_user.id)
    keyboard = await build_main_settings_keyboard(lang, callback.from_user.id)
    await callback.message.edit_text(get_text('settings_menu_title', lang), reply_markup=keyboard)
    await callback.answer()

@settings_router.callback_query(F.data == "settings:manage_visibility", IsAdmin())
async def admin_manage_visibility(callback: types.CallbackQuery):
    # XATOLIK TUZATILDI: Asinxron funksiyalar 'await' bilan chaqirildi
    lang = await get_user_language(callback.from_user.id)
    keyboard = await build_visibility_management_keyboard(lang, callback.from_user.id)
    await callback.message.edit_text("Tugmalar ko'rinishini boshqaring:", reply_markup=keyboard)
    await callback.answer()

@settings_router.callback_query(F.data.in_({"settings:toggle_user", "settings:toggle_global"}))
async def toggle_visibility_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    # XATOLIK TUZATILDI: Asinxron funksiyalar 'await' bilan chaqirildi
    lang = await get_user_language(user_id)
    settings = await get_guide_button_settings(user_id)
    alert_text = ""

    if callback.data == "settings:toggle_user":
        new_status = not settings['user_enabled']
        await toggle_user_guide_setting(user_id, new_status)
        alert_text = get_text('guide_shown', lang) if new_status else get_text('guide_hidden', lang)

    elif callback.data == "settings:toggle_global" and user_id in config.ADMIN_IDS:
        new_status = not settings['globally_enabled']
        await toggle_how_to_use_button(new_status)
        alert_text = get_text('guide_globally_enabled', lang) if new_status else get_text('guide_globally_disabled', lang)

    else:
        return await callback.answer("Error: Ruxsat yo'q!", show_alert=True)

    await callback.answer(alert_text, show_alert=True)

    if user_id in config.ADMIN_IDS:
        # XATOLIK TUZATILDI: Asinxron funksiya 'await' bilan chaqirildi
        keyboard = await build_visibility_management_keyboard(lang, user_id)
    else:
        # XATOLIK TUZATILDI: Asinxron funksiya 'await' bilan chaqirildi
        keyboard = await build_main_settings_keyboard(lang, user_id)
    await callback.message.edit_reply_markup(reply_markup=keyboard)


@settings_router.callback_query(F.data == "settings:edit_content", IsAdmin())
async def admin_edit_content_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminGuideSettings.choosing_language)
    await callback.message.edit_text(
        get_text('guide_admin_prompt', 'uz'),
        reply_markup=build_language_choice_keyboard()
    )
    await callback.answer()

@settings_router.callback_query(F.data.startswith("guide_lang:"), StateFilter(AdminGuideSettings.choosing_language))
async def admin_language_chosen(callback: types.CallbackQuery, state: FSMContext):
    lang_code = callback.data.split(":")[1]
    lang_map = {'uz': "O'zbekcha 🇺🇿", 'ru': "Русский 🇷🇺", 'en': "English 🇬🇧"}

    await state.update_data(chosen_lang=lang_code)
    await state.set_state(AdminGuideSettings.waiting_for_guide_content)

    text = get_text('guide_admin_ask_content', 'uz').format(lang_name=lang_map.get(lang_code, 'Noma\'lum'))
    await callback.message.edit_text(text)
    await callback.answer()

@settings_router.message(StateFilter(AdminGuideSettings.waiting_for_guide_content), F.text | F.photo | F.video)
async def admin_receive_guide_content(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang_code = data.get('chosen_lang')
    if not lang_code:
        await state.clear()
        return await message.answer("Xatolik. Jarayonni /settings orqali qaytadan boshlang.")

    content_type = message.content_type.name.lower()
    text_or_caption = message.html_text
    file_id = None

    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.video:
        file_id = message.video.file_id

    await set_guide_content(lang_code, content_type, text_or_caption, file_id)
    await state.clear()

    lang_map = {'uz': "O'zbekcha 🇺🇿", 'ru': "Русский 🇷🇺", 'en': "English 🇬🇧"}
    lang_name = lang_map.get(lang_code)
    await message.answer(get_text('guide_admin_content_set', 'uz').format(lang_name=lang_name))
#--- END OF FILE settings_handler.py ---
