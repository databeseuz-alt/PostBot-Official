import logging
import html
from aiogram import F, Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ReplyKeyboardRemove

from xdata_handlers import config
from post_handlers.post_handler import PostCreation
from post_handlers.xreply_keyboard import get_post_settings_kb, get_main_menu
from post_handlers.xinline_keyboard import generate_post_keyboard, get_edit_send_keyboard, EditSendCallbackFactory, generate_preview_keyboard
from xdata_handlers.database import get_post_from_db, check_post_owner, get_user_language, unsave_post_name
from xdata_handlers.translator import get_text
from post_handlers.send_handler import start_sending_handler
from post_handlers.start_handler import start_post_editing_process

edit_post_router = Router()


@edit_post_router.message(F.text, Command("delete_post"))
async def delete_saved_post_handler(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    text = message.text.strip()
    
    if "@" in text:
        parts = text.split()
        if len(parts) >= 2:
            post_code = parts[1]
        else:
            await message.answer(get_text('delete_command_format', lang))
            return
    else:
        try:
            post_code = text.split()[1]
        except IndexError:
            await message.answer(get_text('delete_command_format', lang))
            return

    post_name = await unsave_post_name(post_code, user_id)

    if post_name:
        safe_post_name = html.escape(post_name)
        await message.answer(get_text('post_deleted', lang).format(post_name=safe_post_name))
        await start_post_editing_process(message, state, bot)
    else:
        await message.answer(get_text('post_not_found_or_not_owner', lang))



async def load_post_for_editing(post_code: str, user_id: int, chat_id: int, state: FSMContext, bot: Bot, message_to_delete: types.Message | None = None):
    lang = await get_user_language(user_id)
    is_owner = await check_post_owner(post_code, user_id)
    is_admin = user_id in config.ADMIN_IDS

    if not is_owner and not is_admin:
        await bot.send_message(chat_id, get_text('post_not_found', lang))
        await state.clear()
        await bot.send_message(
            chat_id, get_text('main_menu', lang),
            reply_markup=await get_main_menu(lang, user_id)
        )
        return

    full_post = await get_post_from_db(post_code)
    if not full_post:
        await bot.send_message(chat_id, get_text('post_load_error', lang))
        return

    if message_to_delete:
        try:
            await message_to_delete.delete()
        except TelegramBadRequest:
            pass

    if is_admin and not is_owner:
        await bot.send_message(chat_id, "⚠️ <b>Diqqat:</b> Siz ushbu postning egasi emassiz. Admin huquqi bilan tahrirlamoqdasiz.")

    post_data = full_post.get('post_content')
    buttons_matrix = full_post.get('buttons_matrix', [])

    if not post_data:
        await bot.send_message(chat_id, get_text('post_load_error', lang))
        return

    post_data.setdefault('parse_mode', 'HTML')
    post_data.setdefault('disable_web_page_preview', False)  # Standart yoqilgan

    await state.set_data({
        "post_data": post_data,
        "buttons_matrix": buttons_matrix,
        "editing_post_code": post_code
    })

    await state.set_state(PostCreation.configuring_post)

    content_type = post_data.get('content_type', 'text')
    has_caption = bool(post_data.get('caption'))

    settings_kb = get_post_settings_kb(
        content_type=content_type,
        has_caption=has_caption,
        lang=lang,
        is_editing=True  # YANGI: Tahrirlash rejimida Edit tugmasini ko'rsatish
    )

    instruction = get_text('post_opened_for_editing', lang).format(post_code=post_code)
    
    keyboard = generate_post_keyboard(buttons_matrix, lang)
    sent_message = None

    message_kwargs = {
        "reply_markup": keyboard,
        "parse_mode": post_data.get('parse_mode', 'HTML'),
        "disable_web_page_preview": post_data.get('disable_web_page_preview', False)  # Standart yoqilgan
    }
    media_kwargs = {
        "reply_markup": keyboard,
        "parse_mode": post_data.get('parse_mode', 'HTML')
    }

    try:
        if post_data.get('is_paid', False) and content_type in ['photo', 'video']:
            stars = post_data.get('paid_price', 1)
            from aiogram.types import InputPaidMediaPhoto, InputPaidMediaVideo
            if content_type == 'photo':
                media_list = [InputPaidMediaPhoto(media=post_data.get('file_id'))]
            else:
                media_list = [InputPaidMediaVideo(media=post_data.get('file_id'))]
                
            orig_caption = post_data.get('caption') or ""
            full_caption = f"{instruction}\n\n{orig_caption}"
            show_caption_above = post_data.get('show_caption_above_media', False)
                
            sent_message = await bot.send_paid_media(
                chat_id=chat_id,
                star_count=stars,
                media=media_list,
                caption=full_caption,
                parse_mode=post_data.get('parse_mode', 'HTML'),
                show_caption_above_media=show_caption_above,
                reply_markup=keyboard
            )
        elif content_type == 'text':
            full_text = f"{instruction}\n\n{post_data.get('text')}"
            sent_message = await bot.send_message(chat_id, full_text, **message_kwargs)
        elif content_type in ['photo', 'video', 'audio', 'document', 'animation', 'voice']:
            orig_caption = post_data.get('caption') or ""
            full_caption = f"{instruction}\n\n{orig_caption}"
            
            # Media sozlamalari
            has_spoiler = post_data.get('has_spoiler', False)
            show_caption_above = post_data.get('show_caption_above_media', False)
            
            # Media turlari bo'yicha yuborish
            if content_type == 'photo':
                sent_message = await bot.send_photo(chat_id, post_data.get('file_id'), caption=full_caption, has_spoiler=has_spoiler, show_caption_above_media=show_caption_above, **media_kwargs)
            elif content_type == 'video':
                sent_message = await bot.send_video(chat_id, post_data.get('file_id'), caption=full_caption, has_spoiler=has_spoiler, show_caption_above_media=show_caption_above, **media_kwargs)
            elif content_type == 'audio':
                sent_message = await bot.send_audio(chat_id, post_data.get('file_id'), caption=full_caption, **media_kwargs)
            elif content_type == 'document':
                sent_message = await bot.send_document(chat_id, post_data.get('file_id'), caption=full_caption, **media_kwargs)
            elif content_type == 'animation':
                sent_message = await bot.send_animation(chat_id, post_data.get('file_id'), caption=full_caption, has_spoiler=has_spoiler, show_caption_above_media=show_caption_above, **media_kwargs)
            elif content_type == 'voice':
                sent_message = await bot.send_voice(chat_id, post_data.get('file_id'), caption=full_caption, **media_kwargs)
        elif content_type == 'video_note':
            await bot.send_message(chat_id, instruction, reply_markup=settings_kb, parse_mode="HTML")
            sent_message = await bot.send_video_note(chat_id, post_data.get('file_id'), reply_markup=keyboard)
        elif content_type == 'sticker':
            await bot.send_message(chat_id, instruction, reply_markup=settings_kb, parse_mode="HTML")
            sent_message = await bot.send_sticker(chat_id, post_data.get('file_id'), reply_markup=keyboard)
        elif content_type == 'poll':
            await bot.send_message(chat_id, instruction, reply_markup=settings_kb, parse_mode="HTML")
            sent_message = await bot.send_poll(
                chat_id,
                question=post_data.get('poll_question', ''),
                options=post_data.get('poll_options', []),
                is_anonymous=post_data.get('poll_is_anonymous', True),
                allows_multiple_answers=post_data.get('poll_allows_multiple_answers', False),
                correct_option_id=post_data.get('poll_correct_option_id'),
                type='quiz' if post_data.get('poll_is_quiz', False) else 'regular',
                explanation=post_data.get('poll_explanation'),
                reply_markup=keyboard
            )
        elif content_type == 'location':
            await bot.send_message(chat_id, instruction, reply_markup=settings_kb, parse_mode="HTML")
            sent_message = await bot.send_location(
                chat_id,
                latitude=post_data.get('latitude'),
                longitude=post_data.get('longitude'),
                reply_markup=keyboard
            )
        elif content_type == 'dice':
            await bot.send_message(chat_id, instruction, reply_markup=settings_kb, parse_mode="HTML")
            sent_message = await bot.send_dice(
                chat_id,
                emoji=post_data.get('dice_emoji', '🎲'),
                reply_markup=keyboard
            )
        elif content_type == 'paid_media':
            await bot.send_message(chat_id, instruction, reply_markup=settings_kb, parse_mode="HTML")
            from aiogram.types import InputPaidMediaPhoto, InputPaidMediaVideo
            media_types = post_data.get('paid_media_types', [])
            file_ids = post_data.get('paid_media_file_ids', [])
            paid_price = post_data.get('paid_price', 1)
            
            input_media_list = []
            for m_type, f_id in zip(media_types, file_ids):
                if m_type == 'photo':
                    input_media_list.append(InputPaidMediaPhoto(media=f_id))
                else:
                    input_media_list.append(InputPaidMediaVideo(media=f_id))
            
            sent_message = await bot.send_paid_media(
                chat_id=chat_id,
                star_count=paid_price,
                media=input_media_list,
                caption=post_data.get('caption', ''),
                parse_mode=post_data.get('parse_mode', 'HTML'),
                show_caption_above_media=post_data.get('show_caption_above_media', False),
                reply_markup=keyboard
            )
        else:
            await bot.send_message(chat_id, get_text('edit_type_error', lang).format(content_type=content_type))
            await state.clear()
            return

        if sent_message:
            post_data['message_id'] = sent_message.message_id
            post_data['chat_id'] = sent_message.chat.id
            await state.update_data(post_data=post_data)

    except TelegramBadRequest as e:
        if "can't parse entities" in str(e).lower():
            error_mode = f"<code>{post_data.get('parse_mode', 'HTML') or 'HTML'}</code>"
            await bot.send_message(chat_id, get_text('parse_mode_error', lang).format(parse_mode=error_mode))
        else:
            await bot.send_message(chat_id, get_text('post_display_error', lang))
    except Exception as e:
        logging.error(f"Tahrirlash uchun postni yuborishda xatolik: {e}")
        await bot.send_message(chat_id, get_text('post_display_error', lang))


async def show_post_preview(message: types.Message, post_code: str, bot: Bot):
    full_post = await get_post_from_db(post_code)
    if not full_post:
        return False

    post_data = full_post.get('post_content', {})
    buttons_matrix = full_post.get('buttons_matrix', [])
    keyboard = generate_preview_keyboard(buttons_matrix)

    lang = await get_user_language(message.from_user.id)

    try:
        content_type = post_data.get('content_type')
        chat_id = message.chat.id
        file_id = post_data.get('file_id')
        caption = post_data.get('caption')
        text = post_data.get('text')
        parse_mode = post_data.get('parse_mode', 'HTML')
        disable_preview = post_data.get('disable_web_page_preview', False)  # Standart yoqilgan

        has_spoiler = post_data.get('has_spoiler', False)
        show_caption_above = post_data.get('show_caption_above_media', False)

        if post_data.get('is_paid', False) and content_type in ['photo', 'video']:
            stars = post_data.get('paid_price', 1)
            from aiogram.types import InputPaidMediaPhoto, InputPaidMediaVideo
            if content_type == 'photo':
                media_list = [InputPaidMediaPhoto(media=file_id)]
            else:
                media_list = [InputPaidMediaVideo(media=file_id)]
                
            await bot.send_paid_media(
                chat_id=chat_id,
                star_count=stars,
                media=media_list,
                caption=caption,
                parse_mode=parse_mode,
                show_caption_above_media=show_caption_above,
                reply_markup=keyboard
            )
        elif content_type == 'text':
            await bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode=parse_mode, disable_web_page_preview=disable_preview)
        elif content_type == 'photo':
            await bot.send_photo(chat_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode, has_spoiler=has_spoiler, show_caption_above_media=show_caption_above)
        elif content_type == 'video':
            await bot.send_video(chat_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode, has_spoiler=has_spoiler, show_caption_above_media=show_caption_above)
        elif content_type == 'audio':
            await bot.send_audio(chat_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode)
        elif content_type == 'document':
            await bot.send_document(chat_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode)
        elif content_type == 'animation':
            await bot.send_animation(chat_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode, has_spoiler=has_spoiler, show_caption_above_media=show_caption_above)
        elif content_type == 'video_note':
            await bot.send_video_note(chat_id, file_id, reply_markup=keyboard)
        elif content_type == 'voice':
            await bot.send_voice(chat_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode)
        elif content_type == 'sticker':
            await bot.send_sticker(chat_id, file_id, reply_markup=keyboard)
        elif content_type == 'poll':
            await bot.send_poll(
                chat_id,
                question=post_data.get('poll_question', ''),
                options=post_data.get('poll_options', []),
                is_anonymous=post_data.get('poll_is_anonymous', True),
                allows_multiple_answers=post_data.get('poll_allows_multiple_answers', False),
                correct_option_id=post_data.get('poll_correct_option_id'),
                type='quiz' if post_data.get('poll_is_quiz', False) else 'regular',
                explanation=post_data.get('poll_explanation'),
                reply_markup=keyboard
            )
        elif content_type == 'dice':
            await bot.send_dice(
                chat_id,
                emoji=post_data.get('dice_emoji', '🎲'),
                reply_markup=keyboard
            )
        elif content_type == 'location':
            await bot.send_location(
                chat_id,
                latitude=post_data.get('latitude'),
                longitude=post_data.get('longitude'),
                reply_markup=keyboard
            )
        elif content_type == 'paid_media':
            from aiogram.types import InputPaidMediaPhoto, InputPaidMediaVideo
            media_types = post_data.get('paid_media_types', [])
            file_ids = post_data.get('paid_media_file_ids', [])
            paid_price = post_data.get('paid_price', 1)
            
            input_media_list = []
            for m_type, f_id in zip(media_types, file_ids):
                if m_type == 'photo':
                    input_media_list.append(InputPaidMediaPhoto(media=f_id))
                else:
                    input_media_list.append(InputPaidMediaVideo(media=f_id))
            
            await bot.send_paid_media(
                chat_id=chat_id,
                star_count=paid_price,
                media=input_media_list,
                caption=caption,
                parse_mode=parse_mode,
                show_caption_above_media=show_caption_above,
                reply_markup=keyboard
            )
        else:
            await bot.send_message(chat_id, get_text('preview_type_error', lang))

        return True
    except Exception:
        return False

