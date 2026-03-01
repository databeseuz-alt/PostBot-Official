from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.types import ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest

from admin_handlers.admin_handler import IsAdmin
from admin_handlers.admin_handler import AdminStates
from xdata_handlers import config
from admin_handlers.xinline_keyboard import get_channel_main_menu_keyboard, get_channel_list_keyboard


async def check_user_membership(user: types.User, bot: Bot):
    """Foydalanuvchining barcha majburiy kanallarga a'zoligini tekshiradi."""
    from xdata_handlers.database import get_all_required_channels, get_user_language
    from xdata_handlers.translator import get_text

    if user.id in config.ADMIN_IDS:
        return True, None, None

    channels = await get_all_required_channels()
    if not channels:
        return True, None, None

    lang = await get_user_language(user.id)
    not_joined_channels = []

    for channel in channels:
        try:
            member = await bot.get_chat_member(chat_id=int(channel['id']), user_id=user.id)
            if member.status in ['left', 'kicked']:
                not_joined_channels.append(channel)
        except Exception:
            not_joined_channels.append(channel)

    if not_joined_channels:
        text = get_text('join_required_msg', lang)
        builder = InlineKeyboardBuilder()
        for ch in not_joined_channels:
            if ch.get('username'):
                link = f"https://t.me/{ch['username'].replace('@', '')}"
            else:
                try:
                    link = await bot.export_chat_invite_link(int(ch['id']))
                except Exception:
                    link = None
            
            if link:
                btn_text = get_text('subscribe_btn', lang).format(title=ch['title'])
                builder.button(text=btn_text, url=link)

        builder.button(text=get_text('joined_btn', lang), callback_data="check_subscription_again")
        builder.adjust(1)
        return False, text, builder.as_markup()

    return True, None, None


channel_router = Router()

@channel_router.callback_query(F.data == "admin:channel_menu", IsAdmin())
async def channel_management_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "📢 Majburiy a'zolik uchun kanalni boshqarish bo'limi.",
        reply_markup=get_channel_main_menu_keyboard()
    )
    await callback.answer()

@channel_router.callback_query(F.data == "admin:channel_show_list", IsAdmin())
async def show_channel_list(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    keyboard, text = await get_channel_list_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@channel_router.callback_query(F.data == "admin:channel_add_start", IsAdmin())
async def add_channel_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_channel_forward)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Asosiy panel", callback_data="admin:back_to_main_menu"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:channel_menu")
    )

    await callback.message.edit_text(
        "<b>Kanal qo'shish jarayoni</b>\n\n"
        "1. Botni kerakli kanalga <b>admin</b> qiling.\n"
        "2. Quyidagi usullardan birini bajaring:\n"
        "   - Kanaldan istalgan xabarni shu yerga <b>forward qiling.</b>\n"
        "   - Kanalning <b>@username</b> yoki <b>ID</b>sini yuboring.",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

async def _add_channel_to_db(message: types.Message, state: FSMContext, bot: Bot, chat_info: types.Chat):
    """Kanalni tekshiradi va bazaga qo'shish uchun yordamchi funksiya."""
    from xdata_handlers.database import add_required_channel

    if chat_info.type != 'channel':
        return await message.answer("❌ Xatolik: Bu kanal emas.")

    try:
        member = await bot.get_chat_member(chat_info.id, bot.id)
        if member.status not in ['administrator', 'creator']:
            return await message.answer(f"❌ <b>Xatolik:</b> Men <b>«{chat_info.title}»</b> kanalida admin emasman!")
    except Exception as e:
        return await message.answer(f"❌ Kanalni tekshirishda kutilmagan xatolik yuz berdi: {e}")

    await add_required_channel(
        channel_id=chat_info.id,
        title=chat_info.title,
        username=chat_info.username
    )
    await state.clear()
    await message.answer(f"✅ <b>Muvaffaqiyatli!</b>\n<b>{chat_info.title}</b> kanali majburiy a'zolik ro'yxatiga qo'shildi.", reply_markup=ReplyKeyboardRemove())

    await message.answer(
        "📢 Majburiy a'zolik uchun kanalni boshqarish bo'limi.",
        reply_markup=get_channel_main_menu_keyboard()
    )

@channel_router.message(AdminStates.waiting_for_channel_forward, F.forward_from_chat, IsAdmin())
async def process_channel_forward(message: types.Message, state: FSMContext, bot: Bot):
    await _add_channel_to_db(message, state, bot, message.forward_from_chat)

@channel_router.message(AdminStates.waiting_for_channel_forward, F.text, IsAdmin())
async def process_channel_id_or_username(message: types.Message, state: FSMContext, bot: Bot):
    channel_identifier = message.text
    try:
        chat_info = await bot.get_chat(channel_identifier)
        await _add_channel_to_db(message, state, bot, chat_info)
    except TelegramBadRequest:
        await message.answer(f"❌ <b>Xatolik:</b> '{channel_identifier}' nomli kanal topilmadi. Iltimos, to'g'ri @username yoki ID kiriting.")
    except Exception as e:
        await message.answer(f"❌ Noma'lum xatolik yuz berdi: {e}")

@channel_router.callback_query(F.data.startswith("admin:channel_remove:"), IsAdmin())
async def remove_channel_from_list(callback: types.CallbackQuery, state: FSMContext):
    from xdata_handlers.database import remove_required_channel

    try:
        channel_id_to_remove = int(callback.data.split(':')[-1])
    except (ValueError, IndexError):
        await callback.answer("Xatolik: Kanal ID topilmadi.", show_alert=True)
        return

    await remove_required_channel(channel_id_to_remove)
    await callback.answer("✅ Kanal ro'yxatdan o'chirildi!", show_alert=True)
    await show_channel_list(callback, state)
