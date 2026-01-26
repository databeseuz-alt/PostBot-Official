#--- START OF FILE post_handlers/button_handler.py ---

import re
import logging
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder, KeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter

from post_handlers.vpost_states import PostCreation
from post_handlers.xreply_keyboard import get_post_settings_kb, get_button_creation_cancel_kb
from post_handlers.xinline_keyboard import generate_post_keyboard
from xdata_handlers.database import get_user_language
from xdata_handlers.translator import get_text
from post_handlers.localize_filter import LocalizedText

button_router = Router()

#==================================================
# --- Y A N G I L A N G A N   U R L   T E K SH I R U V I ---
#==================================================
# Bu RegEx t.co, google.com, sub.domain.uz kabi barcha variantlarni to'g'ri qabul qiladi
# va TLD kamida 2ta harf bo'lishini talab qiladi.
URL_PATTERN = re.compile(
    r'^(https?:\/\/)?'  # Protokol (ixtiyoriy)
    r'([a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,})'  # Asosiy domen qismi (masalan, google.com yoki sub.google.com)
    r'(\/.*)?$',  # Yo'l va so'rovlar (ixtiyoriy)
    re.IGNORECASE
)

USERNAME_PATTERN = re.compile(r'^@([a-zA-Z0-9_]{5,32})$')


#=============================================================================
# YORDAMCHI FUNKSIYA: POSTNI QAYTA CHIZISH (OPTIMALLASHTIRILGAN)
#=============================================================================

async def redraw_post(message: types.Message, state: FSMContext, answer_text: str = None):
    data = await state.get_data()
    buttons_matrix = data.get("buttons_matrix", [])
    post_data = data.get("post_data", {})
    if not post_data:
        return

    chat_id = post_data.get("chat_id")
    message_id = post_data.get("message_id")
    new_keyboard = generate_post_keyboard(buttons_matrix)

    # --- X A T O L I K   T U Z A T I L D I ---
    # `get_post_settings_kb` uchun kerakli argumentlarni `state`'dan olamiz
    lang = await get_user_language(message.from_user.id)
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
        logging.warning(f"Klaviaturani o'zgartirib bo'lmadi, postni qayta yuborish...")
    except Exception as e:
        logging.error(f"Klaviaturani tahrirlashda kutilmagan xatolik: {e}")

    # ZAXIRA USUL
    try:
        await message.bot.delete_message(chat_id, message_id)
    except Exception:
        pass

    content_type = post_data.get('content_type')
    file_id = post_data.get("file_id")
    caption = post_data.get("caption")
    text = post_data.get("text")
    parse_mode = post_data.get("parse_mode")
    disable_preview = post_data.get("disable_web_page_preview", False)
    sent_message = None

    # Parametrlarni alohida tayyorlaymiz
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
        # YANGI: Voice (ovozli xabar) qayta yuborish
        elif content_type == 'voice':
            sent_message = await message.bot.send_voice(chat_id, file_id, caption=caption, **media_kwargs)

        if sent_message:
            post_data['message_id'] = sent_message.message_id
            await state.update_data(post_data=post_data)
    except Exception as e:
        logging.error(f"Postni zaxira usulida qayta yuborishda xatolik: {e}")


#=============================================================================
# HANDLERLAR: YANGI TUGMA QO'SHISH
#=============================================================================

@button_router.callback_query(PostCreation.configuring_post, F.data.startswith("add:"))
async def ask_for_button_text(callback: types.CallbackQuery, state: FSMContext):
    coords = callback.data.split(':')[1:]
    await state.update_data(target_button_coords=(int(coords[0]), int(coords[1])))
    await state.update_data(is_editing_button=False)
    await state.set_state(PostCreation.waiting_for_button_text)

    try:
        await callback.message.delete()
    except Exception:
        pass

    lang = await get_user_language(callback.from_user.id)
    await callback.message.answer(get_text('ask_button_text', lang), reply_markup=get_button_creation_cancel_kb(lang))
    await callback.answer()

