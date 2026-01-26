#--- START OF FILE post_handlers/done_handler.py ---

import logging
from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from post_handlers.vpost_states import PostCreation
from post_handlers.xreply_keyboard import get_post_done_menu, get_save_cancel_kb, get_save_cancelled_kb
from post_handlers.xinline_keyboard import get_post_management_keyboard, SavePostCallbackFactory, get_post_save_edit_keyboard
from xdata_handlers.database import (
    add_post_to_db, update_post_in_db, get_user_language, save_post_name, unsave_post_name
)
from admin_handlers.channel_handler import check_user_membership
from post_handlers.start_handler import start_post_creation, cmd_start
from xdata_handlers.translator import get_text
from xdata_handlers import config
from post_handlers.localize_filter import LocalizedText

done_router = Router()

#=============================================================================
# --- POST YARATISHNI YAKUNLASH HANDLERI ---
#=============================================================================

@done_router.message(PostCreation.configuring_post, LocalizedText('btn_done'))
async def done_post_creation(message: types.Message, state: FSMContext, bot: Bot):
    lang = await get_user_language(message.from_user.id)
    is_member, check_text, check_keyboard = await check_user_membership(message.from_user, bot)

    if not is_member:
        await state.clear()
        await message.answer(
            get_text('join_channel_to_continue', lang),
            reply_markup=ReplyKeyboardRemove()
        )
        await message.answer(check_text, reply_markup=check_keyboard)
        return
    data = await state.get_data()
    post_data = data.get("post_data", {})
    buttons_matrix = data.get("buttons_matrix", [])

    if not post_data:
        return await message.answer(get_text('save_error', lang))

    editing_post_code = data.get("editing_post_code")
    if editing_post_code:
        success = await update_post_in_db(editing_post_code, post_data, buttons_matrix)
        post_code_for_user = editing_post_code if success else None
    else:
        post_code_for_user = await add_post_to_db(
            message.from_user.id,
            post_data,
            buttons_matrix,
            admin_ids=config.ADMIN_IDS
        )

    if not post_code_for_user:
        return await message.answer(get_text('save_error', lang))

    # Bot usernameni olish
    bot_info = await bot.get_me()
    bot_username = bot_info.username

    # Xabar matni o'zgartirildi (To'liq format: Kod + Yo'riqnoma)
    final_message = get_text('post_inline_usage', lang).format(
        post_code=post_code_for_user,
        bot_username=bot_username
    )

    # --- K L A V I A T U R A L A R N I   B O SH Q A R I SH ---
    reply_kb = get_post_done_menu(lang)
    # Yangilangan (agar nom bo'lsa Tahrirlash, bo'lmasa Saqlash chiqadi)
    inline_kb = await get_post_management_keyboard(post_code_for_user)

    await state.clear()
    await message.answer(get_text('post_saved_to_db', lang), reply_markup=reply_kb)
    await message.answer(
        final_message,
        reply_markup=inline_kb,
        parse_mode="HTML"
    )

#=============================================================================
# --- POSTNI NOMLAB SAQLASH HANDLERLARI (BOSHIDAN SAQLASH) ---
#=============================================================================

@done_router.callback_query(SavePostCallbackFactory.filter(F.action == "start_save"))
async def save_post_prompt(callback: types.CallbackQuery, callback_data: SavePostCallbackFactory, state: FSMContext):
    post_code = callback_data.post_code
    lang = await get_user_language(callback.from_user.id)

    await state.set_state(PostCreation.waiting_for_post_name)
    
    await state.update_data(
        post_code_to_save=post_code,
        original_post_msg_id=callback.message.message_id,
        original_post_chat_id=callback.message.chat.id
    )

    await callback.message.answer(
        get_text('enter_post_name_to_save', lang),
        reply_markup=get_save_cancel_kb(lang)
    )
    await callback.answer()

#=============================================================================
# --- TAHRIRLASH (EDIT SAVE) MENYUSI ---
#=============================================================================

@done_router.callback_query(SavePostCallbackFactory.filter(F.action == "edit_save_menu"))
async def show_edit_save_menu(callback: types.CallbackQuery, callback_data: SavePostCallbackFactory):
    """'Tahrirlash' bosilganda [Qayta nomlash][O'chirish] menyusini chiqaradi."""
    post_code = callback_data.post_code
    
    lang = await get_user_language(callback.from_user.id)
    await callback.message.answer(
        get_text('edit_save_prompt', lang),
        reply_markup=get_post_save_edit_keyboard(post_code, lang)
    )
    await callback.answer()

@done_router.callback_query(SavePostCallbackFactory.filter(F.action == "delete_name"))
async def delete_post_name_handler(callback: types.CallbackQuery, callback_data: SavePostCallbackFactory, state: FSMContext):
    """'O'chirish' bosilganda nomni o'chiradi va yana 'Saqlash' holatiga qaytaradi."""
    post_code = callback_data.post_code
    user_id = callback.from_user.id
    
    # Bazadan nomni o'chirish
    await unsave_post_name(post_code, user_id)
    
    # Xabarni o'chiramiz (tahrirlash menyusini)
    try:
        await callback.message.delete()
    except: pass
    
    lang = await get_user_language(user_id)
    await callback.message.answer(get_text('saved_name_deleted', lang))
    
    # Qayta post kodini chiqarish (Saqlash tugmasi bilan)
    inline_kb = await get_post_management_keyboard(post_code)
    final_message = get_text('post_inline_usage', lang).format(
        post_code=post_code,
        bot_username=(await callback.bot.get_me()).username
    )
    
    await callback.message.answer(final_message, reply_markup=inline_kb, parse_mode="HTML")
    await callback.answer()

