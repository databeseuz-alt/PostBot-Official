import html

from aiogram import F, Router, types, Bot
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from admin_handlers.channel_handler import check_user_membership
from xdata_handlers.translator import get_text
from xdata_handlers.database import get_user_language, add_or_update_user, get_posts_by_user, get_user_post_settings, get_user_info_from_db
from post_handlers.xreply_keyboard import get_main_menu, get_cancel_reply_kb
from post_handlers.post_handler import PostCreation
from post_handlers.send_handler import PostSending
from xdata_handlers import config
from post_handlers.localize_filter import LocalizedText

start_router = Router()

async def check_user_has_language(user_id: int) -> bool:
    """Foydalanuvchi til tanlaganligini tekshiradi"""
    user_info = await get_user_info_from_db(user_id)
    if user_info and user_info.get('language'):
        return True
    return False

async def show_language_selection(message: types.Message):
    """Yangi foydalanuvchilar uchun til tanlash menyusi"""
    builder = InlineKeyboardBuilder()
    languages = [
        ("🇺🇿 O'zbek", "lang:uzl"), ("🇺🇿 Ўзбек", "lang:uzk"),
        ("🇹🇯 Tojik", "lang:tj"), ("🇹🇲 Turkman", "lang:tk"),
        ("🇬🇧 English", "lang:en"), ("🇷🇺 Русский", "lang:ru"),
        ("🇰🇿 Қазақ", "lang:kz"), ("🇦🇿 Azərca", "lang:az"),
        ("🇹🇷 Türkçe", "lang:tr"), ("🇰🇬 Кыргыз", "lang:kg"),
        ("🇸🇦 العربية", "lang:ar"), ("🇪🇸 Español", "lang:es"),
        ("🇫🇷 Français", "lang:fr"), ("🇩🇪 Deutsch", "lang:de"),
        ("🇮🇹 Italiano", "lang:it")
    ]

    for text, callback_data in languages:
        builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))

    builder.adjust(2)

    await message.answer(
        "🌐 Iltimos, o'z tilingizni tanlang:\nПожалуйста, выберите ваш язык:\nPlease select your language:",
        reply_markup=builder.as_markup()
    )

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
        await event.answer(start_text, reply_markup=main_menu_keyboard)
    elif isinstance(event, types.CallbackQuery):
        try:
            await event.message.delete()
        except Exception:
            pass
        await event.message.answer(start_text, reply_markup=main_menu_keyboard)

@start_router.message(CommandStart(), StateFilter("*"), F.forward_from.is_(None))
async def cmd_start(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot):
    user = event.from_user

    has_language = await check_user_has_language(user.id)

    if not has_language:
        if isinstance(event, types.Message):
            await show_language_selection(event)
        elif isinstance(event, types.CallbackQuery):
            await show_language_selection(event.message)
        return

    is_member, text, keyboard = await check_user_membership(event.from_user, bot)

    if not is_member:
        if isinstance(event, types.Message):
            remover_message = await event.answer(".", reply_markup=ReplyKeyboardRemove())
            await remover_message.delete()
            await event.answer(text, reply_markup=keyboard)
        elif isinstance(event, types.CallbackQuery):
            await event.message.answer(text, reply_markup=keyboard)
            try:
                await event.message.delete()
            except Exception:
                pass
        return

    await show_main_menu(event, state, bot)

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

@start_router.message(Command("features"))
async def cmd_features(message: types.Message, state: FSMContext):
    """Features bo'limi - vaqtinchalik o'chirilgan."""
    await message.answer(
        "🛠 <b>Features</b> bo'limi vaqtinchalik o'chirilgan.\n\n"
        "⏳ Tez orada ishga tushadi!",
        parse_mode="HTML"
    )

@start_router.callback_query(F.data == "check_subscription_again")
async def check_subscription_again(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    is_member, text, keyboard = await check_user_membership(callback.from_user, bot)
    lang = await get_user_language(callback.from_user.id)

    if is_member:
        await callback.answer()
        await show_main_menu(callback, state, bot)
    else:
        await callback.answer(get_text('join_alert_msg', lang), show_alert=True)

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

@start_router.message(LocalizedText('edit_post_btn'), StateFilter(None))
async def start_post_editing_process(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot):
    user = event.from_user
    lang = await get_user_language(user.id)

    disabled_text = "⏳ <b>Tahrirlash bo'limi vaqtinchalik o'chirilgan</b>\n\nKuting, tez orada qayta ishga tushadi!"

    if isinstance(event, types.CallbackQuery):
        await event.answer()
        await event.message.answer(disabled_text, parse_mode="HTML")
    else:
        await event.answer(disabled_text, parse_mode="HTML")

@start_router.callback_query(F.data.startswith("lang:"))
async def set_language_from_start(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Yangi foydalanuvchi til tanlaganda ishga tushadi"""
    from xdata_handlers.database import set_user_language

    try:
        parts = callback.data.split(":")
        lang_code = parts[1] if len(parts) > 1 else "uzl"

        await set_user_language(
            user_id=callback.from_user.id,
            nickname=callback.from_user.full_name,
            username=callback.from_user.username,
            language=lang_code
        )

        await callback.answer(get_text('lang_changed', lang_code))

        is_member, text, keyboard = await check_user_membership(callback.from_user, bot)

        if not is_member:
            await callback.message.answer(text, reply_markup=keyboard)
            return

        await show_main_menu(callback, state, bot)

    except Exception:
        await callback.answer("Xatolik yuz berdi. Qayta urinib ko'ring.")

@start_router.message(
    StateFilter(
        PostCreation.waiting_for_content,
        PostCreation.waiting_for_edit_code,
        PostCreation.configuring_post,
        PostCreation.waiting_for_button_text,
        PostCreation.waiting_for_button_url,
        PostCreation.waiting_for_post_name,
        PostSending.waiting_for_channel_info,
        PostSending.choosing_channel_to_send,
        PostCreation.waiting_for_media_settings,
        PostCreation.waiting_for_thumbnail,
        PostCreation.waiting_for_paid_price
    ),
    LocalizedText('cancel_btn')
)
async def cancel_action(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    await cmd_start(message, state, bot)