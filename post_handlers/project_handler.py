import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from xdata_handlers.database import get_user_language

logger = logging.getLogger(__name__)

project_router = Router()

class ProjectStates(StatesGroup):
    waiting_for_project_name = State()
    managing_project = State()

@project_router.message(Command("projects"))
async def cmd_projects(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    
    text = (
        "🗂 <b>Loyihalar (Projects)</b>\n\n"
        "Loyihalar orqali siz o'z kanallaringizni guruhlashingiz, tahrirchilar qo'shishingiz va har bir loyiha uchun alohida sozlamalar (suv belgisi, imzo) kiritishingiz mumkin.\n\n"
        "Hozirda sizda loyihalar mavjud emas."
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yangi loyiha yaratish", callback_data="project_create")
    builder.adjust(1)
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@project_router.callback_query(F.data == "project_create")
async def create_project(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Yangi loyiha nomini kiriting:")
    await state.set_state(ProjectStates.waiting_for_project_name)
    await callback.answer()

@project_router.message(ProjectStates.waiting_for_project_name)
async def process_project_name(message: types.Message, state: FSMContext):
    project_name = message.text
    # Save project to database
    
    text = f"✅ <b>{project_name}</b> loyihasi muvaffaqiyatli yaratildi!\n\nQuyidagi amallardan birini tanlang:"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Tahrirchi qo'shish", callback_data=f"project_add_editor:1")
    builder.button(text="📢 Kanallarni biriktirish", callback_data=f"project_add_channel:1")
    builder.button(text="⚙️ Loyiha sozlamalari", callback_data=f"project_settings:1")
    builder.button(text="◀️ Orqaga", callback_data="project_list")
    builder.adjust(1)
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await state.clear()
