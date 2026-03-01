import logging
from contextlib import suppress
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder

from post_handlers.post_handler import PostCreation
from post_handlers.xreply_keyboard import (
    get_main_menu, get_cancel_kb, get_post_settings_kb, 
    get_button_creation_cancel_kb, get_edit_content_kb,
    get_media_settings_kb
)
from aiogram.types import Message, InputMediaPhoto, InputMediaVideo, InputMediaAudio, InputMediaDocument, InputMediaAnimation
from post_handlers.xinline_keyboard import (
    generate_preview_keyboard, create_post_options_keyboard,
    get_media_settings_inline_kb, generate_post_keyboard
)
from xdata_handlers.database import get_user_language
from xdata_handlers.translator import get_text
from post_handlers.localize_filter import LocalizedText

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
            
    except Exception as e:
        logging.error(f"Postni tahrirlab bo'lmadi (callback): {e}")
        # Xatolik bo'lsa ham qayta yuborib ko'ramiz
        try:
            await callback.bot.delete_message(chat_id, message_id)
        except Exception:
            pass
        await send_new_post_with_settings(callback.message, state, post_data, new_keyboard)


@reply_router.message(PostCreation.configuring_post, LocalizedText('settings_btn'))
async def options_menu_handler(message: types.Message, state: FSMContext):
    """Sozlamalar tugmasi bosilganda media sozlamalari inline keyboardini ko'rsatish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(message.from_user.id)

    has_spoiler = post_data.get('has_spoiler', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))
    content_type = post_data.get('content_type', 'text')
    is_paid = post_data.get('is_paid', False)

    await state.set_state(PostCreation.waiting_for_media_settings)
    
    await message.answer(
        get_text('media_settings_msg', lang),
        reply_markup=get_media_settings_inline_kb(
            lang=lang, 
            has_spoiler=has_spoiler, 
            is_paid=is_paid,
            show_caption_above=show_caption_above, 
            has_caption=has_caption,
            content_type=content_type
        )
    )


@reply_router.message(PostCreation.configuring_post, LocalizedText('get_buttons_btn'))
async def get_buttons_handler(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    buttons_matrix = data.get("buttons_matrix", [])
    post_data = data.get("post_data", {})

    has_real_buttons = any(any(btn and not btn.get('is_placeholder') for btn in row) for row in buttons_matrix)

    if not has_real_buttons:
        return await message.answer(
            get_text('no_buttons_msg', lang)
        )

    response_text = get_text('your_buttons_msg', lang) + "\n\n"
    button_count = 1
    from xdata_handlers.database import get_text_button_content
    for row in buttons_matrix:
        for button in row:
            if button and not button.get('is_placeholder'):
                if button.get('type') == 'text_btn':
                    content = await get_text_button_content(button['db_id'])
                    sub_text = content.get('content_sub', 'N/A') if content else 'N/A'
                    nonsub_text = content.get('content_nonsub', 'N/A') if content else 'N/A'
                    
                    response_text += f"{button_count}. {button['text']} :\n"
                    response_text += f"obunachilar uchun : {sub_text}\n"
                    response_text += f"obunasizlar uchun : {nonsub_text}\n\n"
                else:
                    button_url = button.get('url', 'URL missing')
                    response_text += f"{button_count}. {button['text']} = {button_url}\n"
                button_count += 1
    await message.answer(
        response_text.strip()
    )

@reply_router.message(PostCreation.configuring_post, LocalizedText('edit_content_btn'))
async def edit_content_handler(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})
    
    await state.set_state(PostCreation.waiting_for_content)
    await message.answer(
        get_text('ask_new_content_msg', lang), 
        reply_markup=get_edit_content_kb(post_data, lang)
    )

@reply_router.message(PostCreation.configuring_post, LocalizedText('preview_btn'))
async def preview_post_handler(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})
    buttons_matrix = data.get("buttons_matrix", [])

    if not post_data:
        return await message.answer(get_text('post_load_error_msg', lang))

    await message.answer(
        get_text('preview_title_msg', lang)
    )

    keyboard = generate_preview_keyboard(buttons_matrix)
    content_type = post_data.get('content_type')
    chat_id = message.chat.id
    file_id = post_data.get("file_id")
    text = post_data.get("text")
    caption = post_data.get("caption")
    parse_mode = post_data.get("parse_mode", 'HTML')
    disable_preview = post_data.get("disable_web_page_preview", False)  # Standart yoqilgan

    message_kwargs = {
        "reply_markup": keyboard,
        "disable_web_page_preview": disable_preview,
        "parse_mode": parse_mode
    }
    media_kwargs = {
        "reply_markup": keyboard,
        "parse_mode": parse_mode
    }

    try:
        if post_data.get('is_paid', False) and content_type in ['photo', 'video']:
            stars = post_data.get('paid_price', 1)
            from aiogram.types import InputPaidMediaPhoto, InputPaidMediaVideo
            if content_type == 'photo':
                media_list = [InputPaidMediaPhoto(media=file_id)]
            else:
                media_list = [InputPaidMediaVideo(media=file_id)]
                
            await message.bot.send_paid_media(
                chat_id=chat_id,
                star_count=stars,
                media=media_list,
                caption=caption,
                parse_mode=parse_mode,
                show_caption_above_media=post_data.get('show_caption_above_media', False),
                reply_markup=keyboard
            )
        elif content_type == 'text':
            await message.bot.send_message(chat_id, text, **message_kwargs)
        elif content_type == 'photo':
            await message.bot.send_photo(chat_id, file_id, caption=caption, has_spoiler=post_data.get('has_spoiler', False), show_caption_above_media=post_data.get('show_caption_above_media', False), **media_kwargs)
        elif content_type == 'video':
            await message.bot.send_video(chat_id, file_id, caption=caption, has_spoiler=post_data.get('has_spoiler', False), show_caption_above_media=post_data.get('show_caption_above_media', False), **media_kwargs)
        elif content_type == 'animation':
            await message.bot.send_animation(chat_id, file_id, caption=caption, has_spoiler=post_data.get('has_spoiler', False), show_caption_above_media=post_data.get('show_caption_above_media', False), **media_kwargs)
        elif content_type == 'audio':
            await message.bot.send_audio(chat_id, file_id, caption=caption, **media_kwargs)
        elif content_type == 'document':
            await message.bot.send_document(chat_id, file_id, caption=caption, **media_kwargs)
        elif content_type == 'voice':
            await message.bot.send_voice(chat_id, file_id, caption=caption, **media_kwargs)

        elif content_type == 'video_note':
            await message.bot.send_video_note(chat_id, file_id, reply_markup=keyboard)
        elif content_type == 'poll':
            await message.bot.send_poll(
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
            await message.bot.send_dice(
                chat_id,
                emoji=post_data.get('dice_emoji', '🎲'),
                reply_markup=keyboard
            )
        elif content_type == 'location':
            await message.bot.send_location(
                chat_id,
                latitude=post_data.get('latitude'),
                longitude=post_data.get('longitude'),
                reply_markup=keyboard
            )
    except TelegramBadRequest as e:
        if "can't parse entities" in str(e).lower():
            error_mode = f"<code>{parse_mode or 'None'}</code>"
            await message.answer(get_text('parse_mode_error_msg', lang).format(error_mode=error_mode))
        else:
            logging.error(f"Previewda xatolik: {e}")
            await message.answer(get_text('preview_error_msg', lang))
    except Exception as e:
        logging.error(f"Previewda kutilmagan xatolik: {e}")
        await message.answer(get_text('preview_error_msg', lang))


@reply_router.message(PostCreation.configuring_post, LocalizedText('cancel_btn'))
async def cancel_post_creation_handler(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    await state.clear()
    await message.answer(
        get_text('cancel_success_msg', lang),
        reply_markup=await get_main_menu(lang=lang, user_id=message.from_user.id)
    )


# ==================== MEDIA SOZLAMALARI (Post tahrirlashda) ====================

@reply_router.callback_query(PostCreation.configuring_post, F.data == "post_media_settings")
async def post_media_settings_menu(callback: types.CallbackQuery, state: FSMContext):
    """Post tahrirlashda media sozlamalari menyusini ochish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)
    
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    
    has_caption = bool(post_data.get('caption'))
    await callback.message.edit_text(
        get_text('media_settings_msg', lang),
        reply_markup=get_media_settings_inline_kb(
            lang, 
            has_spoiler=has_spoiler, 
            is_paid=is_paid, 
            show_caption_above=show_caption_above,
            has_caption=has_caption
        )
    )
    await callback.answer()


