#--- START OF FILE feedback_handler.py ---
import logging
import html
from aiogram import F, Router, types, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from xdata_handlers import config
from user_handlers.vuser_states import FeedbackState
from xdata_handlers.database import (
    get_user_language, add_or_update_user, log_feedback,
    check_feedback_agreement, accept_feedback_agreement
)
from admin_handlers.admin_handler import IsAdmin
from user_handlers.xinline_keyboard import (
    get_feedback_agreement_keyboard, get_feedback_reply_to_user_keyboard,
    get_feedback_reply_to_admin_keyboard
)
from post_handlers.xreply_keyboard import get_main_menu, get_cancel_kb
from xdata_handlers.translator import get_text

feedback_router = Router()

#=============================================================================
# FIKR-MULOHAZA BO'LIMIGA KIRISH
#=============================================================================

@feedback_router.message(Command("feedback"), ~IsAdmin())
async def cmd_feedback_user(message: types.Message, state: FSMContext):
    await state.clear()

    remover_message = await message.answer("...", reply_markup=ReplyKeyboardRemove())
    await remover_message.delete()

    await add_or_update_user(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
        admin_ids=config.ADMIN_IDS
    )

    has_agreed = await check_feedback_agreement(message.from_user.id)
    lang = await get_user_language(message.from_user.id)

    if has_agreed:
        await message.answer(
            "Fikr-mulohazangizni yoki xatolik haqida xabaringizni yuboring.",
            reply_markup=get_cancel_kb(lang)
        )
        await state.set_state(FeedbackState.waiting_for_feedback)
    else:
        text = (
            "<b>Diqqat!</b>\n\n"
            "Iltimos, xatolikni yuborishdan oldin uni tekshiring, joyini aniq ayting.\n"
            "Feyk (yolg'on) xabar uchun bloklanishingiz mumkin."
        )
        await message.answer(text, reply_markup=get_feedback_agreement_keyboard())

@feedback_router.message(Command("feedback"), IsAdmin())
async def cmd_feedback_admin(message: types.Message):
    await message.answer("Bu buyruq faqat oddiy foydalanuvchilar uchun mo'ljallangan.")

#=============================================================================
# SHARTLARGA ROZILIK BERISH
#=============================================================================

@feedback_router.callback_query(F.data == "feedback_agreement:accept")
async def process_feedback_agreement(callback: types.CallbackQuery, state: FSMContext):
    await accept_feedback_agreement(callback.from_user.id)
    lang = await get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        "Fikr-mulohazangizni yoki xatolik haqida xabaringizni yuboring.",
        reply_markup=None
    )
    await callback.message.answer("Endi xabaringizni yozishingiz mumkin.", reply_markup=get_cancel_kb(lang))
    await state.set_state(FeedbackState.waiting_for_feedback)
    await callback.answer("✅ Roziligingiz qabul qilindi!")

#=============================================================================
# FOYDALANUVCHIDAN BIRINCHI XABARNI QABUL QILISH
#=============================================================================

@feedback_router.message(
    StateFilter(FeedbackState.waiting_for_feedback),
    F.content_type.in_({'text', 'photo', 'video', 'document', 'audio', 'voice'}),
    ~F.text.startswith('/'),
    ~F.text.in_({get_text('btn_cancel', 'uz'), get_text('btn_cancel', 'ru'), get_text('btn_cancel', 'en')}),
    ~IsAdmin()
)
async def process_first_feedback(message: types.Message, state: FSMContext, bot: Bot):
    if not config.FEEDBACK_RECIPIENT_ID:
        logging.warning("FEEDBACK_RECIPIENT_ID topilmadi. Fikr-mulohaza yuborilmadi.")
        await message.answer("Kechirasiz, hozirda texnik nosozlik. Iltimos, keyinroq urinib ko'ring.")
        return

    try:
        safe_full_name = html.escape(message.from_user.full_name)
        user_info = (f"👤 <b>Yangi fikr-mulohaza!</b>\n\n"
                     f"<b>Yuboruvchi:</b> {safe_full_name}\n<b>ID:</b> <code>{message.from_user.id}</code>\n"
                     f"<b>Username:</b> @{message.from_user.username or 'N/A'}")

        await bot.send_message(config.FEEDBACK_RECIPIENT_ID, user_info)
        await message.copy_to(
            config.FEEDBACK_RECIPIENT_ID,
            reply_markup=get_feedback_reply_to_user_keyboard(message.from_user.id)
        )

        await log_feedback(user_id=message.from_user.id, message_id=message.message_id, chat_id=message.chat.id)

        lang = await get_user_language(message.from_user.id)
        await message.answer(
            get_text('feedback_sent', lang),
            reply_markup=await get_main_menu(lang, message.from_user.id)
        )
        await state.clear()

    except Exception as e:
        logging.error(f"Fikr-mulohazani adminga yuborishda xatolik: {e}")
        await message.answer("❌ Xabarni yuborishda xatolik yuz berdi.")

#=============================================================================
# ADMIN VA FOYDALANUVCHI O'RTASIDAGI MULOQOT
#=============================================================================

