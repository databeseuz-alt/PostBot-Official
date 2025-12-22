#--- START OF FILE editp_handler.py ---
import logging
import html
from aiogram import F, Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ReplyKeyboardRemove

from xdata_handlers import config
from post_handlers.vpost_states import PostCreation
from post_handlers.xreply_keyboard import get_post_settings_kb, get_main_menu
from post_handlers.xinline_keyboard import generate_post_keyboard, get_edit_send_keyboard, EditSendCallbackFactory, generate_preview_keyboard
from xdata_handlers.database import get_post_from_db, check_post_owner, get_user_language, unsave_post_name
from xdata_handlers.translator import get_text
from post_handlers.send_handler import start_sending_handler
from post_handlers.start_handler import start_post_editing_process

edit_post_router = Router()

#==================================================
# --- P O S T N I   S A Q L A N G A N L A R D A N   O' CH I R I SH ---
#==================================================

# --- O'ZGARISH: Command("delate_post") -> Command("delete_post") ---
@edit_post_router.message(Command("delete_post"))
async def delete_saved_post_handler(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    try:
        post_code = message.text.split()[1]
    except IndexError:
        # --- O'ZGARISH: Xabar matnida ham to'g'rilandi ---
        await message.answer("❌ Noto'g'ri buyruq formati. Namuna: `/delete_post ABCDE`")
        return

    post_name = await unsave_post_name(post_code, user_id)

    if post_name:
        safe_post_name = html.escape(post_name)
        await message.answer(f"✅ \"{safe_post_name}\" nomli post saqlanganlar ro'yxatidan o'chirildi.")
        # Yangilangan ro'yxatni ko'rsatish uchun start_post_editing_process funksiyasini chaqiramiz
        await start_post_editing_process(message, state, bot)
    else:
        await message.answer("❌ Bunday kodli saqlangan post topilmadi yoki u sizga tegishli emas.")


#==================================================
# --- P O S T N I   T A H R I R L A SH   U CH U N   Y U K L A SH ---
#==================================================

async def load_post_for_editing(post_code: str, user_id: int, chat_id: int, state: FSMContext, bot: Bot, message_to_delete: types.Message | None = None):
    lang = await get_user_language(user_id)
    is_owner = await check_post_owner(post_code, user_id)
    is_admin = user_id in config.ADMIN_IDS

    if not is_owner and not is_admin:
        await bot.send_message(chat_id, get_text('post_not_found', lang))
        await state.clear()
        await bot.send_message(
            chat_id, "Asosiy menyu.",
            reply_markup=await get_main_menu(lang, user_id)
        )
        return

    full_post = await get_post_from_db(post_code)
    if not full_post:
        await bot.send_message(chat_id, get_text('post_load_error', lang))
        return

    if message_to_delete:
        try:
            await message_to_delete.delete()
        except TelegramBadRequest:
            pass

    if is_admin and not is_owner:
        await bot.send_message(chat_id, "⚠️ <b>Diqqat:</b> Siz ushbu postning egasi emassiz. Admin huquqi bilan tahrirlamoqdasiz.")

    post_data = full_post.get('post_content')
    buttons_matrix = full_post.get('buttons_matrix', [])

    if not post_data:
        await bot.send_message(chat_id, get_text('post_load_error', lang))
        return

    post_data.setdefault('parse_mode', None)
    post_data.setdefault('disable_web_page_preview', False)

    await state.set_data({
        "post_data": post_data,
        "buttons_matrix": buttons_matrix,
        "editing_post_code": post_code
    })

    await state.set_state(PostCreation.configuring_post)

    content_type = post_data.get('content_type', 'text')
    has_caption = bool(post_data.get('caption'))

    settings_kb = get_post_settings_kb(
        content_type=content_type,
        has_caption=has_caption
    )

    await bot.send_message(
        chat_id,
        f"`{post_code}` kodli post tahrirlash uchun ochildi.",
        reply_markup=settings_kb,
        parse_mode="Markdown"
    )

    keyboard = generate_post_keyboard(buttons_matrix)
    sent_message = None

    message_kwargs = {
        "reply_markup": keyboard,
        "parse_mode": post_data.get('parse_mode'),
        "disable_web_page_preview": post_data.get('disable_web_page_preview', False)
    }
    media_kwargs = {
        "reply_markup": keyboard,
        "parse_mode": post_data.get('parse_mode')
    }

    try:
        if content_type == 'text':
            sent_message = await bot.send_message(chat_id, post_data.get('text'), **message_kwargs)
        elif content_type == 'photo':
            sent_message = await bot.send_photo(chat_id, post_data.get('file_id'), caption=post_data.get('caption'), **media_kwargs)
        elif content_type == 'video':
            sent_message = await bot.send_video(chat_id, post_data.get('file_id'), caption=post_data.get('caption'), **media_kwargs)
        elif content_type == 'audio':
            sent_message = await bot.send_audio(chat_id, post_data.get('file_id'), caption=post_data.get('caption'), **media_kwargs)
        elif content_type == 'document':
            sent_message = await bot.send_document(chat_id, post_data.get('file_id'), caption=post_data.get('caption'), **media_kwargs)
        elif content_type == 'animation':
            sent_message = await bot.send_animation(chat_id, post_data.get('file_id'), caption=post_data.get('caption'), **media_kwargs)
        elif content_type == 'video_note':
            sent_message = await bot.send_video_note(chat_id, post_data.get('file_id'), reply_markup=keyboard)
        # --- O'ZGARISH: Voice (ovozli xabar) qo'shildi ---
        elif content_type == 'voice':
            sent_message = await bot.send_voice(chat_id, post_data.get('file_id'), caption=post_data.get('caption'), **media_kwargs)
        else:
            await bot.send_message(chat_id, get_text('edit_type_error', lang).format(content_type=content_type))
            await state.clear()
            return

        if sent_message:
            post_data['message_id'] = sent_message.message_id
            post_data['chat_id'] = sent_message.chat.id
            await state.update_data(post_data=post_data)

    except TelegramBadRequest as e:
        if "can't parse entities" in str(e).lower():
            error_mode = f"<code>{post_data.get('parse_mode') or 'None'}</code>"
            await bot.send_message(chat_id, f"⚠️ <b>Xatolik:</b> Postdagi matn tanlangan {error_mode} formatiga mos kelmadi. Uni tahrirlab ko'ring.")
        else:
            logging.error(f"Tahrirlash uchun postni yuborishda xatolik: {e}")
            await bot.send_message(chat_id, "Postni ko'rsatishda xatolik yuz berdi.")
    except Exception as e:
        logging.error(f"Tahrirlash uchun postni yuborishda xatolik: {e}")
        await bot.send_message(chat_id, "Postni ko'rsatishda xatolik yuz berdi. Ehtimol, media fayl eskirgan yoki o'chirilgan.")

#==================================================
# --- T A H R I R L A SH   K O D I N I   Q A B U L   Q I L I SH ---
#==================================================

async def show_post_preview(message: types.Message, post_code: str, bot: Bot):
    full_post = await get_post_from_db(post_code)
    if not full_post:
        return False

    post_data = full_post.get('post_content', {})
    buttons_matrix = full_post.get('buttons_matrix', [])
    keyboard = generate_preview_keyboard(buttons_matrix)

    try:
        content_type = post_data.get('content_type')
        chat_id = message.chat.id
        file_id = post_data.get('file_id')
        caption = post_data.get('caption')
        text = post_data.get('text')
        parse_mode = post_data.get('parse_mode')
        disable_preview = post_data.get('disable_web_page_preview', False)

        if content_type == 'text':
            await bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode=parse_mode, disable_web_page_preview=disable_preview)
        elif content_type == 'photo':
            await bot.send_photo(chat_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode)
        elif content_type == 'video':
            await bot.send_video(chat_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode)
        elif content_type == 'audio':
            await bot.send_audio(chat_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode)
        elif content_type == 'document':
            await bot.send_document(chat_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode)
        elif content_type == 'animation':
            await bot.send_animation(chat_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode)
        elif content_type == 'video_note':
            await bot.send_video_note(chat_id, file_id, reply_markup=keyboard)
        # --- O'ZGARISH: Voice (ovozli xabar) qo'shildi ---
        elif content_type == 'voice':
            await bot.send_voice(chat_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode)
        else:
            await bot.send_message(chat_id, "Bu turdagi postni ko'rsatib bo'lmadi.")

        return True
    except Exception:
        return False

