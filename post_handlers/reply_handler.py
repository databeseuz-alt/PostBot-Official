#--- START OF FILE post_handlers/reply_handler.py ---
import logging
from contextlib import suppress
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from post_handlers.vpost_states import PostCreation
from post_handlers.xreply_keyboard import get_main_menu, get_cancel_kb, get_post_settings_kb, get_button_creation_cancel_kb
from post_handlers.xinline_keyboard import (
    generate_preview_keyboard, PostSettingsCallbackFactory, create_post_options_keyboard,
    create_post_parse_mode_keyboard, create_post_url_preview_keyboard
)
from xdata_handlers.database import get_user_language, update_user_post_settings
from xdata_handlers.translator import get_text
from post_handlers.localize_filter import LocalizedText

reply_router = Router()

#=============================================================================
# POSTNI SOZLASH MENYUSI HANDLERLARI
#=============================================================================

@reply_router.message(PostCreation.configuring_post, LocalizedText('btn_options'))
async def options_menu_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(message.from_user.id)

    if 'last_options_message_id' in data:
        with suppress(TelegramBadRequest):
            await message.bot.delete_message(message.chat.id, data['last_options_message_id'])

    content_type = post_data.get('content_type', 'text')
    has_caption = bool(post_data.get('caption'))
    current_parse_mode = post_data.get('parse_mode')
    url_preview_disabled = post_data.get("disable_web_page_preview", False)

    # Agar faqat matn formati sozlamasi mavjud bo'lsa (rasm/video/voice izohi uchun)
    if (content_type != 'text') and has_caption:
        keyboard = create_post_parse_mode_keyboard(current_parse_mode, show_back_button=False, lang=lang)
        text = get_text('select_text_format', lang)
    else:
        keyboard = create_post_options_keyboard(
            content_type=content_type,
            has_caption=has_caption,
            current_parse_mode=current_parse_mode,
            url_preview_disabled=url_preview_disabled,
            lang=lang
        )
        text = get_text('post_additions', lang)

    options_msg = await message.answer(text, reply_markup=keyboard)
    await state.update_data(last_options_message_id=options_msg.message_id)


