#--- START OF FILE user_handlers/ad_handler.py ---
import logging
from aiogram import F, Router, types, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from xdata_handlers import config
from user_handlers.vuser_states import AdvertisingState
from xdata_handlers.database import (
    add_or_update_user, check_ad_agreement, accept_ad_agreement,
    get_assigned_admin, assign_admin_to_user, get_user_language
)
from user_handlers.xinline_keyboard import (
    get_ad_agreement_keyboard, get_reply_to_user_keyboard, get_reply_to_admin_keyboard
)
from admin_handlers.admin_handler import IsAdmin
from post_handlers.xreply_keyboard import get_main_menu, get_cancel_kb
from xdata_handlers.translator import get_text

ad_router = Router()

# =============================================================================
# REKLAMA BO'LIMIGA KIRISH HANDLERI
# =============================================================================

@ad_router.message(Command("reklama"), ~IsAdmin())
async def cmd_advertisement_user(message: types.Message, state: FSMContext):
    await state.clear()
    
    lang = await get_user_language(message.from_user.id)
    remover_message = await message.answer(
        get_text('ad_section_opening', lang),
        reply_markup=ReplyKeyboardRemove()
    )
    await remover_message.delete()

    await add_or_update_user(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
        admin_ids=config.ADMIN_IDS
    )

    has_agreed = await check_ad_agreement(message.from_user.id)

    if has_agreed:
        await message.answer(
            get_text('ad_you_agreed', lang),
            reply_markup=get_cancel_kb(lang)
        )
        await state.set_state(AdvertisingState.waiting_for_ad_content)

    else:
        text = get_text('ad_warning_agreement', lang)
        await message.answer(text, reply_markup=get_ad_agreement_keyboard(lang))

@ad_router.message(Command("reklama"), IsAdmin())
async def cmd_advertisement_admin(message: types.Message):
    lang = await get_user_language(message.from_user.id)
    await message.answer(get_text('cmd_only_for_users', lang))


# =============================================================================
# SHARTLARGA ROZILIK BERISH HANDLERI
# =============================================================================

@ad_router.callback_query(F.data == "ad_agreement:accept")
async def process_ad_agreement(callback: types.CallbackQuery, state: FSMContext):
    await accept_ad_agreement(callback.from_user.id)
    await state.set_state(AdvertisingState.waiting_for_ad_content)
    lang = await get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        get_text('ad_start_conversation', lang)
    )
    await callback.answer(get_text('agreement_accepted', lang))

# =============================================================================
# FOYDALANUVCHIDAN BIRINCHI REKLAMA XABARINI QABUL QILISH
# =============================================================================

