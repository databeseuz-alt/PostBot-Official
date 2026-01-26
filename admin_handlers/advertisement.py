#--- START OF FILE admin_handlers/advertisement.py ---
import asyncio
import logging
import re
from aiogram import F, Router, types, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder, InlineKeyboardButton

# Loyihaning joriy strukturasiga moslashtirilgan importlar
from admin_handlers.admin_handler import IsAdmin
from admin_handlers.vadmin_states import AdminStates
from xdata_handlers.database import get_all_active_users
from xdata_handlers import config
from admin_handlers.xreply_keyboard import get_ad_post_settings_kb, get_admin_back_kb, get_cancel_kb, get_ad_back_kb
from post_handlers.xinline_keyboard import generate_preview_keyboard
from admin_handlers.xinline_keyboard import get_main_admin_keyboard

ad_router = Router()
URL_PATTERN = re.compile(r"^(https?://)?([\w-]{1,32}\.[\w-]{1,32})[^\s@]*$")

# =============================================================================
# YORDAMCHI FUNKSIYALAR
# =============================================================================

def generate_ad_edit_keyboard(buttons_matrix: list | None = None):
    builder = InlineKeyboardBuilder()
    if not buttons_matrix:
        builder.button(text="➕", callback_data="ad:add:0:0")
        return builder.as_markup()

    for r_idx, row in enumerate(buttons_matrix):
        current_row_buttons = []
        for c_idx, btn in enumerate(row):
            if btn.get('is_placeholder'):
                current_row_buttons.append(InlineKeyboardButton(text="➕", callback_data=f"ad:add:{r_idx}:{c_idx}"))
            else:
                current_row_buttons.append(InlineKeyboardButton(text=f"{btn['text']}", callback_data=f"ad:manage:{r_idx}:{c_idx}"))
        if current_row_buttons:
            builder.row(*current_row_buttons)
    return builder.as_markup()

