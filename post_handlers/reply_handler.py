import logging
from contextlib import suppress
from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder

from post_handlers.post_handler import PostCreation
from post_handlers.xreply_keyboard import (
    get_main_menu, get_cancel_kb, get_post_settings_kb,
    get_button_creation_cancel_kb, get_edit_content_kb
)
from aiogram.types import Message, InputMediaPhoto, InputMediaVideo, InputMediaAudio, InputMediaDocument, InputMediaAnimation
from post_handlers.xinline_keyboard import (
    generate_preview_keyboard, create_post_options_keyboard,
    get_media_settings_inline_kb, generate_post_keyboard,
    get_settings_menu_inline_kb, get_post_settings_inline_kb
)
from xdata_handlers.database import get_user_language
from xdata_handlers.translator import get_text
from post_handlers.localize_filter import LocalizedText

logger = logging.getLogger(__name__)
reply_router = Router()


async def redraw_post_with_callback(callback: types.CallbackQuery, state: FSMContext):
    """Postni yangilangan sozlamalar bilan qayta chizish (callback uchun) - o'chirmasdan tahrirlash"""
    data = await state.get_data()
    buttons_matrix = data.get("buttons_matrix", [])
    post_data = data.get("post_data", {})
    if not post_data:
        return

    chat_id = post_data.get("chat_id")
    message_id = post_data.get("message_id")
    
    user_id = callback.from_user.id if callback.from_user else post_data.get("user_id")
    lang = await get_user_language(user_id)
    
    new_keyboard = generate_post_keyboard(buttons_matrix, lang)
    
    # Media sozlamalarini olish
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))
    content_type = post_data.get('content_type', 'text')
    
    settings_keyboard = get_media_settings_inline_kb(
        lang, 
        has_spoiler=has_spoiler, 
        is_paid=is_paid, 
        show_caption_above=show_caption_above, 
        has_caption=has_caption,
        content_type=content_type
    )
    
    file_id = post_data.get("file_id")
    caption = post_data.get("caption")
    parse_mode = post_data.get("parse_mode", 'HTML')
    
    # Post mavjudligini tekshirish
    if not chat_id or not message_id:
        return
    
    try:
        # Pulli media bo'lsa, editMessageMedia ishlamaydi, shuning uchun qayta yuboramiz
        if (is_paid and content_type in ['photo', 'video']) or content_type == 'paid_media':
            try:
                await callback.bot.delete_message(chat_id, message_id)
            except Exception:
                pass
            
            # send_new_post_with_settings funksiyasi message ob'ektini kutadi. 
            # CallbackQuery da message ob'ekti bor.
            await send_new_post_with_settings(callback.message, state, post_data, new_keyboard)
            
            # Alohida xabarda media sozlamalari tugmalarini ko'rsatish
            await callback.message.answer(
                get_text('media_settings_msg', lang),
                reply_markup=settings_keyboard
            )
            
            # State ni to'g'ri holatga o'rnatish
            await state.set_state(PostCreation.configuring_post)
            return

        # Postni joyida tahrirlash (o'chirmasdan)
        if content_type == 'photo':
            from aiogram.types import InputMediaPhoto
            media = InputMediaPhoto(
                media=file_id,
                caption=caption,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
            await callback.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=new_keyboard
            )
        elif content_type == 'video':
            from aiogram.types import InputMediaVideo
            media = InputMediaVideo(
                media=file_id,
                caption=caption,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
            await callback.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=new_keyboard
            )
        elif content_type == 'audio':
            from aiogram.types import InputMediaAudio
            media = InputMediaAudio(
                media=file_id,
                caption=caption,
                parse_mode=parse_mode
            )
            await callback.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=new_keyboard
            )
        elif content_type == 'document':
            from aiogram.types import InputMediaDocument
            media = InputMediaDocument(
                media=file_id,
                caption=caption,
                parse_mode=parse_mode
            )
            await callback.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=new_keyboard
            )
        elif content_type == 'animation':
            from aiogram.types import InputMediaAnimation
            media = InputMediaAnimation(
                media=file_id,
                caption=caption,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
            await callback.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=new_keyboard
            )
        elif content_type == 'text':
            await callback.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=caption or post_data.get('text', ''),
                parse_mode=parse_mode,
                reply_markup=new_keyboard
            )
        elif content_type == 'location':
            # Locationni tahrirlab bo'lmaydi, shuning uchun qayta yuborish kerak
            try:
                await callback.bot.delete_message(chat_id, message_id)
            except Exception:
                pass
            await send_new_post_with_settings(callback.message, state, post_data, new_keyboard)
        elif content_type in ['poll', 'dice']:
            # Poll va Dice ni tahrirlab bo'lmaydi, shuning uchun qayta yuborish kerak
            try:
                await callback.bot.delete_message(chat_id, message_id)
            except Exception:
                pass
            await send_new_post_with_settings(callback.message, state, post_data, new_keyboard)
        else:
            # Boshqa turlar uchun faqat klaviaturani o'zgartirish
            await callback.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=new_keyboard
            )
            
    except Exception:
        # Xatolik bo'lsa ham qayta yuborib ko'ramiz
        try:
            await callback.bot.delete_message(chat_id, message_id)
        except Exception:
            pass
        await send_new_post_with_settings(callback.message, state, post_data, new_keyboard)


