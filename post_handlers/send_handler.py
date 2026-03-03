import html

import asyncio
from contextlib import suppress
from aiogram import F, Router, types, Bot
from aiogram.types import BufferedInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup

from xdata_handlers.database import (
    get_user_channels, add_user_channel, get_post_from_db, get_user_language, 
    save_sent_post, get_user_bot_settings
)
from post_handlers.xinline_keyboard import (
    PostSendCallbackFactory, get_channel_list_keyboard,
    get_send_confirmation_keyboard, get_add_channel_prompt_keyboard,
    generate_final_keyboard, get_add_channel_with_post_keyboard,
    get_post_management_keyboard
)

from xdata_handlers.translator import get_text
from post_handlers.xreply_keyboard import get_post_done_menu, get_save_cancel_kb, get_save_cancelled_kb, get_cancel_only_kb
from post_handlers.localize_filter import LocalizedText

async def schedule_message_deletion(bot: Bot, chat_id: int, message_id: int, delete_after_seconds: int):
    """Xabarni ketma-ket sozlangan vaqtdan so'ng o'chiradi."""
    try:
        await asyncio.sleep(delete_after_seconds)
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest:
        pass  # Xabar allaqachon o'chirilgan yoki topilmadi
    except Exception:
        pass  # Boshqa xatolar - o'tkazib yuborish

send_router = Router()

async def safe_callback_answer(callback: types.CallbackQuery):
    """Callback.answer() ni xavfsiz chaqiradi (Telegram xatolarini tutadi)."""
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass  # Xatolar o'tkazib yuboriladi
    except Exception:
        pass  # Boshqa xatolar

class PostSending(StatesGroup):
    waiting_for_channel_info = State()
    choosing_channel_to_send = State()
    choosing_schedule_time = State() 
    confirming_post_send = State()

