from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from contextlib import suppress
import logging

logger = logging.getLogger(__name__)

from post_handlers.post_handler import PostCreation
from post_handlers.xreply_keyboard import get_post_done_menu, get_save_cancel_kb, get_save_cancelled_kb, get_cancel_reply_kb
from post_handlers.xinline_keyboard import get_post_management_keyboard, SavePostCallbackFactory, get_post_save_edit_keyboard, get_done_inline_keyboard, generate_preview_keyboard, generate_final_keyboard
from post_handlers.xreply_keyboard import get_main_menu as get_main_menu_reply
from xdata_handlers.database import (
    add_post_to_db, update_post_in_db, get_user_language, save_post_name, unsave_post_name, get_post_from_db, get_user_post_settings
)
from admin_handlers.channel_handler import check_user_membership
from post_handlers.start_handler import start_post_creation, cmd_start
from xdata_handlers.translator import get_text
from xdata_handlers import config
from post_handlers.localize_filter import LocalizedText

done_router = Router()

async def send_post_preview(chat_id: int, post_code: str, lang: str, bot: Bot, success_keyboard=None, show_code: bool = True):
    """Postni preview sifatida yuboradi va post kodi xabarini chiqaradi."""
    full_post = await get_post_from_db(post_code)
    if not full_post:
        return None

    post_data = full_post.get('post_content', {})
    buttons_matrix = full_post.get('buttons_matrix', [])
    
    # If success_keyboard is provided (no buttons in post), use it instead of preview keyboard
    if success_keyboard:
        preview_keyboard = success_keyboard
    else:
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
            is_paid = post_data.get('is_paid', False)
            if is_paid:
                from aiogram.types import InputPaidMediaPhoto
                preview_message = await bot.send_paid_media(
                    chat_id=chat_id,
                    star_count=post_data.get('paid_price', 1),
                    media=[InputPaidMediaPhoto(media=post_data.get('file_id'))],
                    caption=post_data.get('caption', ''),
                    reply_markup=preview_keyboard,
                    parse_mode=parse_mode,
                    show_caption_above_media=show_caption_above
                )
            else:
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
            is_paid = post_data.get('is_paid', False)
            if is_paid:
                from aiogram.types import InputPaidMediaVideo
                preview_message = await bot.send_paid_media(
                    chat_id=chat_id,
                    star_count=post_data.get('paid_price', 1),
                    media=[InputPaidMediaVideo(media=post_data.get('file_id'))],
                    caption=post_data.get('caption', ''),
                    reply_markup=preview_keyboard,
                    parse_mode=parse_mode,
                    show_caption_above_media=show_caption_above
                )
            else:
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
                question=post_data.get('question', ''),
                options=post_data.get('options', []),
                is_anonymous=post_data.get('is_anonymous', True),
                type=post_data.get('type', 'regular'),
                allows_multiple_answers=post_data.get('allows_multiple_answers', False),
                correct_option_id=post_data.get('correct_option_id'),
                explanation=post_data.get('explanation'),
                reply_markup=preview_keyboard
            )
        elif content_type == 'dice':
            preview_message = await bot.send_dice(
                chat_id,
                emoji=post_data.get('dice_emoji', '🎲'),
                reply_markup=preview_keyboard
            )
        elif content_type == 'location':
            preview_message = await bot.send_location(
                chat_id,
                latitude=post_data.get('latitude'),
                longitude=post_data.get('longitude'),
                reply_markup=preview_keyboard
            )
        elif content_type == 'paid_media':
            from aiogram.types import InputPaidMediaPhoto, InputPaidMediaVideo
            media_types = post_data.get('paid_media_types', [])
            file_ids = post_data.get('paid_media_file_ids', [])
            input_media_list = []
            for m_type, f_id in zip(media_types, file_ids):
                if m_type == 'photo':
                    input_media_list.append(InputPaidMediaPhoto(media=f_id))
                else:
                    input_media_list.append(InputPaidMediaVideo(media=f_id))

            preview_message = await bot.send_paid_media(
                chat_id=chat_id,
                star_count=post_data.get('paid_price', 1),
                media=input_media_list,
                caption=post_data.get('caption'),
                parse_mode=parse_mode,
                show_caption_above_media=post_data.get('show_caption_above_media', False),
                reply_markup=preview_keyboard
            )
    except Exception:
        pass

    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    if show_code:
        post_code_message = get_text('post_saved_msg', lang).format(
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
@done_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('done_btn')
)
@done_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('edit_confirm_btn')
)
@done_router.callback_query(
    PostCreation.configuring_post,
    F.data == "done_post_creation"
)
@done_router.callback_query(
    PostCreation.waiting_for_media_settings,
    F.data == "done_post_creation"
)
async def done_post_creation(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot):
    user = event.from_user
    chat_id = event.chat.id if isinstance(event, types.Message) else event.message.chat.id

    lang = await get_user_language(user.id)
    is_member, check_text, check_keyboard = await check_user_membership(user, bot)

    if not is_member:
        await state.clear()
        if isinstance(event, types.Message):
            await event.answer(
                get_text('join_required_msg', lang),
                reply_markup=ReplyKeyboardRemove()
            )
            await event.answer(check_text, reply_markup=check_keyboard)
        else:
            await event.message.answer(
                get_text('join_required_msg', lang),
                reply_markup=ReplyKeyboardRemove()
            )
            await event.message.answer(check_text, reply_markup=check_keyboard)
            await event.answer()
        return

    data = await state.get_data()
    post_data = data.get("post_data", {})
    buttons_matrix = data.get("buttons_matrix", [])

    if not post_data:
        if isinstance(event, types.Message):
            return await event.answer(get_text('save_error', lang))
        else:
            return await event.message.answer(get_text('save_error', lang))

    # Suv belgisini qo'llash (agar yoqilgan bo'lsa va hali qo'llanilmagan bo'lsa)
    if post_data.get('watermark_enabled') and post_data.get('watermark_file_id'):
        # Agar file_id o'zgarmagan bo'lsa (hali wm qo'shilmagan)
        if 'original_file_id' not in post_data or post_data.get('file_id') == post_data.get('original_file_id'):
            try:
                from post_handlers.watermark_handler import apply_watermark
                new_file_id = await apply_watermark(bot, post_data['file_id'], post_data['watermark_file_id'])
                if new_file_id and new_file_id != post_data['file_id']:
                    post_data['original_file_id'] = post_data['file_id']
                    post_data['file_id'] = new_file_id
                    await state.update_data(post_data=post_data)
            except Exception as e:
                logger.error(f"Auto watermark application error: {e}")

    # Tekshirish: agar post tarkibida inline rejimga mos kelmaydigan elementlar bo'lsa, kod ko'rsatilmaydi
    has_incompatible_feature = False
    incompatible_reason = None

    if buttons_matrix:
        for row in buttons_matrix:
            for btn in row:
                if btn:
                    btn_type = btn.get('type')
                    if btn_type == 'reaction':
                        has_incompatible_feature = True
                        break
                    elif btn_type == 'text_btn':
                        has_incompatible_feature = True
                        break
            if has_incompatible_feature:
                break
    
    content_type = post_data.get('content_type')
    if content_type in ['poll', 'paid_media', 'dice', 'location']:
        has_incompatible_feature = True
    
    # Print settings (inline rejimda ishlamaydi)
    print_settings = data.get('print_settings', {})
    if any(print_settings.get(k) for k in ['silent_mode', 'protect_content', 'auto_pin', 'comments_enabled', 'auto_delete', 'reply_to_msg_id']):
        has_incompatible_feature = True

    show_code = not has_incompatible_feature

    if has_incompatible_feature:
        if isinstance(event, types.Message):
            await event.answer(get_text('cant_generate_code_poll_reaction', lang))
        else:
            await event.message.answer(get_text('cant_generate_code_poll_reaction', lang))
        if isinstance(event, types.CallbackQuery):
            await event.answer()

    editing_post_code = data.get("editing_post_code")
    if editing_post_code:
        success = await update_post_in_db(editing_post_code, post_data, buttons_matrix)
        post_code_for_user = editing_post_code if success else None
    else:
        post_code_for_user = await add_post_to_db(
            user.id,
            post_data,
            buttons_matrix,
            admin_ids=config.ADMIN_IDS
        )

    if not post_code_for_user:
        if isinstance(event, types.Message):
            return await event.answer(get_text('save_error', lang))
        else:
            return await event.message.answer(get_text('save_error', lang))

    await state.clear()

    # Show success message with reply keyboard
    from post_handlers.xreply_keyboard import get_post_done_menu, get_back_button_kb
    
    # Check if there are any buttons in the post
    has_buttons = False
    if buttons_matrix:
        for row in buttons_matrix:
            for btn in row:
                if btn and not btn.get('is_placeholder'):
                    has_buttons = True
                    break
            if has_buttons:
                break
    
    # Get post data for preview
    full_post_for_preview = await get_post_from_db(post_code_for_user)
    preview_post_data = full_post_for_preview.get('post_content', {}) if full_post_for_preview else {}
    
    if has_buttons:
        # If there are buttons, show success message separately and then preview with buttons
        if isinstance(event, types.Message):
            success_message = await event.answer(
                get_text('post_saved_to_db', lang),
                reply_markup=get_post_done_menu(lang)
            )
        else:
            success_message = await event.message.answer(
                get_text('post_saved_to_db', lang),
                reply_markup=get_post_done_menu(lang)
            )
        
        if isinstance(event, types.CallbackQuery):
            await event.answer()
        
        await send_post_preview(chat_id, post_code_for_user, lang, bot, show_code=show_code)
    else:
        # If there are NO buttons, show success message IN the preview message via reply_markup
        if isinstance(event, types.CallbackQuery):
            await event.answer()
        
        await send_post_preview(chat_id, post_code_for_user, lang, bot, get_post_done_menu(lang), show_code=show_code)