@ad_router.message(
    StateFilter(AdvertisingState.waiting_for_ad_content),
    F.content_type.in_({'text', 'photo', 'video', 'document', 'audio', 'animation', 'voice'}),
    ~IsAdmin()
)
async def process_first_ad_content(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id

    assigned_admin_id = await get_assigned_admin(user_id)
    if not assigned_admin_id:
        assigned_admin_id = await assign_admin_to_user(user_id, config.ADMIN_IDS)

    if not assigned_admin_id:
        lang = await get_user_language(user_id)
        await message.answer(get_text('error_no_admins', lang))
        logging.warning("Reklama uchun adminlar topilmadi yoki ADMIN_IDS bo'sh.")
        return

    try:
        header_text = (
            f"👤 <b>Yangi reklama bo'yicha murojaat!</b>\n\n"
            f"<b>Yuboruvchi:</b> {message.from_user.full_name}\n"
            f"<b>ID:</b> <code>{user_id}</code>\n"
            f"<b>Username:</b> @{message.from_user.username or 'N/A'}"
        )
        await bot.send_message(assigned_admin_id, header_text)
        await message.copy_to(
            chat_id=assigned_admin_id,
            reply_markup=get_reply_to_user_keyboard(user_id)
        )

        lang = await get_user_language(user_id)
        await message.answer(
            get_text('ad_message_sent', lang),
            reply_markup=await get_main_menu(lang, user_id)
        )

        await state.clear()

    except Exception as e:
        logging.error(f"Reklama xabarini adminga ({assigned_admin_id}) yuborishda xatolik: {e}")
        lang = await get_user_language(user_id)
        await message.answer(get_text('error_sending_message', lang))

# =============================================================================
# ADMIN VA FOYDALANUVCHI O'RTASIDAGI MULOQOT
# =============================================================================

@ad_router.callback_query(F.data.startswith("reply_ad:"))
async def reply_from_admin_handler(callback: types.CallbackQuery, state: FSMContext):
    remover_message = await callback.message.answer("...", reply_markup=ReplyKeyboardRemove())
    await remover_message.delete()

    user_id_to_reply = int(callback.data.split(":")[1])
    await state.set_state(AdvertisingState.chatting_with_admin)
    await state.update_data(recipient_user_id=user_id_to_reply)

    lang = await get_user_language(callback.from_user.id)
    await callback.message.answer(
        get_text('admin_reply_prompt', lang).format(user_id=user_id_to_reply),
        reply_markup=get_cancel_kb(lang)
    )
    await callback.answer()

@ad_router.message(StateFilter(AdvertisingState.chatting_with_admin), IsAdmin())
async def send_message_from_admin(message: types.Message, state: FSMContext, bot: Bot):
    lang = await get_user_language(message.from_user.id)
    if message.text == get_text('btn_cancel', lang):
        await state.clear()
        await message.answer(get_text('reply_cancelled', lang), reply_markup=ReplyKeyboardRemove())
        return

    data = await state.get_data()
    recipient_user_id = data.get('recipient_user_id')
    if not recipient_user_id: return

    try:
        admin_id = message.from_user.id
        user_lang = await get_user_language(recipient_user_id)
        await bot.send_message(
            chat_id=recipient_user_id,
            text=get_text('ad_notification_from_admin', user_lang)
        )
        await message.copy_to(
            chat_id=recipient_user_id,
            reply_markup=get_reply_to_admin_keyboard(admin_id)
        )
        await message.answer(get_text('reply_sent_to_user', lang), reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        logging.error(f"Admindan ({admin_id}) foydalanuvchiga ({recipient_user_id}) javob yuborishda xatolik: {e}")
        await message.answer(get_text('error_reply_to_user', lang), reply_markup=ReplyKeyboardRemove())
    finally:
        await state.clear()

@ad_router.callback_query(F.data.startswith("reply_ad_to_admin:"))
async def reply_from_user_handler(callback: types.CallbackQuery, state: FSMContext):
    remover_message = await callback.message.answer("...", reply_markup=ReplyKeyboardRemove())
    await remover_message.delete()

    admin_id_to_reply = int(callback.data.split(":")[1])
    await state.set_state(AdvertisingState.chatting_with_admin)
    await state.update_data(chatting_with_admin_id=admin_id_to_reply)

    lang = await get_user_language(callback.from_user.id)
    await callback.message.answer(get_text('user_reply_prompt', lang), reply_markup=get_cancel_kb(lang))
    await callback.answer()

@ad_router.message(StateFilter(AdvertisingState.chatting_with_admin), ~IsAdmin())
async def send_message_from_user(message: types.Message, state: FSMContext, bot: Bot):
    lang = await get_user_language(message.from_user.id)
    if message.text == get_text('btn_cancel', lang):
        await state.clear()
        await message.answer(get_text('reply_cancelled', lang), reply_markup=await get_main_menu(lang, message.from_user.id))
        return

    data = await state.get_data()
    admin_id = data.get('chatting_with_admin_id')
    if not admin_id:
        await message.answer(get_text('error_restart_process', lang), reply_markup=await get_main_menu(lang, message.from_user.id))
        await state.clear()
        return

    try:
        user_info = (
            f"💬 <b>Foydalanuvchidan javob:</b>\n\n"
            f"<b>Yuboruvchi:</b> {message.from_user.full_name}\n"
            f"<b>ID:</b> <code>{message.from_user.id}</code>"
        )
        await bot.send_message(admin_id, user_info)
        await message.copy_to(
            chat_id=admin_id,
            reply_markup=get_reply_to_user_keyboard(message.from_user.id)
        )
        await message.answer(
            get_text('reply_sent_to_admin', lang),
            reply_markup=await get_main_menu(lang, message.from_user.id)
        )
    except Exception as e:
        logging.error(f"Foydalanuvchidan ({message.from_user.id}) adminga ({admin_id}) javob yuborishda xatolik: {e}")
        await message.answer(get_text('error_reply_to_admin', lang), reply_markup=await get_main_menu(lang, message.from_user.id))
    finally:
        await state.clear()

#--- END OF FILE user_handlers/ad_handler.py ---