@send_router.message(Command("addchannel"))
async def cmd_add_channel(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(PostSending.waiting_for_channel_info)
    lang = await get_user_language(message.from_user.id)
    await message.answer(
        get_text('add_channel_msg', lang),
        reply_markup=ReplyKeyboardRemove()
    )

async def _add_channel_to_db(message: types.Message, state: FSMContext, bot: Bot, chat_info: types.Chat):
    """Kanalni tekshiradi va bazaga qo'shish uchun yordamchi funksiya."""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)

    if chat_info.type != 'channel':
        return await message.answer(get_text('invalid_channel_msg', lang))

    try:
        bot_member = await bot.get_chat_member(chat_info.id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            return await message.answer(get_text('bot_not_admin_msg', lang).format(channel_name=html.escape(chat_info.title)))

        user_member = await bot.get_chat_member(chat_info.id, user_id)
        if user_member.status not in ['administrator', 'creator']:
            return await message.answer(get_text('user_not_admin_msg', lang).format(channel_name=html.escape(chat_info.title)))

    except Exception:
        error_text = get_text('add_channel_error_msg', lang)
        return await message.answer(error_text)

    success = await add_user_channel(
        user_id=user_id,
        channel_id=chat_info.id,
        channel_name=chat_info.title
    )

    if success:
        data = await state.get_data()
        pending_post_code = data.get('pending_post_code')

        original_panel_id = data.get('original_panel_id')
        prompt_message_id = data.get('prompt_message_id')

        if pending_post_code:
            if original_panel_id:
                with suppress(Exception):
                    await bot.delete_message(chat_id=message.chat.id, message_id=original_panel_id)

            if prompt_message_id:
                with suppress(Exception):
                    await bot.delete_message(chat_id=message.chat.id, message_id=prompt_message_id)

            with suppress(Exception):
                await message.delete()

            await message.answer(get_text('add_channel_success_msg', lang).format(channel_name=html.escape(chat_info.title)))

            bot_info = await bot.get_me()
            bot_username = bot_info.username

            final_message = get_text('post_saved_msg', lang).format(
                post_code=pending_post_code,
                bot_username=bot_username
            )

            inline_kb = await get_post_management_keyboard(pending_post_code)
            await message.answer(final_message, reply_markup=inline_kb, parse_mode="HTML")

            await state.clear()
        else:
            await state.clear()
            await message.answer(get_text('add_channel_success_msg', lang).format(channel_name=html.escape(chat_info.title)))
            from post_handlers.start_handler import cmd_start # LOCAL IMPORT
            await cmd_start(message, state, bot)
    else:
        await message.answer(get_text('channel_exists_msg', lang))

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
        await message.answer(get_text('channel_not_found_msg', lang).format(channel_name=html.escape(channel_identifier)))
    except Exception as e:
        await message.answer(get_text('unknown_error_msg', lang).format(error=e))

@send_router.callback_query(PostSendCallbackFactory.filter(F.action == "start_sending"))
async def start_sending_handler(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext, bot: Bot):
    post_code = callback_data.post_code
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    await state.set_state(PostSending.choosing_channel_to_send)
    await state.update_data(
        post_code=post_code,
        original_post_msg_id=callback.message.message_id,
        original_post_chat_id=callback.message.chat.id
    )

    user_channels = await get_user_channels(user_id)

    if not user_channels:
        await callback.message.answer(
            get_text('need_channel_msg', lang),
            reply_markup=get_add_channel_with_post_keyboard(post_code)
        )
    else:
        await callback.message.answer(
            get_text('choose_channel_msg', lang),
            reply_markup=get_channel_list_keyboard(user_channels, post_code)
        )

    await callback.answer()

@send_router.callback_query(PostSendCallbackFactory.filter(F.action == "add_channel_with_post"))
async def redirect_to_add_channel_with_post(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext):
    """Post yuborish jarayonida kanal qo'shishga o'tish."""
    post_code = callback_data.post_code
    lang = await get_user_language(callback.from_user.id)

    await state.set_state(PostSending.waiting_for_channel_info)

    await callback.message.edit_text(
        get_text('add_channel_msg', lang),
        reply_markup=None
    )

    await state.update_data(
        pending_post_code=post_code,
        prompt_message_id=callback.message.message_id
    )

    await callback.answer()

@send_router.callback_query(F.data == "add_channel_redirect")
async def redirect_to_add_channel(callback: types.CallbackQuery, state: FSMContext):
    await cmd_add_channel(callback.message, state)
    await callback.answer()

@send_router.message(PostSending.choosing_channel_to_send, LocalizedText('back_btn'))
async def back_from_sending(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    lang = await get_user_language(message.from_user.id)
    await message.answer(get_text('cancel_send_msg', lang))
    from post_handlers.start_handler import cmd_start # LOCAL IMPORT
    await cmd_start(message, state, bot)

@send_router.callback_query(PostSending.choosing_channel_to_send, PostSendCallbackFactory.filter(F.action == "select_channel"))
async def select_channel_handler(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext, bot: Bot):
    """Kanal tanlagandan keyin: Qachon yuborilsin? oynasini ko'rsatadi."""
    from post_handlers.xinline_keyboard import get_send_timing_keyboard

    lang_task = get_user_language(callback.from_user.id)
    channels_task = get_user_channels(callback.from_user.id)
    lang, user_channels = await asyncio.gather(lang_task, channels_task)

    channel_name = "Noma'lum"
    for ch in user_channels:
        if ch['channel_id'] == callback_data.channel_id:
            channel_name = ch['channel_name']
            break

    safe_channel_name = html.escape(channel_name)

    await state.update_data(selected_channel_id=callback_data.channel_id, selected_channel_name=safe_channel_name)

    await callback.message.edit_text(
        get_text('send_timing_msg', lang).format(channel_name=safe_channel_name),
        reply_markup=get_send_timing_keyboard(callback_data.post_code, callback_data.channel_id, lang)
    )

    await callback.answer()

@send_router.callback_query(PostSendCallbackFactory.filter(F.action == "confirm_prompt"))
async def confirm_prompt_handler(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext, bot: Bot):
    """Hozir yuborish tanlanganda tasdiqlash oynasini ko'rsatadi."""
    await state.set_state(PostSending.confirming_post_send)

    lang = await get_user_language(callback.from_user.id)
    data = await state.get_data()
    safe_channel_name = data.get('selected_channel_name', get_text('channel_label_msg', lang))

    await callback.message.edit_text(
        get_text('confirm_send_msg', lang).format(channel_name=safe_channel_name),
        reply_markup=get_send_confirmation_keyboard(callback_data.post_code, callback_data.channel_id, lang)
    )

    await callback.answer()

@send_router.callback_query(PostSending.confirming_post_send, PostSendCallbackFactory.filter(F.action == "back_to_channels"))
async def back_to_timing_from_confirm(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext, bot: Bot):
    """Tasdiqlashdan 'Qachon yuborilsin' oynasiga qaytish (Yo'q tugmasi)."""
    from post_handlers.xinline_keyboard import get_send_timing_keyboard

    lang = await get_user_language(callback.from_user.id)
    data = await state.get_data()
    channel_name = data.get('selected_channel_name', get_text('channel_label_msg', lang))

    await callback.message.edit_text(
        get_text('send_timing_msg', lang).format(channel_name=channel_name),
        reply_markup=get_send_timing_keyboard(callback_data.post_code, callback_data.channel_id, lang)
    )

    await callback.answer()

@send_router.callback_query(PostSending.confirming_post_send, PostSendCallbackFactory.filter(F.action == "confirm_send"))
async def confirm_send_handler(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, bot: Bot, state: FSMContext):
    post_code = callback_data.post_code
    channel_id = callback_data.channel_id
    user_id = callback.from_user.id # User ID ni olamiz
    lang = await get_user_language(user_id)

    try:
        await callback.message.delete()
    except Exception:
        pass

    data = await state.get_data()
    original_msg_id = data.get('original_post_msg_id')
    original_chat_id = data.get('original_post_chat_id')
    if original_msg_id and original_chat_id:
        try:
            await bot.delete_message(original_chat_id, original_msg_id)
        except Exception:
            pass

    full_post = await get_post_from_db(post_code)
    if not full_post:
        await bot.send_message(user_id, get_text('post_not_found_msg', lang))
        return

    post_data = full_post.get('post_content', {})
    buttons_matrix = full_post.get('buttons_matrix', [])
    keyboard = generate_final_keyboard(buttons_matrix)

    parse_mode = post_data.get('parse_mode', 'HTML')
    disable_preview = post_data.get('disable_web_page_preview', False)  # Standart yoqilgan
    show_caption_above = post_data.get('show_caption_above_media', False)  # Caption joylashuvi
    has_spoiler = post_data.get('has_spoiler', False)  # Spoiler effekti

    try:
        content_type = post_data.get('content_type')
        sent_message = None

        if post_data.get('is_paid', False) and content_type in ['photo', 'video']:
            stars = post_data.get('paid_price', 1)
            from aiogram.types import InputPaidMediaPhoto, InputPaidMediaVideo
            if content_type == 'photo':
                media_list = [InputPaidMediaPhoto(media=post_data.get('file_id'))]
            else:
                media_list = [InputPaidMediaVideo(media=post_data.get('file_id'))]

            sent_message = await bot.send_paid_media(
                chat_id=channel_id,
                star_count=stars,
                media=media_list,
                caption=post_data.get('caption', ''),
                parse_mode=parse_mode,
                show_caption_above_media=show_caption_above,
                reply_markup=keyboard
            )
        elif content_type == 'text':
            sent_message = await bot.send_message(channel_id, post_data.get('text', ''), reply_markup=keyboard, parse_mode=parse_mode, disable_web_page_preview=disable_preview)
        elif content_type == 'photo':
            sent_message = await bot.send_photo(
                channel_id,
                post_data.get('file_id'),
                caption=post_data.get('caption', ''),
                reply_markup=keyboard,
                parse_mode=parse_mode,
                show_caption_above_media=show_caption_above,
                has_spoiler=has_spoiler
            )
        elif content_type == 'video':
            sent_message = await bot.send_video(
                channel_id, 
                post_data.get('file_id'), 
                caption=post_data.get('caption', ''), 
                reply_markup=keyboard, 
                parse_mode=parse_mode,
                show_caption_above_media=show_caption_above,
                has_spoiler=has_spoiler
            )
        elif content_type == 'audio':
            sent_message = await bot.send_audio(
                channel_id, 
                post_data.get('file_id'), 
                caption=post_data.get('caption', ''), 
                reply_markup=keyboard, 
                parse_mode=parse_mode
            )
        elif content_type == 'document':
            sent_message = await bot.send_document(
                channel_id, 
                post_data.get('file_id'), 
                caption=post_data.get('caption', ''), 
                reply_markup=keyboard, 
                parse_mode=parse_mode
            )
        elif content_type == 'voice':
            sent_message = await bot.send_voice(
                channel_id, 
                post_data.get('file_id'), 
                caption=post_data.get('caption', ''), 
                reply_markup=keyboard, 
                parse_mode=parse_mode
            )
        elif content_type == 'animation':
            sent_message = await bot.send_animation(
                channel_id, 
                post_data.get('file_id'), 
                caption=post_data.get('caption', ''), 
                reply_markup=keyboard, 
                parse_mode=parse_mode,
                show_caption_above_media=show_caption_above,
                has_spoiler=has_spoiler
            )
        elif content_type == 'video_note':
            sent_message = await bot.send_video_note(channel_id, post_data.get('file_id'), reply_markup=keyboard)
        elif content_type == 'sticker':
            sent_message = await bot.send_sticker(channel_id, post_data.get('file_id'), reply_markup=keyboard)
        elif content_type == 'poll':
            sent_message = await bot.send_poll(
                channel_id,
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
            sent_message = await bot.send_dice(
                channel_id,
                emoji=post_data.get('dice_emoji', '🎲'),
                reply_markup=keyboard
            )
        elif content_type == 'location':
            sent_message = await bot.send_location(
                channel_id,
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
            for media_type, file_id in zip(media_types, file_ids):
                if media_type == 'photo':
                    input_media_list.append(InputPaidMediaPhoto(media=file_id))
                else:
                    input_media_list.append(InputPaidMediaVideo(media=file_id))

            sent_message = await bot.send_paid_media(
                chat_id=channel_id,
                star_count=paid_price,
                media=input_media_list,
                caption=post_data.get('caption', ''),
                parse_mode=parse_mode,
                show_caption_above_media=show_caption_above,
                reply_markup=keyboard
            )

        if sent_message:
            channel_name = data.get('selected_channel_name', '')
            await save_sent_post(
                post_code=post_code,
                user_id=user_id,
                channel_id=channel_id,
                channel_name=channel_name,
                message_id=sent_message.message_id
            )

            print_settings = full_post.get('print_settings', {})
            delete_timer_seconds = print_settings.get('delete_timer_seconds')

            if delete_timer_seconds and delete_timer_seconds > 0:
                asyncio.create_task(
                    schedule_message_deletion(bot, channel_id, sent_message.message_id, delete_timer_seconds)
                )

        await bot.send_message(
            user_id,
            get_text('post_sent_success_msg', lang),
            reply_markup=get_post_done_menu(lang)
        )

        bot_info = await bot.get_me()
        final_message = get_text('post_saved_msg', lang).format(
            post_code=post_code,
            bot_username=bot_info.username
        )

        inline_kb = await get_post_management_keyboard(post_code)

        await bot.send_message(
            user_id,
            final_message,
            reply_markup=inline_kb,
            parse_mode="HTML"
        )

        await state.clear()

    except Exception:
        await bot.send_message(user_id, get_text('send_error_msg', lang))

    await callback.answer()
