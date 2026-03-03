from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder, KeyboardButton, InlineKeyboardBuilder, InlineKeyboardButton

from xdata_handlers.database import set_user_language, get_user_language
from xdata_handlers.translator import get_text
from post_handlers.start_handler import cmd_start
from post_handlers.localize_filter import LocalizedText

from aiogram.filters import Command

lang_router = Router()

@lang_router.message(Command("language"))
async def language_command_handler(message: types.Message):
    """/language buyrug'i uchun handler"""
    lang = await get_user_language(message.from_user.id)

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
        get_text('choose_language', lang),
        reply_markup=builder.as_markup()
    )

@lang_router.message(LocalizedText('btn_language_settings'))
async def language_settings_handler(message: types.Message):
    lang = await get_user_language(message.from_user.id)

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
        get_text('choose_language', lang),
        reply_markup=builder.as_markup()
    )

@lang_router.callback_query(F.data.startswith("lang:"))
async def set_language_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    try:
        parts = callback.data.split(":")
        lang_code = parts[1] if len(parts) > 1 else ""

        await set_user_language(
            user_id=callback.from_user.id,
            nickname=callback.from_user.full_name,
            username=callback.from_user.username,
            language=lang_code
        )

        await callback.answer(get_text('lang_changed', lang_code))

        await callback.message.answer(get_text('lang_changed', lang_code))

        await cmd_start(callback, state, bot)

    except Exception:
        await callback.answer("Xatolik yuz berdi. Qayta urinib ko'ring.")