@reply_router.callback_query(PostCreation.configuring_post, F.data == "media_toggle_position")
@reply_router.callback_query(PostCreation.waiting_for_media_settings, F.data == "media_toggle_position")
async def post_media_toggle_position(callback: types.CallbackQuery, state: FSMContext):
    """Post tahrirlashda joylashuvni almashtirish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)
    content_type = post_data.get('content_type', 'photo')
    
    current_position = post_data.get('show_caption_above_media', False)
    new_position = not current_position
    post_data['show_caption_above_media'] = new_position
    await state.update_data(post_data=post_data)
    
    if new_position:
        alert_text = "Matn yuqorida ko'rsatiladi"
    else:
        alert_text = "Matn pastda ko'rsatiladi"
    
    await callback.answer(alert_text)
    
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    
    # Postni yangilash (faqat configuring_post holatida)
    current_state = await state.get_state()
    if current_state == PostCreation.configuring_post:
        await redraw_post_with_callback(callback, state)
    
    has_caption = bool(post_data.get('caption'))
    await callback.message.edit_reply_markup(
        reply_markup=get_media_settings_inline_kb(
            lang,
            has_spoiler=has_spoiler,
            is_paid=is_paid,
            show_caption_above=new_position,
            has_caption=has_caption,
            content_type=content_type
        )
    )


@reply_router.callback_query(PostCreation.configuring_post, F.data == "media_toggle_spoiler")
@reply_router.callback_query(PostCreation.waiting_for_media_settings, F.data == "media_toggle_spoiler")
async def post_media_toggle_spoiler(callback: types.CallbackQuery, state: FSMContext):
    """Post tahrirlashda spoilerni yoqish/o'chirish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)
    content_type = post_data.get('content_type', 'photo')
    
    current_spoiler = post_data.get('has_spoiler', False)
    new_spoiler = not current_spoiler
    post_data['has_spoiler'] = new_spoiler
    await state.update_data(post_data=post_data)
    
    if new_spoiler:
        alert_text = get_text('spoiler_enabled_msg', lang)
    else:
        alert_text = get_text('spoiler_disabled_msg', lang)
    
    await callback.answer(alert_text)
    
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    
    # Postni yangilash (faqat configuring_post holatida)
    current_state = await state.get_state()
    if current_state == PostCreation.configuring_post:
        await redraw_post_with_callback(callback, state)
    
    has_caption = bool(post_data.get('caption'))
    await callback.message.edit_reply_markup(
        reply_markup=get_media_settings_inline_kb(
            lang,
            has_spoiler=new_spoiler,
            is_paid=is_paid,
            show_caption_above=show_caption_above,
            has_caption=has_caption,
            content_type=content_type
        )
    )


