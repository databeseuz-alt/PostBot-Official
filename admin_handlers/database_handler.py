import json
import html
from datetime import datetime
from aiogram import F, Router, types, Bot
from aiogram.types import BufferedInputFile, ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

logger = logging.getLogger(__name__)

from xdata_handlers import config
from admin_handlers.admin_handler import IsAdmin
from xdata_handlers.database import (
    get_users_for_export, get_post_creators_for_export, get_user_settings_for_export,
    find_user_by_id_or_username, get_posts_by_user, get_post_from_db,
    get_feedbacks_by_user, get_errors_by_user, get_user_language,
    block_user, unblock_user
)
from admin_handlers.admin_handler import AdminStates
from admin_handlers.xreply_keyboard import get_admin_back_kb
from admin_handlers.xinline_keyboard import (
    get_main_admin_keyboard, get_user_data_keyboard, get_export_period_keyboard,
    get_export_type_keyboard, get_user_search_start_keyboard, get_user_profile_actions_keyboard
)
from post_handlers.xinline_keyboard import generate_preview_keyboard
from xdata_handlers.translator import get_text

db_router = Router()

@db_router.callback_query(F.data == "admin:user_data_menu", IsAdmin())
async def user_data_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("ℹ️ ma'lumotlar bazasi:", reply_markup=get_user_data_keyboard())
    await callback.answer()

@db_router.callback_query(F.data == "admin:export_menu_period", IsAdmin())
async def show_export_period_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Ma'lumotlarni qaysi vaqt oralig'i uchun eksport qilmoqchisiz?",
        reply_markup=get_export_period_keyboard()
    )
    await callback.answer()

@db_router.callback_query(F.data.startswith("admin:export_type_menu:"), IsAdmin())
async def show_export_type_menu(callback: types.CallbackQuery):
    period = callback.data.split(":")[-1]
    await callback.message.edit_text(
        f"<b>{period.capitalize()}</b> davr uchun qanday ma'lumot turini olmoqchisiz?",
        reply_markup=get_export_type_keyboard(period)
    )
    await callback.answer()

@db_router.callback_query(F.data.startswith("admin:export_do:"), IsAdmin())
async def do_export_handler(callback: types.CallbackQuery):
    await callback.answer("Ma'lumotlar tayyorlanmoqda, iltimos kuting...", show_alert=False)

    try:
        _, _, period, export_type = callback.data.split(":")
    except ValueError:
        await callback.message.answer("Xatolik: Noto'g'ri buyruq.")
        return

    export_data = {}
    filename = f"export_{period}_{export_type}_{datetime.now():%Y-%m-%d}.json"
    caption = f"✅ {period.capitalize()} davr uchun {export_type} ma'lumotlari."
    data_key = "data"

    if export_type == "full_list":
        users_data = await get_users_for_export(admin_ids=config.ADMIN_IDS, period=period)
        data_key = "users_data"
        export_data = {
            "export_date_utc": datetime.utcnow().isoformat(),
            "period": period,
            "total_users": len(users_data),
            data_key: users_data
        }

    elif export_type == "post_creators":
        users_data = await get_post_creators_for_export(admin_ids=config.ADMIN_IDS, period=period)
        data_key = "users_who_created_posts"
        export_data = {
            "export_date_utc": datetime.utcnow().isoformat(),
            "period": period,
            data_key: users_data
        }

    elif export_type == "user_settings":
        settings_data = await get_user_settings_for_export(admin_ids=config.ADMIN_IDS, period=period)
        data_key = "user_settings"
        export_data = {
            "export_date_utc": datetime.utcnow().isoformat(),
            "period": period,
            data_key: settings_data
        }

    if not export_data or not export_data.get(data_key):
        await callback.message.answer("Bu davr uchun ma'lumotlar topilmadi.")
        return

    json_data_str = json.dumps(export_data, indent=4, ensure_ascii=False, default=str)
    input_file = BufferedInputFile(json_data_str.encode('utf-8'), filename=filename)
    await callback.message.answer_document(document=input_file, caption=caption)

async def prompt_user_search(message: types.Message, state: FSMContext):
    """Qidiruv so'rovini yuborish uchun yordamchi funksiya."""
    await state.set_state(AdminStates.waiting_for_user_query)
    await message.answer(
        "🔎 Qidiruv uchun foydalanuvchi <b>IDsi</b> yoki <b>@username</b>'ini yuboring.\n\n"
        "<i>Bekor qilish uchun /cancel buyrug'ini yuboring.</i>",
        reply_markup=ReplyKeyboardRemove()
    )

