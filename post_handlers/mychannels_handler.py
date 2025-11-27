#--- START OF FILE mychannels_handler.py ---
import html
from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from xdata_handlers.database import get_user_channels, remove_user_channel
from post_handlers.send_handler import cmd_add_channel

mychannels_router = Router()

#==================================================
# --- K L A V I A T U R A   Y A R A T I SH ---
#==================================================

class MyChannelsCallback(CallbackData, prefix="my_channels"):
    action: str
    channel_id: int | None = None

async def get_my_channels_keyboard(user_id: int):
    """Foydalanuvchi kanallari ro'yxati uchun inline klaviatura yaratadi."""
    builder = InlineKeyboardBuilder()
    user_channels = await get_user_channels(user_id)

    builder.button(
        text="➕ Yangi kanal qo'shish",
        callback_data=MyChannelsCallback(action="add_new").pack()
    )

    if user_channels:
        for channel in user_channels:
            builder.button(
                text=channel['channel_name'],
                callback_data=MyChannelsCallback(action="select", channel_id=channel['channel_id']).pack()
            )
        builder.adjust(1, 3)
    else:
        builder.adjust(1)

    return builder.as_markup()

def get_channel_manage_keyboard(channel_id: int):
    """Tanlangan kanalni boshqarish uchun inline klaviatura yaratadi."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🗑️ Kanalni o'chirish",
        callback_data=MyChannelsCallback(action="delete", channel_id=channel_id).pack()
    )
    builder.button(
        text="◀️ Ortga",
        callback_data=MyChannelsCallback(action="back_to_list").pack()
    )
    builder.adjust(1)
    return builder.as_markup()

#==================================================
# --- A S O S I Y   H A N D L E R L A R ---
#==================================================

@mychannels_router.message(Command("mychannels"))
async def cmd_my_channels(message: types.Message):
    """/mychannels buyrug'iga javob beradi va kanallar ro'yxatini ko'rsatadi."""
    keyboard = await get_my_channels_keyboard(message.from_user.id)
    await message.answer(
        "Iltimos tanlamoqchi bo'lgan kanalingiz ustiga bosing:",
        reply_markup=keyboard
    )

@mychannels_router.callback_query(MyChannelsCallback.filter(F.action == "add_new"))
async def handle_add_new_channel(callback: types.CallbackQuery, state: FSMContext):
    """'Yangi kanal qo'shish' tugmasi bosilganda /addchannel jarayonini boshlaydi."""
    await callback.message.delete()
    await cmd_add_channel(callback.message, state)
    await callback.answer()

@mychannels_router.callback_query(MyChannelsCallback.filter(F.action == "select"))
async def handle_select_channel(callback: types.CallbackQuery, callback_data: MyChannelsCallback):
    """Foydalanuvchi biror kanalni tanlaganda, boshqaruv menyusini ko'rsatadi."""
    channel_name = callback.message.reply_markup.inline_keyboard[0][0].text
    for row in callback.message.reply_markup.inline_keyboard:
        for button in row:
            if button.callback_data == callback.data:
                channel_name = button.text
                break

    safe_channel_name = html.escape(channel_name)

    await callback.message.edit_text(
        f"<b>{safe_channel_name}</b> ushbu kanal bilan nima qilmoqchisiz?",
        reply_markup=get_channel_manage_keyboard(callback_data.channel_id)
    )
    await callback.answer()

@mychannels_router.callback_query(MyChannelsCallback.filter(F.action == "delete"))
async def handle_delete_channel(callback: types.CallbackQuery, callback_data: MyChannelsCallback):
    """Kanalni o'chirish tugmasi bosilganda uni bazadan o'chiradi."""
    success = await remove_user_channel(callback.from_user.id, callback_data.channel_id)

    if success:
        await callback.answer("✅ Kanal muvaffaqiyatli o'chirildi!", show_alert=True)
        # Ro'yxatni yangilaymiz
        keyboard = await get_my_channels_keyboard(callback.from_user.id)
        await callback.message.edit_text(
            "Iltimos tanlamoqchi bo'lgan kanalingiz ustiga bosing:",
            reply_markup=keyboard
        )
    else:
        await callback.answer("❌ Xatolik: Kanalni o'chirib bo'lmadi.", show_alert=True)

@mychannels_router.callback_query(MyChannelsCallback.filter(F.action == "back_to_list"))
async def handle_back_to_list(callback: types.CallbackQuery):
    """'Ortga' tugmasi bosilganda kanallar ro'yxatiga qaytaradi."""
    keyboard = await get_my_channels_keyboard(callback.from_user.id)
    await callback.message.edit_text(
        "Iltimos tanlamoqchi bo'lgan kanalingiz ustiga bosing:",
        reply_markup=keyboard
    )
    await callback.answer()
#--- END OF FILE mychannels_handler.py ---
