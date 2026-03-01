import logging
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from post_handlers.post_handler import PostCreation
from post_handlers.xinline_keyboard import (
    get_media_settings_inline_kb, get_settings_menu_inline_kb
)
from post_handlers.xreply_keyboard import get_post_settings_kb
from post_handlers.localize_filter import LocalizedText
from xdata_handlers.database import get_user_language
from xdata_handlers.translator import get_text

logger = logging.getLogger(__name__)
media_router = Router()


@media_router.callback_query(PostCreation.configuring_post, F.data == "post_media_settings")
@media_router.callback_query(PostCreation.waiting_for_media_settings, F.data == "post_media_settings")
async def post_media_settings_menu(callback: types.CallbackQuery, state: FSMContext):
    """Post tahrirlashda media sozlamalari menyusini ochish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)
    
    content_type = post_data.get('content_type', 'photo')
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))
    
    await state.set_state(PostCreation.waiting_for_media_settings)
    
    await callback.message.edit_text(
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
    await callback.answer()


@media_router.callback_query(PostCreation.configuring_post, F.data == "media_toggle_position")
@media_router.callback_query(PostCreation.waiting_for_media_settings, F.data == "media_toggle_position")
async def post_media_toggle_position(callback: types.CallbackQuery, state: FSMContext):
    """Post tahrirlashda joylashuvni almashtirish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)
    
    content_type = post_data.get('content_type', 'photo')
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))
    
    # Joylashuvni almashtirish
    post_data['show_caption_above_media'] = not show_caption_above
    await state.update_data(post_data=post_data)
    
    await state.set_state(PostCreation.waiting_for_media_settings)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_media_settings_inline_kb(
            lang=lang,
            has_spoiler=has_spoiler,
            is_paid=is_paid,
            show_caption_above=not show_caption_above,
            has_caption=has_caption,
            content_type=content_type
        )
    )
    await callback.answer()


@media_router.callback_query(PostCreation.configuring_post, F.data == "media_toggle_spoiler")
@media_router.callback_query(PostCreation.waiting_for_media_settings, F.data == "media_toggle_spoiler")
async def post_media_toggle_spoiler(callback: types.CallbackQuery, state: FSMContext):
    """Post tahrirlashda spoilerni yoqish/o'chirish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)
    
    content_type = post_data.get('content_type', 'photo')
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))
    
    # Spoilerni almashtirish
    post_data['has_spoiler'] = not has_spoiler
    await state.update_data(post_data=post_data)
    
    await state.set_state(PostCreation.waiting_for_media_settings)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_media_settings_inline_kb(
            lang=lang,
            has_spoiler=not has_spoiler,
            is_paid=is_paid,
            show_caption_above=show_caption_above,
            has_caption=has_caption,
            content_type=content_type
        )
    )
    await callback.answer()


@media_router.callback_query(PostCreation.configuring_post, F.data == "media_toggle_paid")
@media_router.callback_query(PostCreation.waiting_for_media_settings, F.data == "media_toggle_paid")
async def post_media_toggle_paid(callback: types.CallbackQuery, state: FSMContext):
    """Post tahrirlashda pulli mediani yoqish/o'chirish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)
    
    content_type = post_data.get('content_type', 'photo')
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))
    
    # Pulli mediani almashtirish
    new_paid = not is_paid
    post_data['is_paid'] = new_paid
    
    # Agar pulli media yoqilayotgan bo'lsa, narx so'ralishi mumkin
    if new_paid and not post_data.get('paid_price'):
        post_data['paid_price'] = 1  # Default narx
    
    await state.update_data(post_data=post_data)
    await state.set_state(PostCreation.waiting_for_media_settings)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_media_settings_inline_kb(
            lang=lang,
            has_spoiler=has_spoiler,
            is_paid=new_paid,
            show_caption_above=show_caption_above,
            has_caption=has_caption,
            content_type=content_type
        )
    )
    await callback.answer()


@media_router.callback_query(PostCreation.configuring_post, F.data == "back_to_post_settings")
@media_router.callback_query(PostCreation.waiting_for_media_settings, F.data == "back_to_post_settings")
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
        from post_handlers.xinline_keyboard import create_post_options_keyboard
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
        await callback.message.answer(
            get_text('post_settings_msg', lang),
            reply_markup=get_post_settings_kb(content_type, has_caption, lang, is_paid=is_paid)
        )
    
    await callback.answer()


@media_router.callback_query(PostCreation.configuring_post, F.data == "back_to_settings_menu")
@media_router.callback_query(PostCreation.waiting_for_media_settings, F.data == "back_to_settings_menu")
async def back_to_settings_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    """Media sozlamalaridan sozlamalar menyusiga qaytish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)
    
    content_type = post_data.get('content_type', 'text')
    
    await state.set_state(PostCreation.waiting_for_media_settings)
    
    # Sozlamalar menyusini ko'rsatish (Media sozlamalari va Watermark tugmalari)
    await callback.message.edit_text(
        get_text('select_settings_msg', lang),
        reply_markup=get_settings_menu_inline_kb(lang=lang, content_type=content_type)
    )
    
    await callback.answer()


@media_router.message(
    PostCreation.configuring_post,
    LocalizedText('media_settings_btn')
)
@media_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('media_settings_btn')
)
async def open_media_settings(message: Message, state: FSMContext):
    """Media sozlamalari menyusini ochish - inline klaviatura"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(message.from_user.id)
    
    content_type = post_data.get('content_type', 'photo')
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))
    
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


@media_router.callback_query(PostCreation.waiting_for_media_settings, F.data == "open_media_settings_menu")
@media_router.callback_query(PostCreation.configuring_post, F.data == "open_media_settings_menu")
async def open_media_settings_inline(callback: types.CallbackQuery, state: FSMContext):
    """Inline Media tugmasi bosilganda - inline klaviaturani ko'rsatish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)
    
    content_type = post_data.get('content_type', 'photo')
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))
    
    await state.set_state(PostCreation.waiting_for_media_settings)
    
    await callback.message.answer(
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
    await callback.answer()