@feedback_router.callback_query(F.data.startswith("reply_feedback:"))
async def reply_from_admin_handler(callback: types.CallbackQuery, state: FSMContext):
    remover_message = await callback.message.answer("...", reply_markup=ReplyKeyboardRemove())
    await remover_message.delete()

    user_id_to_reply = int(callback.data.split(":")[1])
    await state.set_state(FeedbackState.chatting_with_admin)
    await state.update_data(recipient_user_id=user_id_to_reply)

    lang = await get_user_language(callback.from_user.id)
    await callback.message.answer(
        f"Foydalanuvchiga (<code>{user_id_to_reply}</code>) javobingizni yuboring:",
        reply_markup=get_cancel_kb(lang)
    )
    await callback.answer()

@feedback_router.message(
    StateFilter(FeedbackState.chatting_with_admin),
    ~F.text.startswith('/'),
    IsAdmin()
)
async def send_message_from_admin(message: types.Message, state: FSMContext, bot: Bot):
    lang = await get_user_language(message.from_user.id)
    if message.text == get_text('btn_cancel', lang):
        await state.clear()
        await message.answer("Javob yozish bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        return

    data = await state.get_data()
    recipient_user_id = data.get('recipient_user_id')
    if not recipient_user_id: return

    try:
        user_lang = await get_user_language(recipient_user_id)
        await bot.send_message(
            chat_id=recipient_user_id,
            text=get_text('user_notification_from_admin', user_lang)
        )
        await message.copy_to(
            chat_id=recipient_user_id,
            reply_markup=get_feedback_reply_to_admin_keyboard()
        )
        await message.answer("✅ Javobingiz foydalanuvchiga yuborildi.", reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        logging.error(f"Admindan ({message.from_user.id}) foydalanuvchiga ({recipient_user_id}) javob yuborishda xatolik: {e}")
        await message.answer("❌ Foydalanuvchiga javob yuborib bo'lmadi.", reply_markup=ReplyKeyboardRemove())
    finally:
        await state.clear()

@feedback_router.callback_query(F.data == "reply_feedback_to_admin:start")
async def reply_from_user_handler(callback: types.CallbackQuery, state: FSMContext):
    remover_message = await callback.message.answer("...", reply_markup=ReplyKeyboardRemove())
    await remover_message.delete()

    await state.set_state(FeedbackState.chatting_with_admin)
    lang = await get_user_language(callback.from_user.id)
    await callback.message.answer("Adminga javobingizni yuboring:", reply_markup=get_cancel_kb(lang))
    await callback.answer()

@feedback_router.message(
    StateFilter(FeedbackState.chatting_with_admin),
    ~F.text.startswith('/'),
    ~F.text.in_({get_text('btn_cancel', 'uz'), get_text('btn_cancel', 'ru'), get_text('btn_cancel', 'en')}),
    ~IsAdmin()
)
async def send_message_from_user(message: types.Message, state: FSMContext, bot: Bot):
    if not config.FEEDBACK_RECIPIENT_ID:
        lang = await get_user_language(message.from_user.id)
        await message.answer("Kechirasiz, texnik nosozlik.", reply_markup=await get_main_menu(lang, message.from_user.id))
        await state.clear()
        return

    try:
        data = await state.get_data()
        admin_id = data.get('chatting_with_admin_id')
        if not admin_id:
             admin_id = config.FEEDBACK_RECIPIENT_ID

        safe_full_name = html.escape(message.from_user.full_name)
        user_info = (f"💬 <b>Foydalanuvchidan javob:</b>\n\n"
                     f"<b>Yuboruvchi:</b> {safe_full_name}\n"
                     f"<b>ID:</b> <code>{message.from_user.id}</code>")

        await bot.send_message(admin_id, user_info)
        await message.copy_to(
            chat_id=admin_id,
            reply_markup=get_feedback_reply_to_user_keyboard(message.from_user.id)
        )

        lang = await get_user_language(message.from_user.id)
        await message.answer(
            "✅ Javobingiz adminga yuborildi.\n\nAsosiy menyuga qaytildi.",
            reply_markup=await get_main_menu(lang, message.from_user.id)
        )
    except Exception as e:
        logging.error(f"Foydalanuvchidan adminga javob yuborishda xatolik: {e}")
        lang = await get_user_language(message.from_user.id)
        await message.answer("❌ Adminga javob yuborishda xatolik yuz berdi.", reply_markup=await get_main_menu(lang, message.from_user.id))
    finally:
        await state.clear()

#=============================================================================
# UMUMIY BEKOR QILISH HANDLERI
#=============================================================================

@feedback_router.message(
    StateFilter(FeedbackState.waiting_for_feedback, FeedbackState.chatting_with_admin),
    F.text.in_({get_text('btn_cancel', 'uz'), get_text('btn_cancel', 'ru'), get_text('btn_cancel', 'en')})
)
async def cancel_feedback_process(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    await state.clear()
    await message.answer(
        "Jarayon bekor qilindi.",
        reply_markup=await get_main_menu(lang, message.from_user.id)
    )

#--- END OF FILE feedback_handler.py ---
