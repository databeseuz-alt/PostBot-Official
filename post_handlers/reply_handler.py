from contextlib import suppress
from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder

from post_handlers.post_handler import PostCreation
from post_handlers.xreply_keyboard import (
    get_main_menu, get_cancel_kb, get_post_settings_kb,
    get_button_creation_cancel_kb, get_edit_content_kb, get_back_button_kb
)
from aiogram.types import Message, InputMediaPhoto, InputMediaVideo, InputMediaAudio, InputMediaDocument, InputMediaAnimation
from post_handlers.xinline_keyboard import (
    generate_preview_keyboard,
    generate_post_keyboard,
    get_settings_menu_inline_kb
)
from post_handlers.media_handler import redraw_post_with_callback, send_new_post_with_settings
from xdata_handlers.database import get_user_language
from xdata_handlers.translator import get_text
from post_handlers.localize_filter import LocalizedText

reply_router = Router()
callback_router = Router()

@reply_router.callback_query(PostCreation.configuring_post, F.data == "cancel_post_creation")
async def cancel_post_creation_callback(callback: types.CallbackQuery, state: FSMContext):
    """Post yaratishni bekor qilish"""
    from post_handlers.xreply_keyboard import get_main_menu
    lang = await get_user_language(callback.from_user.id)

    await state.clear()

    await callback.message.edit_text(
        "❌ Post bekor qilindi",
        reply_markup=get_main_menu(lang)
    )
    await callback.answer()

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
        await message.answer(get_text('post_not_found_msg', lang))
        return

    await message.answer(get_text('preview_title_msg', lang))

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
            is_paid = post_data.get('is_paid', False)
            paid_price = post_data.get('paid_price', 1)
            if is_paid:
                from aiogram.types import InputPaidMediaPhoto
                await message.answer_paid_media(
                    star_count=paid_price,
                    media=[InputPaidMediaPhoto(media=file_id)],
                    caption=caption,
                    parse_mode=parse_mode,
                    show_caption_above_media=show_caption_above,
                    reply_markup=preview_keyboard
                )
            else:
                await message.answer_photo(
                    file_id,
                    caption=caption,
                    reply_markup=preview_keyboard,
                    parse_mode=parse_mode,
                    has_spoiler=has_spoiler,
                    show_caption_above_media=show_caption_above
                )
        elif content_type == 'video':
            is_paid = post_data.get('is_paid', False)
            paid_price = post_data.get('paid_price', 1)
            if is_paid:
                from aiogram.types import InputPaidMediaVideo
                await message.answer_paid_media(
                    star_count=paid_price,
                    media=[InputPaidMediaVideo(media=file_id)],
                    caption=caption,
                    parse_mode=parse_mode,
                    show_caption_above_media=show_caption_above,
                    reply_markup=preview_keyboard
                )
            else:
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

    except Exception as e:
        await message.answer(get_text('preview_error_msg', lang))


@reply_router.message(
    PostCreation.configuring_post,
    LocalizedText('settings_btn')
)
@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('settings_btn')
)
async def settings_menu_handler(message: types.Message, state: FSMContext):
    """Sozlamalar tugmasi - sozlamalar menyusini ko'rsatish"""
    data = await state.get_data()
    post_data = data.get('post_data', {})
    lang = await get_user_language(message.from_user.id)

    content_type = post_data.get('content_type', 'text')

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
        await message.answer(get_text('post_not_found_msg', lang))
        return

    has_buttons = False
    button_list = []

    for row in buttons_matrix:
        for btn in row:
            if btn and not btn.get('is_placeholder'):
                has_buttons = True
                button_list.append(btn)

    if not has_buttons:
        instructions = get_text('no_buttons_added_msg', lang)
        await message.answer(instructions)
        return

    response_text = get_text('your_buttons_list_msg', lang) + "\n\n"
    count = 1

    for btn in button_list:
        btn_text = btn.get('text', 'Tugma')
        btn_type = btn.get('type', 'url')

        if btn_type == 'text_btn':
            sub_content = btn.get('sub_content', '')
            nonsub_content = btn.get('nonsub_content', '')
            response_text += f"{count}. {btn_text} :\n"
            response_text += f"{get_text('button_type_text_btn_sub', lang)} = {sub_content}\n"
            response_text += f"{get_text('button_type_text_btn_nonsub', lang)} = {nonsub_content}\n"
        elif btn_type == 'reaction':
            response_text += f"{count}. {btn_text} = {get_text('button_value_none', lang)}\n"
        else:
            btn_url = btn.get('url', 'URL mavjud emas')
            response_text += f"{count}. {btn_text} = {btn_url}\n"

        count += 1

    await message.answer(response_text)

@reply_router.message(
    PostCreation.configuring_post,
    LocalizedText('auto_signature_btn')
)
@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('auto_signature_btn')
)
async def auto_signature_reply_handler(message: types.Message, state: FSMContext):
    """Avto imzo tugmasi - sozlamalarni ko'rsatish"""
    from post_handlers.signature_handler import show_auto_signature_settings_reply
    await show_auto_signature_settings_reply(message, state)

@reply_router.message(
    PostCreation.configuring_post,
    LocalizedText('media_settings_btn')
)
@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('media_settings_btn')
)
async def media_settings_reply_handler(message: types.Message, state: FSMContext):
    """Media sozlamalari tugmasi - inline klaviaturani ko'rsatish"""
    from post_handlers.media_handler import open_media_settings_from_reply
    await open_media_settings_from_reply(message, state)

@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('get_buttons_btn')
)
async def get_buttons_handler_media_state(message: types.Message, state: FSMContext):
    """Tugma tugmasi - waiting_for_media_settings state'da ham ishlaydi"""
    await get_buttons_handler(message, state)

@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('preview_btn')
)
async def preview_post_handler_media_state(message: types.Message, state: FSMContext, bot: Bot):
    """Ko'rish tugmasi - waiting_for_media_settings state'da ham ishlaydi"""
    await preview_post_handler(message, state, bot)

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

    await state.set_state(PostCreation.waiting_for_content)

    if content_type == 'text':
        await message.answer(
            get_text('ask_new_content_msg', lang),
            reply_markup=get_back_button_kb(lang)
        )
    else:
        from post_handlers.xreply_keyboard import get_edit_content_kb
        await message.answer(
            get_text('ask_new_content_msg', lang),
            reply_markup=get_edit_content_kb(post_data, lang)
        )


@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('edit_content_btn')
)
async def edit_content_handler_media_state(message: types.Message, state: FSMContext):
    """Tahrirlash tugmasi - waiting_for_media_settings state'da ham ishlaydi"""
    await edit_content_handler(message, state)