@reply_router.callback_query(PostCreation.configuring_post, F.data == "cancel_post_creation")
async def cancel_post_creation_callback(callback: types.CallbackQuery, state: FSMContext):
    """Post yaratishni bekor qilish"""
    from post_handlers.xreply_keyboard import get_main_menu
    lang = await get_user_language(callback.from_user.id)
    
    # State ni tozalash
    await state.clear()
    
    await callback.message.edit_text(
        "❌ Post bekor qilindi",
        reply_markup=get_main_menu(lang)
    )
    await callback.answer()


async def send_new_post_with_settings(message: types.Message, state: FSMContext, post_data: dict, keyboard):
    """Postni yangi xabar sifatida yuborish va sozlamalarni ko'rsatish"""
    from post_handlers.xreply_keyboard import get_post_settings_kb
    
    content_type = post_data.get('content_type', 'text')
    file_id = post_data.get('file_id')
    caption = post_data.get('caption')
    text = post_data.get('text')
    parse_mode = post_data.get('parse_mode', 'HTML')
    disable_preview = post_data.get('disable_web_page_preview', False)
    has_spoiler = post_data.get('has_spoiler', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    
    lang = await get_user_language(message.from_user.id)
    
    sent_message = None
    
    try:
        if content_type == 'text':
            sent_message = await message.answer(
                text or '',
                reply_markup=keyboard,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview
            )
        elif content_type == 'photo':
            sent_message = await message.answer_photo(
                file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
        elif content_type == 'video':
            sent_message = await message.answer_video(
                file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
        elif content_type == 'audio':
            sent_message = await message.answer_audio(
                file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'document':
            sent_message = await message.answer_document(
                file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'voice':
            sent_message = await message.answer_voice(
                file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'video_note':
            sent_message = await message.answer_video_note(
                file_id,
                reply_markup=keyboard
            )
        elif content_type == 'animation':
            sent_message = await message.answer_animation(
                file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
        elif content_type == 'sticker':
            sent_message = await message.answer_sticker(
                file_id,
                reply_markup=keyboard
            )
        elif content_type == 'location':
            sent_message = await message.answer_location(
                latitude=post_data.get('latitude', 0),
                longitude=post_data.get('longitude', 0),
                reply_markup=keyboard
            )
        elif content_type == 'poll':
            sent_message = await message.answer_poll(
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
            sent_message = await message.answer_dice(
                emoji=post_data.get('dice_emoji', '🎲'),
                reply_markup=keyboard
            )
        elif content_type == 'paid_media':
            from aiogram.types import InputPaidMediaPhoto, InputPaidMediaVideo
            media_types = post_data.get('paid_media_types', [])
            file_ids = post_data.get('paid_media_file_ids', [])
            paid_price = post_data.get('paid_price', 1)
            
            input_media_list = []
            for media_type, f_id in zip(media_types, file_ids):
                if media_type == 'photo':
                    input_media_list.append(InputPaidMediaPhoto(media=f_id))
                else:
                    input_media_list.append(InputPaidMediaVideo(media=f_id))
            
            sent_message = await message.answer_paid_media(
                star_count=paid_price,
                media=input_media_list,
                caption=caption,
                parse_mode=parse_mode,
                show_caption_above_media=show_caption_above,
                reply_markup=keyboard
            )
        
        if sent_message:
            post_data['message_id'] = sent_message.message_id
            post_data['chat_id'] = sent_message.chat.id
            await state.update_data(post_data=post_data)
            
    except Exception as e:
        logger.exception(f"Error sending post: {e}")


# ========== Reply Keyboard Button Handlers ==========

@reply_router.message(
    PostCreation.configuring_post,
    LocalizedText('preview_btn')
)
async def preview_post_handler(message: types.Message, state: FSMContext, bot: Bot):
    """Ko'rish tugmasi - postni preview sifatida yuborish"""
    data = await state.get_data()
    post_data = data.get('post_data', {})
    buttons_matrix = data.get('buttons_matrix', [])
    lang = await get_user_language(message.from_user.id)
    
    if not post_data:
        await message.answer(get_text('post_not_found', lang))
        return
    
    # Generating preview keyboard (without management buttons)
    from post_handlers.xinline_keyboard import generate_preview_keyboard
    preview_keyboard = generate_preview_keyboard(buttons_matrix)
    
    content_type = post_data.get('content_type', 'text')
    file_id = post_data.get('file_id')
    caption = post_data.get('caption')
    text = post_data.get('text')
    parse_mode = post_data.get('parse_mode', 'HTML')
    disable_preview = post_data.get('disable_web_page_preview', False)
    has_spoiler = post_data.get('has_spoiler', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    
    try:
        if content_type == 'text':
            await message.answer(
                text or '',
                reply_markup=preview_keyboard,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview
            )
        elif content_type == 'photo':
            await message.answer_photo(
                file_id,
                caption=caption,
                reply_markup=preview_keyboard,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
        elif content_type == 'video':
            await message.answer_video(
                file_id,
                caption=caption,
                reply_markup=preview_keyboard,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
        elif content_type == 'audio':
            await message.answer_audio(
                file_id,
                caption=caption,
                reply_markup=preview_keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'document':
            await message.answer_document(
                file_id,
                caption=caption,
                reply_markup=preview_keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'voice':
            await message.answer_voice(
                file_id,
                caption=caption,
                reply_markup=preview_keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'video_note':
            await message.answer_video_note(
                file_id,
                reply_markup=preview_keyboard
            )
        elif content_type == 'animation':
            await message.answer_animation(
                file_id,
                caption=caption,
                reply_markup=preview_keyboard,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
        elif content_type == 'sticker':
            await message.answer_sticker(
                file_id,
                reply_markup=preview_keyboard
            )
        elif content_type == 'location':
            await message.answer_location(
                latitude=post_data.get('latitude', 0),
                longitude=post_data.get('longitude', 0),
                reply_markup=preview_keyboard
            )
        elif content_type == 'poll':
            await message.answer_poll(
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
            await message.answer_dice(
                emoji=post_data.get('dice_emoji', '🎲'),
                reply_markup=preview_keyboard
            )
        elif content_type == 'paid_media':
            from aiogram.types import InputPaidMediaPhoto, InputPaidMediaVideo
            media_types = post_data.get('paid_media_types', [])
            file_ids = post_data.get('paid_media_file_ids', [])
            paid_price = post_data.get('paid_price', 1)
            
            input_media_list = []
            for media_type, f_id in zip(media_types, file_ids):
                if media_type == 'photo':
                    input_media_list.append(InputPaidMediaPhoto(media=f_id))
                else:
                    input_media_list.append(InputPaidMediaVideo(media=f_id))
            
            await message.answer_paid_media(
                star_count=paid_price,
                media=input_media_list,
                caption=caption,
                parse_mode=parse_mode,
                show_caption_above_media=show_caption_above,
                reply_markup=preview_keyboard
            )
        
        await message.answer(get_text('content_received', lang))
        
    except Exception as e:
        logger.exception(f"Error in preview: {e}")
        await message.answer(get_text('preview_error_msg', lang))


@reply_router.message(
    PostCreation.configuring_post,
    LocalizedText('settings_btn')
)
async def settings_menu_handler(message: types.Message, state: FSMContext):
    """Sozlamalar tugmasi - sozlamalar menyusini ko'rsatish"""
    data = await state.get_data()
    post_data = data.get('post_data', {})
    lang = await get_user_language(message.from_user.id)
    
    content_type = post_data.get('content_type', 'text')
    
    # Get settings menu keyboard
    from post_handlers.xinline_keyboard import get_settings_menu_inline_kb
    settings_kb = get_settings_menu_inline_kb(lang, content_type)
    
    await message.answer(
        get_text('settings_menu_msg', lang),
        reply_markup=settings_kb
    )


@reply_router.message(
    PostCreation.configuring_post,
    LocalizedText('get_buttons_btn')
)
async def get_buttons_handler(message: types.Message, state: FSMContext):
    """Tugma tugmasi - tugmalarni boshqarish uchun inline tugmani ko'rsatish"""
    data = await state.get_data()
    post_data = data.get('post_data', {})
    buttons_matrix = data.get('buttons_matrix', [])
    lang = await get_user_language(message.from_user.id)
    
    if not post_data:
        await message.answer(get_text('post_not_found', lang))
        return
    
    chat_id = post_data.get('chat_id')
    message_id = post_data.get('message_id')
    
    # Create button management message with instructions
    instructions = get_text('your_buttons_msg', lang) + "\n\n" + get_text('add_inline_btn', lang) + " - tugmasini bosing"
    
    await message.answer(instructions)


@reply_router.message(
    PostCreation.configuring_post,
    LocalizedText('edit_content_btn')
)
async def edit_content_handler(message: types.Message, state: FSMContext):
    """Tahrirlash tugmasi - kontentni tahrirlash rejimiga o'tish"""
    data = await state.get_data()
    post_data = data.get('post_data', {})
    lang = await get_user_language(message.from_user.id)
    
    content_type = post_data.get('content_type', 'text')
    
    # Set state to waiting for content
    await state.set_state(PostCreation.waiting_for_content)
    
    # Show edit content keyboard based on content type
    if content_type == 'text':
        await message.answer(
            get_text('ask_new_content_msg', lang),
            reply_markup=get_cancel_kb(lang)
        )
    else:
        # For media, show options to delete or replace
        from post_handlers.xreply_keyboard import get_edit_content_kb
        await message.answer(
            get_text('ask_new_content_msg', lang),
            reply_markup=get_edit_content_kb(post_data, lang)
        )