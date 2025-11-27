#--- START OF FILE done_handler.py ---

import logging
from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from post_handlers.vpost_states import PostCreation
from post_handlers.xreply_keyboard import get_post_done_menu, get_cancel_kb
from post_handlers.xinline_keyboard import get_post_management_keyboard
from xdata_handlers.database import (
    add_post_to_db, update_post_in_db, get_user_language, save_post_name
)
from admin_handlers.channel_handler import check_user_membership
from post_handlers.start_handler import start_post_creation, cmd_start
from xdata_handlers.translator import get_text
from xdata_handlers import config
from post_handlers.localize_filter import LocalizedText

done_router = Router()

#=============================================================================
# POST YARATISHNI YAKUNLASH HANDLERI
#=============================================================================

@done_router.message(PostCreation.configuring_post, LocalizedText('btn_done'))
async def done_post_creation(message: types.Message, state: FSMContext, bot: Bot):
    is_member, check_text, check_keyboard = await check_user_membership(message.from_user, bot)
    if not is_member:
        await state.clear()
        await message.answer(
            "Bu amalni bajarish uchun avval kanalga a'zo bo'lishingiz kerak. Amal bekor qilindi.",
            reply_markup=ReplyKeyboardRemove()
        )
        await message.answer(check_text, reply_markup=check_keyboard)
        return

    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})
    buttons_matrix = data.get("buttons_matrix", [])

    if not post_data:
        return await message.answer(get_text('save_error', lang))

    editing_post_code = data.get("editing_post_code")
    if editing_post_code:
        success = await update_post_in_db(editing_post_code, post_data, buttons_matrix)
        post_code_for_user = editing_post_code if success else None
        final_text_key = 'post_updated_final'
    else:
        post_code_for_user = await add_post_to_db(
            message.from_user.id,
            post_data,
            buttons_matrix,
            admin_ids=config.ADMIN_IDS
        )
        final_text_key = 'post_saved'

    if not post_code_for_user:
        return await message.answer(get_text('save_error', lang))

    bot_info = await bot.get_me()
    inline_usage_text = f"@{bot_info.username} {post_code_for_user}"
    raw_message_text = get_text(final_text_key, lang)
    final_message = raw_message_text.format(
        post_code=f"<code>{post_code_for_user}</code>",
        bot_username=f"<code>{inline_usage_text}</code>"
    )

    # --- K L A V I A T U R A L A R N I   B O SH Q A R I SH ---
    reply_kb = get_post_done_menu(lang)
    inline_kb = get_post_management_keyboard(post_code_for_user)

    await state.clear()
    await message.answer("Amal yakunlandi.", reply_markup=reply_kb)
    await message.answer(
        final_message,
        reply_markup=inline_kb,
        parse_mode="HTML"
    )

#=============================================================================
# POSTNI NOMLAB SAQLASH HANDLERLARI
#=============================================================================

@done_router.callback_query(F.data.startswith("save_post:"))
async def save_post_prompt(callback: types.CallbackQuery, state: FSMContext):
    post_code = callback.data.split(":")[1]
    lang = await get_user_language(callback.from_user.id)

    await state.set_state(PostCreation.waiting_for_post_name)
    await state.update_data(post_code_to_save=post_code)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Postingizni saqlash uchun nom yozing:",
        reply_markup=get_cancel_kb(lang)
    )
    await callback.answer()


@done_router.message(PostCreation.waiting_for_post_name, F.text)
async def save_post_name_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    post_code = data.get("post_code_to_save")
    post_name = message.text

    if not post_code:
        await state.clear()
        return

    success = await save_post_name(post_code, post_name)

    if success:
        await message.answer(
            "✅ Post saqlandi, uni tahrirlash bo'limidan topishingiz mumkin.",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.answer(
            "❌ Post nomini saqlashda xatolik yuz berdi.",
            reply_markup=ReplyKeyboardRemove()
        )

    await state.clear()
    await cmd_start(message, state, message.bot)

#=============================================================================
# YAKUNIY MENYU HANDLERLARI
#=============================================================================

@done_router.message(LocalizedText('btn_create_another'))
async def create_another_post_handler(message: types.Message, state: FSMContext, bot: Bot):
    await start_post_creation(message, state, bot)

@done_router.message(LocalizedText('btn_back'))
async def back_to_main_menu_handler(message: types.Message, state: FSMContext, bot: Bot):
    await cmd_start(message, state, bot)

#--- END OF FILE done_handler.py ---