@db_router.callback_query(F.data == "admin:search_user_start", IsAdmin())
async def search_user_start_callback(callback: types.CallbackQuery, state: FSMContext):
    """Tugma orqali qidiruvni boshlash."""
    await callback.message.delete() # Eski menyuni o'chiramiz
    await prompt_user_search(callback.message, state)
    await callback.answer()

@db_router.message(Command("search"), IsAdmin())
async def search_user_command(message: types.Message, state: FSMContext):
    """Buyruq orqali qidiruvni boshlash."""
    await prompt_user_search(message, state)

@db_router.message(StateFilter(AdminStates.waiting_for_user_query), Command("cancel"))
async def cancel_user_search(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Qidiruv bekor qilindi.", reply_markup=get_user_data_keyboard())

@db_router.message(StateFilter(AdminStates.waiting_for_user_query), F.text, ~F.text.startswith('/'))
async def process_user_search(message: types.Message, state: FSMContext):
    query = message.text.strip()
    user_data = await find_user_by_id_or_username(query)

    if not user_data:
        safe_query = html.escape(query)
        return await message.answer(f"❌ '{safe_query}' bo'yicha foydalanuvchi topilmadi. Qaytadan urinib ko'ring yoki /cancel.")

    await state.set_state(AdminStates.viewing_user_profile)

    user_id = user_data['user_id']
    user_posts = await get_posts_by_user(user_id)
    user_feedbacks = await get_feedbacks_by_user(user_id)
    user_errors = await get_errors_by_user(user_id)

    feedback_count = len(user_feedbacks)
    replied_count = sum(1 for f in user_feedbacks if f['has_reply'])
    feedback_text = f"{feedback_count} ta ({replied_count} tasiga javob berilgan)"

    errors_count = len(user_errors)
    errors_text = f"{errors_count} ta"

    posts_list_str = "Yo'q"
    if user_posts:
        post_codes = [p['code'] for p in user_posts]
        posts_list_str = f"{len(user_posts)} ta [ {', '.join(post_codes)} ]"

    join_date = user_data.get('join_date')
    join_date_str = join_date.strftime('%d.%m.%Y %H:%M') if join_date else "Noma'lum"

    last_activity = user_data.get('last_activity_date')
    last_activity_str = last_activity.strftime('%d.%m.%Y %H:%M') if last_activity else "Noma'lum"

    lang_code = user_data.get('language_code', 'uzl')
    lang_map = {
        'uzl': "O'zbekcha", 'uzk': "Ўзбекча", 'ru': "Русский", 'en': "English",
        'kz': "Qazaqsha", 'az': "Azərca", 'tr': "Türkçe", 'kg': "Kırgızça",
        'tj': "Tojik", 'tk': "Turkman"
    }
    lang_str = lang_map.get(lang_code, lang_code)

    is_blocked = user_data.get('is_blocked', False)
    status_str = "🚫 Bloklangan" if is_blocked else "✅ Faol (Bloklanmagan)"

    safe_nickname = html.escape(user_data.get('nickname', 'N/A'))
    username = user_data.get('username')
    username_str = f"@{username}" if username else "Mavjud emas"

    info_text = (
        f"👤 <b>Foydalanuvchi Profili</b>\n\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"👤 <b>Nickname:</b> {safe_nickname}\n"
        f"🔗 <b>Username:</b> {username_str}\n"
        f"📅 <b>Qo'shilgan:</b> {join_date_str}\n"
        f"⏳ <b>Oxirgi faollik:</b> {last_activity_str}\n"
        f"🌍 <b>Foydalanuvchi tili:</b> {lang_str}\n"
        f"🚫 <b>Holati:</b> {status_str}\n"
        f"✍️ <b>Postlar soni:</b> {posts_list_str}\n"
        f"💬 <b>Fikr-mulohazalar:</b> {feedback_text}\n"
        f"⚠️ <b>Xatoliklar:</b> {errors_text}"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="✉️ Xabar yozish", callback_data=f"admin:dm_from_profile:{user_id}")

    if is_blocked:
        builder.button(text="✅ Blokdan chiqarish", callback_data=f"admin:unblock_from_profile:{user_id}")
    else:
        builder.button(text="🚫 Bloklash", callback_data=f"admin:block_from_profile:{user_id}")

    builder.adjust(2)

    await message.answer(info_text, reply_markup=builder.as_markup())

@db_router.callback_query(F.data.startswith("admin:review_post:"), IsAdmin())
async def review_user_post_from_search(callback: types.CallbackQuery, bot: Bot):
    post_code = callback.data.split(":")[2]
    await callback.answer(f"{post_code} posti yuklanmoqda...", show_alert=False)

    full_post = await get_post_from_db(post_code)
    if not full_post:
        return await callback.message.answer(f"❌ '{post_code}' kodli post topilmadi yoki o'chirilgan.")

    post_data = full_post.get('post_content', {})
    buttons_matrix = full_post.get('buttons_matrix', [])
    keyboard = generate_preview_keyboard(buttons_matrix)

    nav_builder = InlineKeyboardBuilder()
    nav_builder.row(
        types.InlineKeyboardButton(text="🔙 Asosiy panel", callback_data="admin:back_to_main_menu"),
        types.InlineKeyboardButton(text="🔙 Ortga (Qidiruv)", callback_data="admin:search_user_start")
    )
    nav_builder.adjust(2)

    try:
        await callback.message.delete()

        content_type = post_data.get('content_type')
        chat_id = callback.from_user.id
        file_id = post_data.get('file_id')
        caption = post_data.get('caption', '')
        text = post_data.get('text', '')

        if content_type == 'text':
            await bot.send_message(chat_id, text, reply_markup=keyboard, disable_web_page_preview=post_data.get('disable_web_page_preview', True))
        elif content_type == 'photo':
            await bot.send_photo(chat_id, file_id, caption=caption, reply_markup=keyboard)
        elif content_type == 'video':
            await bot.send_video(chat_id, file_id, caption=caption, reply_markup=keyboard)
        elif content_type == 'audio':
            await bot.send_audio(chat_id, file_id, caption=caption, reply_markup=keyboard)
        elif content_type == 'document':
            await bot.send_document(chat_id, file_id, caption=caption, reply_markup=keyboard)
        elif content_type == 'animation':
            await bot.send_animation(chat_id, file_id, caption=caption, reply_markup=keyboard)
        elif content_type == 'video_note':
            await bot.send_video_note(chat_id, file_id, reply_markup=keyboard)
        elif content_type == 'voice':
            await bot.send_voice(chat_id, file_id, caption=caption, reply_markup=keyboard)
        else:
            await bot.send_message(chat_id, f"Bu turdagi postni ko'rsatib bo'lmadi (turi: {content_type}).")

        await bot.send_message(
            chat_id,
            "Postni ko'rish rejimi.",
            reply_markup=nav_builder.as_markup()
        )
    except Exception:
        await bot.send_message(callback.from_user.id, "Postni ko'rsatishda xatolik yuz berdi. Ehtimol, media fayl eskirgan yoki o'chirilgan.", reply_markup=get_main_admin_keyboard())

@db_router.callback_query(F.data == "admin:direct_message_start", IsAdmin())
async def direct_message_start_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_direct_message_user_id)

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🔙 Asosiy panel", callback_data="admin:back_to_main_menu"),
        types.InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:user_data_menu")
    )

    await callback.message.edit_text(
        "✉️ <b>Foydalanuvchiga xabar yuborish</b>\n\n"
        "Iltimos, xabar yubormoqchi bo'lgan foydalanuvchining <b>ID raqamini</b> yoki <b>@username</b>'ini yuboring.",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@db_router.message(StateFilter(AdminStates.waiting_for_direct_message_user_id), F.text)
async def direct_message_user_id_received(message: types.Message, state: FSMContext):
    user_input = message.text.strip()
    target_user_id = None

    if user_input.isdigit():
        target_user_id = int(user_input)
        user_data = await find_user_by_id_or_username(user_input)
        if not user_data:
            return await message.answer(f"❌ ID <code>{user_input}</code> bazada topilmadi. Iltimos, to'g'ri ID kiriting.")

    elif user_input.startswith("@"):
        user_data = await find_user_by_id_or_username(user_input)
        if user_data:
            target_user_id = user_data['user_id']
        else:
            return await message.answer(f"❌ Username <code>{user_input}</code> bazada topilmadi. Iltimos, to'g'ri username kiriting.")

    else:
        return await message.answer("❌ Iltimos, faqat <b>ID raqam</b> yoki <b>@username</b> kiriting.")

    await state.update_data(target_user_id=target_user_id)
    await state.set_state(AdminStates.waiting_for_direct_message_content)

    await message.answer(
        f"✅ Foydalanuvchi ID: <code>{target_user_id}</code> qabul qilindi.\n\n"
        "Endi unga yuboriladigan xabarni yozing (matn, rasm, video, audio...):\n\n"
        "xabar yuborishni bekor qilish buyruqi - /cancel",
        reply_markup=ReplyKeyboardRemove()
    )

@db_router.message(StateFilter(AdminStates.waiting_for_direct_message_content), Command("cancel"))
async def cancel_direct_message(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("ℹ️ ma'lumotlar bazasi:", reply_markup=get_user_data_keyboard())

@db_router.message(StateFilter(AdminStates.waiting_for_direct_message_content), F.content_type.in_({'text', 'photo', 'video', 'audio', 'document', 'voice', 'animation'}))
async def direct_message_content_received(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    target_user_id = data.get('target_user_id')

    if not target_user_id:
        await state.clear()
        return await message.answer("Xatolik yuz berdi. Iltimos, qaytadan boshlang.")

    try:
        await message.copy_to(chat_id=target_user_id)

        await message.answer(f"✅ Xabar foydalanuvchiga (ID: {target_user_id}) muvaffaqiyatli yuborildi!")

        await state.clear()
        await message.answer("Yana xabar yuborasizmi yoki boshqa bo'limga o'tasizmi?", reply_markup=get_user_data_keyboard())

    except Exception as e:
        await message.answer(f"❌ Xabarni yuborishda xatolik: {e}\nEhtimol foydalanuvchi botni bloklagan.")

@db_router.callback_query(F.data.startswith("admin:block_from_profile:"), IsAdmin())
async def block_user_from_profile(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[2])
    if user_id in config.ADMIN_IDS:
        return await callback.answer("Adminni bloklab bo'lmaydi!", show_alert=True)

    if await block_user(user_id, config.ADMIN_IDS):
        await callback.answer("✅ Foydalanuvchi bloklandi!")
        msg = types.Message(chat=callback.message.chat, from_user=callback.from_user, text=str(user_id), bot=callback.bot)
        await process_user_search(msg, state)
        await callback.message.delete() # Eski xabarni o'chiramiz
    else:
        await callback.answer("Xatolik yuz berdi.", show_alert=True)

@db_router.callback_query(F.data.startswith("admin:unblock_from_profile:"), IsAdmin())
async def unblock_user_from_profile(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[2])

    if await unblock_user(user_id):
        await callback.answer("✅ Foydalanuvchi blokdan chiqarildi!")
        msg = types.Message(chat=callback.message.chat, from_user=callback.from_user, text=str(user_id), bot=callback.bot)
        await process_user_search(msg, state)
        await callback.message.delete()
    else:
        await callback.answer("Xatolik yuz berdi.", show_alert=True)

@db_router.callback_query(F.data.startswith("admin:dm_from_profile:"), IsAdmin())
async def dm_user_from_profile(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[2])
    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_direct_message_content)

    await callback.message.answer(
        f"✅ Foydalanuvchi ID: <code>{user_id}</code> tanlandi.\n\n"
        "Endi unga yuboriladigan xabarni yozing (matn, rasm, video, audio...):\n\n"
        "xabar yuborishni bekor qilish buyruqi - /cancel",
        reply_markup=ReplyKeyboardRemove()
    )
    await callback.answer()

@db_router.message(StateFilter(AdminStates.viewing_user_profile), F.text, ~F.text.startswith('/'))
async def view_post_from_profile(message: types.Message, bot: Bot):
    post_code = message.text.strip()
    full_post = await get_post_from_db(post_code)

    if not full_post:
        return await message.answer(f"❌ '{post_code}' kodli post topilmadi.")

    post_data = full_post.get('post_content', {})
    buttons_matrix = full_post.get('buttons_matrix', [])
    keyboard = generate_preview_keyboard(buttons_matrix)

    try:
        content_type = post_data.get('content_type')
        chat_id = message.chat.id
        file_id = post_data.get('file_id')
        caption = post_data.get('caption', '')
        text = post_data.get('text', '')

        if content_type == 'text':
            await bot.send_message(chat_id, text, reply_markup=keyboard, disable_web_page_preview=post_data.get('disable_web_page_preview', True))
        elif content_type == 'photo':
            await bot.send_photo(chat_id, file_id, caption=caption, reply_markup=keyboard)
        elif content_type == 'video':
            await bot.send_video(chat_id, file_id, caption=caption, reply_markup=keyboard)
        elif content_type == 'audio':
            await bot.send_audio(chat_id, file_id, caption=caption, reply_markup=keyboard)
        elif content_type == 'document':
            await bot.send_document(chat_id, file_id, caption=caption, reply_markup=keyboard)
        elif content_type == 'animation':
            await bot.send_animation(chat_id, file_id, caption=caption, reply_markup=keyboard)
        elif content_type == 'video_note':
            await bot.send_video_note(chat_id, file_id, reply_markup=keyboard)
        elif content_type == 'voice':
            await bot.send_voice(chat_id, file_id, caption=caption, reply_markup=keyboard)
        else:
            await message.answer(f"Bu turdagi postni ko'rsatib bo'lmadi (turi: {content_type}).")

    except Exception as e:
        await message.answer(f"Postni ko'rsatishda xatolik: {e}")

@db_router.message(StateFilter(AdminStates.viewing_user_profile), Command("cancel"))
async def cancel_profile_view(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Amal bekor qilindi.", reply_markup=get_user_data_keyboard())
