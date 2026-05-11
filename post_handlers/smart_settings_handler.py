import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder

from post_handlers.post_handler import PostCreation
from xdata_handlers.database import get_user_language

logger = logging.getLogger(__name__)

smart_settings_router = Router()

@smart_settings_router.message(F.text == "⚙️ Aqlli sozlamalar", StateFilter(PostCreation.configuring_post))
async def show_smart_settings(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    
    text = (
        "⚙️ <b>Aqlli sozlamalar</b>\n\n"
        "Ushbu bo'limda siz post uchun qulay avtomatlashtirish imkoniyatlarini sozlashingiz mumkin:\n\n"
        "🗑 <b>Avto-o'chirish:</b> Postni belgilangan vaqtdan keyin (masalan, 24 soat) avtomatik o'chirib yuborish.\n"
        "📌 <b>Avto-qadash (Pin):</b> Postni kanalga e'lon qilingandan so'ng avtomatik qadab qo'yish (pin).\n"
        "🔄 <b>Takrorlash:</b> Postni har hafta yoki har oy muntazam ravishda qayta e'lon qilish.\n"
        "📝 <b>Shablon:</b> Joriy sozlamalarni (suv belgisi, imzo, tugmalar va hk) shablon sifatida saqlab qo'yish.\n\n"
        "<i>Kerakli sozlamani tanlang:</i>"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Avto-o'chirish", callback_data="smart_auto_delete")
    builder.button(text="📌 Avto-qadash", callback_data="smart_auto_pin")
    builder.button(text="🔄 Takroriy post", callback_data="smart_recurring")
    builder.button(text="📝 Shablon qilib saqlash", callback_data="smart_save_template")
    builder.button(text="❌ Yopish", callback_data="smart_close")
    
    builder.adjust(2, 1, 1, 1)
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@smart_settings_router.callback_query(F.data.startswith("smart_"))
async def process_smart_settings(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data
    
    if action == "smart_close":
        await callback.message.delete()
        await callback.answer()
        return
        
    # Placeholder for actual logic
    if action == "smart_auto_delete":
        await callback.answer("Bu funksiya tez orada ishga tushadi!", show_alert=True)
    elif action == "smart_auto_pin":
        await callback.answer("Bu funksiya tez orada ishga tushadi!", show_alert=True)
    elif action == "smart_recurring":
        await callback.answer("Bu funksiya tez orada ishga tushadi!", show_alert=True)
    elif action == "smart_save_template":
        await callback.answer("Shablon saqlandi!", show_alert=True)
        
    await callback.answer()
