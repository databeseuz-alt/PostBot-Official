from contextlib import suppress
from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder

from post_handlers.post_handler import PostCreation
from post_handlers.xreply_keyboard import (
    get_main_menu, get_cancel_kb, get_post_settings_kb,
    get_button_creation_cancel_kb, get_edit_content_kb, get_back_button_kb,
    get_quiz_settings_kb
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
    LocalizedText('watermark_btn')
)
@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('watermark_btn')
)
async def watermark_reply_handler(message: types.Message, state: FSMContext):
    """Suv belgisi tugmasi - watermark sozlamalarini ochish"""
    from post_handlers.watermark_handler import show_watermark_settings_reply
    await show_watermark_settings_reply(message, state)

@reply_router.message(
    PostCreation.configuring_post,
    LocalizedText('quiz_btn')
)
@reply_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('quiz_btn')
)
async def quiz_reply_handler(message: types.Message, state: FSMContext):
    """Viktorina tugmasi - sozlamalarni ko'rsatish"""
    lang = await get_user_language(message.from_user.id)
    from post_handlers.xreply_keyboard import get_quiz_settings_kb
    
    # Initialize quiz data in state if not exists
    data = await state.get_data()
    if 'quiz_options' not in data:
        await state.update_data(
            quiz_options=[], 
            quiz_correct_index=None, 
            quiz_is_anonymous=False,
            quiz_question="Viktorina"
        )
    
    # Edit the same message with quiz settings
    await message.answer(
        get_text('quiz_settings_title', lang),
        reply_markup=get_quiz_settings_kb(lang),
        parse_mode='HTML'
    )
    await state.set_state(PostCreation.configuring_post)

@callback_router.callback_query(F.data == 'quiz_add_option')
async def quiz_add_option_callback(callback: types.CallbackQuery, state: FSMContext):
    """Variant qo'shish inline tugmasi"""
    await callback.answer()
    lang = await get_user_language(callback.from_user.id)
    message = callback.message
    
    await state.set_state(PostCreation.waiting_for_quiz_option)
    
    # Store the message ID for editing later
    await state.update_data(quiz_option_message_id=message.message_id)
    
    # Build inline keyboard with Back button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=get_text('back_btn', lang), callback_data='quiz_option_back'))
    
    # Edit the SAME message (not new message)
    await message.edit_text(
        get_text('quiz_ask_option_msg', lang),
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )

@callback_router.callback_query(F.data == 'quiz_correct_answer')
async def quiz_correct_answer_callback(callback: types.CallbackQuery, state: FSMContext):
    """To'g'ri javob inline tugmasi"""
    await callback.answer()
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    message = callback.message
    
    data = await state.get_data()
    quiz_options = data.get('quiz_options', [])
    
    if not quiz_options:
        await message.answer("⚠️ Avval variantlar qo'shing!")
        return
    
    # Initialize for single correct answer mode
    selected_correct = data.get('quiz_selected_correct', [])
    
    await state.set_state(PostCreation.waiting_for_quiz_correct_answer)
    await state.update_data(quiz_correct_mode='single', quiz_selected_correct=[])
    
    # Build inline keyboard with options
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    
    for i, opt in enumerate(quiz_options):
        prefix = "✅ " if i in selected_correct else ""
        builder.add(InlineKeyboardButton(
            text=prefix + opt,
            callback_data=f'quiz_toggle_correct_{i}'
        ))
    
    # Add Multiple answers and Back buttons
    builder.add(InlineKeyboardButton(text=get_text('quiz_multiple_btn', lang), callback_data='quiz_multiple_answer'))
    builder.add(InlineKeyboardButton(text=get_text('back_btn', lang), callback_data='quiz_correct_back'))
    
    builder.adjust(1, 1, 2)
    
    await message.edit_text(
        get_text('quiz_select_correct_msg', lang),
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )

