import html
from aiogram import F, Router, types, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup

from xdata_handlers.database import (
    get_user_language, add_or_update_user
)
from xdata_handlers import config

class FeedbackState(StatesGroup):
    waiting_for_feedback = State()
    chatting_with_admin = State()
from admin_handlers.admin_handler import IsAdmin
from user_handlers.xinline_keyboard import (
    get_feedback_reply_to_user_keyboard,
    get_feedback_reply_to_admin_keyboard
)
from post_handlers.xreply_keyboard import get_main_menu, get_cancel_kb
from xdata_handlers.translator import get_text

feedback_router = Router()


@feedback_router.message(Command("feedback"), ~IsAdmin())
async def cmd_feedback_user(message: types.Message, state: FSMContext):
    await state.clear()

    remover_message = await message.answer("...", reply_markup=ReplyKeyboardRemove())
    await remover_message.delete()

    lang = await get_user_language(message.from_user.id)

    await add_or_update_user(
        user_id=message.from_user.id,
        nickname=message.from_user.full_name,
        username=message.from_user.username
    )

    await message.answer(
        get_text('feedback_prompt_msg', lang),
        reply_markup=get_cancel_kb(lang)
    )
    await state.set_state(FeedbackState.waiting_for_feedback)

@feedback_router.message(Command("feedback"), IsAdmin())
async def cmd_feedback_admin(message: types.Message):
    await message.answer("Bu buyruq faqat oddiy foydalanuvchilar uchun mo'ljallangan.")




@feedback_router.message(
    StateFilter(FeedbackState.waiting_for_feedback),
    F.content_type.in_({'text', 'photo', 'video', 'document', 'audio', 'voice'}),
    ~F.text.startswith('/'),
    ~F.text.in_({get_text('cancel_btn', 'uz'), get_text('cancel_btn', 'ru'), get_text('cancel_btn', 'en')}),
    ~IsAdmin()
)
async def process_first_feedback(message: types.Message, state: FSMContext, bot: Bot):
    if not config.FEEDBACK_RECIPIENT_ID:
        lang = await get_user_language(message.from_user.id)
        await message.answer(get_text('error_technical', lang))
        return

    # Tasdiqlashni olib tashamiz - to'g'ridan yuboramiz
    try:
        safe_nickname = html.escape(message.from_user.full_name)
        user_info = (f"👤 <b>Yangi fikr-mulohaza!</b>\n\n"
                     f"<b>Yuboruvchi:</b> {safe_nickname}\n"
                     f"<b>ID:</b> <code>{message.from_user.id}</code>\n"
                     f"<b>Username:</b> @{message.from_user.username or 'mavjud emas'}")

        await bot.send_message(config.FEEDBACK_RECIPIENT_ID, user_info)
        await message.copy_to(
            config.FEEDBACK_RECIPIENT_ID,
            reply_markup=get_feedback_reply_to_user_keyboard(message.from_user.id)
        )


        lang = await get_user_language(message.from_user.id)
        await message.answer(
            get_text('feedback_success_msg', lang),
            reply_markup=await get_main_menu(lang, message.from_user.id)
        )
        await state.clear()

    except Exception:
        lang = await get_user_language(message.from_user.id)
        await message.answer(get_text('feedback_error_msg', lang))


