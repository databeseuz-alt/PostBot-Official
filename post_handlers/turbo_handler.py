import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from xdata_handlers.database import get_user_language
from xdata_handlers.translator import get_text
from post_handlers.xreply_keyboard import get_cancel_reply_kb

logger = logging.getLogger(__name__)

turbo_router = Router()

class TurboModeStates(StatesGroup):
    waiting_for_drafts = State()
    choosing_mode = State()

@turbo_router.message(F.text == "⚡️ Turbo rejim")
async def cmd_turbo_mode(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    text = "⚡️ <b>Turbo rejim</b>\n\nBotga bir nechta draftlarni tashlang — va tamom. Bot ularni shabloningizdan foydalangan holda to'liq postlarga aylantiradi: tugmalar, imzo, suv belgisi qo'shadi, matnni qayta yozadi.\n\nIltimos, post matnlari yoki rasmlarini yuboring:"
    await message.answer(text, parse_mode="HTML", reply_markup=get_cancel_reply_kb(lang, False))
    await state.set_state(TurboModeStates.waiting_for_drafts)

@turbo_router.message(TurboModeStates.waiting_for_drafts)
async def process_turbo_drafts(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    # Draftni saqlab olish logikasi shu yerda bo'ladi. Hozircha oddiy qilib davom ettiramiz.
    
    text = "Draft qabul qilindi. Endi nashr qilish turini tanlang:\n\n1️⃣ Tezkor nashr qilish\n2️⃣ Jadval bo'yicha\n3️⃣ Aralash jadval"
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="1️⃣ Tezkor", callback_data="turbo_mode:fast")
    builder.button(text="2️⃣ Jadval", callback_data="turbo_mode:schedule")
    builder.button(text="3️⃣ Aralash", callback_data="turbo_mode:mixed")
    
    await message.answer(text, reply_markup=builder.as_markup())
    await state.set_state(TurboModeStates.choosing_mode)

@turbo_router.callback_query(TurboModeStates.choosing_mode, F.data.startswith("turbo_mode:"))
async def process_turbo_mode_selection(callback: types.CallbackQuery, state: FSMContext):
    mode = callback.data.split(":")[1]
    
    if mode == "fast":
        await callback.message.answer("⚡️ Tezkor nashr qilinmoqda...")
    elif mode == "schedule":
        await callback.message.answer("📅 Jadval bo'yicha saqlanmoqda...")
    elif mode == "mixed":
        await callback.message.answer("🔀 Aralash jadval bo'yicha saqlanmoqda...")
        
    await state.clear()
    await callback.answer()
