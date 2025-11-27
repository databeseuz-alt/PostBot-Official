#--- START OF FILE block_handler.py ---
import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware, F, Router, types, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject, Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# --- O'ZGARTIRISH: Aylanma importni oldini olish uchun IsAdmin ni vfilters.py dan olamiz ---
# Agar vfilters.py hali yaratilmagan bo'lsa, avval uni yaratish kerak bo'ladi.
# Hozircha sizning kodingizdagi kabi qoldiraman, lekin bu aylanma importga sabab bo'lishi mumkin.
from admin_handlers.admin_handler import IsAdmin
from admin_handlers.vadmin_states import AdminStates
from xdata_handlers import config
from xdata_handlers.database import (
    is_user_blocked, add_or_update_user, get_user_language, block_user,
    unblock_user, get_user_info_from_db, find_user_by_id_or_username
)
from xdata_handlers.translator import get_text
from admin_handlers.xinline_keyboard import (
    get_blocked_users_keyboard, get_blocked_list_view_keyboard,
    get_unblock_confirmation_keyboard
)

block_router = Router()

# =============================================================================
# BLOKLASH BO'LIMINING ASOSIY HANDLERLARI
# =============================================================================

@block_router.callback_query(F.data == "admin:blocked_users_menu", IsAdmin())
async def blocked_users_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()

    try:
        await callback.message.edit_text(
            "🚫 Bloklash bo'limi. Kerakli amalni tanlang:",
            reply_markup=get_blocked_users_keyboard()
        )
    except TelegramBadRequest:
        await callback.message.delete()
        await callback.message.answer(
            "🚫 Bloklash bo'limi. Kerakli amalni tanlang:",
            reply_markup=get_blocked_users_keyboard()
        )

    await callback.answer()

@block_router.callback_query(F.data == "admin:block_user_start", IsAdmin())
async def block_user_start_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_block_id)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Asosiy panel", callback_data="admin:back_to_main_menu"),
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:blocked_users_menu")
    )
    builder.adjust(2)
    cancel_kb = builder.as_markup()

    try:
        await callback.message.edit_text(
            "Foydalanuvchini bloklash uchun uning <b>Telegram ID</b>sini yoki <b>@username</b> ni yuboring.",
            reply_markup=cancel_kb
        )
    except TelegramBadRequest:
        await callback.message.delete()
        await callback.message.answer(
            "Foydalanuvchini bloklash uchun uning <b>Telegram ID</b>sini yoki <b>@username</b>'ini yuboring.",
            reply_markup=cancel_kb
        )

    await callback.answer()

@block_router.message(StateFilter(AdminStates.waiting_for_block_id), F.text, IsAdmin())
async def block_user_query_received(message: types.Message, state: FSMContext):
    query = message.text.strip()
    user_data = await find_user_by_id_or_username(query)

    if not user_data:
        return await message.answer(f"❌ '{query}' bo'yicha foydalanuvchi bazadan topilmadi. Qaytadan yuboring.")

    user_id_to_block = user_data.get('user_id')

    if user_id_to_block in config.ADMIN_IDS:
        return await message.answer("Siz adminni bloklay olmaysiz!")

    if await is_user_blocked(user_id_to_block, admin_ids=config.ADMIN_IDS):
        return await message.answer("Bu foydalanuvchi allaqachon bloklangan.")

    if await block_user(user_id_to_block, admin_ids=config.ADMIN_IDS):
        full_name = user_data.get('full_name', 'Noma\'lum')
        await message.answer(f"✅ Foydalanuvchi <b>{full_name}</b> (<code>{user_id_to_block}</code>) muvaffaqiyatli bloklandi!")

        await state.clear()
        await message.answer(
            "🚫 Bloklash bo'limi. Kerakli amalni tanlang:",
            reply_markup=get_blocked_users_keyboard()
        )
    else:
        await message.answer("Noma'lum xatolik yuz berdi. Foydalanuvchi bloklanmadi.")

@block_router.callback_query(F.data == "admin:show_blocked_list", IsAdmin())
async def show_blocked_list_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()

    keyboard = await get_blocked_list_view_keyboard(admin_ids=config.ADMIN_IDS, adjust_size=3)

    if len(keyboard.inline_keyboard) <= 1:
        text = "Hozircha bloklangan foydalanuvchilar yo'q."
    else:
        text = "Bloklanganlar ro'yxati (blokdan chiqarish uchun bosing):"

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)

    await callback.answer()


@block_router.callback_query(F.data.startswith("admin:unblock_confirm:"), IsAdmin())
async def unblock_confirm_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[2])
    user_info = await get_user_info_from_db(user_id)
    if not user_info:
        await callback.answer("Foydalanuvchi bazadan topilmadi!", show_alert=True)
        return await show_blocked_list_handler(callback, state)

    display_name = user_info.get('full_name') or f"Noma'lum ({user_id})"

    try:
        await callback.message.edit_text(
            f"Haqiqatdan ham <b>{display_name}</b> (<code>{user_id}</code>) ni blokdan chiqarmoqchimisiz?",
            reply_markup=get_unblock_confirmation_keyboard(user_id)
        )
    except TelegramBadRequest:
        await callback.message.delete()
        await callback.message.answer(
            f"Haqiqatdan ham <b>{display_name}</b> (<code>{user_id}</code>) ni blokdan chiqarmoqchimisiz?",
            reply_markup=get_unblock_confirmation_keyboard(user_id)
        )

    await callback.answer()

@block_router.callback_query(F.data.startswith("admin:unblock_do:"), IsAdmin())
async def unblock_do_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[2])
    await unblock_user(user_id)
    await callback.answer(f"Foydalanuvchi {user_id} blokdan chiqarildi!", show_alert=True)
    await show_blocked_list_handler(callback, state)

# =============================================================================
# MIDDLEWARE: FOYDALANUVCHILARNI BLOKLASH UCHUN TEKSHIRISH
# =============================================================================

class BlockUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get('event_from_user')
        chat = data.get('event_chat')

        if user and not user.is_bot and chat and chat.type == 'private':
            await add_or_update_user(
                user_id=user.id,
                full_name=user.full_name,
                username=user.username,
                admin_ids=config.ADMIN_IDS
            )

        # XATOLIK TUZATILDI: Asinxron funksiyalarga `await` qo'shildi
        if user and await is_user_blocked(user.id, admin_ids=config.ADMIN_IDS):
            logging.warning(f"[BLOCK_CHECK] Foydalanuvchi ID: {user.id} BLOKLANGAN. So'rov to'xtatildi.")
            lang = await get_user_language(user.id)
            if isinstance(event, CallbackQuery):
                await event.answer(get_text('you_are_blocked', lang), show_alert=True)
            elif isinstance(event, Message):
                await event.answer(get_text('you_are_blocked', lang))
            return

        return await handler(event, data)
#--- END OF FILE block_handler.py ---