@reply_router.message(PostCreation.configuring_post, LocalizedText('btn_get_buttons'))
async def get_buttons_handler(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    buttons_matrix = data.get("buttons_matrix", [])
    post_data = data.get("post_data", {})

    has_real_buttons = any(any(btn and not btn.get('is_placeholder') for btn in row) for row in buttons_matrix)

    reply_markup = get_post_settings_kb(
        content_type=post_data.get('content_type', 'text'),
        has_caption=bool(post_data.get('caption')),
        lang=lang
    )

    if not has_real_buttons:
        return await message.answer(
            get_text('no_buttons_yet', lang),
            reply_markup=reply_markup
        )

    response_text = get_text('your_buttons', lang) + "\n\n"
    button_count = 1
    for row in buttons_matrix:
        for button in row:
            if button and not button.get('is_placeholder'):
                response_text += f"{button_count}. {button['text']} = {button['url']}\n"
                button_count += 1
    await message.answer(
        response_text,
        reply_markup=reply_markup
    )

@reply_router.message(PostCreation.configuring_post, LocalizedText('btn_edit_content'))
async def edit_content_handler(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    await state.set_state(PostCreation.waiting_for_content)
    await message.answer(get_text('ask_for_new_content', lang), reply_markup=get_button_creation_cancel_kb(lang))

@reply_router.message(PostCreation.configuring_post, LocalizedText('btn_preview'))
async def preview_post_handler(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})
    buttons_matrix = data.get("buttons_matrix", [])

    if not post_data:
        return await message.answer(get_text('post_load_error', lang))

    reply_markup = get_post_settings_kb(
        content_type=post_data.get('content_type', 'text'),
        has_caption=bool(post_data.get('caption')),
        lang=lang
    )
    await message.answer(
        get_text('preview_title', lang),
        reply_markup=reply_markup
    )

    keyboard = generate_preview_keyboard(buttons_matrix)
    content_type = post_data.get('content_type')
    chat_id = message.chat.id
    file_id = post_data.get("file_id")
    text = post_data.get("text")
    caption = post_data.get("caption")
    parse_mode = post_data.get("parse_mode")
    disable_preview = post_data.get("disable_web_page_preview", False)

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
        if content_type == 'text':
            await message.bot.send_message(chat_id, text, **message_kwargs)
        elif content_type == 'photo':
            await message.bot.send_photo(chat_id, file_id, caption=caption, **media_kwargs)
        elif content_type == 'video':
            await message.bot.send_video(chat_id, file_id, caption=caption, **media_kwargs)
        elif content_type == 'audio':
            await message.bot.send_audio(chat_id, file_id, caption=caption, **media_kwargs)
        elif content_type == 'document':
            await message.bot.send_document(chat_id, file_id, caption=caption, **media_kwargs)
        # YANGI: Voice preview
        elif content_type == 'voice':
            await message.bot.send_voice(chat_id, file_id, caption=caption, **media_kwargs)
        elif content_type == 'video_note':
            await message.bot.send_video_note(chat_id, file_id, reply_markup=keyboard)
    except TelegramBadRequest as e:
        if "can't parse entities" in str(e).lower():
            error_mode = f"<code>{parse_mode or 'None'}</code>"
            await message.answer(get_text('parse_mode_error_preview', lang).format(error_mode=error_mode))
        else:
            logging.error(f"Previewda xatolik: {e}")
            await message.answer(get_text('preview_error', lang))
    except Exception as e:
        logging.error(f"Previewda kutilmagan xatolik: {e}")
        await message.answer(get_text('preview_error', lang))


@reply_router.message(PostCreation.configuring_post, LocalizedText('btn_cancel_full'))
async def cancel_post_creation_handler(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    await state.clear()
    await message.answer(
        get_text('action_canceled', lang),
        reply_markup=await get_main_menu(lang=lang, user_id=message.from_user.id)
    )

#=============================================================================
# OPTIONS INLINE TUGMALARI UCHUN HANDLERLAR
#=============================================================================

@reply_router.callback_query(PostCreation.configuring_post, PostSettingsCallbackFactory.filter(F.action == "show_parse_mode"))
async def show_parse_mode_options(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_mode = data.get("post_data", {}).get("parse_mode")
    lang = await get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        get_text('select_text_format', lang),
        reply_markup=create_post_parse_mode_keyboard(current_mode, show_back_button=True, lang=lang)
    )

@reply_router.callback_query(PostCreation.configuring_post, PostSettingsCallbackFactory.filter(F.action == "set_parse_mode"))
async def set_parse_mode(callback: types.CallbackQuery, state: FSMContext, callback_data: PostSettingsCallbackFactory):
    clicked_mode = callback_data.value

    data = await state.get_data()
    post_data = data.get("post_data", {})
    current_mode = post_data.get("parse_mode")

    if current_mode == clicked_mode:
        new_mode = None
    else:
        new_mode = clicked_mode

    # Lokal sozlamani (FSMContext ichida) har doim yangilaymiz
    post_data["parse_mode"] = new_mode
    await state.update_data(post_data=post_data)

    # --- O'ZGARISH BOSHLANDI ---
    # Rejimni tekshiramiz: agar tahrirlash rejimi bo'lmasa, global sozlamani yangilaymiz
    is_editing = "editing_post_code" in data
    if not is_editing:
        await update_user_post_settings(
            user_id=callback.from_user.id,
            parse_mode=new_mode,
            url_preview_disabled=post_data.get("disable_web_page_preview", False)
        )
    # --- O'ZGARISH TUGADI ---

    lang = await get_user_language(callback.from_user.id)
    if new_mode is None:
        await callback.answer(get_text('parse_mode_removed', lang))
    else:
        await callback.answer(get_text('parse_mode_selected', lang).format(mode=new_mode))

    content_type = post_data.get('content_type')
    show_back_button = (content_type == 'text')

    await callback.message.edit_reply_markup(reply_markup=create_post_parse_mode_keyboard(new_mode, show_back_button=show_back_button, lang=lang))


@reply_router.callback_query(PostCreation.configuring_post, PostSettingsCallbackFactory.filter(F.action == "show_url_preview"))
async def show_url_preview_options(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    is_disabled = data.get("post_data", {}).get("disable_web_page_preview", False)
    lang = await get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        get_text('url_preview_settings', lang),
        reply_markup=create_post_url_preview_keyboard(is_disabled, lang=lang)
    )

@reply_router.callback_query(PostCreation.configuring_post, PostSettingsCallbackFactory.filter(F.action == "set_url_preview"))
async def set_url_preview(callback: types.CallbackQuery, state: FSMContext, callback_data: PostSettingsCallbackFactory):
    is_disabled = callback_data.value == "true"

    data = await state.get_data()
    post_data = data.get("post_data", {})

    # Lokal sozlamani (FSMContext ichida) har doim yangilaymiz
    post_data["disable_web_page_preview"] = is_disabled
    await state.update_data(post_data=post_data)

    # --- O'ZGARISH BOSHLANDI ---
    # Rejimni tekshiramiz: agar tahrirlash rejimi bo'lmasa, global sozlamani yangilaymiz
    is_editing = "editing_post_code" in data
    if not is_editing:
        await update_user_post_settings(
            user_id=callback.from_user.id,
            parse_mode=post_data.get("parse_mode"),
            url_preview_disabled=is_disabled
        )
    # --- O'ZGARISH TUGADI ---

    lang = await get_user_language(callback.from_user.id)
    status_text = get_text('url_preview_disabled', lang) if is_disabled else get_text('url_preview_enabled', lang)
    await callback.answer(status_text)
    await callback.message.edit_reply_markup(reply_markup=create_post_url_preview_keyboard(is_disabled, lang=lang))


@reply_router.callback_query(PostCreation.configuring_post, PostSettingsCallbackFactory.filter(F.action == "back_to_options"))
async def back_to_options(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    keyboard = create_post_options_keyboard(
        content_type=post_data.get('content_type', 'text'),
        has_caption=bool(post_data.get('caption')),
        current_parse_mode=post_data.get('parse_mode'),
        url_preview_disabled=post_data.get("disable_web_page_preview", False),
        lang=lang
    )
    await callback.message.edit_text(
        get_text('post_additions', lang),
        reply_markup=keyboard
    )
    await callback.answer()

#--- END OF FILE post_handlers/reply_handler.py ---
