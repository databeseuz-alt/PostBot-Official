
import re
import logging
from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder, KeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter

from post_handlers.post_handler import PostCreation
from post_handlers.xreply_keyboard import get_post_settings_kb, get_button_creation_cancel_kb, get_reactions_selection_kb
from post_handlers.xinline_keyboard import generate_post_keyboard, get_button_type_reply_kb, ButtonTypeCallbackFactory
from admin_handlers.channel_handler import check_user_membership
from xdata_handlers.database import get_user_language, get_text_button_content
from xdata_handlers.translator import get_text
from xdata_handlers import config
from post_handlers.localize_filter import LocalizedText

logger = logging.getLogger(__name__)
button_router = Router()

URL_PATTERN = re.compile(
    r'^(https?:\/\/)?'
    r'([a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5})'
    r'(:[0-9]{1,5})?'
    r'(\/.*)?$',
    re.IGNORECASE
)

USERNAME_PATTERN = re.compile(r'^@([a-zA-Z0-9_]{5,32})$')



async def redraw_post(message: types.Message, state: FSMContext, answer_text: str = None):
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
    settings_keyboard = get_post_settings_kb(
        content_type=post_data.get('content_type', 'text'),
        has_caption=bool(post_data.get('caption')),
        lang=lang
    )

    if answer_text:
        await message.answer(answer_text, reply_markup=settings_keyboard)

    try:
        await message.bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=new_keyboard
        )
        try:
            await message.delete()
        except Exception:
            pass
        return
    except TelegramBadRequest:
        pass
    except Exception:
        pass

    try:
        await message.bot.delete_message(chat_id, message_id)
    except Exception:
        pass

    content_type = post_data.get('content_type')
    file_id = post_data.get("file_id")
    caption = post_data.get("caption")
    text = post_data.get("text")
    parse_mode = post_data.get("parse_mode", 'HTML')
    disable_preview = post_data.get("disable_web_page_preview", False)  # Standart yoqilgan
    sent_message = None

    message_kwargs = {
        "reply_markup": new_keyboard,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_preview
    }
    media_kwargs = {
        "reply_markup": new_keyboard,
        "parse_mode": parse_mode
    }

    try:
        if content_type == 'text':
            sent_message = await message.bot.send_message(chat_id, text=text, **message_kwargs)
        elif content_type == 'photo':
            sent_message = await message.bot.send_photo(chat_id, file_id, caption=caption, **media_kwargs)
        elif content_type == 'video':
            sent_message = await message.bot.send_video(chat_id, file_id, caption=caption, **media_kwargs)
        elif content_type == 'audio':
            sent_message = await message.bot.send_audio(chat_id, file_id, caption=caption, **media_kwargs)
        elif content_type == 'document':
            sent_message = await message.bot.send_document(chat_id, file_id, caption=caption, **media_kwargs)
        elif content_type == 'video_note':
            sent_message = await message.bot.send_video_note(chat_id, file_id, reply_markup=new_keyboard)
        elif content_type == 'voice':
            sent_message = await message.bot.send_voice(chat_id, file_id, caption=caption, **media_kwargs)
        elif content_type == 'animation':
            sent_message = await message.bot.send_animation(chat_id, file_id, caption=caption, **media_kwargs)
        elif content_type == 'sticker':
            sent_message = await message.bot.send_sticker(chat_id, file_id, reply_markup=new_keyboard)
        elif content_type in ['poll', 'dice', 'location']:
            # Ushbu turlar uchun alohida yuborish metodlari (poll, dice, location)
            if content_type == 'poll':
                sent_message = await message.bot.send_poll(
                    chat_id,
                    question=post_data.get('poll_question', ''),
                    options=post_data.get('poll_options', []),
                    is_anonymous=post_data.get('poll_is_anonymous', True),
                    allows_multiple_answers=post_data.get('poll_allows_multiple_answers', False),
                    correct_option_id=post_data.get('poll_correct_option_id'),
                    type='quiz' if post_data.get('poll_is_quiz', False) else 'regular',
                    explanation=post_data.get('poll_explanation'),
                    reply_markup=new_keyboard
                )
            elif content_type == 'dice':
                sent_message = await message.bot.send_dice(
                    chat_id,
                    emoji=post_data.get('dice_emoji', '🎲'),
                    reply_markup=new_keyboard
                )
            elif content_type == 'location':
                sent_message = await message.bot.send_location(
                    chat_id,
                    latitude=post_data.get('latitude'),
                    longitude=post_data.get('longitude'),
                    reply_markup=new_keyboard
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
            
            sent_message = await message.bot.send_paid_media(
                chat_id=chat_id,
                star_count=post_data.get('paid_price', 1),
                media=input_media_list,
                caption=caption,
                parse_mode=parse_mode,
                show_caption_above_media=post_data.get('show_caption_above_media', False),
                reply_markup=new_keyboard
            )

        if sent_message:
            post_data['message_id'] = sent_message.message_id
            await state.update_data(post_data=post_data)
    except Exception:
        pass



@button_router.callback_query(PostCreation.configuring_post, F.data.startswith("add:"))
async def start_add_button(callback: types.CallbackQuery, state: FSMContext):
    coords = callback.data.split(':')[1:]
    await state.update_data(target_button_coords=(int(coords[0]), int(coords[1])))
    await state.update_data(is_editing_button=False)
    
    lang = await get_user_language(callback.from_user.id)
    
    await state.set_state(PostCreation.waiting_for_button_type)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(get_text('ask_btn_type_msg', lang), reply_markup=get_button_type_reply_kb(lang))
    await callback.answer()

@button_router.message(PostCreation.waiting_for_button_type, LocalizedText('url_type_btn'))
async def process_button_type_url(message: types.Message, state: FSMContext):
    """URL tugma tanlandi -> Eski oqim"""
    lang = await get_user_language(message.from_user.id)
    await state.set_state(PostCreation.waiting_for_button_text)
    await message.answer(get_text('ask_btn_text_msg', lang), reply_markup=get_button_creation_cancel_kb(lang))

@button_router.message(PostCreation.waiting_for_button_type, LocalizedText('text_type_btn'))
async def process_button_type_text(message: types.Message, state: FSMContext):
    """Matnli tugma tanlandi -> Yangi oqim"""
    lang = await get_user_language(message.from_user.id)
    await state.set_state(PostCreation.waiting_for_button_text)
    await state.update_data(button_type="text_btn")
    await message.answer(get_text('ask_btn_text_msg', lang), reply_markup=get_button_creation_cancel_kb(lang))

@button_router.message(PostCreation.waiting_for_button_type, LocalizedText('reactions_btn'))
async def process_button_type_reactions(message: types.Message, state: FSMContext):
    """Reaksiya tugma tanlandi"""
    lang = await get_user_language(message.from_user.id)
    await state.set_state(PostCreation.waiting_for_reactions)
    await state.update_data(button_type="reaction")
    
    await message.answer(
        get_text("reactions_prompt_msg", lang),
        reply_markup=get_reactions_selection_kb(lang),
        parse_mode="HTML"
    )

@button_router.message(PostCreation.waiting_for_button_type, LocalizedText('back_btn'))
async def process_button_type_back(message: types.Message, state: FSMContext):
    """Ortga -> Post sozlashga qaytish"""
    lang = await get_user_language(message.from_user.id)
    await state.set_state(PostCreation.configuring_post)
    await redraw_post(message, state, get_text('back_to_settings_msg', lang))

@button_router.message(
    StateFilter(
        PostCreation.waiting_for_content,
        PostCreation.waiting_for_button_text,
        PostCreation.waiting_for_button_url,
        PostCreation.waiting_for_text_btn_content_sub,
        PostCreation.waiting_for_text_btn_content_nonsub,
        PostCreation.editing_button_text,
        PostCreation.editing_button_url,
        PostCreation.editing_button_url
    ),
    LocalizedText('back_btn')
)
async def back_to_configuring_post(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    await state.set_state(PostCreation.configuring_post)
    lang = await get_user_language(message.from_user.id)

    answer_text = get_text('back_to_settings_msg', lang)
    if current_state == PostCreation.waiting_for_content:
        answer_text = get_text('edit_cancelled_msg', lang)

    await redraw_post(message, state, answer_text)

@button_router.message(
    PostCreation.waiting_for_button_text,
    F.text,
    ~LocalizedText('back_btn')
)
async def process_button_text(message: types.Message, state: FSMContext):
    # Premium emoji ni to'g'ri qabul qilish
    button_text = message.text
    custom_emoji_id = None
    
    # Agar custom emoji bo'lsa, uni saqlash
    if message.entities:
        for entity in message.entities:
            if entity.type == 'custom_emoji':
                custom_emoji_id = entity.custom_emoji_id
                break
    
    await state.update_data(button_text=button_text, button_emoji_id=custom_emoji_id)
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    
    if data.get("button_type") == "text_btn":
        await state.set_state(PostCreation.waiting_for_text_btn_content_sub)
        await message.answer(get_text('ask_btn_sub_msg', lang), reply_markup=get_button_creation_cancel_kb(lang))
    else:
        await message.answer(get_text('ask_btn_url_msg', lang), reply_markup=get_button_creation_cancel_kb(lang))
        await state.set_state(PostCreation.waiting_for_button_url)

@button_router.message(
    PostCreation.waiting_for_text_btn_content_sub,
    F.text,
    ~LocalizedText('back_btn')
)
async def process_text_btn_content_sub(message: types.Message, state: FSMContext):
    await state.update_data(text_btn_content_sub=message.text)
    lang = await get_user_language(message.from_user.id)
    await state.set_state(PostCreation.waiting_for_text_btn_content_nonsub)
    await message.answer(get_text('ask_btn_nonsub_msg', lang), reply_markup=get_button_creation_cancel_kb(lang))

@button_router.message(
    PostCreation.waiting_for_text_btn_content_nonsub,
    F.text,
    ~LocalizedText('back_btn')
)
async def process_text_btn_content_nonsub(message: types.Message, state: FSMContext):
    content_nonsub = message.text
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    content_sub = data.get("text_btn_content_sub")
    button_text = data.get("button_text")
    
    from xdata_handlers.database import create_text_button
    btn_id = await create_text_button(content_sub, content_nonsub)
    
    if not btn_id:
        await message.answer(get_text('btn_creation_error_msg', lang))
        return

    button_emoji_id = data.get("button_emoji_id")
    buttons_matrix = data.get("buttons_matrix", [])
    is_editing = data.get("is_editing_button", False)
    
    if is_editing:
        target_row, target_col = data.get("editing_button_coords")
        status_text = get_text('btn_edited_msg', lang)
    else:
        target_row, target_col = data.get("target_button_coords")
        status_text = get_text('btn_added_msg', lang)
    
    new_btn = {
        'text': button_text,
        'url': None,
        'type': 'text_btn',
        'btn_id': btn_id
    }
    if button_emoji_id:
        new_btn['emoji_id'] = button_emoji_id
    
    # Matritsani kengaytirish
    while len(buttons_matrix) <= target_row: buttons_matrix.append([])
    while len(buttons_matrix[target_row]) <= target_col: buttons_matrix[target_row].append(None)
    
    if is_editing:
        if len(buttons_matrix) > target_row and len(buttons_matrix[target_row]) > target_col:
            buttons_matrix[target_row][target_col] = new_btn
    else:
        buttons_matrix[target_row][target_col] = new_btn
        
        # Clean matrix logic
        clean_matrix = [list(filter(None, row)) for row in buttons_matrix]
        clean_matrix = [row for row in clean_matrix if row]
        final_matrix = []
        for row in clean_matrix:
            new_row = [btn for btn in row if not btn.get('is_placeholder')]
            if len(new_row) < 8: new_row.append({'is_placeholder': True})
            final_matrix.append(new_row)
        if not final_matrix or any(btn and not btn.get('is_placeholder') for btn in final_matrix[-1]):
            final_matrix.append([{'is_placeholder': True}])
        buttons_matrix = final_matrix
    
    await state.update_data(buttons_matrix=buttons_matrix, is_editing_button=False)
    await state.set_state(PostCreation.configuring_post)
    await redraw_post(message, state, status_text)


@button_router.message(
    PostCreation.waiting_for_button_url,
    F.text,
    ~LocalizedText('back_btn')
)
async def add_or_edit_button(message: types.Message, state: FSMContext):
    user_input = message.text
    lang = await get_user_language(message.from_user.id)
    final_url = ""
    
    username_match = USERNAME_PATTERN.match(user_input)
    if username_match:
        final_url = f"https://t.me/{username_match.group(1)}"
    else:
        temp_url = user_input
        if not temp_url.startswith(('http://', 'https://')):
            temp_url = 'https://' + temp_url
        if URL_PATTERN.match(temp_url):
            final_url = temp_url
        else:
            return await message.answer(get_text('invalid_url_msg', lang))
    data = await state.get_data()
    button_text = data.get("button_text")
    button_emoji_id = data.get("button_emoji_id")
    buttons_matrix = data.get("buttons_matrix", [])
    is_editing = data.get("is_editing_button", False)

    new_btn = {'text': button_text, 'url': final_url}
    if button_emoji_id:
        new_btn['emoji_id'] = button_emoji_id

    if is_editing:
        target_row, target_col = data.get("editing_button_coords")
        status_text = get_text('btn_edited_msg', lang)
        if len(buttons_matrix) > target_row and len(buttons_matrix[target_row]) > target_col:
            # Preserve existing properties (like type) if editing
            old_btn = buttons_matrix[target_row][target_col]
            if old_btn: new_btn['type'] = old_btn.get('type', 'url')
            buttons_matrix[target_row][target_col] = new_btn
    else:
        target_row, target_col = data.get("target_button_coords")
        status_text = get_text('btn_added_msg', lang)
        while len(buttons_matrix) <= target_row: buttons_matrix.append([])
        while len(buttons_matrix[target_row]) <= target_col: buttons_matrix[target_row].append(None)
        
        new_btn['type'] = 'url'
        buttons_matrix[target_row][target_col] = new_btn

        # Clean matrix logic
        clean_matrix = [list(filter(None, row)) for row in buttons_matrix]
        clean_matrix = [row for row in clean_matrix if row]
        final_matrix = []
        for row in clean_matrix:
            new_row = [btn for btn in row if not btn.get('is_placeholder')]
            if len(new_row) < 8: new_row.append({'is_placeholder': True})
            final_matrix.append(new_row)
        if not final_matrix or any(btn and not btn.get('is_placeholder') for btn in final_matrix[-1]):
             final_matrix.append([{'is_placeholder': True}])
        buttons_matrix = final_matrix

    await state.update_data(buttons_matrix=buttons_matrix, is_editing_button=False)
    await state.set_state(PostCreation.configuring_post)
    await redraw_post(message, state, status_text)


@button_router.callback_query(PostCreation.configuring_post, F.data.startswith("manage:"))
async def manage_button_menu(callback: types.CallbackQuery, state: FSMContext):
    coords = callback.data.split(':')[1:]
    row_idx, col_idx = int(coords[0]), int(coords[1])
    await state.update_data(editing_button_coords=(row_idx, col_idx))
    await state.set_state(PostCreation.managing_button)
    lang = await get_user_language(callback.from_user.id)

    data = await state.get_data()
    buttons_matrix = data.get("buttons_matrix", [])
    if len(buttons_matrix) > row_idx and len(buttons_matrix[row_idx]) > col_idx:
        btn = buttons_matrix[row_idx][col_idx]
        if btn:
            await state.update_data(button_type=btn.get('type', 'url'))

    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=get_text('edit_post_btn', lang)), KeyboardButton(text=get_text('delete_btn', lang)))
    builder.row(KeyboardButton(text=get_text('back_btn', lang)))
    builder.adjust(2,1)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(get_text('manage_btn_msg', lang).format(row=row_idx+1, number=col_idx+1), reply_markup=builder.as_markup(resize_keyboard=True))
    await callback.answer()

