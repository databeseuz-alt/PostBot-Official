#--- START OF FILE start_handler.py ---
import html
from aiogram import F, Router, types, Bot
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from admin_handlers.channel_handler import check_user_membership
from xdata_handlers.translator import get_text
from xdata_handlers.database import get_user_language, add_or_update_user, get_posts_by_user
from post_handlers.xreply_keyboard import get_main_menu, get_cancel_kb
from post_handlers.vpost_states import PostCreation, PostSending
from xdata_handlers import config
from post_handlers.localize_filter import LocalizedText

start_router = Router()

#==================================================
# --- A S O S I Y   B U Y R U Q L A R   V A   N A V I G A T S I Y A ---
#==================================================

async def show_main_menu(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot):
    # Har qanday holatni tozalaymiz, bu jarayonni bekor qiladi
    await state.clear()
    user = event.from_user

    await add_or_update_user(
        user_id=user.id,
        full_name=user.full_name,
        username=user.username,
        admin_ids=config.ADMIN_IDS
    )

    lang = await get_user_language(user.id)
    safe_user_name = html.escape(user.full_name)
    start_text = get_text('welcome', lang).format(user_name=safe_user_name)

    main_menu_keyboard = await get_main_menu(lang=lang, user_id=user.id)

    if isinstance(event, types.Message):
        # Yangi reply klaviatura avtomatik ravishda eskisini almashtiradi.
        # Ortiqcha xabar yuborishga hojat yo'q.
        await event.answer(start_text, reply_markup=main_menu_keyboard)
    elif isinstance(event, types.CallbackQuery):
        await event.message.delete()
        await event.message.answer(start_text, reply_markup=main_menu_keyboard)


@start_router.message(CommandStart(), F.forward_from.is_(None))
async def cmd_start(message: types.Message, state: FSMContext, bot: Bot):
    is_member, text, keyboard = await check_user_membership(message.from_user, bot)

    if not is_member:
        remover_message = await message.answer(".", reply_markup=ReplyKeyboardRemove())
        await remover_message.delete()
        await message.answer(text, reply_markup=keyboard)
        return

    await show_main_menu(message, state, bot)


@start_router.callback_query(F.data == "check_subscription_again")
async def check_subscription_again(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    is_member, text, keyboard = await check_user_membership(callback.from_user, bot)

    if is_member:
        await callback.answer()
        await show_main_menu(callback, state, bot)
    else:
        await callback.answer("⚠️ Kanal(lar)ga a'zo bo'ling va qaytadan urining!", show_alert=True)

#==================================================
# --- A S O S I Y   M E N Y U   T U G M A L A R I   U C H U N   H A N D L E R L A R ---
#==================================================

@start_router.message(LocalizedText('btn_create_post'), StateFilter(None))
async def start_post_creation(message: types.Message, state: FSMContext, bot: Bot):
    is_member, text, keyboard = await check_user_membership(message.from_user, bot)
    if not is_member:
        remover_message = await message.answer(".", reply_markup=ReplyKeyboardRemove())
        await remover_message.delete()
        await message.answer(text, reply_markup=keyboard)
        return

    await state.clear()
    lang = await get_user_language(message.from_user.id)
    await message.answer(get_text('ask_for_content', lang), reply_markup=get_cancel_kb(lang))
    await state.set_state(PostCreation.waiting_for_content)


@start_router.message(LocalizedText('btn_edit_post'), StateFilter(None))
async def start_post_editing_process(message: types.Message, state: FSMContext, bot: Bot):
    is_member, text, keyboard = await check_user_membership(message.from_user, bot)
    if not is_member:
        remover_message = await message.answer(".", reply_markup=ReplyKeyboardRemove())
        await remover_message.delete()
        await message.answer(text, reply_markup=keyboard)
        return

    await state.clear()
    lang = await get_user_language(message.from_user.id)

    user_posts = await get_posts_by_user(message.from_user.id)

    saved_posts = [post for post in user_posts if post.get('name')]

    if not saved_posts:
        await message.answer(get_text('ask_for_edit_code', lang), reply_markup=get_cancel_kb(lang))
    else:
        bot_info = await bot.get_me()
        posts_list_text = "<b>Saqlangan postlaringiz:</b>\n\n"
        count = 1
        for post in saved_posts:
            safe_post_name = html.escape(post.get('name', ''))
            post_code = post['code']
            posts_list_text += f"{count}. {safe_post_name}\n"
            posts_list_text += f"<code>@{bot_info.username} {post_code}</code>\n"
            posts_list_text += f"<code>/delete_post {post_code}</code>\n\n"
            count += 1

        posts_list_text += "Postingizni tahrirlash uchun post kodingizni kiriting!"
        await message.answer(posts_list_text, reply_markup=get_cancel_kb(lang))

    await state.set_state(PostCreation.waiting_for_edit_code)

#==================================================
# --- U M U M I Y   B E K O R   Q I L I SH   H A N D L E R I ---
#==================================================

@start_router.message(
    StateFilter(
        PostCreation.waiting_for_content,
        PostCreation.waiting_for_edit_code,
        PostCreation.configuring_post,
        PostCreation.waiting_for_button_text,
        PostCreation.waiting_for_button_url,
        PostCreation.waiting_for_post_name,
        PostSending.waiting_for_channel_info,
        PostSending.choosing_channel_to_send
    ),
    LocalizedText('btn_cancel')
)
async def cancel_action(message: types.Message, state: FSMContext, bot: Bot):
    is_member, check_text, check_keyboard = await check_user_membership(message.from_user, bot)
    if not is_member:
        await state.clear()
        lang = await get_user_language(message.from_user.id)
        await message.answer(get_text('action_canceled', lang), reply_markup=ReplyKeyboardRemove())
        await message.answer(check_text, reply_markup=check_keyboard)
        return

    await state.clear()
    lang = await get_user_language(message.from_user.id)
    await message.answer(
        get_text('action_canceled', lang),
        reply_markup=await get_main_menu(lang=lang, user_id=message.from_user.id)
    )
#--- END OF FILE start_handler.py ---