@reply_router.callback_query(PostCreation.configuring_post, F.data == "media_toggle_paid")
@reply_router.callback_query(PostCreation.waiting_for_media_settings, F.data == "media_toggle_paid")
async def post_media_toggle_paid(callback: types.CallbackQuery, state: FSMContext):
    """Post tahrirlashda pulli mediani yoqish/o'chirish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)
    content_type = post_data.get('content_type', 'photo')
    
    current_paid = post_data.get('is_paid', False)
    new_paid = not current_paid
    post_data['is_paid'] = new_paid
    if new_paid and not post_data.get('paid_price'):
        post_data['paid_price'] = 1
        
    await state.update_data(post_data=post_data)
    
    if new_paid:
        alert_text = get_text('paid_media_enabled_msg', lang).format(price=post_data.get('paid_price', 1))
    else:
        alert_text = get_text('paid_media_disabled_msg', lang)
    
    await callback.answer(alert_text)
    
    has_spoiler = post_data.get('has_spoiler', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))
    
    # Current state ni tekshirish
    current_state = await state.get_state()
    
    if current_state == PostCreation.configuring_post:
        # Inline keyboard xabarini o'chirish (faqat configuring_post da)
        try:
            await callback.message.delete()
        except Exception:
            pass
        # Postni yangilash (yangi post yuborish)
        await redraw_post_with_callback(callback, state)
    else:
        # Settings menyusida bo'lsak, faqat inline klaviaturani yangilaymiz
        await callback.message.edit_reply_markup(
            reply_markup=get_media_settings_inline_kb(
                lang,
                has_spoiler=has_spoiler,
                is_paid=new_paid,
                show_caption_above=show_caption_above,
                has_caption=has_caption,
                content_type=content_type
            )
        )


@reply_router.callback_query(PostCreation.configuring_post, F.data == "media_set_price")
async def post_media_set_price_callback(callback: types.CallbackQuery, state: FSMContext):
    """Inline klaviaturadan narx o'rnatishni boshlash"""
    lang = await get_user_language(callback.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})
    
    await state.set_state(PostCreation.waiting_for_paid_price)
    
    # Faqat orqaga tugmasi ko'rsatiladi
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('back_btn', lang), callback_data="media_price_back")
    
    await callback.message.answer(
        get_text('paid_media_stars_prompt', lang),
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@reply_router.callback_query(PostCreation.configuring_post, F.data == "back_to_post_settings")
@reply_router.callback_query(PostCreation.waiting_for_media_settings, F.data == "back_to_post_settings")
async def back_from_media_to_post_settings(callback: types.CallbackQuery, state: FSMContext):
    """Media sozlamalaridan post sozlamalariga qaytish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)
    
    content_type = post_data.get('content_type', 'text')
    has_caption = bool(post_data.get('caption'))
    is_paid = post_data.get('is_paid', False)
    
    # Oldingi state ni tekshirish
    previous_state = await state.get_state()
    
    # State ni configuring_post ga o'tkazish
    await state.set_state(PostCreation.configuring_post)
    
    if previous_state == PostCreation.configuring_post:
        # Asosiy post sozlamalari (inline klaviatura)
        keyboard = create_post_options_keyboard(
            content_type=content_type,
            lang=lang
        )
        
        if keyboard:
            await callback.message.edit_text(
                get_text('post_settings_msg', lang),
                reply_markup=keyboard
            )
        else:
            try:
                await callback.message.delete()
            except Exception:
                pass
    else:
        # waiting_for_media_settings dan qaytish - inline xabarni o'chirib, reply klaviaturani qaytarish
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        # Asosiy menyuni reply klaviatura bilan ko'rsatish
        from post_handlers.xreply_keyboard import get_post_settings_kb
        await callback.message.answer(
            get_text('post_settings_msg', lang),
            reply_markup=get_post_settings_kb(content_type, has_caption, lang, is_paid=is_paid)
        )
    
    await callback.answer()


# ==================== MEDIA SOZLAMALARI (Reply Keyboard) ====================

async def redraw_post_with_settings(message: types.Message, state: FSMContext, answer_text: str = None, hide_reply_keyboard: bool = False, hide_inline_keyboard: bool = False):
    """Postni yangilangan sozlamalar bilan qayta chizish (o'chirmasdan tahrirlash)"""
    data = await state.get_data()
    buttons_matrix = data.get("buttons_matrix", [])
    post_data = data.get("post_data", {})
    if not post_data:
        return

    chat_id = post_data.get("chat_id")
    message_id = post_data.get("message_id")
    
    user_id = message.from_user.id if message.from_user else post_data.get("user_id")
    lang = await get_user_language(user_id)
    
    new_keyboard = generate_post_keyboard(buttons_matrix, lang)
    
    # Media sozlamalarini olish
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    
    has_caption = bool(post_data.get('caption'))
    
    # content_type va is_paid ni post_data dan olish
    content_type = post_data.get('content_type')
    is_paid = post_data.get('is_paid', False)
    
    # Inline keyboard o'rniga Reply keyboard ishlatamiz
    settings_keyboard = get_media_settings_kb(
        lang=lang, 
        has_spoiler=has_spoiler, 
        show_caption_above=show_caption_above, 
        has_caption=has_caption,
        content_type=content_type,
        is_paid=is_paid
    )

    # Post mavjudligini tekshirish
    if not chat_id or not message_id:
        # Agar post hali yuborilmagan bo'lsa, uni yuborish
        await send_new_post_with_settings(message, state, post_data, new_keyboard)
        try:
            await message.delete()
        except Exception:
            pass
        
        # Menyuni ostida ko'rsatish
        final_text = answer_text if answer_text else get_text('media_settings_msg', lang)
        
        # Reply keyboardni doim ko'rsatamiz (agar hide_reply_keyboard False bo'lsa)
        if not hide_reply_keyboard:
            await message.answer(final_text, reply_markup=settings_keyboard)
        else:
            await message.answer(final_text)
        
        # Sobiq: configure_post ga qaytib ketmasa kerak, chunki biz Settings menyumiz
        # Lekin agar qaysidir handler bizni bu yerga Configuring_post'dan yuborgan bo'lsa...
        # Hozircha waiting_for_media_settings da qolamiz.
        return

    file_id = post_data.get("file_id")
    caption = post_data.get("caption")
    parse_mode = post_data.get("parse_mode", 'HTML')

    # Media turlari uchun edit_message_media dan foydalanish
    try:
        if (is_paid and content_type in ['photo', 'video']) or content_type == 'paid_media':
            # Pulli media uchun send_paid_media ishlatish kerak, lekin edit_media orqali bo'lmaydi
            # Shuning uchun eski postni o'chirib, yangisini yuboramiz
            try:
                await message.bot.delete_message(chat_id, message_id)
            except Exception:
                pass
            await send_new_post_with_settings(message, state, post_data, new_keyboard)
        elif content_type == 'photo':
            media = InputMediaPhoto(
                media=file_id,
                caption=caption,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
            await message.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=new_keyboard
            )
        elif content_type == 'video':
            media = InputMediaVideo(
                media=file_id,
                caption=caption,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
            await message.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=new_keyboard
            )
        elif content_type == 'audio':
            media = InputMediaAudio(
                media=file_id,
                caption=caption,
                parse_mode=parse_mode
            )
            await message.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=new_keyboard
            )
        elif content_type == 'document':
            media = InputMediaDocument(
                media=file_id,
                caption=caption,
                parse_mode=parse_mode
            )
            await message.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=new_keyboard
            )
        elif content_type == 'animation':
            media = InputMediaAnimation(
                media=file_id,
                caption=caption,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
            await message.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=new_keyboard
            )
        elif content_type == 'text':
            # Text uchun edit_message_text dan foydalanish
            await message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=caption or post_data.get('text', ''),
                parse_mode=parse_mode,
                reply_markup=new_keyboard
            )
        else:
            # Boshqa turlar uchun faqat klaviaturani o'zgartirish
            await message.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=new_keyboard
            )
        
        # Post yangilangandan so'ng menyuni ostida ko'rsatish
        final_text = answer_text if answer_text else get_text('media_settings_msg', lang)
        if hide_reply_keyboard:
            await message.answer(final_text)
        else:
            await message.answer(final_text, reply_markup=settings_keyboard)
        
        try:
            await message.delete()
        except Exception:
            pass
        return
    except Exception as e:
        logging.error(f"Postni tahrirlab bo'lmadi: {e}")
        # Xatolik yuz berganda (masalan, edit_media ishlamasa) yangisini yuboramiz
        try:
            await message.bot.delete_message(chat_id, message_id)
        except Exception:
            pass
        await send_new_post_with_settings(message, state, post_data, new_keyboard)
        
        # Menyuni ostida ko'rsatish
        final_text = answer_text if answer_text else get_text('media_settings_msg', lang)
        if hide_reply_keyboard or hide_inline_keyboard:
            await message.answer(final_text)
        else:
            await message.answer(final_text, reply_markup=settings_keyboard)
        
        try:
            await message.delete()
        except Exception:
            pass