@done_router.callback_query(SavePostCallbackFactory.filter(F.action == "start_save"))
async def save_post_prompt(callback: types.CallbackQuery, callback_data: SavePostCallbackFactory, state: FSMContext):
    post_code = callback_data.post_code
    
    # post_code None bo'lsa, state dan olishga urinib ko'rish
    if not post_code:
        data = await state.get_data()
        post_code = data.get("post_code_to_save") or data.get("post_code")
    
    # Yana ham None bo'lsa, xabar berish
    if not post_code:
        lang = await get_user_language(callback.from_user.id)
        await callback.message.answer(get_text('post_code_missing_error', lang), parse_mode="HTML")
        await callback.answer()
        return
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
async def show_edit_save_menu(callback: types.CallbackQuery, callback_data: SavePostCallbackFactory, state: FSMContext):
    """'Tahrirlash' bosilganda [Qayta nomlash][O'chirish] menyusini chiqaradi."""
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
    post_code = callback_data.post_code
    user_id = callback.from_user.id

    await unsave_post_name(post_code, user_id)

    try:
        await callback.message.delete()
    except: pass

    lang = await get_user_language(user_id)
    await callback.message.answer(get_text('saved_name_deleted', lang))

    inline_kb = await get_post_management_keyboard(post_code)
    final_message = get_text('post_saved_msg', lang).format(
        post_code=post_code,
        bot_username=(await callback.bot.get_me()).username
    )

    await callback.message.answer(final_message, reply_markup=inline_kb, parse_mode="HTML")
    await callback.answer()

