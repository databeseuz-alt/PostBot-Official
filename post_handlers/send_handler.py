import html
import os

import asyncio
from contextlib import suppress
from aiogram import F, Router, types, Bot
from aiogram.types import BufferedInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup

from xdata_handlers.database import (
    get_user_channels, add_user_channel, get_post_from_db, get_user_language, 
    save_sent_post, get_user_bot_settings, get_user_channel_bundles, get_user_channel_bundle_by_id
)
from post_handlers.post_handler import validate_and_fix_html
from post_handlers.xinline_keyboard import (
    PostSendCallbackFactory, get_channel_list_keyboard,
    get_send_confirmation_keyboard, get_add_channel_prompt_keyboard,
    generate_final_keyboard, get_add_channel_with_post_keyboard,
    get_post_management_keyboard
)

from xdata_handlers.translator import get_text, safe_format, get_text_formatted
from post_handlers.localize_filter import LocalizedText
from post_handlers.xreply_keyboard import get_post_done_menu, get_turbo_done_menu, get_save_cancel_kb, get_save_cancelled_kb, get_cancel_only_kb
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_turbo_success_keyboard(lang: str = 'uzl', post_code: str = None):
    builder = InlineKeyboardBuilder()
    main_menu_text = get_text('turbo_main_menu_btn', lang)
    edit_text = get_text('turbo_edit_btn', lang)
    builder.button(
        text=main_menu_text,
        callback_data="turbo:exit_to_main_menu",
        icon_custom_emoji_id="6042137469204303531"
    )
    if post_code:
        builder.button(
            text=edit_text,
            callback_data=f"edit_select:{post_code}",
            icon_custom_emoji_id="6026080811277621020"
        )
    else:
        builder.button(
            text=edit_text,
            callback_data="main:edit_post",
            icon_custom_emoji_id="6026080811277621020"
        )
    builder.adjust(2)
    return builder.as_markup()