async def send_new_post_with_settings(message: types.Message, state: FSMContext, post_data: dict, keyboard):
    """Yangilangan sozlamalar bilan yangi post yuborish"""
    content_type = post_data.get('content_type')
    file_id = post_data.get("file_id")
    caption = post_data.get("caption")
    parse_mode = post_data.get("parse_mode", 'HTML')
    
    # Asosiy parametrlar
    media_kwargs = {
        "reply_markup": keyboard,
        "parse_mode": parse_mode,
    }
    
    if content_type in ['photo', 'video', 'animation']:
        media_kwargs["has_spoiler"] = post_data.get('has_spoiler', False)
        media_kwargs["show_caption_above_media"] = post_data.get('show_caption_above_media', False)
    
    try:
        sent_message = None
        
        # Pulli media (Stars)
        if (post_data.get('is_paid', False) and content_type in ['photo', 'video']) or content_type == 'paid_media':
            stars = post_data.get('paid_price', 1)
            from aiogram.types import InputPaidMediaPhoto, InputPaidMediaVideo
            
            if content_type == 'paid_media':
                media_types = post_data.get('paid_media_types', [])
                file_ids = post_data.get('paid_media_file_ids', [])
                input_media_list = []
                for m_type, f_id in zip(media_types, file_ids):
                    if m_type == 'photo':
                        input_media_list.append(InputPaidMediaPhoto(media=f_id))
                    else:
                        input_media_list.append(InputPaidMediaVideo(media=f_id))
            else:
                if content_type == 'photo':
                    input_media_list = [InputPaidMediaPhoto(media=file_id)]
                else:
                    input_media_list = [InputPaidMediaVideo(media=file_id)]
                    
            sent_message = await message.bot.send_paid_media(
                message.chat.id, 
                stars, 
                input_media_list, 
                caption=caption, 
                parse_mode=parse_mode, 
                reply_markup=keyboard,
                show_caption_above_media=post_data.get('show_caption_above_media', False)
            )
        else:
            if content_type == 'photo':
                sent_message = await message.bot.send_photo(message.chat.id, file_id, caption=caption, **media_kwargs)
            elif content_type == 'video':
                sent_message = await message.bot.send_video(message.chat.id, file_id, caption=caption, **media_kwargs)
            elif content_type == 'audio':
                sent_message = await message.bot.send_audio(message.chat.id, file_id, caption=caption, **media_kwargs)
            elif content_type == 'document':
                sent_message = await message.bot.send_document(message.chat.id, file_id, caption=caption, **media_kwargs)
            elif content_type == 'animation':
                sent_message = await message.bot.send_animation(message.chat.id, file_id, caption=caption, **media_kwargs)
            elif content_type == 'voice':
                sent_message = await message.bot.send_voice(message.chat.id, file_id, caption=caption, **media_kwargs)
            elif content_type == 'video_note':
                sent_message = await message.bot.send_video_note(message.chat.id, file_id, reply_markup=keyboard)
            elif content_type == 'sticker':
                sent_message = await message.bot.send_sticker(message.chat.id, file_id, reply_markup=keyboard)
            elif content_type == 'text':
                sent_message = await message.bot.send_message(message.chat.id, caption, **media_kwargs)
            elif content_type == 'poll':
                sent_message = await message.bot.send_poll(
                    message.chat.id,
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
                sent_message = await message.bot.send_dice(
                    message.chat.id,
                    emoji=post_data.get('dice_emoji', '🎲'),
                    reply_markup=keyboard
                )

        if sent_message:
            post_data['chat_id'] = message.chat.id
            post_data['message_id'] = sent_message.message_id
            await state.update_data(post_data=post_data)
    except Exception as e:
        logging.error(f"Postni qayta yuborishda xatolik: {e}")


@reply_router.message(
    PostCreation.configuring_post,
    LocalizedText('media_settings_btn')
)
async def open_media_settings(message: Message, state: FSMContext):
    """Media sozlamalari menyusini ochish"""
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})
    
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    
    await state.set_state(PostCreation.waiting_for_media_settings)
    
    settings_text = get_text('media_settings_msg', lang)
    has_caption = bool(post_data.get('caption'))
    await message.answer(
        settings_text,
        reply_markup=get_media_settings_inline_kb(lang, has_spoiler=has_spoiler, is_paid=is_paid, show_caption_above=show_caption_above, has_caption=has_caption)
    )