@button_router.message(PostCreation.managing_button, LocalizedText('back_btn'))
async def back_from_edit_button(message: types.Message, state: FSMContext):
    await state.set_state(PostCreation.configuring_post)
    lang = await get_user_language(message.from_user.id)
    await redraw_post(message, state, get_text('back_to_settings_msg', lang))

@button_router.message(PostCreation.managing_button, LocalizedText('edit_post_btn'))
async def ask_for_edit_text(message: types.Message, state: FSMContext):
    await state.update_data(is_editing_button=True)
    await state.set_state(PostCreation.editing_button_text) # Yangilangan holat
    lang = await get_user_language(message.from_user.id)
    await message.answer(get_text('ask_edit_btn_text_msg', lang), reply_markup=get_button_creation_cancel_kb(lang))

@button_router.message(PostCreation.managing_button, LocalizedText('delete_btn'))
async def delete_button(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = await get_user_language(message.from_user.id)
    coords = data.get("editing_button_coords")
    if not coords: return

    target_row, target_col = coords
    buttons_matrix = data.get("buttons_matrix", [])

    real_buttons_in_row = [btn for btn in buttons_matrix[target_row] if btn and not btn.get('is_placeholder')]
    if len(real_buttons_in_row) > target_col:
        btn_to_del = real_buttons_in_row[target_col]
        buttons_matrix[target_row].remove(btn_to_del)

    clean_matrix = []
    for row in buttons_matrix:
        new_row = [btn for btn in row if btn and not btn.get('is_placeholder')]
        if new_row:
            clean_matrix.append(new_row)

    final_matrix = []
    for row in clean_matrix:
        if len(row) < 8:
            row.append({'is_placeholder': True})
        final_matrix.append(row)

    if not final_matrix or all(not btn.get('is_placeholder') for btn in final_matrix[-1]):
        final_matrix.append([{'is_placeholder': True}])


    await state.update_data(buttons_matrix=final_matrix)
    await state.set_state(PostCreation.configuring_post)
    await redraw_post(message, state, get_text('btn_deleted_msg', lang))



@button_router.message(
    PostCreation.editing_button_text,
    F.text,
    ~LocalizedText('back_btn')
)
async def process_editing_button_text(message: types.Message, state: FSMContext):
    # Premium emoji ni to'g'ri qabul qilish
    button_text = message.text
    custom_emoji_id = None
    
    # Agar custom emoji bo'lsa, uni saqlash
    if message.entities:
        for entity in message.entities:
            if entity.type == 'custom_emoji':
                custom_emoji_id = entity.custom_emoji_id
                break
    
    await state.update_data(button_text=button_text, button_emoji_id=custom_emoji_id)
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    
    if data.get("button_type") == "text_btn":
        await state.set_state(PostCreation.waiting_for_text_btn_content_sub)
        await message.answer(get_text('ask_btn_sub_msg', lang), reply_markup=get_button_creation_cancel_kb(lang))
    elif data.get("button_type") == "reaction":
        buttons_matrix = data.get("buttons_matrix", [])
        target_row, target_col = data.get("editing_button_coords")
        if len(buttons_matrix) > target_row and len(buttons_matrix[target_row]) > target_col:
            buttons_matrix[target_row][target_col]['text'] = button_text
            if custom_emoji_id:
                buttons_matrix[target_row][target_col]['emoji_id'] = custom_emoji_id
        
        await state.update_data(buttons_matrix=buttons_matrix, is_editing_button=False)
        await state.set_state(PostCreation.configuring_post)
        await redraw_post(message, state, get_text('btn_edited_msg', lang))
    else:
        await state.set_state(PostCreation.waiting_for_button_url)
        await message.answer(get_text('ask_edit_btn_url_msg', lang), reply_markup=get_button_creation_cancel_kb(lang))






@button_router.callback_query(F.data.startswith("text_btn:"))
async def handle_text_button_click(callback: types.CallbackQuery, bot: Bot):
    try:
        parts = callback.data.split(":")
        btn_id = int(parts[1]) if len(parts) > 1 else None
    except (ValueError, IndexError):
        lang = await get_user_language(callback.from_user.id)
        await callback.answer(get_text('btn_id_error_msg', lang), show_alert=True)
        return

    lang = await get_user_language(callback.from_user.id)
    content = await get_text_button_content(btn_id)
    if not content:
        await callback.answer(get_text('btn_not_found_msg', lang), show_alert=True)
        return

    is_member, warning_text, keyboard = await check_user_membership(callback.from_user, bot)

    if is_member and callback.from_user.id not in config.ADMIN_IDS:
        if callback.message.chat.type in ['channel', 'supergroup']:
            try:
                chat_member = await bot.get_chat_member(callback.message.chat.id, callback.from_user.id)
                if chat_member.status in ['left', 'kicked']:
                    is_member = False
            except Exception:
                pass

    if is_member:
        text = content.get('content_sub', "")
        if text:
            if len(text) > 190:
                 await callback.answer(text[:192] + "...", show_alert=True)
            else:
                 await callback.answer(text, show_alert=True)
        else:
            await callback.answer()
    else:
        if keyboard:
            await callback.answer(get_text('join_alert_msg', lang), show_alert=True)
            try:
                await bot.send_message(
                    chat_id=callback.from_user.id,
                    text=warning_text,
                    reply_markup=keyboard
                )
            except Exception:
                pass
        else:
            text = content.get('content_nonsub', "")
            if text:
                if len(text) > 190:
                    await callback.answer(text[:192] + "...", show_alert=True)
                else:
                    await callback.answer(text, show_alert=True)
            else:
                await callback.answer()


@button_router.callback_query(F.data.startswith("text_btn_preview:"))
async def handle_text_button_preview(callback: types.CallbackQuery):
    try:
        parts = callback.data.split(":")
        btn_id = int(parts[1]) if len(parts) > 1 else None
    except:
        return

    lang = await get_user_language(callback.from_user.id)
    content = await get_text_button_content(btn_id)
    if not content:
        await callback.answer(get_text('no_data_error_msg', lang), show_alert=True)
        return

    text = content.get('content_sub', "")
    preview_text = f"{get_text('preview_prefix_msg', lang)} {text}"
    await callback.answer(preview_text, show_alert=True)


@button_router.message(PostCreation.configuring_post, LocalizedText("reactions_btn"))
async def start_adding_reactions(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    await message.answer(
        get_text("reactions_prompt_msg", lang),
        reply_markup=get_reactions_selection_kb(lang),
        parse_mode="HTML"
    )
    await state.set_state(PostCreation.waiting_for_reactions)

@button_router.message(PostCreation.waiting_for_reactions)
async def process_reactions(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    text = message.text.strip()
    
    if text == get_text('back_btn', lang):
        await state.set_state(PostCreation.configuring_post)
        await redraw_post(message, state, get_text('back_to_settings_msg', lang))
        return

    # Parse reactions
    raw_reactions = [r.strip() for r in text.split('/')]
    reactions = [r for r in raw_reactions if r]
    
    if not reactions:
        await message.answer(get_text("reactions_prompt_msg", lang))
        return
        
    data = await state.get_data()
    
    # Reaksiyalarni joylashtirish
    # Koordinatalarni aniqlash
    if data.get("is_editing_button"):
        target_row, target_col = data.get("editing_button_coords")
    else:
        target_row, target_col = data.get("target_button_coords")

    buttons_matrix = data.get("buttons_matrix", [])
    while len(buttons_matrix) <= target_row: buttons_matrix.append([])
    while len(buttons_matrix[target_row]) <= target_col: buttons_matrix[target_row].append(None)

    # Birinchi reaksiya
    first_reaction = reactions[0]
    first_btn = {
        'text': first_reaction,
        'url': None,
        'type': 'reaction',
        'is_placeholder': False
    }
    
    if len(buttons_matrix[target_row]) > target_col:
        buttons_matrix[target_row][target_col] = first_btn
    else:
        buttons_matrix[target_row].insert(target_col, first_btn)

    # Qolgan reaksiyalar
    for i, reaction in enumerate(reactions[1:], start=1):
        next_col = target_col + i
        next_btn = {
            'text': reaction,
            'url': None,
            'type': 'reaction',
            'is_placeholder': False
        }
        if len(buttons_matrix[target_row]) > next_col:
             buttons_matrix[target_row].insert(next_col, next_btn)
        else:
             buttons_matrix[target_row].append(next_btn)

    # Clean matrix logic
    clean_matrix = [list(filter(None, row)) for row in buttons_matrix]
    clean_matrix = [row for row in clean_matrix if row]
    final_matrix = []
    for row in clean_matrix:
        new_row = [btn for btn in row if not btn.get('is_placeholder')]
        if len(new_row) < 8: new_row.append({'is_placeholder': True})
        final_matrix.append(new_row)
    if not final_matrix or any(btn and not btn.get('is_placeholder') for btn in final_matrix[-1]):
            final_matrix.append([{'is_placeholder': True}])
    buttons_matrix = final_matrix

    await state.update_data(buttons_matrix=buttons_matrix, is_editing_button=False)
    await state.set_state(PostCreation.configuring_post)
    await redraw_post(message, state, get_text("reactions_saved_msg", lang))


@button_router.callback_query(PostCreation.waiting_for_reaction_color, F.data.startswith("btn_color:"))
async def process_reaction_color(callback: types.CallbackQuery, state: FSMContext):
    """Reaksiya tugmalari uchun rang tanlash"""
    lang = await get_user_language(callback.from_user.id)
    parts = callback.data.split(":")
    style = parts[1] if len(parts) > 1 and parts[1] else ""
    
    data = await state.get_data()
    reactions = data.get("temp_reactions", [])
    buttons_matrix = data.get("buttons_matrix", [])
    is_editing = data.get("is_editing_button", False)
    
    # Koordinatalarni aniqlash
    if is_editing:
        target_row, target_col = data.get("editing_button_coords")
    else:
        target_row, target_col = data.get("target_button_coords")

    # Matritsani kengaytirish (xavfsizlik uchun)
    while len(buttons_matrix) <= target_row: buttons_matrix.append([])
    while len(buttons_matrix[target_row]) <= target_col: buttons_matrix[target_row].append(None)

    emoji = get_style_emoji(style) if style else ''

    # Reaksiyalarni joylashtirish
    # Birinchi reaksiyani bosilgan tugma o'rniga qo'yamiz
    first_reaction = reactions[0]
    first_btn_text = f"{emoji} {first_reaction}".strip() or first_reaction
    first_btn = {
        'text': first_btn_text,
        'url': None,
        'type': 'reaction',
        'is_placeholder': False
    }
    if style:
        first_btn['style'] = style
    
    # Agar tahrirlash bo'lsa yoki joy bo'sh bo'lsa (yoki placeholder bo'lsa) o'rniga yozamiz
    if len(buttons_matrix[target_row]) > target_col:
        buttons_matrix[target_row][target_col] = first_btn
    else:
        buttons_matrix[target_row].insert(target_col, first_btn)

    # Qolgan reaksiyalarni (masalan, 👍/👎 dagi ikkinchisi) o'ng tomonga qo'shamiz
    for i, reaction in enumerate(reactions[1:], start=1):
        next_col = target_col + i
        next_btn_text = f"{emoji} {reaction}".strip() or reaction
        next_btn = {
            'text': next_btn_text,
            'url': None,
            'type': 'reaction',
            'is_placeholder': False
        }
        if style:
            next_btn['style'] = style
        # Insert qilamiz, shunda o'ngdagi tugmalar suriladi
        if len(buttons_matrix[target_row]) > next_col:
             buttons_matrix[target_row].insert(next_col, next_btn)
        else:
             buttons_matrix[target_row].append(next_btn)

    # Tozalash va Placeholderlarni qayta tartiblash
    clean_matrix = [list(filter(None, row)) for row in buttons_matrix]
    clean_matrix = [row for row in clean_matrix if row]
    final_matrix = []
    for row in clean_matrix:
        new_row = [btn for btn in row if not btn.get('is_placeholder')]
        # Har bir qatorda 8 tagacha tugma bo'lishi mumkin + 1 placeholder
        if len(new_row) < 8: new_row.append({'is_placeholder': True})
        final_matrix.append(new_row)
        
    # Agar oxirgi qator to'liq bo'lsa, yangi placeholder qator qo'shamiz
    if not final_matrix or any(btn and not btn.get('is_placeholder') for btn in final_matrix[-1]):
            final_matrix.append([{'is_placeholder': True}])
            
    buttons_matrix = final_matrix
    
    # Vaqtinchalik ma'lumotlarni tozalash
    await state.update_data(
        buttons_matrix=buttons_matrix, 
        is_editing_button=False,
        temp_reactions=None
    )
    
    await state.set_state(PostCreation.configuring_post)
    
    await callback.answer()
    await redraw_post(callback.message, state, get_text("reactions_saved_msg", lang))

@button_router.callback_query(F.data.startswith("reaction:"))
async def handle_reaction_click(callback: types.CallbackQuery):
    try:
        parts = callback.data.split(":")
        reaction = parts[1] if len(parts) > 1 else ""
    except IndexError:
        await callback.answer()
        return

    # Xabar mavjud emasligini tekshirish
    if callback.message is None:
        await callback.answer("Xabar topilmadi", show_alert=True)
        return

    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    message_id = callback.message.message_id
    
    from xdata_handlers.database import add_or_update_reaction_by_chat_message, get_user_language, get_reaction_count_by_chat_message
    
    lang = await get_user_language(user_id)
    
    # DB ga yozish va holatni tekshirish
    status, old_reaction = await add_or_update_reaction_by_chat_message(user_id, chat_id, message_id, reaction)
    
    if status == 'error':
        await callback.answer("Error occurred", show_alert=True)
        return
        
    if status == 'already_voted':
        await callback.answer(get_text('already_voted_msg', lang), show_alert=True)
        return

    # Klaviaturani yangilash (faqat yangi reaksiya qo'shilganda)
    if status == 'added':
        keyboard = callback.message.reply_markup
        if not keyboard:
            await callback.answer()
            return
        
        found = False
        new_kb_list = []
        
        for row in keyboard.inline_keyboard:
            new_row = []
            for btn in row:
                # Matnni parse qilish (masalan "👍 42")
                parts = btn.text.split()
                
                # Bazadan haqiqiy reaksiya sonini olamiz
                if btn.callback_data and btn.callback_data.startswith("reaction:"):
                    parts = btn.callback_data.split(":")
                    btn_reaction = parts[1] if len(parts) > 1 else ""
                    count = await get_reaction_count_by_chat_message(chat_id, message_id, btn_reaction)
                    
                    # Emojini matn boshidan olish (raqamni olib tashlab)
                    current_emoji = " ".join(parts[:-1]) if len(parts) > 1 else parts[0]
                    if len(parts) == 1: current_emoji = parts[0]
                    
                    btn.text = f"{current_emoji} {count}"
                    found = True

                new_row.append(btn)
            new_kb_list.append(new_row)
                
        if found:
            try:
                updated_markup = types.InlineKeyboardMarkup(inline_keyboard=new_kb_list)
                await callback.message.edit_reply_markup(reply_markup=updated_markup)
                
                alert_text = get_text('vote_accepted_msg', lang).format(reaction=reaction)
                await callback.answer(alert_text)
            except TelegramBadRequest:
                await callback.answer()
        else:
            await callback.answer()
    else:
        await callback.answer()
