import logging
from contextlib import suppress
from aiogram import F, Router, types
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