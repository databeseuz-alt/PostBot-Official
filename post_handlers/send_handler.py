#--- START OF FILE post_handlers/send_handler.py ---

import logging
import html
import asyncio
from contextlib import suppress
from aiogram import F, Router, types, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

from post_handlers.vpost_states import PostSending
from xdata_handlers.database import (
    get_user_channels, add_user_channel, get_post_from_db, get_user_language
)
from post_handlers.xinline_keyboard import (
    PostSendCallbackFactory, get_channel_list_keyboard,
    get_send_confirmation_keyboard, get_add_channel_prompt_keyboard,
    generate_final_keyboard, get_add_channel_with_post_keyboard,
    get_post_management_keyboard
)
from post_handlers.start_handler import cmd_start
from xdata_handlers.translator import get_text
from post_handlers.xreply_keyboard import get_post_done_menu, get_save_cancel_kb, get_save_cancelled_kb, get_cancel_only_kb
from post_handlers.localize_filter import LocalizedText

send_router = Router()

#==================================================
# --- KANAL QO'SHISH JARAYONI (/addchannel) ---
#==================================================

@send_router.message(Command("addchannel"))
async def cmd_add_channel(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(PostSending.waiting_for_channel_info)
    lang = await get_user_language(message.from_user.id)
    # --- K L A V I A T U R A L A R N I   B O SH Q A R I SH ---
    await message.answer(
        get_text('add_channel_title', lang),
        reply_markup=ReplyKeyboardRemove()
    )

async def _add_channel_to_db(message: types.Message, state: FSMContext, bot: Bot, chat_info: types.Chat):
    """Kanalni tekshiradi va bazaga qo'shish uchun yordamchi funksiya."""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)

    if chat_info.type != 'channel':
        return await message.answer(get_text('add_channel_not_channel', lang))

    try:
        # 1. Bot kanal a'zosi va admin ekanligini tekshirish
        bot_member = await bot.get_chat_member(chat_info.id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            return await message.answer(get_text('add_channel_bot_not_admin', lang).format(channel_name=html.escape(chat_info.title)))

        # 2. Buyruqni yuborgan foydalanuvchi kanal admini ekanligini tekshirish
        user_member = await bot.get_chat_member(chat_info.id, user_id)
        if user_member.status not in ['administrator', 'creator']:
            return await message.answer(get_text('add_channel_user_not_admin', lang).format(channel_name=html.escape(chat_info.title)))

    except Exception as e:
        logging.error(f"Kanalni tekshirishda xato: {e}")
        error_text = get_text('add_channel_error', lang)
        return await message.answer(error_text)

    success = await add_user_channel(
        user_id=user_id,
        channel_id=chat_info.id,
        channel_name=chat_info.title
    )

    if success:
        # --- YANGI MANTIQ: Agar post yuborish jarayonidan kelgan bo'lsa ---
        data = await state.get_data()
        pending_post_code = data.get('pending_post_code')
        
        # Saqlangan ID lar
        original_panel_id = data.get('original_panel_id')
        prompt_message_id = data.get('prompt_message_id')

        if pending_post_code:
            # 1. Eski Post Panelini o'chiramiz (Move effekti uchun)
            if original_panel_id:
                with suppress(Exception):
                    await bot.delete_message(chat_id=message.chat.id, message_id=original_panel_id)

            # 2. Yo'riqnoma xabarini o'chiramiz
            if prompt_message_id:
                with suppress(Exception):
                    await bot.delete_message(chat_id=message.chat.id, message_id=prompt_message_id)

            # 3. Foydalanuvchi yuborgan xabarni (kanal manzili) o'chiramiz
            with suppress(Exception):
                await message.delete()
            
            # 4. Muvaffaqiyat xabarini chiqaramiz
            await message.answer(get_text('add_channel_success', lang).format(channel_name=html.escape(chat_info.title)))

            # 5. Postni boshqarish panelini YANGI xabar sifatida chiqaramiz
            # DIQQAT: Kanal qo'shilganda to'liq xabar (Kod + Yo'riqnoma) chiqishi kerak
            bot_info = await bot.get_me()
            bot_username = bot_info.username
            
            final_message = get_text('post_inline_usage', lang).format(
                post_code=pending_post_code,
                bot_username=bot_username
            )
            
            # TUZATILDI: await qo'shildi
            inline_kb = await get_post_management_keyboard(pending_post_code)
            await message.answer(final_message, reply_markup=inline_kb, parse_mode="HTML")
            
            await state.clear()
        else:
            # Oddiy holatda
            await state.clear()
            await message.answer(get_text('add_channel_success', lang).format(channel_name=html.escape(chat_info.title)))
            await cmd_start(message, state, bot)
    else:
        await message.answer(get_text('add_channel_exists_error', lang))


@send_router.message(PostSending.waiting_for_channel_info, F.forward_from_chat)
async def process_channel_forward(message: types.Message, state: FSMContext, bot: Bot):
    await _add_channel_to_db(message, state, bot, message.forward_from_chat)

@send_router.message(PostSending.waiting_for_channel_info, F.text)
async def process_channel_id_or_username(message: types.Message, state: FSMContext, bot: Bot):
    channel_identifier = message.text
    lang = await get_user_language(message.from_user.id)
    try:
        chat_info = await bot.get_chat(channel_identifier)
        await _add_channel_to_db(message, state, bot, chat_info)
    except TelegramBadRequest:
        await message.answer(get_text('channel_not_found', lang).format(channel_name=html.escape(channel_identifier)))
    except Exception as e:
        await message.answer(get_text('unknown_error', lang).format(error=e))

#==================================================
# --- POSTNI KANALGA YUBORISH JARAYONI ---
#==================================================

@send_router.callback_query(PostSendCallbackFactory.filter(F.action == "start_sending"))
async def start_sending_handler(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext, bot: Bot):
    post_code = callback_data.post_code
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    # --- Holatni o'rnatamiz ---
    await state.set_state(PostSending.choosing_channel_to_send)
    await state.update_data(
        post_code=post_code,
        # Post saqlangan xabar (kodli xabar) ID sini saqlaymiz, chunki uni keyinroq move qilamiz
        original_post_msg_id=callback.message.message_id,
        original_post_chat_id=callback.message.chat.id
    )

    # --- Foydalanuvchi kanallarini olamiz ---
    user_channels = await get_user_channels(user_id)
    
    # DIQQAT: Eski xabarni O'CHIRMAYMIZ! (callback.message.delete() yo'q)
    # Yangi xabar (Answer) sifatida kanal tanlashni chiqaramiz.

    if not user_channels:
        await callback.message.answer(
            get_text('need_channel_first', lang),
            reply_markup=get_add_channel_with_post_keyboard(post_code)
        )
    else:
        await callback.message.answer(
            get_text('choose_channel', lang),
            reply_markup=get_channel_list_keyboard(user_channels, post_code)
        )

    await callback.answer()

@send_router.callback_query(PostSendCallbackFactory.filter(F.action == "add_channel_with_post"))
async def redirect_to_add_channel_with_post(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext):
    """Post yuborish jarayonida kanal qo'shishga o'tish."""
    post_code = callback_data.post_code
    lang = await get_user_language(callback.from_user.id)
    
    # Holatni saqlaymiz
    await state.set_state(PostSending.waiting_for_channel_info)
    
    # --- Kanal qo'shish xabarini EDIT qilamiz ---
    await callback.message.edit_text(
        get_text('add_channel_title', lang),
        reply_markup=None
    )
    
    await state.update_data(
        pending_post_code=post_code,
        prompt_message_id=callback.message.message_id
    )
    
    await callback.answer()

@send_router.callback_query(F.data == "add_channel_redirect")
async def redirect_to_add_channel(callback: types.CallbackQuery, state: FSMContext):
    # --- Yangi xabar sifatida yuboramiz (eski xabarni o'chirmaymiz) ---
    await cmd_add_channel(callback.message, state)
    await callback.answer()

@send_router.message(PostSending.choosing_channel_to_send, LocalizedText('btn_back'))
async def back_from_sending(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    lang = await get_user_language(message.from_user.id)
    await message.answer(get_text('cancel_send', lang))
    await cmd_start(message, state, bot)

@send_router.callback_query(PostSending.choosing_channel_to_send, PostSendCallbackFactory.filter(F.action == "select_channel"))
async def select_channel_handler(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext, bot: Bot):
    """Kanal tanlagandan keyin: Qachon yuborilsin? oynasini ko'rsatadi."""
    from post_handlers.xinline_keyboard import get_send_timing_keyboard
    
    channel_name = "Noma'lum"
    try:
        chat_info = await bot.get_chat(callback_data.channel_id)
        channel_name = chat_info.title
    except Exception as e:
        logging.warning(f"Kanal nomini olishda xatolik: {e}")
        user_channels = await get_user_channels(callback.from_user.id)
        for ch in user_channels:
            if ch['channel_id'] == callback_data.channel_id:
                channel_name = ch['channel_name']
                break

    safe_channel_name = html.escape(channel_name)
    lang = await get_user_language(callback.from_user.id)
    
    # State ga kanal ma'lumotlarini saqlaymiz
    await state.update_data(selected_channel_id=callback_data.channel_id, selected_channel_name=safe_channel_name)

    # YANGI OYNA: Qachon yuborilsin?
    await callback.message.edit_text(
        get_text('send_timing_prompt', lang).format(channel_name=safe_channel_name),
        reply_markup=get_send_timing_keyboard(callback_data.post_code, callback_data.channel_id, lang)
    )

    await callback.answer()

# YANGI: "Hozir yuborish" bosilganda tasdiqlash oynasiga o'tish
@send_router.callback_query(PostSendCallbackFactory.filter(F.action == "confirm_prompt"))
async def confirm_prompt_handler(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext, bot: Bot):
    """Hozir yuborish tanlanganda tasdiqlash oynasini ko'rsatadi."""
    await state.set_state(PostSending.confirming_post_send)
    
    lang = await get_user_language(callback.from_user.id)
    data = await state.get_data()
    safe_channel_name = data.get('selected_channel_name', 'Kanal')

    await callback.message.edit_text(
        get_text('confirm_send_prompt', lang).format(channel_name=safe_channel_name),
        reply_markup=get_send_confirmation_keyboard(callback_data.post_code, callback_data.channel_id, lang)
    )

    await callback.answer()

@send_router.callback_query(PostSending.confirming_post_send, PostSendCallbackFactory.filter(F.action == "back_to_channels"))
async def back_to_timing_from_confirm(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext, bot: Bot):
    """Tasdiqlashdan 'Qachon yuborilsin' oynasiga qaytish (Yo'q tugmasi)."""
    from post_handlers.xinline_keyboard import get_send_timing_keyboard
    
    lang = await get_user_language(callback.from_user.id)
    data = await state.get_data()
    channel_name = data.get('selected_channel_name', 'Kanal')
    
    await callback.message.edit_text(
        get_text('send_timing_prompt', lang).format(channel_name=channel_name),
        reply_markup=get_send_timing_keyboard(callback_data.post_code, callback_data.channel_id, lang)
    )
    
    await callback.answer()

@send_router.callback_query(PostSending.confirming_post_send, PostSendCallbackFactory.filter(F.action == "confirm_send"))
async def confirm_send_handler(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, bot: Bot, state: FSMContext):
    post_code = callback_data.post_code
    channel_id = callback_data.channel_id
    user_id = callback.from_user.id # User ID ni olamiz
    lang = await get_user_language(user_id)
    
    # 1. "Tasdiqlash" (Confirmation) xabarini o'chiramiz
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    data = await state.get_data()
    # 2. Move uchun eski Post Saved xabarini (eng boshidagi kodli xabarni) o'chirish
    original_msg_id = data.get('original_post_msg_id')
    original_chat_id = data.get('original_post_chat_id')
    if original_msg_id and original_chat_id:
        try:
            await bot.delete_message(original_chat_id, original_msg_id)
        except Exception:
            pass

    full_post = await get_post_from_db(post_code)
    if not full_post:
        # Xabar o'chirilgan bo'lsa, alert yetarli emas, yangi xabar chiqarish kerak
        await bot.send_message(user_id, get_text('post_not_found_send', lang))
        return

    post_data = full_post.get('post_content', {})
    buttons_matrix = full_post.get('buttons_matrix', [])
    keyboard = generate_final_keyboard(buttons_matrix)

    try:
        content_type = post_data.get('content_type')
        # KANALGA YUBORISH
        if content_type == 'text':
            await bot.send_message(channel_id, post_data.get('text', ''), reply_markup=keyboard)
        elif content_type == 'photo':
            await bot.send_photo(channel_id, post_data.get('file_id'), caption=post_data.get('caption', ''), reply_markup=keyboard)
        elif content_type == 'video':
            await bot.send_video(channel_id, post_data.get('file_id'), caption=post_data.get('caption', ''), reply_markup=keyboard)
        elif content_type == 'audio':
            await bot.send_audio(channel_id, post_data.get('file_id'), caption=post_data.get('caption', ''), reply_markup=keyboard)
        elif content_type == 'document':
            await bot.send_document(channel_id, post_data.get('file_id'), caption=post_data.get('caption', ''), reply_markup=keyboard)
        elif content_type == 'voice':
            await bot.send_voice(channel_id, post_data.get('file_id'), caption=post_data.get('caption', ''), reply_markup=keyboard)
        elif content_type == 'animation':
            await bot.send_animation(channel_id, post_data.get('file_id'), caption=post_data.get('caption', ''), reply_markup=keyboard)
        elif content_type == 'video_note':
            await bot.send_video_note(channel_id, post_data.get('file_id'), reply_markup=keyboard)

        # 3. FOYDALANUVCHIGA JAVOB (bot.send_message orqali)
        
        # --- Muvaffaqiyat xabari va menyu ---
        await bot.send_message(
            user_id,
            get_text('post_sent_success', lang),
            reply_markup=get_post_done_menu(lang)
        )
        
        # --- Post kodli xabarni qayta pastga yuboramiz (Move effekti) ---
        # BU YERDA: Faqat kod chiqadi (qisqa format)
        final_message = f"postni inline yuborish uchun noyob post kodingiz : <code>{post_code}</code>"
        
        # TUZATILDI: await qo'shildi
        inline_kb = await get_post_management_keyboard(post_code)
        
        await bot.send_message(
            user_id,
            final_message,
            reply_markup=inline_kb,
            parse_mode="HTML"
        )
        
        await state.clear()

    except Exception as e:
        logging.error(f"Postni ({post_code}) kanalga ({channel_id}) yuborishda xato: {e}")
        # Xatolik xabarini ham bot.send_message orqali yuboramiz
        await bot.send_message(user_id, get_text('send_error', lang))

    await callback.answer()

#--- END OF FILE post_handlers/send_handler.py ---