@callback_router.callback_query(F.data.startswith('quiz_toggle_correct_'))
async def quiz_toggle_correct_callback(callback: types.CallbackQuery, state: FSMContext):
    """To'g'ri javobni tanlash/tanlashni bekor qilish"""
    await callback.answer()
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    message = callback.message
    
    option_index = int(callback.data.split('_')[-1])
    
    data = await state.get_data()
    quiz_options = data.get('quiz_options', [])
    selected_correct = data.get('quiz_selected_correct', [])
    correct_mode = data.get('quiz_correct_mode', 'single')
    
    if correct_mode == 'single':
        # In single mode, immediately save and go back
        await state.update_data(quiz_correct_index=option_index, quiz_selected_correct=[option_index])
        
        # Delete previous poll if exists
        if data.get('quiz_poll_message_id'):
            try:
                await message.bot.delete_message(message.chat.id, data['quiz_poll_message_id'])
            except:
                pass
        
        # Send quiz poll with correct answer
        poll_message = await message.answer_poll(
            question=data.get('quiz_question', 'Viktorina'),
            options=quiz_options,
            is_anonymous=data.get('quiz_is_anonymous', False),
            type='quiz',
            correct_option_id=option_index
        )
        
        await state.update_data(quiz_poll_message_id=poll_message.message_id)
        
        # Send settings keyboard again
        from post_handlers.xreply_keyboard import get_quiz_settings_kb
        settings_msg = await message.answer(
            get_text('quiz_settings_title', lang),
            reply_markup=get_quiz_settings_kb(lang),
            parse_mode='HTML'
        )
        
        await state.update_data(quiz_settings_message_id=settings_msg.message_id)
        await state.set_state(PostCreation.configuring_post)
    else:
        # Multiple mode - toggle
        if option_index in selected_correct:
            selected_correct.remove(option_index)
        else:
            selected_correct.append(option_index)
        
        await state.update_data(quiz_selected_correct=selected_correct)
        
        # Rebuild inline keyboard
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        builder = InlineKeyboardBuilder()
        
        for i, opt in enumerate(quiz_options):
            prefix = "✅ " if i in selected_correct else ""
            builder.add(InlineKeyboardButton(
                text=prefix + opt,
                callback_data=f'quiz_toggle_correct_{i}'
            ))
        
        builder.add(InlineKeyboardButton(text=get_text('quiz_done_btn', lang), callback_data='quiz_done_correct'))
        builder.add(InlineKeyboardButton(text=get_text('back_btn', lang), callback_data='quiz_correct_back'))
        
        builder.adjust(1, 1, 2)
        
        await message.edit_reply_markup(reply_markup=builder.as_markup())

@callback_router.callback_query(F.data == 'quiz_done_correct')
async def quiz_done_correct_callback(callback: types.CallbackQuery, state: FSMContext):
    """Tayyor tugmasi bosilganda"""
    await callback.answer()
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    message = callback.message
    
    data = await state.get_data()
    selected_correct = data.get('quiz_selected_correct', [])
    quiz_options = data.get('quiz_options', [])
    
    if not selected_correct:
        await callback.answer("Iltimos, kamida bitta to'g'ri javobni tanlang!", show_alert=True)
        return
    
    # Set the correct answer index
    correct_index = selected_correct[0] if len(selected_correct) == 1 else selected_correct
    await state.update_data(quiz_correct_index=correct_index)
    
    # Delete previous poll if exists
    if data.get('quiz_poll_message_id'):
        try:
            await message.bot.delete_message(message.chat.id, data['quiz_poll_message_id'])
        except:
            pass
    
    # Send quiz poll with correct answer
    poll_message = await message.answer_poll(
        question=data.get('quiz_question', 'Viktorina'),
        options=quiz_options,
        is_anonymous=data.get('quiz_is_anonymous', False),
        type='quiz',
        correct_option_id=correct_index
    )
    
    await state.update_data(quiz_poll_message_id=poll_message.message_id)
    
    # Send settings keyboard again
    from post_handlers.xreply_keyboard import get_quiz_settings_kb
    settings_msg = await message.answer(
        get_text('quiz_settings_title', lang),
        reply_markup=get_quiz_settings_kb(lang),
        parse_mode='HTML'
    )
    
    await state.update_data(quiz_settings_message_id=settings_msg.message_id)
    await state.set_state(PostCreation.configuring_post)

@callback_router.callback_query(F.data == 'quiz_multiple_answer')
async def quiz_multiple_answer_callback(callback: types.CallbackQuery, state: FSMContext):
    """Bir nechta to'g'ri javob - bir nechta javob tanlash mumkin bo'lgan poll"""
    await callback.answer()
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    message = callback.message
    
    data = await state.get_data()
    quiz_options = data.get('quiz_options', [])
    
    if not quiz_options:
        await message.answer("⚠️ Avval variantlar qo'shing!")
        return
    
    # Send regular poll with multiple answers allowed
    poll_message = await message.answer_poll(
        question=data.get('quiz_question', 'Viktorina'),
        options=quiz_options,
        is_anonymous=data.get('quiz_is_anonymous', False),
        allows_multiple_answers=True
    )
    
    await state.update_data(quiz_poll_message_id=poll_message.message_id, quiz_correct_index=None)
    
    # Send settings keyboard again
    from post_handlers.xreply_keyboard import get_quiz_settings_kb
    settings_msg = await message.answer(
        get_text('quiz_settings_title', lang),
        reply_markup=get_quiz_settings_kb(lang),
        parse_mode='HTML'
    )
    
    await state.update_data(quiz_settings_message_id=settings_msg.message_id)
    await state.set_state(PostCreation.configuring_post)