async def redraw_ad_post(bot: Bot, chat_id: int, state: FSMContext, answer_text: str = None):
    data = await state.get_data()
    post_data = data.get("ad_post_data", {})
    buttons_matrix = data.get("ad_buttons_matrix", [])

    if 'last_ad_post_id' in data:
        try:
            await bot.delete_message(chat_id, data['last_ad_post_id'])
        except Exception:
            pass

    settings_kb = get_ad_post_settings_kb(post_data.get("disable_web_page_preview", False))

    if answer_text:
        await bot.send_message(chat_id, answer_text, reply_markup=settings_kb)

    keyboard = generate_ad_edit_keyboard(buttons_matrix)
    content_type = post_data.get('content_type')
    sent_message = None

    try:
        if content_type == 'text':
            sent_message = await bot.send_message(chat_id, post_data.get('text'), reply_markup=keyboard)
        elif content_type == 'photo':
            sent_message = await bot.send_photo(chat_id, post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
        elif content_type == 'video':
            sent_message = await bot.send_video(chat_id, post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
        elif content_type == 'audio':
            sent_message = await bot.send_audio(chat_id, post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
        elif content_type == 'document':
            sent_message = await bot.send_document(chat_id, post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
        elif content_type == 'animation':
            sent_message = await bot.send_animation(chat_id, post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
        # YANGI: Voice (ovozli xabar) uchun
        elif content_type == 'voice':
            sent_message = await bot.send_voice(chat_id, post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)

    except Exception as e:
        logging.error(f"Reklamani qayta chizishda xatolik: {e}")

    if sent_message:
        await state.update_data(last_ad_post_id=sent_message.message_id)

# =============================================================================
# REKLAMA YARATISH JARAYONI
# =============================================================================

@ad_router.callback_query(F.data == "admin:send_ad_start", IsAdmin())
async def send_ad_start(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AdminStates.waiting_for_ad_content)
    await callback.message.delete()
    await callback.message.answer("Reklama uchun post yuboring (matn, rasm, video, audio, hujjat, GIF yoki ovozli xabar).", reply_markup=get_admin_back_kb())
    await callback.answer()

@ad_router.message(
    AdminStates.waiting_for_ad_content,
    F.content_type.in_({'text', 'photo', 'video', 'audio', 'document', 'animation', 'voice'}),
    IsAdmin()
)
async def ad_content_received(message: types.Message, state: FSMContext, bot: Bot):
    await state.set_state(AdminStates.configuring_ad_post)
    file_id = None
    if message.photo: file_id = message.photo[-1].file_id
    elif message.video: file_id = message.video.file_id
    elif message.audio: file_id = message.audio.file_id
    elif message.document: file_id = message.document.file_id
    elif message.animation: file_id = message.animation.file_id
    elif message.voice: file_id = message.voice.file_id # YANGI

    await state.update_data(
        ad_post_data={
            'content_type': message.content_type,
            'text': message.text, 'caption': message.caption, 'file_id': file_id,
            'disable_web_page_preview': False
        },
        ad_buttons_matrix=[[{'is_placeholder': True}]]
    )
    await message.answer("Post qabul qilindi. Sozlash uchun menyudan foydalaning:", reply_markup=get_ad_post_settings_kb())
    await redraw_ad_post(bot, message.chat.id, state)

@ad_router.message(AdminStates.waiting_for_ad_content, IsAdmin())
async def ad_wrong_content_type(message: types.Message):
    await message.answer("❌ Ushbu media turi qabul qilinmaydi. Iltimos, faqat matn, rasm, video, audio, hujjat, GIF yoki ovozli xabar yuboring.")

# =============================================================================
# TUGMALARNI BOSHQARISH
# =============================================================================

@ad_router.callback_query(AdminStates.configuring_ad_post, F.data.startswith("ad:add:"), IsAdmin())
async def ad_ask_for_button_text(callback: types.CallbackQuery, state: FSMContext):
    coords = tuple(map(int, callback.data.split(':')[2:]))
    await state.update_data(target_ad_button_coords=coords, is_editing_ad_button=False)
    await state.set_state(AdminStates.waiting_for_ad_button_text)
    await callback.message.delete()
    await callback.message.answer("Tugma uchun matnni yuboring:", reply_markup=get_ad_back_kb())
    await callback.answer()

@ad_router.message(
    F.text == "◀️ Ortga",
    StateFilter(AdminStates.waiting_for_ad_button_text, AdminStates.waiting_for_ad_button_url),
    IsAdmin()
)
async def back_from_button_creation(message: types.Message, state: FSMContext, bot: Bot):
    await state.set_state(AdminStates.configuring_ad_post)
    await redraw_ad_post(bot, message.chat.id, state, "Tugma yaratish bekor qilindi. Asosiy sozlash menyusi.")

@ad_router.message(
    AdminStates.waiting_for_ad_button_text,
    F.text,
    ~F.text.in_({"◀️ Ortga"}),
    IsAdmin()
)
async def ad_ask_for_button_url(message: types.Message, state: FSMContext):
    await state.update_data(ad_button_text=message.text)
    await state.set_state(AdminStates.waiting_for_ad_button_url)
    await message.answer("Tugma uchun URL (havola) yuboring:", reply_markup=get_ad_back_kb())

@ad_router.message(
    AdminStates.waiting_for_ad_button_url,
    F.text,
    ~F.text.in_({"◀️ Ortga"}),
    IsAdmin()
)
async def ad_add_or_edit_button(message: types.Message, state: FSMContext, bot: Bot):
    user_url = message.text
    if not user_url.startswith(('http://', 'https://')): user_url = 'https://' + user_url
    if not URL_PATTERN.match(user_url): return await message.answer("Noto'g'ri URL! Qaytadan yuboring:")

    data = await state.get_data()
    buttons_matrix = data.get("ad_buttons_matrix", [])
    button_text = data.get("ad_button_text")
    is_editing = data.get("is_editing_ad_button", False)

    if is_editing:
        target_row, target_col = data.get("editing_ad_button_coords")
        status_text = "Tugma tahrirlandi!"
        buttons_matrix[target_row][target_col] = {'text': button_text, 'url': user_url}
    else:
        target_row, target_col = data.get("target_ad_button_coords")
        status_text = "Tugma qo'shildi!"
        while len(buttons_matrix) <= target_row: buttons_matrix.append([])
        while len(buttons_matrix[target_row]) <= target_col: buttons_matrix[target_row].append(None)
        buttons_matrix[target_row][target_col] = {'text': button_text, 'url': user_url}

    clean_matrix = [list(filter(None, row)) for row in buttons_matrix]
    clean_matrix = [row for row in clean_matrix if row]
    final_matrix = []
    for row in clean_matrix:
        new_row = [btn for btn in row if not btn.get('is_placeholder')]
        if len(new_row) < 8: new_row.append({'is_placeholder': True})
        final_matrix.append(new_row)
    if not final_matrix or any(btn and not btn.get('is_placeholder') for btn in final_matrix[-1]):
         final_matrix.append([{'is_placeholder': True}])

    await state.update_data(ad_buttons_matrix=final_matrix, is_editing_ad_button=False)
    await state.set_state(AdminStates.configuring_ad_post)
    await redraw_ad_post(bot, message.chat.id, state, status_text)

@ad_router.callback_query(AdminStates.configuring_ad_post, F.data.startswith("ad:manage:"), IsAdmin())
async def ad_manage_button_menu(callback: types.CallbackQuery, state: FSMContext):
    coords = tuple(map(int, callback.data.split(':')[2:]))
    await state.update_data(editing_ad_button_coords=coords)
    await state.set_state(AdminStates.managing_ad_button)
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="✏️ Tahrirlash"), types.KeyboardButton(text="🗑️ O'chirish"))
    builder.row(types.KeyboardButton(text="◀️ Ortga"))
    builder.adjust(2, 1)
    await callback.message.answer("Ushbu tugma bilan nima qilmoqchisiz?", reply_markup=builder.as_markup(resize_keyboard=True))
    await callback.answer()

@ad_router.message(AdminStates.managing_ad_button, F.text == "◀️ Ortga", IsAdmin())
async def ad_back_from_manage_button(message: types.Message, state: FSMContext, bot: Bot):
    await state.set_state(AdminStates.configuring_ad_post)
    await redraw_ad_post(bot, message.chat.id, state, "Asosiy sozlash menyusiga qaytildi.")

@ad_router.message(AdminStates.managing_ad_button, F.text == "✏️ Tahrirlash", IsAdmin())
async def ad_ask_for_edit_text(message: types.Message, state: FSMContext):
    await state.update_data(is_editing_ad_button=True)
    await state.set_state(AdminStates.waiting_for_ad_button_text)
    await message.answer("Tugma uchun YANGI matnni yuboring:", reply_markup=get_ad_back_kb())

@ad_router.message(AdminStates.managing_ad_button, F.text == "🗑️ O'chirish", IsAdmin())
async def ad_delete_button(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    coords = data.get("editing_ad_button_coords")
    if not coords: return
    buttons_matrix = data.get("ad_buttons_matrix", [])
    buttons_matrix[coords[0]].pop(coords[1])
    if not buttons_matrix[coords[0]]:
        buttons_matrix.pop(coords[0])
    await state.update_data(ad_buttons_matrix=buttons_matrix)
    await state.set_state(AdminStates.configuring_ad_post)
    await redraw_ad_post(bot, message.chat.id, state, "Tugma o'chirildi.")

# =============================================================================
# SOZLASH MENYUSI TUGMALARI
# =============================================================================

@ad_router.message(AdminStates.configuring_ad_post, F.text.in_({"👁️‍🗨️ Preview", "Preview: ON", "Preview: OFF", "🔡 Get Buttons", "✏️ Edit Content"}), IsAdmin())
async def ad_settings_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = message.text
    post_data = data.get("ad_post_data", {})
    buttons_matrix = data.get("ad_buttons_matrix", [])
    content_type = post_data.get('content_type')

    if text == "👁️‍🗨️ Preview":
        keyboard = generate_preview_keyboard(buttons_matrix)
        disable_preview = post_data.get("disable_web_page_preview", False)

        if content_type == 'text': await message.answer(post_data.get('text'), reply_markup=keyboard, disable_web_page_preview=disable_preview)
        elif content_type == 'photo': await message.answer_photo(post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
        elif content_type == 'video': await message.answer_video(post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
        elif content_type == 'audio': await message.answer_audio(post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
        elif content_type == 'document': await message.answer_document(post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
        elif content_type == 'animation': await message.answer_animation(post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
        # YANGI: Voice preview
        elif content_type == 'voice': await message.answer_voice(post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)

    elif text in {"Preview: ON", "Preview: OFF"}:
        is_disabled = post_data.get('disable_web_page_preview', False)
        new_state = not is_disabled
        post_data['disable_web_page_preview'] = new_state
        await state.update_data(ad_post_data=post_data)
        await message.answer(f"URL oldindan ko'rish {'o''chirildi' if new_state else 'yoqildi'}.", reply_markup=get_ad_post_settings_kb(new_state))

    elif text == "🔡 Get Buttons":
        response_text = "Sizning tugmalaringiz:\n\n"
        count = 1
        for row in buttons_matrix:
            for btn in row:
                if btn and not btn.get('is_placeholder'):
                    response_text += f"{count}. {btn['text']} = {btn['url']}\n"
                    count += 1
        await message.answer(response_text if count > 1 else "Siz hali tugma qo'shmadingiz.")

    elif text == "✏️ Edit Content":
        await state.set_state(AdminStates.waiting_for_ad_content)
        await message.answer("Post uchun yangi kontentni yuboring. Tugmalar saqlanib qoladi.", reply_markup=get_admin_back_kb())

# =============================================================================
# JARAYONNI YAKUNLASH VA YUBORISH
# =============================================================================

@ad_router.message(AdminStates.configuring_ad_post, F.text == "✅ Done", IsAdmin())
async def ad_done_confirmation(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    post_data = data.get("ad_post_data", {})
    buttons_matrix = data.get("ad_buttons_matrix", [])
    content_type = post_data.get('content_type')
    keyboard = generate_preview_keyboard(buttons_matrix)

    await message.answer("Yakuniy ko'rinish:", reply_markup=ReplyKeyboardRemove())

    if content_type == 'text': await message.answer(post_data.get('text'), reply_markup=keyboard, disable_web_page_preview=post_data.get("disable_web_page_preview", False))
    elif content_type == 'photo': await message.answer_photo(post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
    elif content_type == 'video': await message.answer_video(post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
    elif content_type == 'audio': await message.answer_audio(post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
    elif content_type == 'document': await message.answer_document(post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
    elif content_type == 'animation': await message.answer_animation(post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
    # YANGI: Voice final preview
    elif content_type == 'voice': await message.answer_voice(post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)

    confirmation_kb = InlineKeyboardBuilder()
    confirmation_kb.button(text="✅ Ha, yuborilsin", callback_data="ad:send_now")
    confirmation_kb.button(text="❌ Yo'q, bekor qilish", callback_data="ad:cancel_sending")
    await message.answer("Ushbu postni barcha faol foydalanuvchilarga yuborishni tasdiqlaysizmi?", reply_markup=confirmation_kb.as_markup())

async def send_ad_to_user(bot: Bot, user_id: int, post_data: dict, keyboard: types.InlineKeyboardMarkup | None):
    try:
        content_type = post_data.get('content_type')
        if content_type == 'text':
            await bot.send_message(user_id, post_data.get('text'), reply_markup=keyboard, disable_web_page_preview=post_data.get("disable_web_page_preview", False))
        elif content_type == 'photo':
            await bot.send_photo(user_id, post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
        elif content_type == 'video':
            await bot.send_video(user_id, post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
        elif content_type == 'audio':
            await bot.send_audio(user_id, post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
        elif content_type == 'document':
            await bot.send_document(user_id, post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
        elif content_type == 'animation':
            await bot.send_animation(user_id, post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
        # YANGI: Voice send
        elif content_type == 'voice':
            await bot.send_voice(user_id, post_data.get('file_id'), caption=post_data.get('caption'), reply_markup=keyboard)
        return True
    except Exception:
        return False

async def broadcast_advertisement(bot: Bot, users: list, post_data: dict, buttons_matrix: list, admin_chat_id: int, status_message: types.Message):
    keyboard = generate_preview_keyboard(buttons_matrix)
    sent_count, failed_count = 0, 0
    total_users = len(users)
    
    try:
        await bot.edit_message_text(
            text=(
                f"📢 Reklama yuborish jarayoni davom etmoqda...\n\n"
                f"👥 Jami foydalanuvchilar: {total_users} ta\n"
                f"✅ Muvaffaqiyatli: 0 ta\n"
                f"❌ Xatolik yuz berdi: 0 ta"
            ),
            chat_id=admin_chat_id,
            message_id=status_message.message_id
        )
    except TelegramBadRequest:
        pass

    chunk_size = 25
    user_chunks = [users[i:i + chunk_size] for i in range(0, len(users), chunk_size)]

    for chunk in user_chunks:
        tasks = [send_ad_to_user(bot, user_id, post_data, keyboard) for user_id in chunk]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        sent_count += sum(1 for r in results if r is True)
        failed_count += sum(1 for r in results if isinstance(r, Exception) or r is False)
        await asyncio.sleep(1)

    final_text = (
        f"🏁 Reklama yuborish yakunlandi!\n\n"
        f"👥 Jami foydalanuvchilar: {total_users} ta\n"
        f"✅ Muvaffaqiyatli: {sent_count} ta\n"
        f"❌ Xatolik yuz berdi: {failed_count} ta"
    )
    try:
        await bot.edit_message_text(
            text=final_text,
            chat_id=admin_chat_id,
            message_id=status_message.message_id
        )
    except TelegramBadRequest:
        pass

@ad_router.callback_query(F.data == "ad:send_now", IsAdmin())
async def send_ad_now(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    post_data = data.get("ad_post_data", {})
    buttons_matrix = data.get("ad_buttons_matrix", [])

    if not post_data:
        return await callback.answer("Vaqt o'tdi. Qaytadan urinib ko'ring.", show_alert=True)

    users = await get_all_active_users(admin_ids=config.ADMIN_IDS)
    if not users:
        await callback.message.edit_text("Hozirda reklama yuborish uchun aktiv foydalanuvchilar yo'q.")
        await callback.answer()
        return

    await callback.message.delete()
    await callback.answer("Reklama yuborish boshlandi...", show_alert=False)

    total_users = len(users)
    initial_text = (
        f"📢 Reklama yuborish jarayoni boshlandi...\n\n"
        f"👥 Jami foydalanuvchilar: {total_users} ta\n"
        f"✅ Muvaffaqiyatli: 0 ta\n"
        f"❌ Xatolik yuz berdi: 0 ta"
    )
    status_message = await bot.send_message(callback.from_user.id, initial_text)
    await state.clear()

    await broadcast_advertisement(
        bot=bot, users=users, post_data=post_data, buttons_matrix=buttons_matrix,
        admin_chat_id=callback.from_user.id, status_message=status_message
    )

# =============================================================================
# BEKOR QILISH HANDLERLARI
# =============================================================================

async def _cancel_ad_process(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Reklama yaratish bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    await message.answer("Admin panel:", reply_markup=get_main_admin_keyboard())

@ad_router.message(AdminStates.configuring_ad_post, F.text == "❌ Cancel", IsAdmin())
async def cancel_from_settings(message: types.Message, state: FSMContext):
    await _cancel_ad_process(message, state)

@ad_router.message(F.text == "◀️ Ortga (Admin panel)", IsAdmin())
async def cancel_from_any_state(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await _cancel_ad_process(message, state)

@ad_router.callback_query(F.data == "ad:cancel_sending", IsAdmin())
async def cancel_from_confirmation(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await _cancel_ad_process(callback.message, state)

@ad_router.callback_query(F.data == "ad:dummy_button", IsAdmin())
async def dummy_button_handler(callback: types.CallbackQuery):
    await callback.answer("Bu tugma faqat ko'rish uchun, bosilmaydi.")

#--- END OF FILE admin_handlers/advertisement.py ---