@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('position_btn')
)
async def open_position_settings(message: Message, state: FSMContext):
    """Eski funksiya - endi kerak emas, lekin backward compatibility uchun saqlaymiz"""
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})
    
    current_position = post_data.get('show_caption_above_media', False)
    position_state = 'above' if current_position else 'below'
    
    await state.set_state(PostCreation.waiting_for_media_settings)
    
    # To'g'ridan-to'g'ri media sozlamalarini ko'rsatamiz
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    
    has_caption = bool(post_data.get('caption'))
    content_type = post_data.get('content_type', 'photo')
    await message.answer(
        get_text('media_settings_msg', lang),
        reply_markup=get_media_settings_kb(lang, has_spoiler=has_spoiler, show_caption_above=current_position, has_caption=has_caption, content_type=content_type, is_paid=is_paid)
    )


@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('position_above_btn')
)
@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('position_below_btn')
)
async def toggle_position(message: Message, state: FSMContext):
    """Joylashuvni toggle qilish (yuqoriga/pastga)"""
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})
    
    # Hozirgi joylashuvni tekshirish va teskarisiga o'zgartirish
    current_position = post_data.get('show_caption_above_media', False)
    new_position = not current_position
    
    post_data['show_caption_above_media'] = new_position
    await state.update_data(post_data=post_data)
    
    # Muvaffaqiyat xabarini tayyorlash
    if new_position:
        position_text = get_text('position_above_btn', lang)
    else:
        position_text = get_text('position_below_btn', lang)
    
    success_text = get_text('position_set_msg', lang).format(position=position_text)
    
    # Media sozlamalarini yangilangan holda ko'rsatish
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    
    has_caption = bool(post_data.get('caption'))
    content_type = post_data.get('content_type', 'photo')
    await message.answer(
        success_text,
        reply_markup=get_media_settings_kb(lang, has_spoiler=has_spoiler, show_caption_above=new_position, has_caption=has_caption, content_type=content_type, is_paid=is_paid)
    )
    
    # Postni ham yangilash
    await redraw_post_with_settings(message, state)