@callback_router.callback_query(F.data == 'quiz_correct_back')
async def quiz_correct_back_callback(callback: types.CallbackQuery, state: FSMContext):
    """Orqaga tugmasi - to'g'ri javob tanlashdan chiqish"""
    await callback.answer()
    lang = await get_user_language(callback.from_user.id)
    message = callback.message
    
    await state.set_state(PostCreation.configuring_post)
    
    from post_handlers.xreply_keyboard import get_quiz_settings_kb
    await message.edit_text(
        get_text('quiz_settings_title', lang),
        reply_markup=get_quiz_settings_kb(lang),
        parse_mode='HTML'
    )

@callback_router.callback_query(F.data == 'quiz_anonymous')
async def quiz_anonymous_callback(callback: types.CallbackQuery, state: FSMContext):
    """Anonim javob berish inline tugmasi - toggle"""
    await callback.answer()
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    message = callback.message
    
    data = await state.get_data()
    current_anonymous = data.get('quiz_is_anonymous', False)
    new_anonymous = not current_anonymous
    
    await state.update_data(quiz_is_anonymous=new_anonymous)
    
    # If there's an existing poll, delete and resend
    quiz_options = data.get('quiz_options', [])
    if quiz_options:
        # Delete previous poll if exists
        if data.get('quiz_poll_message_id'):
            try:
                await message.bot.delete_message(message.chat.id, data['quiz_poll_message_id'])
            except:
                pass
        
        # Send updated poll
        poll_message = await message.answer_poll(
            question=data.get('quiz_question', 'Viktorina'),
            options=quiz_options,
            is_anonymous=new_anonymous,
            type='quiz' if data.get('quiz_correct_index') is not None else 'regular',
            correct_option_id=data.get('quiz_correct_index')
        )
        
        await state.update_data(quiz_poll_message_id=poll_message.message_id)
    
    # Update inline keyboard with new state
    from post_handlers.xreply_keyboard import get_quiz_settings_kb
    try:
        await message.edit_reply_markup(reply_markup=get_quiz_settings_kb(lang))
    except:
        pass

@callback_router.callback_query(F.data == 'quiz_back')
async def quiz_back_callback(callback: types.CallbackQuery, state: FSMContext):
    """Orqaga tugmasi - viktorina sozlamalaridan chiqish"""
    await callback.answer()
    # Delete the quiz settings message
    try:
        await callback.message.delete()
    except:
        pass
    
    # Clear quiz data
    data = await state.get_data()
    if data.get('quiz_poll_message_id'):
        try:
            await callback.message.bot.delete_message(callback.message.chat.id, data['quiz_poll_message_id'])
        except:
            pass
    
    await state.update_data(quiz_options=[], quiz_correct_index=None, quiz_is_anonymous=False, quiz_poll_message_id=None)

@callback_router.callback_query(F.data == 'quiz_option_back')
async def quiz_option_back_callback(callback: types.CallbackQuery, state: FSMContext):
    """Orqaga tugmasi - variant kiritishdan chiqish"""
    await callback.answer()
    lang = await get_user_language(callback.from_user.id)
    message = callback.message
    
    await state.set_state(PostCreation.configuring_post)
    
    # Clear the option message ID
    await state.update_data(quiz_option_message_id=None)
    
    # Show quiz settings again
    from post_handlers.xreply_keyboard import get_quiz_settings_kb
    await message.edit_text(
        get_text('quiz_settings_title', lang),
        reply_markup=get_quiz_settings_kb(lang),
        parse_mode='HTML'
    )