def validate_html_content(content: str) -> str:
    """
    HTML kontentini validatsiya qilish va xatolarni tuzatish
    """
    if not content:
        return content
    
    return validate_and_fix_html(content)

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
    from xdata_handlers.database import add_user_channel
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    logger.info(f"[SEND_HANDLER] _add_channel_to_db: user_id={user_id}, message.from_user.id={message.from_user.id}, chat_info.id={chat_info.id}, chat_info.title={chat_info.title}")

    if chat_info.type != 'channel':
        return await message.answer(get_text('invalid_channel_msg', lang))

    try:
        bot_member = await bot.get_chat_member(chat_info.id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            return await message.answer(get_text_formatted('bot_not_admin_msg', lang, channel_name=html.escape(chat_info.title)))

        user_member = await bot.get_chat_member(chat_info.id, user_id)
        if user_member.status not in ['administrator', 'creator']:
            return await message.answer(get_text_formatted('user_not_admin_msg', lang, channel_name=html.escape(chat_info.title)))

    except Exception as e:
        logger.error(f"[SEND_HANDLER] Error checking channel membership: {e}")
        error_text = get_text('add_channel_error_msg', lang)
        return await message.answer(error_text)

    success = await add_user_channel(
        user_id=user_id,
        channel_id=chat_info.id,
        channel_name=chat_info.title
    )
    logger.info(f"[SEND_HANDLER] add_user_channel result: success={success}")

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

            await message.answer(get_text_formatted('add_channel_success_msg', lang, channel_name=html.escape(chat_info.title)))

            bot_info = await bot.get_me()
            bot_username = bot_info.username

            final_message = get_text_formatted('post_saved_msg', lang, post_code=pending_post_code, bot_username=bot_username)

            inline_kb = await get_post_management_keyboard(pending_post_code)
            await message.answer(final_message, reply_markup=inline_kb, parse_mode="HTML")

            await state.clear()
        elif data.get('from_post_creation'):
            await state.clear()
            await message.answer(get_text_formatted('add_channel_success_msg', lang, channel_name=html.escape(chat_info.title)))
            from post_handlers.start_handler import start_post_creation # LOCAL IMPORT
            await start_post_creation(message, state, bot)
        else:
            await state.clear()
            await message.answer(get_text_formatted('add_channel_success_msg', lang, channel_name=html.escape(chat_info.title)))
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
        await message.answer(get_text_formatted('channel_not_found_msg', lang, channel_name=html.escape(channel_identifier)))
    except Exception as e:
        await message.answer(get_text_formatted('unknown_error_msg', lang, error=e))

@send_router.callback_query(PostSendCallbackFactory.filter(F.action == "start_sending"))
async def start_sending_handler(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext, bot: Bot):
    import logging
    logger = logging.getLogger(__name__)
    
    post_code = callback_data.post_code
    
    # post_code None bo'lsa, state dan olishga urinib ko'rish
    if not post_code:
        data = await state.get_data()
        post_code = data.get("post_code")
    
    # Yana ham None bo'lsa, xabar berish
    if not post_code:
        lang = await get_user_language(callback.from_user.id)
        await callback.message.answer(get_text('post_code_missing_error', lang), parse_mode="HTML")
        await callback.answer()
        return
    
    # Foydalanuvchi ID sini aniqlash - callback dan olish
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    
    logger.info(f"[SEND_HANDLER] start_sending_handler: callback.from_user.id={user_id}, message.from_user.id={callback.message.from_user.id}, post_code={post_code}")
    logger.info(f"[SEND_HANDLER] Bot info: bot.id={bot.id}")
    
    await state.set_state(PostSending.choosing_channel_to_send)
    await state.update_data(
        post_code=post_code,
        original_post_msg_id=callback.message.message_id,
        original_post_chat_id=callback.message.chat.id
    )

    logger.info(f"[SEND_HANDLER] About to call get_user_channels for user_id={user_id}")
    user_channels = await get_user_channels(user_id)
    logger.info(f"[SEND_HANDLER] get_user_channels returned: user_id={user_id}, count={len(user_channels)}, channels={user_channels}")

    if not user_channels:
        await callback.message.answer(
            get_text('need_channel_msg', lang),
            reply_markup=get_add_channel_with_post_keyboard(post_code)
        )
    else:
        bundles = await get_user_channel_bundles(user_id)
        await callback.message.answer(
            get_text('choose_channel_msg', lang),
            reply_markup=get_channel_list_keyboard(user_channels, post_code, bundles=bundles)
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

    state_data = await state.get_data()
    turbo_mode = state_data.get('turbo_mode', False)
    turbo_action = state_data.get('turbo_action', 'now')

    if turbo_mode:
        if turbo_action == 'schedule':
            from post_handlers.schedule_handler import ScheduleManage, get_schedule_quick_keyboard
            await state.update_data(schedule_post_code=callback_data.post_code, schedule_channel_id=callback_data.channel_id)
            await state.set_state(ScheduleManage.waiting_for_custom_time)
            text = get_text('schedule_when_to_send', lang) + "\n\n" + get_text('schedule_enter_date_format', lang)
            try:
                await callback.message.edit_text(text, reply_markup=get_schedule_quick_keyboard(lang), parse_mode="HTML")
            except Exception:
                await callback.message.answer(text, reply_markup=get_schedule_quick_keyboard(lang), parse_mode="HTML")
            await callback.answer()
            return
        else:
            # TURBO REJIM ('now'): 3 sekund kutiladi, bekor qilish imkoni beriladi va kanalga yuboriladi
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.answer()
            await start_turbo_countdown_and_send(
                bot=bot,
                user_id=callback.from_user.id,
                post_code=callback_data.post_code,
                channel_id=callback_data.channel_id,
                channel_name=safe_channel_name,
                lang=lang,
                state=state
            )
            return

    await callback.message.edit_text(
        get_text_formatted('send_timing_msg', lang, channel_name=safe_channel_name),
        reply_markup=get_send_timing_keyboard(callback_data.post_code, callback_data.channel_id, lang)
    )

    await callback.answer()

@send_router.callback_query(PostSending.choosing_channel_to_send, PostSendCallbackFactory.filter(F.action == "select_bundle"))
async def select_bundle_handler(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext, bot: Bot):
    """To'plam tanlagandan keyin: Qachon yuborilsin? oynasini ko'rsatadi yoki Turbo yuboradi."""
    from post_handlers.xinline_keyboard import get_send_timing_keyboard

    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    bundle_id = callback_data.bundle_id
    bundle = await get_user_channel_bundle_by_id(user_id, bundle_id)

    if not bundle or not bundle.get('channel_ids'):
        await callback.answer(get_text('bundle_no_channels_selected', lang), show_alert=True)
        return

    bundle_name = bundle.get('name', "To'plam")
    safe_bundle_name = html.escape(bundle_name)

    await state.update_data(
        selected_bundle_id=bundle_id,
        selected_bundle_name=bundle_name,
        bundle_channel_ids=bundle['channel_ids'],
        selected_channel_name=f"📁 {bundle_name}"
    )

    state_data = await state.get_data()
    turbo_mode = state_data.get('turbo_mode', False)
    turbo_action = state_data.get('turbo_action', 'now')

    if turbo_mode:
        if turbo_action == 'schedule':
            from post_handlers.schedule_handler import ScheduleManage, get_schedule_quick_keyboard
            await state.update_data(
                schedule_post_code=callback_data.post_code,
                schedule_bundle_id=bundle_id,
                schedule_bundle_name=bundle_name,
                schedule_channel_ids=bundle['channel_ids']
            )
            await state.set_state(ScheduleManage.waiting_for_custom_time)
            text = get_text('schedule_when_to_send', lang) + "\n\n" + get_text('schedule_enter_date_format', lang)
            try:
                await callback.message.edit_text(text, reply_markup=get_schedule_quick_keyboard(lang), parse_mode="HTML")
            except Exception:
                await callback.message.answer(text, reply_markup=get_schedule_quick_keyboard(lang), parse_mode="HTML")
            await callback.answer()
            return
        else:
            # TURBO REJIM ('now'): 3 sekund kutiladi va to'plamdagi barcha kanallarga yuboriladi
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.answer()
            await start_turbo_countdown_and_send_bundle(
                bot=bot,
                user_id=user_id,
                post_code=callback_data.post_code,
                bundle=bundle,
                lang=lang,
                state=state
            )
            return

    await callback.message.edit_text(
        get_text_formatted('send_timing_msg', lang, channel_name=f"📁 {safe_bundle_name}"),
        reply_markup=get_send_timing_keyboard(callback_data.post_code, channel_id=0, lang=lang, bundle_id=bundle_id)
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
        get_text_formatted('confirm_send_msg', lang, channel_name=safe_channel_name),
        reply_markup=get_send_confirmation_keyboard(
            callback_data.post_code,
            callback_data.channel_id,
            lang=lang,
            bundle_id=callback_data.bundle_id
        )
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
        get_text_formatted('send_timing_msg', lang, channel_name=channel_name),
        reply_markup=get_send_timing_keyboard(
            callback_data.post_code,
            callback_data.channel_id,
            lang=lang,
            bundle_id=callback_data.bundle_id
        )
    )

    await callback.answer()

active_turbo_cancels: dict[str, asyncio.Event] = {}

def get_turbo_cancel_keyboard(post_code: str, lang: str):
    builder = InlineKeyboardBuilder()
    cancel_text = get_text('cancel_btn', lang)
    builder.button(text=cancel_text, callback_data=f"turbo_cancel:{post_code}")
    return builder.as_markup()

@send_router.callback_query(F.data.startswith("turbo_cancel:"))
async def handle_turbo_cancel(callback: types.CallbackQuery, state: FSMContext):
    post_code = callback.data.split(":")[1]
    event = active_turbo_cancels.get(post_code)
    if event:
        event.set()
    await callback.answer()

async def start_turbo_countdown_and_send(
    bot: Bot,
    user_id: int,
    post_code: str,
    channel_id: int,
    channel_name: str,
    lang: str,
    state: FSMContext = None
):
    """Turbo rejimda 3 sekund kutiladi va kanalga yuboriladi."""
    sparkle_emoji = '<tg-emoji emoji-id="5890925363067886150">✨</tg-emoji>'
    waiting_text = get_text_formatted('turbo_starting_msg', lang, sparkle=sparkle_emoji)

    waiting_msg = None
    try:
        waiting_msg = await bot.send_message(
            chat_id=user_id,
            text=waiting_text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error sending turbo waiting message: {e}")

    await asyncio.sleep(3.0)

    # Kutish xabarini o'chirib, postni kanalga yuboramiz
    if waiting_msg:
        try:
            await waiting_msg.delete()
        except Exception:
            pass

    await execute_send_post(
        bot=bot,
        user_id=user_id,
        post_code=post_code,
        channel_id=channel_id,
        channel_name=channel_name,
        lang=lang,
        state=state,
        is_turbo=True
    )

async def start_turbo_countdown_and_send_bundle(
    bot: Bot,
    user_id: int,
    post_code: str,
    bundle: dict,
    lang: str,
    state: FSMContext = None
):
    """Turbo rejimda to'plamdagi barcha kanallarga 3 sekund kutib yuborish."""
    sparkle_emoji = '<tg-emoji emoji-id="5890925363067886150">✨</tg-emoji>'
    waiting_text = get_text_formatted('turbo_starting_msg', lang, sparkle=sparkle_emoji)

    waiting_msg = None
    try:
        waiting_msg = await bot.send_message(
            chat_id=user_id,
            text=waiting_text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error sending turbo waiting message: {e}")

    await asyncio.sleep(3.0)

    if waiting_msg:
        try:
            await waiting_msg.delete()
        except Exception:
            pass

    channel_ids = bundle.get('channel_ids', [])
    bundle_name = bundle.get('name', "To'plam")

    for ch_id in channel_ids:
        await execute_send_post(
            bot=bot,
            user_id=user_id,
            post_code=post_code,
            channel_id=ch_id,
            channel_name="",
            lang=lang,
            state=state,
            is_turbo=True,
            suppress_user_message=True
        )

    post_link = "пост" if lang in ['ru', 'uzk', 'tj', 'kg'] else "post"
    sparkle = '<tg-emoji emoji-id="5890925363067886150">✨</tg-emoji>'
    channel_emoji = '<tg-emoji emoji-id="5771695636411847302">📢</tg-emoji>'
    bullet = '<tg-emoji emoji-id="6203760464397078712">🫙</tg-emoji>'
    safe_bname = html.escape(bundle_name)

    success_text = (
        f"{sparkle} <b>Tayyor {post_link} yuborildi !</b>\n"
        f"{channel_emoji} <b>To'plam :</b> 📁 {safe_bname} ({len(channel_ids)} ta kanal)\n\n"
        f"<b>Nima qilamiz:</b>\n"
        f"{bullet} Yangi postlarni yuboring\n"
        f"{bullet} Turbo rejimdan chiqish uchun Bosh menyu tugmasini bosing"
    )

    await bot.send_message(
        user_id,
        success_text,
        reply_markup=get_turbo_success_keyboard(lang, post_code=post_code),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    if state:
        from post_handlers.post_handler import PostCreation
        await state.set_state(PostCreation.waiting_for_content)
        await state.update_data(
            turbo_enabled=True,
            turbo_action='now'
        )

async def execute_send_post(
    bot: Bot,
    user_id: int,
    post_code: str,
    channel_id: int,
    channel_name: str,
    lang: str,
    state: FSMContext = None,
    is_turbo: bool = False,
    suppress_user_message: bool = False
):
    """Postni kanalga to'g'ridan-to'g'ri yuboruvchi asosiy funksiya."""
    data = await state.get_data() if state else {}
    if not channel_name:
        channel_name = data.get('selected_channel_name', '')

    full_post = await get_post_from_db(post_code)
    if not full_post:
        await bot.send_message(user_id, get_text('post_not_found_msg', lang))
        return

    post_data = full_post.get('post_content', {})
    buttons_matrix = full_post.get('buttons_matrix', [])
    keyboard = generate_final_keyboard(buttons_matrix)

    parse_mode = post_data.get('parse_mode', 'HTML')
    disable_preview = post_data.get('disable_web_page_preview', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_spoiler = post_data.get('has_spoiler', False)

    # HTML kontentini validatsiya qilish
    if parse_mode == 'HTML':
        text_content = post_data.get('text')
        caption_content = post_data.get('caption')
        
        if text_content:
            post_data['text'] = validate_html_content(text_content)
        if caption_content:
            post_data['caption'] = validate_html_content(caption_content)

    # Print settings olish
    print_settings = full_post.get('print_settings', {})
    disable_notification = print_settings.get('silent_mode', False)
    protect_content = print_settings.get('protect_content', False)
    reply_to_message_id = print_settings.get('reply_to_message_id', None)
    auto_pin = print_settings.get('auto_pin', False)

    # Media settings
    thumbnail_file_id = post_data.get('thumbnail_file_id', None)
    send_as_document = post_data.get('send_as_document', False)

    # Thumbnail ni InputFile ga aylantirish
    thumbnail = None
    if thumbnail_file_id:
        try:
            thumb_file = await bot.get_file(thumbnail_file_id)
            thumb_data = await bot.download_file(thumb_file.file_path)
            thumbnail = BufferedInputFile(thumb_data.read(), filename="thumb.jpg")
        except Exception:
            thumbnail = None

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
                reply_markup=keyboard,
                disable_notification=disable_notification,
                protect_content=protect_content,
                reply_to_message_id=reply_to_message_id
            )
        elif content_type == 'text':
            sent_message = await bot.send_message(
                channel_id, post_data.get('text', ''), 
                reply_markup=keyboard, 
                parse_mode=parse_mode, 
                disable_web_page_preview=disable_preview,
                disable_notification=disable_notification,
                protect_content=protect_content,
                reply_to_message_id=reply_to_message_id
            )
        elif content_type == 'photo':
            sent_message = await bot.send_photo(
                channel_id,
                post_data.get('file_id'),
                caption=post_data.get('caption', ''),
                reply_markup=keyboard,
                parse_mode=parse_mode,
                show_caption_above_media=show_caption_above,
                has_spoiler=has_spoiler,
                disable_notification=disable_notification,
                protect_content=protect_content,
                reply_to_message_id=reply_to_message_id
            )
        elif content_type == 'video':
            if send_as_document:
                sent_message = await bot.send_document(
                    channel_id,
                    post_data.get('file_id'),
                    caption=post_data.get('caption', ''),
                    reply_markup=keyboard,
                    parse_mode=parse_mode,
                    thumbnail=thumbnail,
                    disable_notification=disable_notification,
                    protect_content=protect_content,
                    reply_to_message_id=reply_to_message_id
                )
            else:
                sent_message = await bot.send_video(
                    channel_id, 
                    post_data.get('file_id'), 
                    caption=post_data.get('caption', ''), 
                    reply_markup=keyboard, 
                    parse_mode=parse_mode,
                    show_caption_above_media=show_caption_above,
                    has_spoiler=has_spoiler,
                    thumbnail=thumbnail,
                    disable_notification=disable_notification,
                    protect_content=protect_content,
                    reply_to_message_id=reply_to_message_id
                )
        elif content_type == 'audio':
            sent_message = await bot.send_audio(
                channel_id, 
                post_data.get('file_id'), 
                caption=post_data.get('caption', ''), 
                reply_markup=keyboard, 
                parse_mode=parse_mode,
                thumbnail=thumbnail,
                disable_notification=disable_notification,
                protect_content=protect_content,
                reply_to_message_id=reply_to_message_id
            )
        elif content_type == 'document':
            sent_message = await bot.send_document(
                channel_id, 
                post_data.get('file_id'), 
                caption=post_data.get('caption', ''), 
                reply_markup=keyboard, 
                parse_mode=parse_mode,
                thumbnail=thumbnail,
                disable_notification=disable_notification,
                protect_content=protect_content,
                reply_to_message_id=reply_to_message_id
            )
        elif content_type == 'voice':
            sent_message = await bot.send_voice(
                channel_id, 
                post_data.get('file_id'), 
                caption=post_data.get('caption', ''), 
                reply_markup=keyboard, 
                parse_mode=parse_mode,
                disable_notification=disable_notification,
                protect_content=protect_content,
                reply_to_message_id=reply_to_message_id
            )
        elif content_type == 'animation':
            if send_as_document:
                sent_message = await bot.send_document(
                    channel_id,
                    post_data.get('file_id'),
                    caption=post_data.get('caption', ''),
                    reply_markup=keyboard,
                    parse_mode=parse_mode,
                    thumbnail=thumbnail,
                    disable_notification=disable_notification,
                    protect_content=protect_content,
                    reply_to_message_id=reply_to_message_id
                )
            else:
                sent_message = await bot.send_animation(
                    channel_id, 
                    post_data.get('file_id'), 
                    caption=post_data.get('caption', ''), 
                    reply_markup=keyboard, 
                    parse_mode=parse_mode,
                    show_caption_above_media=show_caption_above,
                    has_spoiler=has_spoiler,
                    disable_notification=disable_notification,
                    protect_content=protect_content,
                    reply_to_message_id=reply_to_message_id
                )
        elif content_type == 'video_note':
            sent_message = await bot.send_video_note(
                channel_id, post_data.get('file_id'), 
                reply_markup=keyboard,
                thumbnail=thumbnail,
                disable_notification=disable_notification,
                protect_content=protect_content,
                reply_to_message_id=reply_to_message_id
            )
        elif content_type == 'sticker':
            sent_message = await bot.send_sticker(
                channel_id, post_data.get('file_id'), 
                reply_markup=keyboard,
                disable_notification=disable_notification,
                protect_content=protect_content,
                reply_to_message_id=reply_to_message_id
            )
        elif content_type == 'dice':
            sent_message = await bot.send_dice(
                channel_id,
                emoji=post_data.get('dice_emoji', '🎲'),
                reply_markup=keyboard,
                disable_notification=disable_notification,
                protect_content=protect_content,
                reply_to_message_id=reply_to_message_id
            )
        elif content_type == 'location':
            sent_message = await bot.send_location(
                channel_id,
                latitude=post_data.get('latitude'),
                longitude=post_data.get('longitude'),
                reply_markup=keyboard,
                disable_notification=disable_notification,
                protect_content=protect_content,
                reply_to_message_id=reply_to_message_id
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
                reply_markup=keyboard,
                disable_notification=disable_notification,
                protect_content=protect_content,
                reply_to_message_id=reply_to_message_id
            )
        elif content_type == 'poll':
            # Poll yuborish
            sent_message = await bot.send_poll(
                chat_id=channel_id,
                question=post_data.get('question', ''),
                options=post_data.get('options', []),
                is_anonymous=post_data.get('is_anonymous', True),
                type=post_data.get('type', 'regular'),
                allows_multiple_answers=post_data.get('allows_multiple_answers', False),
                correct_option_id=post_data.get('correct_option_id'),
                explanation=post_data.get('explanation'),
                explanation_entities=post_data.get('explanation_entities'),
                open_period=post_data.get('open_period'),
                close_date=post_data.get('close_date'),
                is_closed=post_data.get('is_closed', False),
                reply_markup=keyboard,
                disable_notification=disable_notification,
                protect_content=protect_content,
                reply_to_message_id=reply_to_message_id
            )

        if sent_message:
            if not channel_name:
                channel_name = data.get('selected_channel_name', '')
            await save_sent_post(
                post_code=post_code,
                user_id=user_id,
                channel_id=channel_id,
                channel_name=channel_name,
                message_id=sent_message.message_id
            )

            # Kanalga post kodini yozish
            from xdata_handlers.database import update_channel_post_code
            await update_channel_post_code(user_id, channel_id, post_code)

            # Avtomatik pin
            if auto_pin:
                try:
                    await bot.pin_chat_message(
                        chat_id=channel_id,
                        message_id=sent_message.message_id,
                        disable_notification=disable_notification
                    )
                except Exception:
                    pass

            # Avto o'chirish timer
            delete_timer_seconds = print_settings.get('delete_timer_seconds')

            if delete_timer_seconds and delete_timer_seconds > 0:
                asyncio.create_task(
                    schedule_message_deletion(bot, channel_id, sent_message.message_id, delete_timer_seconds)
                )

        display_channel_name = channel_name or data.get('selected_channel_name', '')

        # Kanal ma'lumotlarini olish va havolani shakllantirish
        chat = None
        try:
            chat = await bot.get_chat(channel_id)
            if not display_channel_name and getattr(chat, 'title', None):
                display_channel_name = chat.title
        except Exception as e:
            logger.warning(f"get_chat error for channel {channel_id}: {e}")

        if not display_channel_name:
            from xdata_handlers.database import get_channel_name
            display_channel_name = await get_channel_name(user_id, channel_id) or "Kanal"

        post_url = ""
        channel_url = ""
        clean_id = str(channel_id).replace("-100", "").replace("-", "")

        if chat:
            username = getattr(chat, 'username', None)
            if username:
                post_url = f"https://t.me/{username}/{sent_message.message_id}" if sent_message else f"https://t.me/{username}"
                channel_url = f"https://t.me/{username}"
            else:
                post_url = f"https://t.me/c/{clean_id}/{sent_message.message_id}" if sent_message else f"https://t.me/c/{clean_id}"
                invite_link = getattr(chat, 'invite_link', None)
                if not invite_link:
                    try:
                        invite_link = await bot.export_chat_invite_link(channel_id)
                    except Exception:
                        invite_link = None
                channel_url = invite_link or f"https://t.me/c/{clean_id}"
        else:
            post_url = f"https://t.me/c/{clean_id}/{sent_message.message_id}" if sent_message else f"https://t.me/c/{clean_id}"
            channel_url = f"https://t.me/c/{clean_id}"

        safe_channel_title = html.escape(display_channel_name.strip() or "Kanal")
        if channel_url:
            channel_link = f'<a href="{channel_url}">{safe_channel_title}</a>'
        else:
            channel_link = safe_channel_title

        if suppress_user_message:
            return

        if not is_turbo and state:
            state_data = await state.get_data()
            is_turbo = state_data.get('turbo_mode', False) or state_data.get('turbo_enabled', False)

        if is_turbo:
            post_link = "пост" if lang in ['ru', 'uzk', 'tj', 'kg'] else "post"

            sparkle = '<tg-emoji emoji-id="5890925363067886150">✨</tg-emoji>'
            channel_emoji = '<tg-emoji emoji-id="5771695636411847302">📢</tg-emoji>'
            bullet = '<tg-emoji emoji-id="6203760464397078712">🫙</tg-emoji>'

            success_text = get_text_formatted(
                'turbo_success_msg',
                lang,
                sparkle=sparkle,
                post_link=post_link,
                channel_emoji=channel_emoji,
                channel_link=channel_link,
                bullet=bullet
            )

            await bot.send_message(
                user_id,
                success_text,
                reply_markup=get_turbo_success_keyboard(lang, post_code=post_code),
                parse_mode="HTML",
                disable_web_page_preview=True
            )

            if state:
                from post_handlers.post_handler import PostCreation
                await state.set_state(PostCreation.waiting_for_content)
                await state.update_data(
                    turbo_enabled=True,
                    turbo_action='now'
                )
        else:
            await bot.send_message(
                user_id,
                safe_format(get_text('post_sent_success_msg', lang), channel_name=display_channel_name),
                reply_markup=get_post_done_menu(lang)
            )

            if state:
                await state.clear()

    except Exception as e:
        # Server console ga yozish
        import traceback
        logger.error(f"[XATOLIK] Post yuborishda xatolik! User: {user_id}, Post: {post_code}, Channel: {channel_id}")
        logger.error(f"[XATOLIK] Xatolik: {str(e)}")
        logger.debug(f"[XATOLIK DETAL] Traceback: {traceback.format_exc()}")
        
        # Xatolikni bazaga yozish
        error_msg = f"Post yuborishda xatolik: {str(e)}"
        from xdata_handlers.database import log_user_error
        await log_user_error(user_id, error_msg)
        
        # Foydalanuvchiga tushunarli xabar berish
        error_text = str(e).lower()
        
        if 'not enough rights' in error_text or 'rights' in error_text or 'not an administrator' in error_text:
            await bot.send_message(user_id, get_text('bot_no_rights_msg', lang))
        elif 'chat not found' in error_text or 'channel not found' in error_text or "chat doesn't exist" in error_text:
            await bot.send_message(user_id, get_text('channel_not_found_msg', lang))
        elif 'bot was kicked' in error_text or 'bot was deleted' in error_text or 'user is deactivated' in error_text:
            await bot.send_message(user_id, get_text('bot_kicked_msg', lang))
        elif 'message not found' in error_text:
            from post_handlers.custom_emojis import HTML_EMOJI_CLOSE
            await bot.send_message(user_id, f"{HTML_EMOJI_CLOSE} <b>Xabar topilmadi!</b>\nEski xabarni o'chirib, qayta urinib ko'ring.", parse_mode="HTML")
        elif 'peer id invalid' in error_text or 'chat id is invalid' in error_text:
            from post_handlers.custom_emojis import HTML_EMOJI_CLOSE
            await bot.send_message(user_id, f"{HTML_EMOJI_CLOSE} <b>Kanal ID noto'g'ri!</b>\nIltimos, kanalni qayta qo'shing.", parse_mode="HTML")
        elif 'too many messages' in error_text or 'flood control' in error_text:
            await bot.send_message(user_id, "⏳ <b>Kutish vaqti!</b>\n juda ko'p so'rovlar. Iltimos, bir necha soniya kuting.", parse_mode="HTML")
        else:
            from post_handlers.custom_emojis import HTML_EMOJI_CLOSE
            # Umumiy xatolik - batafsil ma'lumot bilan
            await bot.send_message(
                user_id, 
                f"{HTML_EMOJI_CLOSE} <b>Yuborishda xatolik yuz berdi!</b>\n\n"
                f"<b>Xatolik:</b> {str(e)}\n\n"
                f"<b>Post kodi:</b> {post_code}\n"
                f"<b>Kanal ID:</b> {channel_id}\n\n"
                f"Iltimos, bot admin ekanligini tekshiring va qayta urinib ko'ring.",
                parse_mode="HTML"
            )


@send_router.callback_query(PostSending.confirming_post_send, PostSendCallbackFactory.filter(F.action == "confirm_send"))
async def confirm_send_handler(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, bot: Bot, state: FSMContext):
    """Postni yuborishni tasdiqlash (normal rejimda 'Ha' tugmasi)."""
    post_code = callback_data.post_code or (await state.get_data()).get("post_code")
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    data = await state.get_data()
    bundle_id = callback_data.bundle_id or data.get('selected_bundle_id')

    try:
        await callback.message.delete()
    except Exception:
        pass

    if bundle_id:
        bundle = await get_user_channel_bundle_by_id(user_id, bundle_id)
        channel_ids = bundle.get('channel_ids', []) if bundle else []
        bundle_name = bundle.get('name', "To'plam") if bundle else "To'plam"

        for ch_id in channel_ids:
            await execute_send_post(
                bot=bot,
                user_id=user_id,
                post_code=post_code,
                channel_id=ch_id,
                channel_name="",
                lang=lang,
                state=state,
                is_turbo=False,
                suppress_user_message=True
            )

        safe_bname = html.escape(bundle_name)
        await bot.send_message(
            user_id,
            f"✅ <b>Post «{safe_bname}» to'plamidagi barcha ({len(channel_ids)} ta) kanallarga muvaffaqiyatli yuborildi!</b>",
            reply_markup=get_post_done_menu(lang),
            parse_mode="HTML"
        )
        if state:
            await state.clear()
    else:
        channel_id = callback_data.channel_id
        channel_name = data.get('selected_channel_name', '')
        await execute_send_post(bot, user_id, post_code, channel_id, channel_name, lang, state)

    await callback.answer()

@send_router.callback_query(F.data == "turbo:exit_to_main_menu")
async def handle_turbo_exit_to_main_menu(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    await state.clear()
    from post_handlers.start_handler import show_main_menu
    await show_main_menu(callback, state, bot)
