import logging
from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from contextlib import suppress

from post_handlers.post_handler import PostCreation
from post_handlers.xreply_keyboard import get_post_done_menu, get_save_cancel_kb, get_save_cancelled_kb, get_cancel_reply_kb
from post_handlers.xinline_keyboard import get_post_management_keyboard, SavePostCallbackFactory, get_post_save_edit_keyboard, get_done_inline_keyboard, generate_preview_keyboard, generate_final_keyboard
from post_handlers.xreply_keyboard import get_main_menu as get_main_menu_reply
from xdata_handlers.database import (
    add_post_to_db, update_post_in_db, get_user_language, save_post_name, unsave_post_name, get_post_from_db
)
from admin_handlers.channel_handler import check_user_membership
from post_handlers.start_handler import start_post_creation, cmd_start
from xdata_handlers.translator import get_text
from xdata_handlers import config
from post_handlers.localize_filter import LocalizedText

done_router = Router()


async def send_post_preview(chat_id: int, post_code: str, lang: str, bot: Bot):
    """Postni preview sifatida yuboradi va post kodi xabarini chiqaradi."""
    full_post = await get_post_from_db(post_code)
    if not full_post:
        return None
    
    post_data = full_post.get('post_content', {})
    buttons_matrix = full_post.get('buttons_matrix', [])
    preview_keyboard = generate_preview_keyboard(buttons_matrix)
    final_keyboard = generate_final_keyboard(buttons_matrix)
    
    parse_mode = post_data.get('parse_mode', 'HTML')
    disable_preview = post_data.get('disable_web_page_preview', False)  # Standart yoqilgan
    has_spoiler = post_data.get('has_spoiler', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    content_type = post_data.get('content_type')
    
    preview_message = None
    try:
        if content_type == 'text':
            preview_message = await bot.send_message(
                chat_id,
                post_data.get('text', ''),
                reply_markup=preview_keyboard,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview
            )
        elif content_type == 'photo':
            preview_message = await bot.send_photo(
                chat_id,
                post_data.get('file_id'),
                caption=post_data.get('caption', ''),
                reply_markup=preview_keyboard,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
        elif content_type == 'video':
            preview_message = await bot.send_video(
                chat_id,
                post_data.get('file_id'),
                caption=post_data.get('caption', ''),
                reply_markup=preview_keyboard,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
        elif content_type == 'audio':
            preview_message = await bot.send_audio(
                chat_id,
                post_data.get('file_id'),
                caption=post_data.get('caption', ''),
                reply_markup=preview_keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'document':
            preview_message = await bot.send_document(
                chat_id,
                post_data.get('file_id'),
                caption=post_data.get('caption', ''),
                reply_markup=preview_keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'voice':
            preview_message = await bot.send_voice(
                chat_id,
                post_data.get('file_id'),
                caption=post_data.get('caption', ''),
                reply_markup=preview_keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'animation':
            preview_message = await bot.send_animation(
                chat_id,
                post_data.get('file_id'),
                caption=post_data.get('caption', ''),
                reply_markup=preview_keyboard,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
        elif content_type == 'video_note':
            preview_message = await bot.send_video_note(
                chat_id,
                post_data.get('file_id'),
                reply_markup=preview_keyboard
            )
        elif content_type == 'sticker':
            preview_message = await bot.send_sticker(
                chat_id,
                post_data.get('file_id'),
                reply_markup=preview_keyboard
            )
        elif content_type == 'poll':
            preview_message = await bot.send_poll(
                chat_id,
                question=post_data.get('poll_question', ''),
                options=post_data.get('poll_options', []),
                is_anonymous=post_data.get('poll_is_anonymous', True),
                allows_multiple_answers=post_data.get('poll_allows_multiple_answers', False),
                correct_option_id=post_data.get('poll_correct_option_id'),
                type='quiz' if post_data.get('poll_is_quiz', False) else 'regular',
                explanation=post_data.get('poll_explanation'),
                reply_markup=preview_keyboard
            )
        elif content_type == 'dice':
            preview_message = await bot.send_dice(
                chat_id,
                emoji=post_data.get('dice_emoji', '🎲'),
                reply_markup=preview_keyboard
            )
    except Exception as e:
        logging.error(f"Post preview yuborishda xatolik: {e}")
    
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    post_code_message = get_text('post_saved', lang).format(
        post_code=post_code,
        bot_username=bot_username
    )
    
    inline_kb = await get_post_management_keyboard(post_code, lang)
    
    await bot.send_message(
        chat_id,
        post_code_message,
        reply_markup=inline_kb,
        parse_mode="HTML"
    )
    
    return preview_message


@done_router.message(
    PostCreation.configuring_post,
    LocalizedText('done_btn')
)
@done_router.message(
    PostCreation.configuring_post,
    LocalizedText('edit_confirm_btn')
)
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

    await state.clear()
    
    try:
        await message.delete()
    except Exception:
        pass
    
    remover_message = await message.answer(get_text('post_saved_to_db', lang), reply_markup=ReplyKeyboardRemove())
    
    try:
        await remover_message.delete()
    except Exception:
        pass
    
    await send_post_preview(message.chat.id, post_code_for_user, lang, bot)


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
    
    await unsave_post_name(post_code, user_id)
    
    try:
        await callback.message.delete()
    except: pass
    
    lang = await get_user_language(user_id)
    await callback.message.answer(get_text('saved_name_deleted', lang))
    
    inline_kb = await get_post_management_keyboard(post_code)
    final_message = get_text('post_saved', lang).format(
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

    await save_post_name(post_code, new_name)
    
    await message.answer(get_text('post_renamed', lang), reply_markup=get_done_inline_keyboard(lang))
    
    inline_kb = await get_post_management_keyboard(post_code)
    final_message = get_text('post_saved', lang).format(
        post_code=post_code,
        bot_username=(await message.bot.get_me()).username
    )
    
    await message.answer(final_message, reply_markup=inline_kb, parse_mode="HTML")
    await state.clear()


@done_router.message(PostCreation.waiting_for_post_name, LocalizedText('back_btn'))
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
        final_message = get_text('post_saved', lang).format(
            post_code=post_code,
            bot_username=(await bot.get_me()).username
        )
        inline_kb = await get_post_management_keyboard(post_code)
        
        await message.answer(
            final_message,
            reply_markup=inline_kb,
            parse_mode="HTML"
        )

@done_router.message(PostCreation.waiting_for_rename, LocalizedText('back_btn'))
async def cancel_rename_post(message: types.Message, state: FSMContext):
    """Qayta nomlashni bekor qilish."""
    data = await state.get_data()
    post_code = data.get('rename_post_code')
    lang = await get_user_language(message.from_user.id) # Tilni aniqlaymiz
    
    await message.answer(get_text('rename_canceled', lang), reply_markup=get_done_inline_keyboard(lang))
    
    if post_code:
        inline_kb = await get_post_management_keyboard(post_code)
        final_message = get_text('post_saved', lang).format(
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
        await message.answer(get_text('post_saved_success', lang), reply_markup=get_done_inline_keyboard(lang))
    else:
        await message.answer(get_text('post_save_error', lang), reply_markup=get_done_inline_keyboard(lang))
        
    final_message = get_text('post_saved', lang).format(
        post_code=post_code,
        bot_username=(await bot.get_me()).username
    )
    inline_kb = await get_post_management_keyboard(post_code)
    
    await message.answer(
        final_message,
        reply_markup=inline_kb,
        parse_mode="HTML"
    )

    await state.clear()


@done_router.message(LocalizedText('cr_another_post_btn'))
async def create_another_post_handler(message: types.Message, state: FSMContext, bot: Bot):
    await start_post_creation(message, state, bot)

@done_router.message(LocalizedText('back_btn'))
async def back_to_main_menu_handler(message: types.Message, state: FSMContext, bot: Bot):
    await cmd_start(message, state, bot)

@done_router.callback_query(F.data == "done_create_another")
async def done_create_another_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    await start_post_creation(callback.message, state, bot)

@done_router.callback_query(F.data == "done_back")
async def done_back_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    await cmd_start(callback.message, state, bot)

@done_router.callback_query(F.data == "print_settings")
async def print_settings_handler(callback: types.CallbackQuery, state: FSMContext):
    """Chop etish sozlamalari tugmasi bosilganda."""
    from post_handlers.xinline_keyboard import get_print_settings_keyboard
    
    # Get post_code from callback if available
    post_code = None
    try:
        # Try to get post_code from the message text
        import re
        msg_text = callback.message.text if callback.message else ""
        code_match = re.search(r'code[=:]\s*(\w+)', msg_text, re.IGNORECASE)
        if code_match:
            post_code = code_match.group(1)
    except:
        pass
    
    lang = await get_user_language(callback.from_user.id)
    await callback.message.answer(
        get_text('print_settings_title', lang),
        reply_markup=get_print_settings_keyboard(lang, post_code),
        parse_mode="HTML"
    )
    await callback.answer()

@done_router.callback_query(F.data.startswith("print:"))
async def print_settings_callback(callback: types.CallbackQuery, state: FSMContext):
    """Chop etish sozlamalari callbacklari."""
    # Parse callback data: print:post_code:action
    parts = callback.data.split(":")
    post_code = parts[1] if len(parts) > 1 and parts[1] != 'none' else None
    action = parts[2] if len(parts) > 2 else None
    
    lang = await get_user_language(callback.from_user.id)
    
    if action == "menu" or action is None:
        # Show the print settings menu
        from post_handlers.xinline_keyboard import get_print_settings_keyboard
        try:
            await callback.message.edit_text(
                get_text('print_settings_title', lang),
                reply_markup=get_print_settings_keyboard(lang, post_code)
            )
        except:
            await callback.message.answer(
                get_text('print_settings_title', lang),
                reply_markup=get_print_settings_keyboard(lang, post_code),
                parse_mode="HTML"
            )
        await callback.answer()
        return
    
    if action == "back":
        # Show the post management keyboard
        from post_handlers.xinline_keyboard import get_post_management_keyboard
        try:
            await callback.message.edit_text(
                get_text('post_saved', lang).format(
                    post_code=post_code,
                    bot_username=(await callback.bot.get_me()).username
                ),
                reply_markup=await get_post_management_keyboard(post_code, lang)
            )
        except:
            await callback.message.answer(
                get_text('post_saved', lang).format(
                    post_code=post_code,
                    bot_username=(await callback.bot.get_me()).username
                ),
                reply_markup=await get_post_management_keyboard(post_code, lang),
                parse_mode="HTML"
            )
        await callback.answer()
        return
    
    if action == "delete_timer":
        # Handle delete timer - ask for time input
        from post_handlers.xreply_keyboard import get_cancel_reply_kb
        from post_handlers.post_handler import PostCreation
        
        await state.set_state(PostCreation.waiting_for_delete_timer)
        await state.update_data(post_code_for_delete_timer=post_code)
        
        try:
            await callback.message.edit_text(
                get_text('delete_timer_prompt', lang),
                reply_markup=get_cancel_reply_kb(lang)
            )
        except:
            await callback.message.answer(
                get_text('delete_timer_prompt', lang),
                reply_markup=get_cancel_reply_kb(lang),
                parse_mode="HTML"
            )
        await callback.answer()
        return
    
    # For now, show coming soon message for all other actions
    action_texts = {
        "pin": "📌 Mahkamlash",
        "protect": "🛡️ Himoya qilish",
        "voice": "🎤 Ovoz bilan",
        "reply": "↩️ Javob posti",
        "auto_repeat": "🔄 Avtotakrorlash"
    }
    
    await callback.message.answer(
        f"<b>✅ {action_texts.get(action, action)}</b>\n\n<i>Bu funksiya tez orada ishga tushiriladi!</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@done_router.message(PostCreation.waiting_for_delete_timer)
async def process_delete_timer(message: types.Message, state: FSMContext):
    """Foydalanuvchi vaqtni kiritganda."""
    import re
    from datetime import datetime, timedelta
    import pytz
    
    lang = await get_user_language(message.from_user.id)
    user_input = message.text.strip()
    
    # Check for cancel
    if user_input == get_text('cancel_btn', lang) or user_input == get_text('back_btn', lang):
        await state.clear()
        await message.answer(get_text('delete_timer_cancelled', lang))
        # Show print settings menu again
        from post_handlers.xinline_keyboard import get_print_settings_keyboard
        await message.answer(
            get_text('print_settings_title', lang),
            reply_markup=get_print_settings_keyboard(lang),
            parse_mode="HTML"
        )
        return
    
    # Parse time input
    delete_after_seconds = None
    display_time = user_input
    
    # Try to parse relative time (e.g., "5 daq", "1 soat", "24 soat")
    # Patterns: X daq(iqa), X minut(a), X soat, X kun, X sek(und)
    relative_pattern = re.search(r'(\d+)\s*(daq|minut?|soat|kun|sek|und)', user_input.lower())
    
    if relative_pattern:
        amount = int(relative_pattern.group(1))
        unit = relative_pattern.group(2)
        
        if 'daq' in unit or 'min' in unit:
            delete_after_seconds = amount * 60
            display_time = f"{amount} daqiqa"
        elif 'soat' in unit:
            delete_after_seconds = amount * 3600
            display_time = f"{amount} soat"
        elif 'kun' in unit:
            delete_after_seconds = amount * 86400
            display_time = f"{amount} kun"
        elif 'sek' in unit:
            delete_after_seconds = amount
            display_time = f"{amount} sekund"
    else:
        # Try to parse exact date/time (e.g., "06.03 20:00", "6.03.2025 20:00")
        # Try different formats
        formats = [
            "%d.%m %H:%M",      # 06.03 20:00
            "%d.%m.%Y %H:%M",   # 06.03.2025 20:00
            "%d.%m.%Y",         # 06.03.2025
            "%H:%M",            # 20:00
        ]
        
        tz = pytz.timezone('Asia/Tashkent')
        now = datetime.now(tz)
        
        for fmt in formats:
            try:
                parsed = datetime.strptime(user_input, fmt)
                
                # Handle different formats
                if fmt == "%H:%M":
                    # Just time - use today or tomorrow
                    parsed = now.replace(hour=parsed.hour, minute=parsed.minute, second=0)
                    if parsed < now:
                        parsed += timedelta(days=1)
                elif fmt == "%d.%m.%Y":
                    # Just date - use 00:00
                    parsed = parsed.replace(year=now.year)
                    parsed = tz.localize(parsed)
                elif fmt == "%d.%m %H:%M":
                    # Date and time - assume current year
                    parsed = parsed.replace(year=now.year)
                    parsed = tz.localize(parsed)
                elif fmt == "%d.%m.%Y %H:%M":
                    parsed = tz.localize(parsed)
                
                # Calculate seconds until deletion
                if parsed > now:
                    delete_after_seconds = int((parsed - now).total_seconds())
                    display_time = parsed.strftime("%d.%m.%Y %H:%M")
                break
            except:
                continue
    
    if delete_after_seconds is None or delete_after_seconds <= 0:
        await message.answer(
            get_text('delete_timer_invalid', lang),
            parse_mode="HTML"
        )
        return
    
    # Get post_code from state if available
    data = await state.get_data()
    post_code = data.get("post_code_for_delete_timer")
    
    if post_code:
        from xdata_handlers.database import update_post_print_settings
        await update_post_print_settings(post_code, {
            'delete_timer_seconds': delete_after_seconds,
            'delete_timer_display': display_time
        })
    
    await state.clear()
    
    await message.answer(
        get_text('delete_timer_set', lang).format(time=display_time),
        parse_mode="HTML"
    )
    
    # Show print settings menu again
    from post_handlers.xinline_keyboard import get_print_settings_keyboard
    await message.answer(
        get_text('print_settings_title', lang),
        reply_markup=get_print_settings_keyboard(lang, post_code),
        parse_mode="HTML"
    )
    
    await state.clear()

@done_router.callback_query(F.data == "print:pin")
async def print_pin_handler(callback: types.CallbackQuery, state: FSMContext):
    """Mahkamlash tugmasi bosilganda."""
    lang = await get_user_language(callback.from_user.id)
    await callback.message.answer(
        f"<b>📌 {get_text('print_pin', lang)}</b>\n\n<i>Bu funksiya tez orada ishga tushiriladi!</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@done_router.callback_query(F.data == "print:protect")
async def print_protect_handler(callback: types.CallbackQuery, state: FSMContext):
    """Himoya qilish tugmasi bosilganda."""
    lang = await get_user_language(callback.from_user.id)
    await callback.message.answer(
        f"<b>🛡️ {get_text('print_protect', lang)}</b>\n\n<i>Bu funksiya tez orada ishga tushiriladi!</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@done_router.callback_query(F.data == "print:voice")
async def print_voice_handler(callback: types.CallbackQuery, state: FSMContext):
    """Ovoz bilan tugmasi bosilganda."""
    lang = await get_user_language(callback.from_user.id)
    await callback.message.answer(
        f"<b>🎤 {get_text('print_with_voice', lang)}</b>\n\n<i>Bu funksiya tez orada ishga tushiriladi!</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@done_router.callback_query(F.data == "print:reply")
async def print_reply_handler(callback: types.CallbackQuery, state: FSMContext):
    """Javob posti tugmasi bosilganda."""
    lang = await get_user_language(callback.from_user.id)
    await callback.message.answer(
        f"<b>↩️ {get_text('print_reply_post', lang)}</b>\n\n<i>Bu funksiya tez orada ishga tushiriladi!</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@done_router.callback_query(F.data == "print:auto_repeat")
async def print_auto_repeat_handler(callback: types.CallbackQuery, state: FSMContext):
    """Avtotakrorlash tugmasi bosilganda."""
    lang = await get_user_language(callback.from_user.id)
    await callback.message.answer(
        f"<b>🔄 {get_text('print_auto_repeat', lang)}</b>\n\n<i>Bu funksiya tez orada ishga tushiriladi!</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@done_router.callback_query(F.data == "cancel_action")
async def cancel_action_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    is_member, check_text, check_keyboard = await check_user_membership(callback.from_user, bot)
    if not is_member:
        await state.clear()
        lang = await get_user_language(callback.from_user.id)
        await callback.message.edit_text(get_text('cancel_btn_msg', lang))
        await callback.message.answer(check_text, reply_markup=check_keyboard)
        return

    await state.clear()
    lang = await get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        get_text('cancel_btn_msg', lang),
        reply_markup=await get_main_menu_reply(lang=lang, user_id=callback.from_user.id)
    )