@feedback_router.callback_query(F.data.startswith("reply_feedback:"))
async def reply_from_admin_handler(callback: types.CallbackQuery, state: FSMContext):
    remover_message = await callback.message.answer("...", reply_markup=ReplyKeyboardRemove())
    await remover_message.delete()

    parts = callback.data.split(":")
    admin_id_to_reply = int(parts[1]) if len(parts) > 1 else None
    user_id_to_reply = int(parts[1]) if len(parts) > 1 else None
    await state.set_state(FeedbackState.chatting_with_admin)
    await state.update_data(recipient_user_id=user_id_to_reply)

    lang = await get_user_language(callback.from_user.id)
    await callback.message.answer(
        get_text('admin_reply_prompt_msg', lang).format(user_id=user_id_to_reply),
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
    if message.text == get_text('cancel_btn', lang):
        await state.clear()
        await message.answer(get_text('admin_reply_cancel_msg', lang), reply_markup=ReplyKeyboardRemove())
        return

    data = await state.get_data()
    recipient_user_id = data.get('recipient_user_id')
    if not recipient_user_id: return

    try:
        user_lang = await get_user_language(recipient_user_id)
        await bot.send_message(
            chat_id=recipient_user_id,
            text=get_text('user_receive_msg', user_lang)
        )
        await message.copy_to(
            chat_id=recipient_user_id,
            reply_markup=get_feedback_reply_to_admin_keyboard()
        )
        await message.answer(get_text('admin_reply_success_msg', lang), reply_markup=ReplyKeyboardRemove())
    except Exception:
        await message.answer(get_text('admin_reply_error_msg', lang), reply_markup=ReplyKeyboardRemove())
    finally:
        await state.clear()

@feedback_router.callback_query(F.data == "reply_feedback_to_admin:start")
async def reply_from_user_handler(callback: types.CallbackQuery, state: FSMContext):
    remover_message = await callback.message.answer("...", reply_markup=ReplyKeyboardRemove())
    await remover_message.delete()

    await state.set_state(FeedbackState.chatting_with_admin)
    lang = await get_user_language(callback.from_user.id)
    await callback.message.answer(get_text('user_reply_prompt', lang), reply_markup=get_cancel_kb(lang))
    await callback.answer()

@feedback_router.message(
    StateFilter(FeedbackState.chatting_with_admin),
    ~F.text.startswith('/'),
    ~F.text.in_({get_text('cancel_btn', 'uz'), get_text('cancel_btn', 'ru'), get_text('cancel_btn', 'en')}),
    ~IsAdmin()
)
async def send_message_from_user(message: types.Message, state: FSMContext, bot: Bot):
    if not config.FEEDBACK_RECIPIENT_ID:
        lang = await get_user_language(message.from_user.id)
        await message.answer(get_text('restart_error_msg', lang), reply_markup=await get_main_menu(lang, message.from_user.id))
        await state.clear()
        return

    try:
        data = await state.get_data()
        admin_id = data.get('chatting_with_admin_id')
        if not admin_id:
             admin_id = config.FEEDBACK_RECIPIENT_ID

        safe_nickname = html.escape(message.from_user.full_name)
        user_info = (f"💬 <b>Foydalanuvchidan javob:</b>\n\n"
                     f"<b>Yuboruvchi:</b> {safe_nickname}\n"
                     f"<b>ID:</b> <code>{message.from_user.id}</code>")

        await bot.send_message(admin_id, user_info)
        await message.copy_to(
            chat_id=admin_id,
            reply_markup=get_feedback_reply_to_user_keyboard(message.from_user.id)
        )

        lang = await get_user_language(message.from_user.id)
        await message.answer(
            get_text('admin_receive_msg', lang),
            reply_markup=await get_main_menu(lang, message.from_user.id)
        )
    except Exception:
        lang = await get_user_language(message.from_user.id)
        await message.answer(get_text('admin_reply_error_msg', lang), reply_markup=await get_main_menu(lang, message.from_user.id))
    finally:
        await state.clear()


@feedback_router.message(
    StateFilter(FeedbackState.waiting_for_feedback, FeedbackState.chatting_with_admin),
    F.text.in_({get_text('cancel_btn', 'uz'), get_text('cancel_btn', 'ru'), get_text('cancel_btn', 'en')})
)
async def cancel_feedback_process(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    await state.clear()
    await message.answer(
        get_text('admin_reply_cancel_msg', lang),
        reply_markup=await get_main_menu(lang, message.from_user.id)
    )