@done_router.callback_query(SavePostCallbackFactory.filter(F.action == "rename"))
async def rename_post_prompt(callback: types.CallbackQuery, callback_data: SavePostCallbackFactory, state: FSMContext):
    """'Qayta nomlash' bosilganda yangi nom so'raydi."""
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
    final_message = get_text('post_saved_msg', lang).format(
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
        final_message = get_text('post_saved_msg', lang).format(
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
        final_message = get_text('post_saved_msg', lang).format(
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

    final_message = get_text('post_saved_msg', lang).format(
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
    """Yangi post yaratish - done_handler dan"""
    user = message.from_user
    is_member, text, keyboard = await check_user_membership(user, bot)
    
    if not is_member:
        remover_message = await message.answer(".", reply_markup=ReplyKeyboardRemove())
        await remover_message.delete()
        await message.answer(text, reply_markup=keyboard)
        return
    
    await state.clear()
    lang = await get_user_language(user.id)
    
    user_settings = await get_user_post_settings(user.id)
    ai_assistant_enabled = user_settings.get('ai_assistant_enabled', False)
    
    content_text = get_text('content_msg', lang)
    if ai_assistant_enabled:
        content_text += get_text('ai_assistant_hint_msg', lang)
    
    content_message = await message.answer(content_text, reply_markup=get_cancel_reply_kb(lang, ai_assistant_enabled))
    
    await state.update_data(content_message_id=content_message.message_id)
    await state.set_state(PostCreation.waiting_for_content)

@done_router.message(LocalizedText('back_btn'))
async def back_to_main_menu_handler(message: types.Message, state: FSMContext, bot: Bot):
    await cmd_start(message, state, bot)

@done_router.callback_query(F.data == "done_create_another")
async def done_create_another_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    await start_post_creation(callback, state, bot)

@done_router.callback_query(F.data == "done_back")
async def done_back_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    await cmd_start(callback, state, bot)

@done_router.callback_query(F.data == "print_settings")
async def print_settings_handler(callback: types.CallbackQuery, state: FSMContext):
    """Chop etish sozlamalari tugmasi bosilganda."""
    from post_handlers.xinline_keyboard import get_print_settings_keyboard
    from xdata_handlers.database import get_post_from_db

    post_code = None
    try:
        import re
        msg_text = callback.message.text if callback.message else ""
        code_match = re.search(r'code[=:]\s*(\w+)', msg_text, re.IGNORECASE)
        if code_match:
            post_code = code_match.group(1)
    except:
        pass

    lang = await get_user_language(callback.from_user.id)

    # Print settings ni bazadan olish
    print_settings = {}
    if post_code:
        full_post = await get_post_from_db(post_code)
        if full_post:
            print_settings = full_post.get('print_settings', {})

    await callback.message.answer(
        get_text('print_settings_title', lang),
        reply_markup=get_print_settings_keyboard(lang, post_code, print_settings),
        parse_mode="HTML"
    )
    await callback.answer()

@done_router.callback_query(F.data.startswith("print:"))
async def print_settings_callback(callback: types.CallbackQuery, state: FSMContext):
    """Chop etish sozlamalari callbacklari."""
    from post_handlers.xinline_keyboard import get_print_settings_keyboard
    from xdata_handlers.database import update_post_print_settings, get_post_from_db

    parts = callback.data.split(":")
    post_code = parts[1] if len(parts) > 1 and parts[1] != 'none' else None
    action = parts[2] if len(parts) > 2 else None

    lang = await get_user_language(callback.from_user.id)

    # Print settings ni bazadan olish
    print_settings = {}
    if post_code:
        full_post = await get_post_from_db(post_code)
        if full_post:
            print_settings = full_post.get('print_settings', {})

    if action == "menu" or action is None:
        try:
            await callback.message.edit_text(
                get_text('print_settings_title', lang),
                reply_markup=get_print_settings_keyboard(lang, post_code, print_settings)
            )
        except:
            await callback.message.answer(
                get_text('print_settings_title', lang),
                reply_markup=get_print_settings_keyboard(lang, post_code, print_settings),
                parse_mode="HTML"
            )
        await callback.answer()
        return

    if action == "back":
        from post_handlers.xinline_keyboard import get_post_management_keyboard
        try:
            await callback.message.edit_text(
                get_text('post_saved_msg', lang).format(
                    post_code=post_code,
                    bot_username=(await callback.bot.get_me()).username
                ),
                reply_markup=await get_post_management_keyboard(post_code, lang)
            )
        except:
            await callback.message.answer(
                get_text('post_saved_msg', lang).format(
                    post_code=post_code,
                    bot_username=(await callback.bot.get_me()).username
                ),
                reply_markup=await get_post_management_keyboard(post_code, lang),
                parse_mode="HTML"
            )
        await callback.answer()
        return

    # ===== JIMJITLIK REJIMI =====
    if action == "silent":
        current = print_settings.get('silent_mode', False)
        print_settings['silent_mode'] = not current
        if post_code:
            await update_post_print_settings(post_code, print_settings)
        
        msg = get_text('print_silent_toggled_on', lang) if not current else get_text('print_silent_toggled_off', lang)
        await callback.answer(msg, show_alert=True)
        
        try:
            await callback.message.edit_reply_markup(
                reply_markup=get_print_settings_keyboard(lang, post_code, print_settings)
            )
        except:
            pass
        return

    # ===== KONTENT HIMOYASI =====
    if action == "protect":
        current = print_settings.get('protect_content', False)
        print_settings['protect_content'] = not current
        if post_code:
            await update_post_print_settings(post_code, print_settings)
        
        msg = get_text('print_protect_toggled_on', lang) if not current else get_text('print_protect_toggled_off', lang)
        await callback.answer(msg, show_alert=True)
        
        try:
            await callback.message.edit_reply_markup(
                reply_markup=get_print_settings_keyboard(lang, post_code, print_settings)
            )
        except:
            pass
        return

    # ===== AVTOMATIK PIN =====
    if action == "pin":
        current = print_settings.get('auto_pin', False)
        print_settings['auto_pin'] = not current
        if post_code:
            await update_post_print_settings(post_code, print_settings)
        
        msg = get_text('print_pin_toggled_on', lang) if not current else get_text('print_pin_toggled_off', lang)
        await callback.answer(msg, show_alert=True)
        
        try:
            await callback.message.edit_reply_markup(
                reply_markup=get_print_settings_keyboard(lang, post_code, print_settings)
            )
        except:
            pass
        return

    # ===== IZOHLAR (COMMENTS) =====
    if action == "comments":
        current = print_settings.get('comments_enabled', False)
        print_settings['comments_enabled'] = not current
        if post_code:
            await update_post_print_settings(post_code, print_settings)
        
        # Show an informative alert since telegram's native comments rely on discussion groups
        msg = get_text('print_comments_info', lang)
        await callback.answer(msg, show_alert=True)
        
        try:
            await callback.message.edit_reply_markup(
                reply_markup=get_print_settings_keyboard(lang, post_code, print_settings)
            )
        except:
            pass
        return

    # ===== JAVOB BERISH (REPLY) =====
    if action == "reply":
        if print_settings.get('reply_to_message_id'):
            # Allaqachon reply o'rnatilgan - menyuga reply_to o'chirish va qaytish
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            builder.button(text=get_text('print_reply_remove_btn', lang), callback_data=f"print:{post_code or 'none'}:reply_remove")
            builder.button(text=get_text('back_btn', lang), callback_data=f"print:{post_code or 'none'}:menu")
            builder.adjust(1)
            
            try:
                await callback.message.edit_text(
                    get_text('print_reply_prompt', lang),
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
            except:
                pass
        else:
            # Reply o'rnatish uchun matn kiritishni so'rash
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            builder.button(text=get_text('back_btn', lang), callback_data=f"print:{post_code or 'none'}:menu")
            builder.adjust(1)

            await state.set_state(PostCreation.waiting_for_reply_message_id)
            await state.update_data(post_code_for_reply=post_code)

            try:
                await callback.message.edit_text(
                    get_text('print_reply_prompt', lang),
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
            except:
                await callback.message.answer(
                    get_text('print_reply_prompt', lang),
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
        await callback.answer()
        return

    # ===== REPLY O'CHIRISH =====
    if action == "reply_remove":
        print_settings.pop('reply_to_message_id', None)
        if post_code:
            await update_post_print_settings(post_code, print_settings)
        
        await callback.answer(get_text('print_reply_removed', lang), show_alert=True)
        
        try:
            await callback.message.edit_text(
                get_text('print_settings_title', lang),
                reply_markup=get_print_settings_keyboard(lang, post_code, print_settings)
            )
        except:
            pass
        return

    # ===== AVTO O'CHIRISH =====
    if action == "auto_delete":
        if print_settings.get('delete_timer_seconds'):
            # Allaqachon taymer o'rnatilgan - o'chirish opsiyasini ko'rsatish
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            builder.button(text=get_text('print_auto_delete_remove_btn', lang), callback_data=f"print:{post_code or 'none'}:auto_delete_remove")
            builder.button(text=get_text('back_btn', lang), callback_data=f"print:{post_code or 'none'}:menu")
            builder.adjust(1)

            await state.set_state(PostCreation.waiting_for_auto_delete_time)
            await state.update_data(post_code_for_auto_delete=post_code)

            try:
                await callback.message.edit_text(
                    get_text('print_auto_delete_prompt', lang),
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
            except:
                pass
        else:
            # Taymer o'rnatish uchun matn kiritishni so'rash
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            builder.button(text=get_text('back_btn', lang), callback_data=f"print:{post_code or 'none'}:menu")
            builder.adjust(1)

            await state.set_state(PostCreation.waiting_for_auto_delete_time)
            await state.update_data(post_code_for_auto_delete=post_code)

            try:
                await callback.message.edit_text(
                    get_text('print_auto_delete_prompt', lang),
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
            except:
                await callback.message.answer(
                    get_text('print_auto_delete_prompt', lang),
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
        await callback.answer()
        return

    # ===== AVTO O'CHIRISH TAYMERNI OLIB TASHLASH =====
    if action == "auto_delete_remove":
        print_settings.pop('delete_timer_seconds', None)
        print_settings.pop('delete_timer_display', None)
        if post_code:
            await update_post_print_settings(post_code, print_settings)
        
        await state.clear()
        await callback.answer(get_text('print_auto_delete_removed', lang), show_alert=True)
        
        try:
            await callback.message.edit_text(
                get_text('print_settings_title', lang),
                reply_markup=get_print_settings_keyboard(lang, post_code, print_settings)
            )
        except:
            pass
        return

    # Eski delete_timer action ni ham qo'llab-quvvatlash (orqaga moslik)
    if action == "delete_timer":
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text=get_text('back_btn', lang), callback_data=f"print:{post_code or 'none'}:menu")
        builder.adjust(1)

        await state.set_state(PostCreation.waiting_for_auto_delete_time)
        await state.update_data(post_code_for_auto_delete=post_code)

        try:
            await callback.message.edit_text(
                get_text('print_auto_delete_prompt', lang),
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        except:
            await callback.message.answer(
                get_text('print_auto_delete_prompt', lang),
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        await callback.answer()
        return

    await callback.answer()

@done_router.callback_query(PostCreation.waiting_for_auto_delete_time, F.data.startswith("print:"))
async def back_from_auto_delete_input(callback: types.CallbackQuery, state: FSMContext):
    """Avto o'chirish kiritishdan orqaga qaytish."""
    from post_handlers.xinline_keyboard import get_print_settings_keyboard
    from xdata_handlers.database import get_post_from_db

    parts = callback.data.split(":")
    post_code = parts[1] if len(parts) > 1 and parts[1] != 'none' else None
    
    lang = await get_user_language(callback.from_user.id)
    await state.clear()

    print_settings = {}
    if post_code:
        full_post = await get_post_from_db(post_code)
        if full_post:
            print_settings = full_post.get('print_settings', {})

    try:
        await callback.message.edit_text(
            get_text('print_settings_title', lang),
            reply_markup=get_print_settings_keyboard(lang, post_code, print_settings)
        )
    except:
        await callback.message.answer(
            get_text('print_settings_title', lang),
            reply_markup=get_print_settings_keyboard(lang, post_code, print_settings),
            parse_mode="HTML"
        )
    await callback.answer()

@done_router.message(PostCreation.waiting_for_auto_delete_time)
async def process_auto_delete_time(message: types.Message, state: FSMContext):
    """Avto o'chirish vaqtini kiritish."""
    import re
    from datetime import datetime, timedelta
    import pytz
    from xdata_handlers.database import update_post_print_settings
    from post_handlers.xinline_keyboard import get_print_settings_keyboard

    lang = await get_user_language(message.from_user.id)
    user_input = message.text.strip()

    if user_input == get_text('cancel_btn', lang) or user_input == get_text('back_btn', lang):
        await state.clear()
        await message.answer(get_text('print_auto_delete_removed', lang))
        return

    delete_after_seconds = None
    display_time = user_input

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
        formats = [
            "%d.%m %H:%M",
            "%d.%m.%Y %H:%M",
            "%d.%m.%Y",
            "%H:%M",
        ]

        tz = pytz.timezone('Asia/Tashkent')
        now = datetime.now(tz)

        for fmt in formats:
            try:
                parsed = datetime.strptime(user_input, fmt)

                if fmt == "%H:%M":
                    parsed = now.replace(hour=parsed.hour, minute=parsed.minute, second=0)
                    if parsed < now:
                        parsed += timedelta(days=1)
                elif fmt == "%d.%m.%Y":
                    parsed = parsed.replace(year=now.year)
                    parsed = tz.localize(parsed)
                elif fmt == "%d.%m %H:%M":
                    parsed = parsed.replace(year=now.year)
                    parsed = tz.localize(parsed)
                elif fmt == "%d.%m.%Y %H:%M":
                    parsed = tz.localize(parsed)

                if parsed > now:
                    delete_after_seconds = int((parsed - now).total_seconds())
                    display_time = parsed.strftime("%d-%m-%Y %H:%M")
                break
            except:
                continue

    if delete_after_seconds is None or delete_after_seconds <= 0:
        await message.answer(
            get_text('print_auto_delete_invalid', lang),
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    post_code = data.get("post_code_for_auto_delete")

    if post_code:
        await update_post_print_settings(post_code, {
            'delete_timer_seconds': delete_after_seconds,
            'delete_timer_display': display_time
        })

    await state.clear()

    await message.answer(
        get_text('print_auto_delete_set', lang).format(time=display_time),
        parse_mode="HTML"
    )

    # Print settings ni bazadan olish va klaviaturani ko'rsatish
    from xdata_handlers.database import get_post_from_db
    print_settings = {}
    if post_code:
        full_post = await get_post_from_db(post_code)
        if full_post:
            print_settings = full_post.get('print_settings', {})

    await message.answer(
        get_text('print_settings_title', lang),
        reply_markup=get_print_settings_keyboard(lang, post_code, print_settings),
        parse_mode="HTML"
    )


# ===== REPLY MESSAGE ID INPUT HANDLER =====

@done_router.callback_query(PostCreation.waiting_for_reply_message_id, F.data.startswith("print:"))
async def back_from_reply_input(callback: types.CallbackQuery, state: FSMContext):
    """Reply kiritishdan orqaga qaytish."""
    from post_handlers.xinline_keyboard import get_print_settings_keyboard
    from xdata_handlers.database import get_post_from_db

    parts = callback.data.split(":")
    post_code = parts[1] if len(parts) > 1 and parts[1] != 'none' else None
    
    lang = await get_user_language(callback.from_user.id)
    await state.clear()

    print_settings = {}
    if post_code:
        full_post = await get_post_from_db(post_code)
        if full_post:
            print_settings = full_post.get('print_settings', {})

    try:
        await callback.message.edit_text(
            get_text('print_settings_title', lang),
            reply_markup=get_print_settings_keyboard(lang, post_code, print_settings)
        )
    except:
        await callback.message.answer(
            get_text('print_settings_title', lang),
            reply_markup=get_print_settings_keyboard(lang, post_code, print_settings),
            parse_mode="HTML"
        )
    await callback.answer()

@done_router.message(PostCreation.waiting_for_reply_message_id)
async def process_reply_message_id(message: types.Message, state: FSMContext):
    """Javob berish uchun xabar ID sini kiritish."""
    import re
    from xdata_handlers.database import update_post_print_settings
    from post_handlers.xinline_keyboard import get_print_settings_keyboard

    lang = await get_user_language(message.from_user.id)
    user_input = message.text.strip()

    if user_input == get_text('cancel_btn', lang) or user_input == get_text('back_btn', lang):
        await state.clear()
        await message.answer(get_text('print_reply_removed', lang))
        return

    msg_id = None

    # URL formatini tekshirish: https://t.me/channel/123 yoki https://t.me/c/123456/789
    url_match = re.search(r't\.me/(?:c/\d+/|[^/]+/)(\d+)', user_input)
    if url_match:
        msg_id = int(url_match.group(1))
    else:
        # Oddiy raqam
        try:
            msg_id = int(user_input)
        except ValueError:
            pass

    if msg_id is None:
        await message.answer(
            get_text('print_reply_invalid', lang),
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    post_code = data.get("post_code_for_reply")

    if post_code:
        await update_post_print_settings(post_code, {
            'reply_to_message_id': msg_id
        })

    await state.clear()

    await message.answer(
        get_text('print_reply_saved', lang).format(msg_id=msg_id),
        parse_mode="HTML"
    )

    # Print settings ni bazadan olish va klaviaturani ko'rsatish
    from xdata_handlers.database import get_post_from_db
    print_settings = {}
    if post_code:
        full_post = await get_post_from_db(post_code)
        if full_post:
            print_settings = full_post.get('print_settings', {})

    await message.answer(
        get_text('print_settings_title', lang),
        reply_markup=get_print_settings_keyboard(lang, post_code, print_settings),
        parse_mode="HTML"
    )

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
    from post_handlers.start_handler import show_main_menu
    await show_main_menu(callback, state, bot)