@reply_router.message(
    PostCreation.waiting_for_quiz_option,
    F.text == "/cancel"
)
async def quiz_option_cancel_handler(message: types.Message, state: FSMContext):
    """Variant qo'shishni bekor qilish"""
    lang = await get_user_language(message.from_user.id)
    
    await state.set_state(PostCreation.configuring_post)
    
    from post_handlers.xreply_keyboard import get_quiz_settings_kb
    await message.answer(
        get_text('quiz_settings_title', lang),
        reply_markup=get_quiz_settings_kb(lang),
        parse_mode='HTML'
    )

@reply_router.message(
    PostCreation.waiting_for_quiz_option,
    F.text
)
async def handle_quiz_option_input(message: types.Message, state: FSMContext):
    """Foydalanuvchi variant matnini kiritdi"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    option_text = message.text.strip()
    if not option_text:
        await message.answer(get_text('wrong_format', lang))
        return
    
    # Get current quiz options and the edited message ID
    data = await state.get_data()
    quiz_options = data.get('quiz_options', [])
    quiz_option_message_id = data.get('quiz_option_message_id')
    
    # Add new option
    quiz_options.append(option_text)
    await state.update_data(quiz_options=quiz_options)
    
    # Delete user's input message
    await message.delete()
    
    # If only 1 option, ask for second option (delete old and send new from below)
    if len(quiz_options) == 1:
        # Delete the "ask for option" message
        if quiz_option_message_id:
            try:
                await message.bot.delete_message(message.chat.id, quiz_option_message_id)
            except:
                pass
        
        # Build inline keyboard with Back button
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text=get_text('back_btn', lang), callback_data='quiz_option_back'))
        
        # Send new message asking for second option (from below)
        new_msg = await message.answer(
            get_text('quiz_ask_second_option_msg', lang),
            reply_markup=builder.as_markup(),
            parse_mode='HTML'
        )
        await state.update_data(quiz_option_message_id=new_msg.message_id)
        return
    
    # If 2 or more options, send poll and show settings
    # Delete the previous poll message if exists
    old_poll_id = data.get('quiz_poll_message_id')
    if old_poll_id:
        try:
            await message.bot.delete_message(message.chat.id, old_poll_id)
        except:
            pass
    
    # Delete the "ask for option" message
    if quiz_option_message_id:
        try:
            await message.bot.delete_message(message.chat.id, quiz_option_message_id)
        except:
            pass
    
    # Send new poll with current options (from below)
    poll_message = await message.answer_poll(
        question=data.get('quiz_question', 'Viktorina'),
        options=quiz_options,
        is_anonymous=data.get('quiz_is_anonymous', False),
        type='regular'
    )
    
    # Update state with new poll message ID
    await state.update_data(quiz_poll_message_id=poll_message.message_id, quiz_option_message_id=None)
    
    # Send new quiz settings (from below, not edit)
    from post_handlers.xreply_keyboard import get_quiz_settings_kb
    settings_msg = await message.answer(
        get_text('quiz_settings_title', lang),
        reply_markup=get_quiz_settings_kb(lang),
        parse_mode='HTML'
    )
    
    await state.update_data(quiz_settings_message_id=settings_msg.message_id)
    await state.set_state(PostCreation.configuring_post)

@reply_router.message(
    PostCreation.waiting_for_quiz_correct_answer,
    F.text == "/cancel"
)
async def quiz_correct_cancel_handler(message: types.Message, state: FSMContext):
    """To'g'ri javob tanlashni bekor qilish"""
    lang = await get_user_language(message.from_user.id)
    
    await state.set_state(PostCreation.configuring_post)
    
    from post_handlers.xreply_keyboard import get_quiz_settings_kb
    settings_msg = await message.answer(
        get_text('quiz_settings_title', lang),
        reply_markup=get_quiz_settings_kb(lang),
        parse_mode='HTML'
    )
    
    await state.update_data(quiz_settings_message_id=settings_msg.message_id)

@reply_router.message(
    PostCreation.waiting_for_quiz_option,
    LocalizedText('back_btn')
)
async def quiz_option_back_handler(message: types.Message, state: FSMContext):
    """Orqaga tugmasi - variant qo'shishdan chiqish"""
    lang = await get_user_language(message.from_user.id)
    
    data = await state.get_data()
    
    await state.set_state(PostCreation.configuring_post)
    
    from post_handlers.xreply_keyboard import get_quiz_settings_kb
    settings_msg = await message.answer(
        get_text('quiz_settings_title', lang),
        reply_markup=get_quiz_settings_kb(lang),
        parse_mode='HTML'
    )
    
    await state.update_data(quiz_settings_message_id=settings_msg.message_id)

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