import logging
from aiogram import F, Router, types, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup

from xdata_handlers import config
from xdata_handlers.database import (
    add_or_update_user,
    get_user_language
)

class AdvertisingState(StatesGroup):
    waiting_for_ad_content = State()
    chatting_with_admin = State()
from user_handlers.xinline_keyboard import (
    get_reply_to_user_keyboard, get_reply_to_admin_keyboard
)
from admin_handlers.admin_handler import IsAdmin
from post_handlers.xreply_keyboard import get_main_menu, get_cancel_kb
from xdata_handlers.translator import get_text

logger = logging.getLogger(__name__)
ad_router = Router()


@ad_router.message(Command("reklama"), ~IsAdmin())
async def cmd_advertisement_user(message: types.Message, state: FSMContext):
    await state.clear()
    
    lang = await get_user_language(message.from_user.id)
    remover_message = await message.answer(
        get_text('ad_section_msg', lang),
        reply_markup=ReplyKeyboardRemove()
    )
    await remover_message.delete()

    await add_or_update_user(
        user_id=message.from_user.id,
        nickname=message.from_user.full_name,
        username=message.from_user.username
    )

    await message.answer(
        get_text('ad_agreed_msg', lang),
        reply_markup=get_cancel_kb(lang)
    )
    await state.set_state(AdvertisingState.waiting_for_ad_content)

@ad_router.message(Command("reklama"), IsAdmin())
async def cmd_advertisement_admin(message: types.Message):
    await message.answer("Bu buyruq faqat oddiy foydalanuvchilar uchun mo'ljallangan.")





@ad_router.message(
    StateFilter(AdvertisingState.waiting_for_ad_content),
    F.content_type.in_({'text', 'photo', 'video', 'document', 'audio', 'animation', 'voice'}),
    ~F.text.in_({get_text('cancel_btn', 'uz'), get_text('cancel_btn', 'ru'), get_text('cancel_btn', 'en')}),
    ~IsAdmin()
)
async def process_first_ad_content(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    
    # Admin tayinlash olib tashlandi - to'g'ridan-to'g'ri adminlarga yuboriladi
    
    if not config.ADMIN_IDS:
        lang = await get_user_language(user_id)
        await message.answer(get_text('no_admins_available', lang))
        return
    
    try:
        header_text = (
            f"👤 <b>Yangi reklama bo'yicha murojaat!</b>\n\n"
            f"<b>Yuboruvchi:</b> {message.from_user.full_name}\n"
            f"<b>ID:</b> <code>{user_id}</code>\n"
            f"<b>Username:</b> @{message.from_user.username or 'mavjud emas'}"
        )
        
        # Barcha adminlarga yuboramiz
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(admin_id, header_text)
                await message.copy_to(
                    chat_id=admin_id,
                    reply_markup=get_reply_to_user_keyboard(user_id)
                )
            except Exception:
                pass
        
        await state.clear()
        lang = await get_user_language(user_id)
        await message.answer(get_text('ad_sent_msg', lang))

    except Exception:
        lang = await get_user_language(user_id)
        await message.answer(get_text('error_msg', lang))


@ad_router.callback_query(F.data.startswith("reply_ad:"))
async def reply_from_admin_handler(callback: types.CallbackQuery, state: FSMContext):
    remover_message = await callback.message.answer("...", reply_markup=ReplyKeyboardRemove())
    await remover_message.delete()

    parts = callback.data.split(":")
    user_id_to_reply = int(parts[1]) if len(parts) > 1 else None
    await state.set_state(AdvertisingState.chatting_with_admin)
    await state.update_data(recipient_user_id=user_id_to_reply)

    lang = await get_user_language(callback.from_user.id)
    await callback.message.answer(
        get_text('admin_reply_msg', lang).format(user_id=user_id_to_reply),
        reply_markup=get_cancel_kb(lang)
    )
    await callback.answer()

@ad_router.message(StateFilter(AdvertisingState.chatting_with_admin), IsAdmin())
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
        admin_id = message.from_user.id
        user_lang = await get_user_language(recipient_user_id)
        await bot.send_message(
            chat_id=recipient_user_id,
            text=get_text('user_receive_msg', user_lang)
        )
        await message.copy_to(
            chat_id=recipient_user_id,
            reply_markup=get_reply_to_admin_keyboard(admin_id)
        )
        await message.answer(get_text('admin_reply_success_msg', lang), reply_markup=ReplyKeyboardRemove())
    except Exception:
        await message.answer(get_text('admin_reply_error_msg', lang), reply_markup=ReplyKeyboardRemove())
    finally:
        await state.clear()

@ad_router.callback_query(F.data.startswith("reply_ad_to_admin:"))
async def reply_from_user_handler(callback: types.CallbackQuery, state: FSMContext):
    remover_message = await callback.message.answer("...", reply_markup=ReplyKeyboardRemove())
    await remover_message.delete()

    parts = callback.data.split(":")
    admin_id_to_reply = int(parts[1]) if len(parts) > 1 else None
    await state.set_state(AdvertisingState.chatting_with_admin)
    await state.update_data(chatting_with_admin_id=admin_id_to_reply)

    lang = await get_user_language(callback.from_user.id)
    await callback.message.answer(get_text('user_reply_prompt', lang), reply_markup=get_cancel_kb(lang))
    await callback.answer()

@ad_router.message(StateFilter(AdvertisingState.chatting_with_admin), ~IsAdmin())
async def send_message_from_user(message: types.Message, state: FSMContext, bot: Bot):
    lang = await get_user_language(message.from_user.id)
    if message.text == get_text('cancel_btn', lang):
        await state.clear()
        await message.answer(get_text('admin_reply_cancel_msg', lang), reply_markup=await get_main_menu(lang, message.from_user.id))
        return

    data = await state.get_data()
    admin_id = data.get('chatting_with_admin_id')
    if not admin_id:
        await message.answer(get_text('restart_error_msg', lang), reply_markup=await get_main_menu(lang, message.from_user.id))
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
            get_text('admin_receive_msg', lang),
            reply_markup=await get_main_menu(lang, message.from_user.id)
        )
    except Exception:
        await message.answer(get_text('admin_reply_error_msg', lang), reply_markup=await get_main_menu(lang, message.from_user.id))
    finally:
        await state.clear()



@ad_router.message(
    StateFilter(AdvertisingState.waiting_for_ad_content, AdvertisingState.chatting_with_admin),
    F.text.in_({get_text('cancel_btn', 'uz'), get_text('cancel_btn', 'ru'), get_text('cancel_btn', 'en')})
)
async def cancel_ad_process(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    await state.clear()
    await message.answer(
        get_text('admin_reply_cancel_msg', lang),
        reply_markup=await get_main_menu(lang, message.from_user.id)
    )