@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('spoiler_btn')
)
@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('spoiler_enabled_btn')
)
async def toggle_spoiler(message: Message, state: FSMContext):
    """Spoiler ni yoqish/o'chirish"""
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})
    
    # Toggle spoiler
    current_spoiler = post_data.get('has_spoiler', False)
    post_data['has_spoiler'] = not current_spoiler
    await state.update_data(post_data=post_data)
    
    if post_data['has_spoiler']:
        success_text = get_text('spoiler_enabled_msg', lang)
    else:
        success_text = get_text('spoiler_disabled_msg', lang)
    
    # Postni qayta chizish
    await redraw_post_with_settings(message, state, success_text)


@reply_router.message(
    PostCreation.configuring_post,
    LocalizedText('paid_media_btn')
)
@reply_router.message(
    PostCreation.configuring_post,
    LocalizedText('paid_media_enabled_btn')
)
@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('paid_media_btn')
)
@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('paid_media_enabled_btn')
)
async def toggle_paid_media(message: Message, state: FSMContext):
    """Pulli mediani yoqish/o'chirish"""
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})
    
    current_paid = post_data.get('is_paid', False)
    new_paid = not current_paid
    
    post_data['is_paid'] = new_paid
    if new_paid and not post_data.get('paid_price'):
        post_data['paid_price'] = 1 
        
    await state.update_data(post_data=post_data)
    
    if new_paid:
        success_text = get_text('paid_media_enabled_msg', lang).format(price=post_data.get('paid_price', 1))
    else:
        success_text = get_text('paid_media_disabled_msg', lang)
    
    # Kelib chiqish nuqtasiga qarab klaviaturani yangilash
    current_state = await state.get_state()
    if current_state == PostCreation.configuring_post:
        # Asosiy menyuda bo'lsak, asosiy menyuni qayta chiqaramiz
        has_caption = bool(post_data.get('caption'))
        content_type = post_data.get('content_type', 'text')
        await message.answer(
            success_text,
            reply_markup=get_post_settings_kb(content_type, has_caption, lang, is_paid=new_paid)
        )
    else:
        # Settings menyusida bo'lsak (eskicha), o'sha yerda qolamiz
        await redraw_post_with_settings(message, state, success_text)