@done_router.callback_query(SavePostCallbackFactory.filter(F.action == "rename"))
async def rename_post_prompt(callback: types.CallbackQuery, callback_data: SavePostCallbackFactory, state: FSMContext):
    """'Qayta nomlash' bosilganda yangi nom so'raydi."""
    post_code = callback_data.post_code
    lang = await get_user_language(callback.from_user.id)
    
    # Xabarni o'chiramiz
    try:
        await callback.message.delete()
    except: pass

    await state.set_state(PostCreation.waiting_for_rename)
    await state.update_data(rename_post_code=post_code)
    
    await callback.message.answer(get_text('enter_new_name', lang), reply_markup=get_save_cancel_kb(lang))
    await callback.answer()

@done_router.message(PostCreation.waiting_for_rename, F.text)
async def process_rename_post(message: types.Message, state: FSMContext):
    """Yangi nomni qabul qiladi va yangilaydi."""
    data = await state.get_data()
    post_code = data.get('rename_post_code')
    new_name = message.text
    lang = await get_user_language(message.from_user.id) # Tilni aniqlaymiz
    
    if not post_code:
        await state.clear()
        return

    # Bazada nomni yangilash
    await save_post_name(post_code, new_name)
    
    # MUHIM O'ZGARISH: reply_markup qo'shildi
    await message.answer(get_text('post_renamed', lang), reply_markup=get_post_done_menu(lang))
    
    # Qayta post kodini chiqarish (Tahrirlash tugmasi bilan)
    inline_kb = await get_post_management_keyboard(post_code)
    final_message = get_text('post_inline_usage', lang).format(
        post_code=post_code,
        bot_username=(await message.bot.get_me()).username
    )
    
    await message.answer(final_message, reply_markup=inline_kb, parse_mode="HTML")
    await state.clear()

#=============================================================================
# --- UMUMIY BEKOR QILISH VA SAQLASH MANTIQI ---
#=============================================================================

@done_router.message(PostCreation.waiting_for_post_name, LocalizedText('btn_back_from_save'))
async def cancel_save_post(message: types.Message, state: FSMContext, bot: Bot):
    """Post saqlash jarayonini bekor qilish."""
    data = await state.get_data()
    lang = await get_user_language(message.from_user.id)
    post_code = data.get("post_code_to_save")
    
    original_msg_id = data.get('original_post_msg_id')
    original_chat_id = data.get('original_post_chat_id')
    
    if original_msg_id and original_chat_id:
        try:
            await bot.delete_message(original_chat_id, original_msg_id)
        except Exception:
            pass
    
    await state.clear()
    
    await message.answer(
        get_text('save_cancelled', lang),
        reply_markup=get_save_cancelled_kb(lang)
    )
    
    if post_code:
        final_message = get_text('post_inline_usage', lang).format(
            post_code=post_code,
            bot_username=(await bot.get_me()).username
        )
        inline_kb = await get_post_management_keyboard(post_code)
        
        await message.answer(
            final_message,
            reply_markup=inline_kb,
            parse_mode="HTML"
        )

@done_router.message(PostCreation.waiting_for_rename, LocalizedText('btn_back_from_save'))
async def cancel_rename_post(message: types.Message, state: FSMContext):
    """Qayta nomlashni bekor qilish."""
    data = await state.get_data()
    post_code = data.get('rename_post_code')
    lang = await get_user_language(message.from_user.id) # Tilni aniqlaymiz
    
    # MUHIM O'ZGARISH: reply_markup qo'shildi
    await message.answer(get_text('rename_canceled', lang), reply_markup=get_post_done_menu(lang))
    
    if post_code:
        inline_kb = await get_post_management_keyboard(post_code)
        final_message = get_text('post_inline_usage', lang).format(
            post_code=post_code,
            bot_username=(await message.bot.get_me()).username
        )
        await message.answer(final_message, reply_markup=inline_kb, parse_mode="HTML")
        
    await state.clear()

@done_router.message(PostCreation.waiting_for_post_name, F.text)
async def save_post_name_received(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    post_code = data.get("post_code_to_save")
    post_name = message.text
    lang = await get_user_language(message.from_user.id)
    
    original_msg_id = data.get('original_post_msg_id')
    original_chat_id = data.get('original_post_chat_id')
    
    if original_msg_id and original_chat_id:
        try:
            await bot.delete_message(original_chat_id, original_msg_id)
        except Exception:
            pass

    if not post_code:
        await state.clear()
        return

    success = await save_post_name(post_code, post_name)

    if success:
        await message.answer(
            get_text('post_saved_success', lang),
            reply_markup=get_post_done_menu(lang)
        )
    else:
        await message.answer(
            get_text('post_save_error', lang),
            reply_markup=get_post_done_menu(lang)
        )
        
    final_message = get_text('post_inline_usage', lang).format(
        post_code=post_code,
        bot_username=(await bot.get_me()).username
    )
    # Endi bu yerda Tahrirlash tugmasi chiqadi (chunki nom saqlandi)
    inline_kb = await get_post_management_keyboard(post_code)
    
    await message.answer(
        final_message,
        reply_markup=inline_kb,
        parse_mode="HTML"
    )

    await state.clear()

#=============================================================================
# --- YAKUNIY MENYU HANDLERLARI ---
#=============================================================================

@done_router.message(LocalizedText('btn_create_another'))
async def create_another_post_handler(message: types.Message, state: FSMContext, bot: Bot):
    await start_post_creation(message, state, bot)

@done_router.message(LocalizedText('btn_back'))
async def back_to_main_menu_handler(message: types.Message, state: FSMContext, bot: Bot):
    await cmd_start(message, state, bot)

#--- END OF FILE post_handlers/done_handler.py ---