@edit_post_router.message(PostCreation.waiting_for_edit_code, F.text)
async def receive_post_code(message: types.Message, state: FSMContext, bot: Bot):
    post_code = message.text.strip()
    user_id = message.from_user.id
    is_owner = await check_post_owner(post_code, user_id)
    is_admin = user_id in config.ADMIN_IDS

    if is_admin and not is_owner:
        await load_post_for_editing(post_code, user_id, message.chat.id, state, bot)
        return

    lang = await get_user_language(user_id)
    full_post = await get_post_from_db(post_code)

    if not full_post or not is_owner:
        return await message.answer(get_text('post_not_found', lang))

    await show_post_preview(message, post_code, bot)
    await message.answer(
        "Ushbu post bilan nima qilmoqchisiz:",
        reply_markup=get_edit_send_keyboard(post_code)
    )

#==================================================
# --- T A N L O V   T U G M A L A R I N I   B O S H Q A R I SH ---
#==================================================

@edit_post_router.callback_query(EditSendCallbackFactory.filter(F.action == "edit"))
async def handle_edit_action(callback: types.CallbackQuery, callback_data: EditSendCallbackFactory, state: FSMContext, bot: Bot):
    await load_post_for_editing(
        post_code=callback_data.post_code,
        user_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
        state=state,
        bot=bot,
        message_to_delete=callback.message
    )
    await callback.answer()

@edit_post_router.callback_query(EditSendCallbackFactory.filter(F.action == "send"))
async def handle_send_action(callback: types.CallbackQuery, callback_data: EditSendCallbackFactory, state: FSMContext):
    # send_handler'dagi funksiyani qayta ishlatamiz
    await start_sending_handler(callback, callback_data, state)
#--- END OF FILE editp_handler.py ---