@reply_router.message(
    PostCreation.configuring_post,
    LocalizedText('poll_settings_btn')
)
@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('poll_settings_btn')
)
async def open_poll_settings_reply(message: Message, state: FSMContext):
    """Poll sozlamalarini ochish"""
    # Callback handlerini chaqiramiz
    # Eslatma: post_poll_settings_callback parametri callback bo'lgani uchun 
    # biz unga messageni callback kabi uzatolmaymiz (callback.message o'rniga message ishlatish kerak bo'ladi)
    # Shuning uchun kodni takrorlamaslik uchun uni biroz o'zgartiramiz:
    lang = await get_user_language(message.from_user.id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="❓ Oddiy so'rovnoma", callback_data="create_poll:regular")
    builder.button(text="❓ Quiz", callback_data="create_poll:quiz")
    builder.button(text=get_text('back_btn', lang), callback_data="back_to_post_settings")
    builder.adjust(2, 1)
    
    await message.answer(
        "<b>❓ Viktorina turini tanlang:</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@reply_router.message(
    PostCreation.configuring_post,
    LocalizedText('location_settings_btn')
)
@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('location_settings_btn')
)
async def open_location_settings_reply(message: Message, state: FSMContext):
    """Location sozlamalarini ochish"""
    lang = await get_user_language(message.from_user.id)
    await message.answer("📍 Joylashuv sozlamalari yaqin orada qo'shiladi.")

@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('watermark_btn')
)
async def open_watermark_settings_reply(message: Message, state: FSMContext):
    """Watermark sozlamalarini ochish"""
    from post_handlers.watermark_handler import watermark_settings_handler
    # watermark_settings_handler ko'p hollarda reply keyboard handlers sifatida ishlaydi
    await watermark_settings_handler(message, state)


@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('paid_media_price_btn')
)
async def prompt_paid_price(message: Message, state: FSMContext):
    """Pulli media narxini so'rash (Reply keyboarddan)"""
    lang = await get_user_language(message.from_user.id)
    await state.set_state(PostCreation.waiting_for_paid_price)
    
    # Inline orqaga tugmasi
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('back_btn', lang), callback_data="media_price_back")
    
    # Reply keyboardni o'chiramiz va inline tugma bilan xabar yuboramiz
    await message.answer(
        get_text('paid_media_stars_prompt', lang),
        reply_markup=builder.as_markup()
    )


@reply_router.callback_query(PostCreation.configuring_post, F.data == "media_set_price")
async def post_media_set_price_callback(callback: types.CallbackQuery, state: FSMContext):
    """Inline klaviaturadan narx o'rnatishni boshlash (Tahrirlash orqali)"""
    lang = await get_user_language(callback.from_user.id)
    await state.set_state(PostCreation.waiting_for_paid_price)
    
    # Inline orqaga tugmasi
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('back_btn', lang), callback_data="media_price_back")
    
    # Xabarni tahrirlaymiz
    await callback.message.edit_text(
        get_text('paid_media_stars_prompt', lang),
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@reply_router.callback_query(PostCreation.waiting_for_paid_price, F.data == "media_price_back")
async def back_from_price_callback(callback: types.CallbackQuery, state: FSMContext):
    """Narx kiritishdan qaytish (Inline tugma orqali)"""
    await state.set_state(PostCreation.waiting_for_media_settings)
    
    # Media sozlamalarini qayta ochish
    lang = await get_user_language(callback.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})
    
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))
    
    # Reply keyboardni qaytarish uchun answer yuboramiz (edit_text reply keyboard qo'sha olmaydi)
    await callback.message.delete()
    await callback.message.answer(
        get_text('media_settings_msg', lang),
        reply_markup=get_media_settings_inline_kb(lang, has_spoiler, is_paid, show_caption_above, has_caption)
    )
    await callback.answer()
        

@reply_router.message(
    PostCreation.waiting_for_paid_price,
    F.text,
    ~LocalizedText('back_btn')
)
async def set_paid_price(message: Message, state: FSMContext):
    """Pulli media narxini o'rnatish"""
    lang = await get_user_language(message.from_user.id)
    
    try:
        price = int(message.text.strip())
        if price < 1:
            raise ValueError("Narx musbat bo'lishi kerak")
        if price > 25000:
            await message.answer("❌ Maksimal narx 25000 ⭐ bo'lishi kerak. Iltimos, qayta urinib ko'ring.")
            return
        
        data = await state.get_data()
        post_data = data.get("post_data", {})
        
        post_data['is_paid'] = True
        post_data['paid_price'] = price
        await state.update_data(post_data=post_data)
        await state.set_state(PostCreation.configuring_post)
        
        success_text = get_text('paid_media_enabled_msg', lang).format(price=price)
        await redraw_post_with_settings(message, state, success_text, hide_reply_keyboard=True, hide_inline_keyboard=False)
        
    except ValueError:
        data = await state.get_data()
        post_data = data.get("post_data", {})
        
        builder = InlineKeyboardBuilder()
        builder.button(text=get_text('back_btn', lang), callback_data="media_price_back")
        
        await message.answer(
            "❌ Iltimos, to'g'ri narx kiriting (masalan: 50)",
            reply_markup=builder.as_markup()
        )



