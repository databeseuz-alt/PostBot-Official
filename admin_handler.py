from aiogram import F, Router, types
from aiogram.types import ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, Filter, StateFilter
from aiogram.fsm.context import FSMContext

from xdata_handlers import config
from admin_handlers.xinline_keyboard import get_main_admin_keyboard
from xdata_handlers.database import is_maintenance_mode, set_maintenance_mode

from aiogram.fsm.state import State, StatesGroup

admin_router = Router()

class IsAdmin(Filter):
    async def __call__(self, message_or_callback: types.Message | types.CallbackQuery) -> bool:
        return message_or_callback.from_user.id in config.ADMIN_IDS


class AdminStates(StatesGroup):
    waiting_for_block_id = State()

    waiting_for_ad_content = State()
    waiting_for_ad_edit_content = State()
    configuring_ad_post = State()
    waiting_for_ad_button_text = State()
    waiting_for_ad_button_url = State()
    managing_ad_button = State()
    waiting_for_ad_limit = State()
    confirming_ad_send = State()

    waiting_for_user_query = State()
    viewing_user_profile = State()

    waiting_for_channel_forward = State()

    waiting_for_direct_message_user_id = State()
    waiting_for_direct_message_content = State()


class AdminGuideSettings(StatesGroup):
    waiting_for_guide_content = State()
    choosing_language = State()


@admin_router.message(Command("admin"), IsAdmin())
async def admin_panel_handler(message: types.Message, state: FSMContext):
    await state.clear()

    remover_message = await message.answer(
        "Admin paneli ochilmoqda...",
        reply_markup=ReplyKeyboardRemove()
    )
    await remover_message.delete()

    is_m = await is_maintenance_mode()
    await message.answer("xush kelibsiz 👋. biror bo'limni tanlang :", reply_markup=get_main_admin_keyboard(is_m))

@admin_router.message(
    F.text == "❌ Bekor qilish",
    StateFilter(
        AdminStates.waiting_for_block_id,
        AdminStates.waiting_for_ad_content,
        AdminStates.waiting_for_ad_edit_content,
        AdminStates.configuring_ad_post,
        AdminStates.waiting_for_ad_button_text,
        AdminStates.waiting_for_ad_button_url,
        AdminStates.managing_ad_button,
        AdminStates.waiting_for_ad_limit,
        AdminStates.confirming_ad_send,
        AdminStates.waiting_for_user_query,
        AdminStates.viewing_user_profile,
        AdminStates.waiting_for_channel_forward,
        AdminStates.waiting_for_direct_message_user_id,
        AdminStates.waiting_for_direct_message_content
    ),
    IsAdmin()
)
async def back_to_main_panel_from_reply(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Asosiy menyuga qaytildi.", reply_markup=ReplyKeyboardRemove())
    is_m = await is_maintenance_mode()
    await message.answer("Kerakli bo'limni tanlang:", reply_markup=get_main_admin_keyboard(is_m))

@admin_router.callback_query(F.data == "admin:back_to_main_menu", IsAdmin())
async def back_to_main_menu_from_inline(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    is_m = await is_maintenance_mode()
    try:
        await callback.message.edit_text(
            "Kerakli bo'limni tanlang:",
            reply_markup=get_main_admin_keyboard(is_m)
        )
    except TelegramBadRequest:
        await callback.message.delete()
        await callback.message.answer(
            "Kerakli bo'limni tanlang:",
            reply_markup=get_main_admin_keyboard(is_m)
        )
    await callback.answer()

@admin_router.callback_query(F.data == "admin:toggle_maintenance", IsAdmin())
async def toggle_maintenance_handler(callback: types.CallbackQuery, state: FSMContext):
    current_status = await is_maintenance_mode()
    new_status = not current_status
    await set_maintenance_mode(new_status)
    
    from xdata_handlers.translator import get_text
    lang = "uzl" 
    
    msg_key = "maintenance_mode_on" if new_status else "maintenance_mode_off"
    await callback.answer(get_text(msg_key, lang), show_alert=True)
    
    # Refresh keyboard
    await back_to_main_menu_from_inline(callback, state)