@button_router.message(
    StateFilter(
        PostCreation.waiting_for_content,
        PostCreation.waiting_for_button_text,
        PostCreation.waiting_for_button_url
    ),
    LocalizedText('btn_back_from_button')
)
async def back_to_configuring_post(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    await state.set_state(PostCreation.configuring_post)
    lang = await get_user_language(message.from_user.id)

    answer_text = get_text('back_to_settings', lang)
    if current_state == PostCreation.waiting_for_content:
        answer_text = get_text('editing_canceled', lang)

    await redraw_post(message, state, answer_text)

@button_router.message(
    PostCreation.waiting_for_button_text,
    F.text,
    ~LocalizedText('btn_back_from_button')
)
async def ask_for_button_url(message: types.Message, state: FSMContext):
    await state.update_data(button_text=message.text)
    lang = await get_user_language(message.from_user.id)
    await message.answer(get_text('ask_button_url', lang), reply_markup=get_button_creation_cancel_kb(lang))
    await state.set_state(PostCreation.waiting_for_button_url)

@button_router.message(
    PostCreation.waiting_for_button_url,
    F.text,
    ~LocalizedText('btn_back_from_button')
)
async def add_or_edit_button(message: types.Message, state: FSMContext):
    user_input = message.text
    lang = await get_user_language(message.from_user.id)
    final_url = ""

    # @username tekshiruvi
    username_match = USERNAME_PATTERN.match(user_input)
    if username_match:
        final_url = f"https://t.me/{username_match.group(1)}"
    else:
        # Oddiy URL tekshiruvi
        temp_url = user_input
        if not temp_url.startswith(('http://', 'https://')):
            temp_url = 'https://' + temp_url

        if URL_PATTERN.match(temp_url):
            final_url = temp_url
        else:
            return await message.answer(get_text('invalid_url', lang))

    data = await state.get_data()
    button_text = data.get("button_text")
    buttons_matrix = data.get("buttons_matrix", [])
    is_editing = data.get("is_editing_button", False)

    if is_editing:
        target_row, target_col = data.get("editing_button_coords")
        status_text = get_text('button_edited', lang)
        if len(buttons_matrix) > target_row and len(buttons_matrix[target_row]) > target_col:
            buttons_matrix[target_row][target_col] = {'text': button_text, 'url': final_url}
    else:
        target_row, target_col = data.get("target_button_coords")
        status_text = get_text('button_added', lang)
        while len(buttons_matrix) <= target_row: buttons_matrix.append([])
        while len(buttons_matrix[target_row]) <= target_col: buttons_matrix[target_row].append(None)
        buttons_matrix[target_row][target_col] = {'text': button_text, 'url': final_url}

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

#=============================================================================
# HANDLERLAR: MAVJUD TUGMANI BOSHQARISH
#=============================================================================

@button_router.callback_query(PostCreation.configuring_post, F.data.startswith("manage:"))
async def manage_button_menu(callback: types.CallbackQuery, state: FSMContext):
    coords = callback.data.split(':')[1:]
    await state.update_data(editing_button_coords=(int(coords[0]), int(coords[1])))
    await state.set_state(PostCreation.managing_button)
    lang = await get_user_language(callback.from_user.id)

    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=get_text('btn_edit', lang)), KeyboardButton(text=get_text('btn_delete', lang)))
    builder.row(KeyboardButton(text=get_text('btn_back_from_button', lang)))
    builder.adjust(2,1)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(get_text('manage_button_prompt', lang), reply_markup=builder.as_markup(resize_keyboard=True))
    await callback.answer()

@button_router.message(PostCreation.managing_button, LocalizedText('btn_back_from_button'))
async def back_from_edit_button(message: types.Message, state: FSMContext):
    await state.set_state(PostCreation.configuring_post)
    lang = await get_user_language(message.from_user.id)
    await redraw_post(message, state, get_text('back_to_settings', lang))

@button_router.message(PostCreation.managing_button, LocalizedText('btn_edit'))
async def ask_for_edit_text(message: types.Message, state: FSMContext):
    await state.update_data(is_editing_button=True)
    await state.set_state(PostCreation.waiting_for_button_text)
    lang = await get_user_language(message.from_user.id)
    await message.answer(get_text('ask_edit_button_text', lang), reply_markup=get_button_creation_cancel_kb(lang))

@button_router.message(PostCreation.managing_button, LocalizedText('btn_delete'))
async def delete_button(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = await get_user_language(message.from_user.id)
    coords = data.get("editing_button_coords")
    if not coords: return

    target_row, target_col = coords
    buttons_matrix = data.get("buttons_matrix", [])

    # Haqiqiy tugmani o'chiramiz
    real_buttons_in_row = [btn for btn in buttons_matrix[target_row] if btn and not btn.get('is_placeholder')]
    if len(real_buttons_in_row) > target_col:
        btn_to_del = real_buttons_in_row[target_col]
        buttons_matrix[target_row].remove(btn_to_del)

    # Butun massivni tozalab, qayta tartiblaymiz
    # 1. Faqat haqiqiy tugmalarni qoldiramiz
    clean_matrix = []
    for row in buttons_matrix:
        new_row = [btn for btn in row if btn and not btn.get('is_placeholder')]
        if new_row:
            clean_matrix.append(new_row)

    # 2. Tozalangan massiv asosida yangi 'placeholder'larni qo'shamiz
    final_matrix = []
    for row in clean_matrix:
        if len(row) < 8:
            row.append({'is_placeholder': True})
        final_matrix.append(row)

    # 3. Agar oxirgi qator to'la bo'lsa yoki umuman qator qolmagan bo'lsa, yangi bo'sh qator qo'shamiz
    if not final_matrix or all(not btn.get('is_placeholder') for btn in final_matrix[-1]):
        final_matrix.append([{'is_placeholder': True}])


    await state.update_data(buttons_matrix=final_matrix)
    await state.set_state(PostCreation.configuring_post)
    await redraw_post(message, state, get_text('button_deleted', lang))

@button_router.message(PostCreation.editing_button_text, F.text)
async def ask_for_edit_url(message: types.Message, state: FSMContext):
    await state.update_data(button_text=message.text)
    await state.set_state(PostCreation.waiting_for_button_url)
    lang = await get_user_language(message.from_user.id)
    await message.answer(get_text('ask_edit_button_url', lang), reply_markup=get_button_creation_cancel_kb(lang))

#--- END OF FILE button_handler.py ---
