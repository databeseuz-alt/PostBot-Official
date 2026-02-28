import html
from aiogram import F, Router, types, Bot
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from admin_handlers.channel_handler import check_user_membership
from xdata_handlers.translator import get_text
from xdata_handlers.database import get_user_language, add_or_update_user, get_posts_by_user, get_user_post_settings
from post_handlers.xreply_keyboard import get_main_menu, get_cancel_reply_kb
from post_handlers.post_handler import PostCreation
from post_handlers.send_handler import PostSending
from xdata_handlers import config
from post_handlers.localize_filter import LocalizedText

start_router = Router()


async def show_main_menu(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    user = event.from_user

    await add_or_update_user(
        user_id=user.id,
        nickname=user.full_name,
        username=user.username
    )

    lang = await get_user_language(user.id)
    safe_nickname = html.escape(user.full_name)
    start_text = get_text('welcome_msg', lang).format(nickname=safe_nickname)

    main_menu_keyboard = await get_main_menu(lang=lang, user_id=user.id)

    if isinstance(event, types.Message):
        await event.reply(start_text, reply_markup=main_menu_keyboard)
    elif isinstance(event, types.CallbackQuery):
        await event.message.delete()
        await event.message.answer(start_text, reply_markup=main_menu_keyboard)


@start_router.message(CommandStart(), StateFilter("*"), F.forward_from.is_(None))
async def cmd_start(message: types.Message, state: FSMContext, bot: Bot):
    is_member, text, keyboard = await check_user_membership(message.from_user, bot)

    if not is_member:
        remover_message = await message.answer(".", reply_markup=ReplyKeyboardRemove())
        await remover_message.delete()
        await message.answer(text, reply_markup=keyboard)
        return

    await show_main_menu(message, state, bot)


@start_router.message(Command("newpost"))
async def cmd_newpost(message: types.Message, state: FSMContext, bot: Bot):
    await start_post_creation(message, state, bot)


@start_router.message(Command("mycodes"))
async def cmd_mycodes(message: types.Message, state: FSMContext, bot: Bot):
    """Foydalanuvchining post kodlarini ko'rsatadi."""
    lang = await get_user_language(message.from_user.id)
    user_posts = await get_posts_by_user(message.from_user.id)

    if not user_posts:
        await message.answer(get_text('mycodes_empty', lang), parse_mode="HTML")
    else:
        result_text = get_text('mycodes_msg', lang)
        result_text += get_text('mycodes_header', lang)

        count = 1
        for post in user_posts:
            post_name = post.get('name') or "Nomsiz post"
            post_code = post.get('code', 'N/A')
            item_text = get_text('mycodes_item', lang).format(
                count=count,
                post_name=html.escape(post_name),
                post_code=post_code,
                created_at="Yaqinda"
            )
            
            if len(result_text) + len(item_text) + 50 > 4096:
                result_text += f"\n\n📊 Jami: <b>{len(user_posts)}</b> ta post"
                await message.answer(result_text, parse_mode="HTML")
                result_text = get_text('mycodes_msg', lang)
            
            result_text += item_text
            count += 1

        result_text += f"\n\n📊 Jami: <b>{len(user_posts)}</b> ta post"
        await message.answer(result_text, parse_mode="HTML")


@start_router.callback_query(F.data == "check_subscription_again")
async def check_subscription_again(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    is_member, text, keyboard = await check_user_membership(callback.from_user, bot)
    lang = await get_user_language(callback.from_user.id)

    if is_member:
        await callback.answer()
        await show_main_menu(callback, state, bot)
    else:
        await callback.answer(get_text('join_alert_msg', lang), show_alert=True)


@start_router.callback_query(F.data == "create_post", StateFilter(None))
@start_router.message(LocalizedText('new_post_btn'), StateFilter(None))
async def start_post_creation(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot):
    user = event.from_user
    is_member, text, keyboard = await check_user_membership(user, bot)
    
    if isinstance(event, types.CallbackQuery):
        await event.answer()
        if not is_member:
            await event.message.answer(text, reply_markup=keyboard)
            return
    else:
        if not is_member:
            remover_message = await event.answer(".", reply_markup=ReplyKeyboardRemove())
            await remover_message.delete()
            await event.answer(text, reply_markup=keyboard)
            return

    await state.clear()
    lang = await get_user_language(user.id)
    
    user_settings = await get_user_post_settings(user.id)
    ai_assistant_enabled = user_settings.get('ai_assistant_enabled', False)
    
    content_text = get_text('content_msg', lang)
    if ai_assistant_enabled:
        content_text += get_text('ai_assistant_hint_msg', lang)

    if isinstance(event, types.CallbackQuery):
        content_message = await event.message.answer(content_text, reply_markup=get_cancel_reply_kb(lang, ai_assistant_enabled))
    else:
        content_message = await event.answer(content_text, reply_markup=get_cancel_reply_kb(lang, ai_assistant_enabled))

    await state.update_data(content_message_id=content_message.message_id)

    await state.set_state(PostCreation.waiting_for_content)


@start_router.callback_query(F.data == "edit_post", StateFilter(None))
@start_router.message(LocalizedText('edit_post_btn'), StateFilter(None))
async def start_post_editing_process(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot):
    user = event.from_user
    lang = await get_user_language(user.id)
    
    # Tahrirlash bo'limi vaqtinchalik o'chirilgan
    disabled_text = "⏳ <b>Tahrirlash bo'limi vaqtinchalik o'chirilgan</b>\n\nKuting, tez orada qayta ishga tushadi!"
    
    if isinstance(event, types.CallbackQuery):
        await event.answer()
        await event.message.answer(disabled_text, parse_mode="HTML")
    else:
        await event.answer(disabled_text, parse_mode="HTML")


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
    LocalizedText('cancel_btn')
)
async def cancel_action(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    await cmd_start(message, state, bot)