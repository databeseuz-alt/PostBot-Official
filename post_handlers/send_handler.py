#--- START OF FILE send_handler.py ---

import logging
import html
from aiogram import F, Router, types, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramBadRequest

from post_handlers.vpost_states import PostSending
from xdata_handlers.database import (
    get_user_channels, add_user_channel, get_post_from_db, get_user_language
)
from post_handlers.xinline_keyboard import (
    PostSendCallbackFactory, get_channel_list_keyboard,
    get_send_confirmation_keyboard, get_add_channel_prompt_keyboard,
    generate_final_keyboard
)
from post_handlers.start_handler import cmd_start

send_router = Router()

#=============================================================================
# KANAL QO'SHISH JARAYONI (/addchannel)
#=============================================================================

@send_router.message(Command("addchannel"))
async def cmd_add_channel(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(PostSending.waiting_for_channel_info)
    # --- K L A V I A T U R A L A R N I   B O SH Q A R I SH ---
    await message.answer(
        "<b>Kanal qo'shish jarayoni</b>\n\n"
        "1. Botni kerakli kanalga <b>admin</b> qiling.\n"
        "2. Quyidagi usullardan birini bajaring:\n"
        "   - Kanaldan istalgan xabarni shu yerga <b>forward qiling.</b>\n"
        "   - Kanalning <b>@username</b> yoki <b>ID</b>sini yuboring.",
        reply_markup=ReplyKeyboardRemove()
    )

async def _add_channel_to_db(message: types.Message, state: FSMContext, bot: Bot, chat_info: types.Chat):
    """Kanalni tekshiradi va bazaga qo'shish uchun yordamchi funksiya."""
    user_id = message.from_user.id

    if chat_info.type != 'channel':
        return await message.answer("❌ Xatolik: Bu kanal emas.")

    try:
        # 1. Bot kanal a'zosi va admin ekanligini tekshirish
        bot_member = await bot.get_chat_member(chat_info.id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            return await message.answer(f"❌ <b>Xatolik:</b> Men <b>«{html.escape(chat_info.title)}»</b> kanalida admin emasman!")

        # 2. Buyruqni yuborgan foydalanuvchi kanal admini ekanligini tekshirish
        user_member = await bot.get_chat_member(chat_info.id, user_id)
        if user_member.status not in ['administrator', 'creator']:
            return await message.answer(f"❌ <b>Xatolik:</b> Siz <b>«{html.escape(chat_info.title)}»</b> kanalida admin emassiz!")

    except Exception as e:
        logging.error(f"Kanalni tekshirishda xato: {e}")
        error_text = (
            "<b>Nimadir xato ketdi! Koʻp uchraydigan xatolar:</b>\n"
            " • Kanalda bot administrator ekanligini tekshiring.\n"
            " • Kanalda siz administrator emassiz.\n"
            " • Kanal manzili/ID si notoʻgʻri yozilgan\n\n"
            "Agar xato ketmagan bo'lsa texnik yordamga yozing: @ibrakhimov_uz"
        )
        return await message.answer(error_text)

    success = await add_user_channel(
        user_id=user_id,
        channel_id=chat_info.id,
        channel_name=chat_info.title
    )

    if success:
        await state.clear()
        await message.answer(f"✅ <b>{html.escape(chat_info.title)}</b> kanali botga muvaffaqiyatli qo'shildi.")
        await cmd_start(message, state, bot)
    else:
        await message.answer("Bu kanal avval qo'shilgan yoki bazaga yozishda xatolik yuz berdi.")


@send_router.message(PostSending.waiting_for_channel_info, F.forward_from_chat)
async def process_channel_forward(message: types.Message, state: FSMContext, bot: Bot):
    await _add_channel_to_db(message, state, bot, message.forward_from_chat)

@send_router.message(PostSending.waiting_for_channel_info, F.text)
async def process_channel_id_or_username(message: types.Message, state: FSMContext, bot: Bot):
    channel_identifier = message.text
    try:
        chat_info = await bot.get_chat(channel_identifier)
        await _add_channel_to_db(message, state, bot, chat_info)
    except TelegramBadRequest:
        await message.answer(f"❌ <b>Xatolik:</b> '{html.escape(channel_identifier)}' nomli kanal topilmadi. Iltimos, to'g'ri @username yoki ID kiriting.")
    except Exception as e:
        await message.answer(f"❌ Noma'lum xatolik yuz berdi: {e}")

#=============================================================================
# POSTNI KANALGA YUBORISH JARAYONI
#=============================================================================

@send_router.callback_query(PostSendCallbackFactory.filter(F.action == "start_sending"))
async def start_sending_handler(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext):
    await state.clear()
    post_code = callback_data.post_code
    user_id = callback.from_user.id

    user_channels = await get_user_channels(user_id)

    if not user_channels:
        await callback.message.edit_text(
            "Siz hali kanal qo'shmadingiz. Iltimos, post yuborish uchun avval kanal qo'shing!",
            reply_markup=get_add_channel_prompt_keyboard()
        )
        await callback.answer()
        return

    await state.set_state(PostSending.choosing_channel_to_send)

    # --- O'ZGARTIRISH BOSHLANDI ---
    # Keraksiz xabar va reply klaviatura olib tashlandi
    try:
        await callback.message.edit_text(
            "Iltimos, postni yubormoqchi bo'lgan kanalingizni tanlang:",
            reply_markup=get_channel_list_keyboard(user_channels, post_code)
        )
    except TelegramBadRequest:
        # Agar xabarni tahrirlab bo'lmasa (masalan, media bilan bo'lsa), uni o'chirib yangisini yuboramiz
        await callback.message.delete()
        await callback.message.answer(
            "Iltimos, postni yubormoqchi bo'lgan kanalingizni tanlang:",
            reply_markup=get_channel_list_keyboard(user_channels, post_code)
        )
    # --- O'ZGARTIRISH TUGADI ---

    await callback.answer()

@send_router.callback_query(F.data == "add_channel_redirect")
async def redirect_to_add_channel(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await cmd_add_channel(callback.message, state)
    await callback.answer()

@send_router.message(PostSending.choosing_channel_to_send, F.text == "◀️ Ortga qaytish")
async def back_from_sending(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    await cmd_start(message, state, bot)

@send_router.callback_query(PostSending.choosing_channel_to_send, PostSendCallbackFactory.filter(F.action == "select_channel"))
async def select_channel_handler(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext, bot: Bot):
    await state.set_state(PostSending.confirming_post_send)

    channel_name = "Noma'lum"
    try:
        chat_info = await bot.get_chat(callback_data.channel_id)
        channel_name = chat_info.title
    except Exception as e:
        logging.warning(f"Kanal nomini olishda xatolik: {e}")
        # Agar nomini ololmasak, bazadagi nomdan foydalanamiz
        user_channels = await get_user_channels(callback.from_user.id)
        for ch in user_channels:
            if ch['channel_id'] == callback_data.channel_id:
                channel_name = ch['channel_name']
                break

    safe_channel_name = html.escape(channel_name)

    await callback.message.edit_text(
        f"Post <b>{safe_channel_name}</b> kanaliga yuborilsinmi?",
        reply_markup=get_send_confirmation_keyboard(callback_data.post_code, callback_data.channel_id)
    )
    await callback.answer()

@send_router.callback_query(PostSending.confirming_post_send, PostSendCallbackFactory.filter(F.action == "confirm_send"))
async def confirm_send_handler(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, bot: Bot, state: FSMContext):
    post_code = callback_data.post_code
    channel_id = callback_data.channel_id
    lang = await get_user_language(callback.from_user.id)

    full_post = await get_post_from_db(post_code)
    if not full_post:
        await callback.answer("❌ Post topilmadi, ehtimol o'chirilgan.", show_alert=True)
        return

    post_data = full_post.get('post_content', {})
    buttons_matrix = full_post.get('buttons_matrix', [])
    keyboard = generate_final_keyboard(buttons_matrix)

    # --- O'ZGARISH: Parse mode va preview sozlamalarini olish ---
    parse_mode = post_data.get('parse_mode')
    disable_preview = post_data.get('disable_web_page_preview', False)

    try:
        content_type = post_data.get('content_type')
        if content_type == 'text':
            await bot.send_message(
                channel_id,
                post_data.get('text', ''),
                reply_markup=keyboard,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview
            )
        elif content_type == 'photo':
            await bot.send_photo(
                channel_id,
                post_data.get('file_id'),
                caption=post_data.get('caption', ''),
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'video':
            await bot.send_video(
                channel_id,
                post_data.get('file_id'),
                caption=post_data.get('caption', ''),
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'audio':
            await bot.send_audio(
                channel_id,
                post_data.get('file_id'),
                caption=post_data.get('caption', ''),
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'document':
            await bot.send_document(
                channel_id,
                post_data.get('file_id'),
                caption=post_data.get('caption', ''),
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'animation':
            await bot.send_animation(
                channel_id,
                post_data.get('file_id'),
                caption=post_data.get('caption', ''),
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'video_note':
            await bot.send_video_note(
                channel_id,
                post_data.get('file_id'),
                reply_markup=keyboard
            )

        await callback.message.edit_text("✅ Post muvaffaqiyatli yuborildi!")
        await callback.message.answer("Bosh menyu.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        await cmd_start(callback.message, state, bot)

    except Exception as e:
        logging.error(f"Postni ({post_code}) kanalga ({channel_id}) yuborishda xato: {e}")
        await callback.message.edit_text(f"❌ Postni yuborishda xatolik yuz berdi. Bot kanalda admin ekanligini tekshiring.")

    await callback.answer()

#--- END OF FILE send_handler.py ---
