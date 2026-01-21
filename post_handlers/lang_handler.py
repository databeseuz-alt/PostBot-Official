#--- START OF FILE lang_handler.py ---

from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder, KeyboardButton

from xdata_handlers.database import set_user_language, get_user_language
from xdata_handlers.translator import get_text
from post_handlers.start_handler import cmd_start
from post_handlers.localize_filter import LocalizedText

lang_router = Router()

#=============================================================================
# TILNI SOZLASH HANDLERLARI
#=============================================================================

@lang_router.message(LocalizedText('btn_language_settings'))
async def language_settings_handler(message: types.Message):
    lang = await get_user_language(message.from_user.id)

    builder = ReplyKeyboardBuilder()
    # Birinchi qator: 5 ta til
    builder.row(
        KeyboardButton(text="🇺🇿 O'zbek"),
        KeyboardButton(text="🇺🇿 Ўзбек"),
        KeyboardButton(text="🇬🇧 English"),
        KeyboardButton(text="🇷🇺 Русский"),
        KeyboardButton(text="🇰🇿 Қазақ")
    )
    # Ikkinchi qator: 5 ta til (shu jumladan yangi qo'shilgan tojik va turkman)
    builder.row(
        KeyboardButton(text="🇦🇿 Azərca"),
        KeyboardButton(text="🇹🇷 Türkçe"),
        KeyboardButton(text="🇰🇬 Кыргыз"),
        KeyboardButton(text="🇹🇯 Тоҷики"),
        KeyboardButton(text="🇹🇲 Türkmen")
    )
    builder.adjust(5, 5)

    await message.answer(
        get_text('choose_language', lang),
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@lang_router.message(F.text.in_({
    "🇺🇿 O'zbek", "🇺🇿 Ўзбек",
    "🇬🇧 English", "🇷🇺 Русский",
    "🇰🇿 Қазақ", "🇦🇿 Azərca",
    "🇹🇷 Türkçe", "🇰🇬 Кыргыз",
    "🇹🇯 Тоҷики", "🇹🇲 Türkmen"
}))
async def set_language_handler(message: types.Message, state: FSMContext, bot: Bot):
    lang_map = {
        "🇺🇿 O'zbek": "uzl",
        "🇺🇿 Ўзбек": "uzk",
        "🇬🇧 English": "en",
        "🇷🇺 Русский": "ru",
        "🇰🇿 Қазақ": "kz",
        "🇦🇿 Azərca": "az",
        "🇹🇷 Türkçe": "tr",
        "🇰🇬 Кыргыз": "kg",
        "🇹🇯 Тоҷики": "tg",
        "🇹🇲 Türkmen": "tk"
    }
    lang_code = lang_map.get(message.text)

    if lang_code:
        await set_user_language(
            user_id=message.from_user.id,
            full_name=message.from_user.full_name,
            username=message.from_user.username,
            lang_code=lang_code
        )
        await message.answer(get_text('lang_changed', lang_code))

    await cmd_start(message, state, bot)

@lang_router.message(LocalizedText('btn_back'))
async def back_to_main_menu(message: types.Message, state: FSMContext, bot: Bot):
    await cmd_start(message, state, bot)

#--- END OF FILE lang_handler.py ---