@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('back_btn')
)
@reply_router.message(
    PostCreation.waiting_for_position,
    LocalizedText('back_btn')
)
@reply_router.message(
    PostCreation.waiting_for_paid_price,
    LocalizedText('back_btn')
)
async def back_from_media_settings(message: Message, state: FSMContext):
    """Media sozlamalaridan qaytish"""
    # Agar narx so'ralayotgan bo'lsa, media sozlamalariga qaytish
    current_state = await state.get_state()
    if current_state == PostCreation.waiting_for_paid_price:
        await open_media_settings(message, state)
        return

    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})
    
    await state.set_state(PostCreation.configuring_post)
    
    content_type = post_data.get('content_type', 'text')
    has_caption = bool(post_data.get('caption'))
    is_paid = post_data.get('is_paid', False)
    
    await message.answer(
        get_text('back_to_settings_msg', lang),
        reply_markup=get_post_settings_kb(content_type, has_caption, lang, is_paid=is_paid)
    )


# ===== Yangi Post Options Keyboard uchun callback handlers =====

@reply_router.callback_query(PostCreation.configuring_post, F.data == "post_get_buttons")
async def post_get_buttons_callback(callback: types.CallbackQuery, state: FSMContext):
    """Tugma sozlamalarini ochish"""
    lang = await get_user_language(callback.from_user.id)
    data = await state.get_data()
    buttons_matrix = data.get("buttons_matrix", [])
    post_data = data.get("post_data", {})
    
    has_real_buttons = any(any(btn and not btn.get('is_placeholder') for btn in row) for row in buttons_matrix)
    
    if not has_real_buttons:
        await callback.answer(get_text('no_buttons_msg', lang), show_alert=True)
    else:
        response_text = get_text('your_buttons_msg', lang) + "\n\n"
        button_count = 1
        from xdata_handlers.database import get_text_button_content
        for row in buttons_matrix:
            for button in row:
                if button and not button.get('is_placeholder'):
                    if button.get('type') == 'text_btn':
                        content = await get_text_button_content(button['db_id'])
                        sub_text = content.get('content_sub', 'N/A') if content else 'N/A'
                        nonsub_text = content.get('content_nonsub', 'N/A') if content else 'N/A'
                        
                        response_text += f"{button_count}. {button['text']} :\n"
                        response_text += f"obunachilar uchun : {sub_text}\n"
                        response_text += f"obuntasizlar uchun : {nonsub_text}\n\n"
                    else:
                        button_url = button.get('url', 'URL missing')
                        response_text += f"{button_count}. {button['text']} = {button_url}\n"
                    button_count += 1
        await callback.answer(response_text.strip(), show_alert=True)
    await callback.answer()


@reply_router.callback_query(PostCreation.configuring_post, F.data == "post_edit_content")
async def post_edit_content_callback(callback: types.CallbackQuery, state: FSMContext):
    """Postni tahrirlash uchun content so'rash"""
    lang = await get_user_language(callback.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})
    
    await state.set_state(PostCreation.waiting_for_content)
    await callback.message.edit_text(
        get_text('ask_new_content_msg', lang),
        reply_markup=get_edit_content_kb(post_data, lang)
    )
    await callback.answer()


@reply_router.callback_query(PostCreation.configuring_post, F.data == "post_media_type")
async def post_media_type_callback(callback: types.CallbackQuery, state: FSMContext):
    """Media turini o'zgartirish"""
    lang = await get_user_language(callback.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})
    
    # Media turini o'zgartirish uchun menyuni ko'rsatish
    builder = InlineKeyboardBuilder()
    builder.button(text="📷 Foto", callback_data="change_media_type:photo")
    builder.button(text="🎥 Video", callback_data="change_media_type:video")
    builder.button(text="🎵 Audio", callback_data="change_media_type:audio")
    builder.button(text="📄 Hujjat", callback_data="change_media_type:document")
    builder.button(text=get_text('back_btn', lang), callback_data="back_to_post_settings")
    builder.adjust(2, 2, 1)
    
    await callback.message.edit_text(
        "<b>📎 Media turini tanlang:</b>",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@reply_router.callback_query(PostCreation.configuring_post, F.data == "post_poll_settings")
async def post_poll_settings_callback(callback: types.CallbackQuery, state: FSMContext):
    """Viktorina (poll) sozlamalari"""
    lang = await get_user_language(callback.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})
    
    # Viktorina sozlamalari uchun keyboard
    builder = InlineKeyboardBuilder()
    builder.button(text="❓ Oddiy so'rovnoma", callback_data="create_poll:regular")
    builder.button(text="❓ Quiz", callback_data="create_poll:quiz")
    builder.button(text=get_text('back_btn', lang), callback_data="back_to_post_settings")
    builder.adjust(2, 1)
    
    await callback.message.edit_text(
        "<b>❓ Viktorina turini tanlang:</b>",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


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


# ===== Debug handler - barcha xabarlarni log qilish (oxirida bo'lishi kerak) =====
@reply_router.message(F.text)
async def debug_handler(message: Message, state: FSMContext):
    """Debug uchun - barcha xabarlarni log qilish"""
    current_state = await state.get_state()
    logging.info(f"DEBUG: Received text: '{message.text}', State: {current_state}, User: {message.from_user.id}")



