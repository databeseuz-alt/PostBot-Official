#--- START OF FILE settings_handler.py ---
import logging
from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter

from xdata_handlers.translator import get_text
from post_handlers.vpost_states import PostCreation
from xdata_handlers.database import (
    get_user_language, get_user_post_settings, update_user_post_settings
)
from post_handlers.xinline_keyboard import (
    create_post_options_keyboard, create_post_parse_mode_keyboard,
    create_post_url_preview_keyboard, PostSettingsCallbackFactory
)

settings_router = Router()

# =============================================================================
# /settings BUYRUG'I - OPTIONS MENYUSI
# =============================================================================

@settings_router.message(Command("settings"))
async def command_settings_handler(message: types.Message):
    """Post sozlamalarini ko'rsatadi (OPTIONS)"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    user_settings = await get_user_post_settings(user_id)
    
    current_parse_mode = user_settings.get('parse_mode')
    url_preview_disabled = user_settings.get('url_preview_disabled', False)
    
    keyboard = create_post_options_keyboard(
        content_type='text',
        has_caption=False,
        current_parse_mode=current_parse_mode,
        url_preview_disabled=url_preview_disabled,
        lang=lang
    )
    await message.answer(get_text('post_additions', lang), reply_markup=keyboard)

# =============================================================================
# CALLBACK HANDLERLARI (Settings menyusi uchun - PostCreation state siz)
# =============================================================================

@settings_router.callback_query(PostSettingsCallbackFactory.filter(F.action == "show_parse_mode"), ~StateFilter(PostCreation))
async def settings_show_parse_mode(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    user_settings = await get_user_post_settings(user_id)
    current_mode = user_settings.get('parse_mode')
    
    await callback.message.edit_text(
        get_text('select_text_format', lang),
        reply_markup=create_post_parse_mode_keyboard(current_mode, show_back_button=True, lang=lang)
    )
    await callback.answer()

@settings_router.callback_query(PostSettingsCallbackFactory.filter(F.action == "set_parse_mode"), ~StateFilter(PostCreation))
async def settings_set_parse_mode(callback: types.CallbackQuery, callback_data: PostSettingsCallbackFactory):
    user_id = callback.from_user.id
    clicked_mode = callback_data.value
    lang = await get_user_language(user_id)
    
    user_settings = await get_user_post_settings(user_id)
    current_mode = user_settings.get('parse_mode')
    url_preview_disabled = user_settings.get('url_preview_disabled', False)
    
    # Toggle: agar bir xil bo'lsa, o'chiramiz
    new_mode = None if current_mode == clicked_mode else clicked_mode
    
    await update_user_post_settings(
        user_id=user_id,
        parse_mode=new_mode,
        url_preview_disabled=url_preview_disabled
    )
    
    if new_mode is None:
        await callback.answer(get_text('parse_mode_removed', lang))
    else:
        await callback.answer(get_text('parse_mode_selected', lang).format(mode=new_mode))
    
    await callback.message.edit_reply_markup(
        reply_markup=create_post_parse_mode_keyboard(new_mode, show_back_button=True, lang=lang)
    )

@settings_router.callback_query(PostSettingsCallbackFactory.filter(F.action == "show_url_preview"), ~StateFilter(PostCreation))
async def settings_show_url_preview(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    user_settings = await get_user_post_settings(user_id)
    is_disabled = user_settings.get('url_preview_disabled', False)
    
    await callback.message.edit_text(
        get_text('url_preview_settings', lang),
        reply_markup=create_post_url_preview_keyboard(is_disabled, lang=lang)
    )
    await callback.answer()

@settings_router.callback_query(PostSettingsCallbackFactory.filter(F.action == "set_url_preview"), ~StateFilter(PostCreation))
async def settings_set_url_preview(callback: types.CallbackQuery, callback_data: PostSettingsCallbackFactory):
    user_id = callback.from_user.id
    is_disabled = callback_data.value == "true"
    lang = await get_user_language(user_id)
    
    user_settings = await get_user_post_settings(user_id)
    parse_mode = user_settings.get('parse_mode')
    
    await update_user_post_settings(
        user_id=user_id,
        parse_mode=parse_mode,
        url_preview_disabled=is_disabled
    )
    
    status_text = get_text('url_preview_disabled', lang) if is_disabled else get_text('url_preview_enabled', lang)
    await callback.answer(status_text)
    
    await callback.message.edit_reply_markup(
        reply_markup=create_post_url_preview_keyboard(is_disabled, lang=lang)
    )

@settings_router.callback_query(PostSettingsCallbackFactory.filter(F.action == "back_to_options"), ~StateFilter(PostCreation))
async def settings_back_to_options(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    user_settings = await get_user_post_settings(user_id)
    
    keyboard = create_post_options_keyboard(
        content_type='text',
        has_caption=False,
        current_parse_mode=user_settings.get('parse_mode'),
        url_preview_disabled=user_settings.get('url_preview_disabled', False),
        lang=lang
    )
    await callback.message.edit_text(get_text('post_additions', lang), reply_markup=keyboard)
    await callback.answer()

#--- END OF FILE settings_handler.py ---
