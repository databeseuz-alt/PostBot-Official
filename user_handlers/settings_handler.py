from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import logging

logger = logging.getLogger(__name__)

from xdata_handlers.translator import get_text
from xdata_handlers.database import (
    get_user_language, get_user_bot_settings, update_user_bot_settings
)
from post_handlers.xinline_keyboard import (
    create_settings_main_keyboard, 
    create_settings_interface_keyboard,
    create_settings_channel_list_conf_keyboard,
    create_settings_folders_keyboard,
    create_settings_post_edit_keyboard
)

settings_router = Router()

@settings_router.message(Command("settings"))
async def command_settings_handler(message: types.Message):
    """Asosiy sozlamalar menyusini ko'rsatadi."""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    # Mock timezone for now
    timezone_str = "Tashkent (23:37)" 

    await message.answer(
        get_text('settings_menu_msg', lang),
        reply_markup=create_settings_main_keyboard(lang=lang, timezone_str=timezone_str)
    )

@settings_router.callback_query(F.data == "back_to_settings_main")
async def settings_back_to_main(callback: types.CallbackQuery):
    lang = await get_user_language(callback.from_user.id)
    timezone_str = "Tashkent (23:37)"
    await callback.message.edit_text(
        get_text('settings_menu_msg', lang),
        reply_markup=create_settings_main_keyboard(lang=lang, timezone_str=timezone_str)
    )
    await callback.answer()

@settings_router.callback_query(F.data == "settings_interface")
async def settings_interface_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    settings = await get_user_bot_settings(user_id)
    await callback.message.edit_text(
        get_text('settings_interface_msg', lang),
        reply_markup=create_settings_interface_keyboard(settings, lang=lang, expanded=False)
    )
    await callback.answer()

@settings_router.callback_query(F.data == "settings_interface_expand")
async def settings_interface_expand(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    settings = await get_user_bot_settings(user_id)
    await callback.message.edit_reply_markup(
        reply_markup=create_settings_interface_keyboard(settings, lang=lang, expanded=True)
    )
    await callback.answer()

@settings_router.callback_query(F.data == "settings_interface_collapse")
async def settings_interface_collapse(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    settings = await get_user_bot_settings(user_id)
    await callback.message.edit_reply_markup(
        reply_markup=create_settings_interface_keyboard(settings, lang=lang, expanded=False)
    )
    await callback.answer()

@settings_router.callback_query(F.data.startswith("set_iface:"))
async def settings_toggle_interface_option(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    option_key = callback.data.split(":")[1]
    
    settings = await get_user_bot_settings(user_id)
    current_val = settings.get(option_key, False)
    new_val = not current_val
    
    await update_user_bot_settings(user_id, **{option_key: new_val})
    
    # Refresh keyboard (staying in expanded mode)
    updated_settings = await get_user_bot_settings(user_id)
    await callback.message.edit_reply_markup(
        reply_markup=create_settings_interface_keyboard(updated_settings, lang=lang, expanded=True)
    )
    await callback.answer()

@settings_router.callback_query(F.data == "settings_channel_list_conf")
async def settings_channel_list_conf_menu(callback: types.CallbackQuery):
    lang = await get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        get_text('settings_channel_list_conf_msg', lang),
        reply_markup=create_settings_channel_list_conf_keyboard(lang=lang)
    )
    await callback.answer()

@settings_router.callback_query(F.data == "settings_folders")
async def settings_folders_menu(callback: types.CallbackQuery):
    lang = await get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        get_text('settings_folders_msg', lang),
        reply_markup=create_settings_folders_keyboard(lang=lang)
    )
    await callback.answer()

@settings_router.callback_query(F.data == "settings_post_edit")
async def settings_post_edit_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    settings = await get_user_bot_settings(user_id)
    
    await callback.message.edit_text(
        get_text('settings_post_edit_msg', lang),
        reply_markup=create_settings_post_edit_keyboard(settings, lang=lang)
    )
    await callback.answer()

@settings_router.callback_query(F.data.startswith("set_edit:"))
async def settings_toggle_edit_option(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    option_key = callback.data.split(":")[1]
    
    settings = await get_user_bot_settings(user_id)
    current_val = settings.get(option_key, False)
    new_val = not current_val
    
    await update_user_bot_settings(user_id, **{option_key: new_val})
    
    # Refresh keyboard
    updated_settings = await get_user_bot_settings(user_id)
    await callback.message.edit_reply_markup(
        reply_markup=create_settings_post_edit_keyboard(updated_settings, lang=lang)
    )
    await callback.answer()

@settings_router.callback_query(F.data == "settings_editors")
async def settings_editors_menu(callback: types.CallbackQuery):
    lang = await get_user_language(callback.from_user.id)
    await callback.message.edit_text(get_text('settings_editors_msg', lang), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="← Orqaga", callback_data="back_to_settings_main")]]))
    await callback.answer()

@settings_router.callback_query(F.data == "settings_mybots")
async def settings_mybots_menu(callback: types.CallbackQuery):
    lang = await get_user_language(callback.from_user.id)
    await callback.message.edit_text(get_text('settings_mybots_msg', lang), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="← Orqaga", callback_data="back_to_settings_main")]]))
    await callback.answer()

@settings_router.callback_query(F.data == "settings_templates")
async def settings_templates_menu(callback: types.CallbackQuery):
    lang = await get_user_language(callback.from_user.id)
    await callback.message.edit_text(get_text('settings_templates_msg', lang), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="← Orqaga", callback_data="back_to_settings_main")]]))
    await callback.answer()

@settings_router.callback_query(F.data == "settings_add_channel")
async def settings_add_channel_menu(callback: types.CallbackQuery):
    lang = await get_user_language(callback.from_user.id)
    await callback.message.edit_text(get_text('settings_add_channel_title', lang), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="← Orqaga", callback_data="back_to_settings_main")]]))
    await callback.answer()

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
