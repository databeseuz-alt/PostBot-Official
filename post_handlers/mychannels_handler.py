import html
import logging

logger = logging.getLogger(__name__)

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from xdata_handlers.database import get_user_channels, remove_user_channel, get_user_language
from post_handlers.send_handler import cmd_add_channel
from xdata_handlers.translator import get_text

mychannels_router = Router()

class MyChannelsCallback(CallbackData, prefix="my_channels"):
    action: str
    channel_id: int | None = None

async def get_my_channels_keyboard(user_id: int):
    """Foydalanuvchi kanallari ro'yxati uchun inline klaviatura yaratadi."""
    builder = InlineKeyboardBuilder()
    user_channels = await get_user_channels(user_id)
    lang = await get_user_language(user_id)

    builder.button(
        text=get_text('add_new_channel_btn', lang),
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

def get_channel_manage_keyboard(channel_id: int, lang: str = 'uzl'):
    """Tanlangan kanalni boshqarish uchun inline klaviatura yaratadi."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text('delete_channel_btn', lang),
        callback_data=MyChannelsCallback(action="delete", channel_id=channel_id).pack()
    )
    builder.button(
        text=get_text('back_btn', lang),
        callback_data=MyChannelsCallback(action="back_to_list").pack()
    )
    builder.adjust(1)
    return builder.as_markup()

@mychannels_router.message(Command("mychannels"))
async def cmd_my_channels(message: types.Message):
    """/mychannels buyrug'iga javob beradi va kanallar ro'yxatini ko'rsatadi."""
    user_id = message.from_user.id
    user_channels = await get_user_channels(user_id)
    lang = await get_user_language(user_id)

    if not user_channels:
        # Agar foydalanuvchi birorta kanal qo'shmagan bo'lsa
        await message.answer(get_text('need_channel_msg', lang))
        return

    keyboard = await get_my_channels_keyboard(user_id)
    await message.answer(
        get_text('choose_channel_msg', lang),
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
    lang = await get_user_language(callback.from_user.id)

    await callback.message.edit_text(
        get_text('channel_action_msg', lang).format(channel_name=safe_channel_name),
        reply_markup=get_channel_manage_keyboard(callback_data.channel_id, lang)
    )
    await callback.answer()

@mychannels_router.callback_query(MyChannelsCallback.filter(F.action == "delete"))
async def handle_delete_channel(callback: types.CallbackQuery, callback_data: MyChannelsCallback):
    """Kanalni o'chirish tugmasi bosilganda uni bazadan o'chiradi."""
    success = await remove_user_channel(callback.from_user.id, callback_data.channel_id)
    lang = await get_user_language(callback.from_user.id)

    if success:
        await callback.answer(get_text('delete_channel_success_msg', lang), show_alert=True)
        
        # Tekshirish - agar kanallar qolgan bo'lsa ro'yxatini ko'rsat, yo'qsa need_channel_msg
        remaining_channels = await get_user_channels(callback.from_user.id)
        if not remaining_channels:
            # Barcha kanallar o'chirildi
            await callback.message.edit_text(get_text('need_channel_msg', lang))
        else:
            keyboard = await get_my_channels_keyboard(callback.from_user.id)
            await callback.message.edit_text(
                get_text('choose_channel_msg', lang),
                reply_markup=keyboard
            )
    else:
        await callback.answer(get_text('delete_channel_error_msg', lang), show_alert=True)

@mychannels_router.callback_query(MyChannelsCallback.filter(F.action == "back_to_list"))
async def handle_back_to_list(callback: types.CallbackQuery):
    """'Ortga' tugmasi bosilganda kanallar ro'yxatiga qaytaradi."""
    keyboard = await get_my_channels_keyboard(callback.from_user.id)
    lang = await get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        get_text('choose_channel_msg', lang),
        reply_markup=keyboard
    )
    await callback.answer()