@edit_post_router.message(PostCreation.waiting_for_edit_code, F.text)
async def receive_post_code(message: types.Message, state: FSMContext, bot: Bot):
    post_code = message.text.strip()
    user_id = message.from_user.id
    is_owner = await check_post_owner(post_code, user_id)
    is_admin = user_id in config.ADMIN_IDS

    if is_admin and not is_owner:
        await load_post_for_editing(post_code, user_id, message.chat.id, state, bot)
        return

    lang = await get_user_language(user_id)
    full_post = await get_post_from_db(post_code)

    if not full_post or not is_owner:
        return await message.answer(get_text('post_not_found', lang))

    await show_post_preview(message, post_code, bot)
    await message.answer(
        get_text('what_to_do_with_post', lang),
        reply_markup=get_edit_send_keyboard(post_code, lang)
    )

@edit_post_router.message(PostCreation.waiting_for_edit_code, F.forward_origin)
async def receive_forwarded_message(message: types.Message, state: FSMContext, bot: Bot):
    """Kanal yoki guruhdan forward qilingan xabarlarni qabul qilish"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    forward_origin = message.forward_origin
    
    if forward_origin.type == "channel":
        channel_id = forward_origin.chat.id
        message_id = forward_origin.message_id
        
        try:
            bot_member = await bot.get_chat_member(channel_id, bot.id)
            if bot_member.status not in ["administrator", "creator"]:
                await message.answer(
                    "❌ Bot bu kanalda admin emas. Faqat bot admin bo'lgan kanallardan forward qilingan xabarlarni tahrirlash mumkin.",
                    parse_mode="HTML"
                )
                return
        except Exception:
            await message.answer(
                "❌ Kanalga kirish imkoni yo'q. Bot kanalda admin ekanligiga ishonch hosil qiling.",
                parse_mode="HTML"
            )
            return
        
        try:
            channel_message = await bot.forward_message(
                chat_id=user_id,
                from_chat_id=channel_id,
                message_id=message_id
            )
            
            text_to_search = channel_message.text or channel_message.caption or ""
            
            import re
            post_code_pattern = r'\b([A-Za-z0-9]{5})\b'
            matches = re.findall(post_code_pattern, text_to_search)
            
            if matches:
                for potential_code in matches:
                    full_post = await get_post_from_db(potential_code)
                    if full_post:
                        await message.answer(
                            f"✅ Post topildi! Kod: <code>{potential_code}</code>\n\n"
                            f"Tahrirlash rejimiga o'tilmoqda...",
                            parse_mode="HTML"
                        )
                        await load_post_for_editing(potential_code, user_id, message.chat.id, state, bot)
                        return
            
            await message.answer(
                "❌ Forward qilingan xabarda post kodi topilmadi.\n\n"
                "Iltimos, post kodini qo'lda kiriting yoki post kodi bo'lgan xabarni forward qiling.",
                parse_mode="HTML"
            )
            
        except Exception as e:
            logging.error(f"Forward xabarni qayta ishlashda xatolik: {e}")
            await message.answer(
                "❌ Xabarni qayta ishlashda xatolik yuz berdi.\n\n"
                "Iltimos, post kodini qo'lda kiriting.",
                parse_mode="HTML"
            )
    else:
        await message.answer(
            "❌ Faqat kanaldan forward qilingan xabarlar qabul qilinadi.\n\n"
            "Iltimos, bot admin bo'lgan kanaldan xabar forward qiling yoki post kodini kiriting.",
            parse_mode="HTML"
        )


@edit_post_router.callback_query(EditSendCallbackFactory.filter(F.action == "edit"))
async def handle_edit_action(callback: types.CallbackQuery, callback_data: EditSendCallbackFactory, state: FSMContext, bot: Bot):
    await load_post_for_editing(
        post_code=callback_data.post_code,
        user_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
        state=state,
        bot=bot,
        message_to_delete=callback.message
    )
    await callback.answer()

@edit_post_router.callback_query(EditSendCallbackFactory.filter(F.action == "send"))
async def handle_send_action(callback: types.CallbackQuery, callback_data: EditSendCallbackFactory, state: FSMContext):
    await start_sending_handler(callback, callback_data, state)
