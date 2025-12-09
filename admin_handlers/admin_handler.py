#--- START OF FILE admin_handler.py ---
from aiogram import F, Router, types
from aiogram.types import ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, Filter
from aiogram.fsm.context import FSMContext

from xdata_handlers import config
from admin_handlers.xinline_keyboard import get_main_admin_keyboard

admin_router = Router()

class IsAdmin(Filter):
    async def __call__(self, message_or_callback: types.Message | types.CallbackQuery) -> bool:
        return message_or_callback.from_user.id in config.ADMIN_IDS

# =============================================================================
# ADMIN PANELIGA KIRISH VA ASOSIY NAVIGATSIYA
# =============================================================================

@admin_router.message(Command("admin"), IsAdmin())
async def admin_panel_handler(message: types.Message, state: FSMContext):
    await state.clear()

    await message.answer("xush kelibsiz 👋. biror bo'limni tanlang :", reply_markup=get_main_admin_keyboard())

@admin_router.message(F.text == "◀️ Ortga (Admin panel)", IsAdmin())
async def back_to_main_panel_from_reply(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Asosiy menyuga qaytildi.", reply_markup=ReplyKeyboardRemove())
    await message.answer("Kerakli bo'limni tanlang:", reply_markup=get_main_admin_keyboard())

@admin_router.callback_query(F.data == "admin:back_to_main_menu", IsAdmin())
async def back_to_main_menu_from_inline(callback: types.CallbackQuery, state: FSMContext):
    # --- O'ZGARTIRISH: Keraksiz tekshiruv olib tashlandi ---
    # Endi "tekshiruv jarayoni" mavjud emas, shuning uchun bu blok kerak emas.
    await state.clear()
    try:
        await callback.message.edit_text(
            "Kerakli bo'limni tanlang:",
            reply_markup=get_main_admin_keyboard()
        )
    except TelegramBadRequest:
        await callback.message.delete()
        await callback.message.answer(
            "Kerakli bo'limni tanlang:",
            reply_markup=get_main_admin_keyboard()
        )
    await callback.answer()

#--- END OF FILE admin_handler.py ---
