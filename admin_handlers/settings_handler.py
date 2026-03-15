from aiogram import F, Router, types, Bot
from aiogram.types import ReplyKeyboardRemove, BotCommand, BotCommandScopeDefault, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats, BotCommandScopeAllChatAdministrators
from aiogram.filters import Filter, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
import logging

logger = logging.getLogger(__name__)

from xdata_handlers import config
from aiogram.utils.keyboard import InlineKeyboardBuilder
from admin_handlers.xinline_keyboard import (
    get_settings_menu_keyboard, get_back_to_main_orqaga_keyboard, 
    get_main_admin_keyboard, get_language_selection_keyboard,
    get_no_commands_keyboard, get_commands_input_nav_keyboard
)

settings_router = Router()


class IsAdmin(Filter):
    async def __call__(self, message_or_callback: types.Message | types.CallbackQuery) -> bool:
        return message_or_callback.from_user.id in config.ADMIN_IDS

class SettingsStates(StatesGroup):
    waiting_for_bot_commands = State()
    waiting_for_bot_bio = State()
    waiting_for_bot_desc = State()
    waiting_for_bot_name = State()
@settings_router.callback_query(F.data == "admin:settings_main_menu", IsAdmin())
async def settings_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    """Sozlamalar bo'limini ko'rsatish."""
    await state.clear()
    try:
        await callback.message.edit_text(
            "⚙️ Sozlamalar bo'limi. Kerakli funksiyani tanlang:",
            reply_markup=get_settings_menu_keyboard()
        )
    except:
        await callback.message.delete()
        await callback.message.answer(
            "⚙️ Sozlamalar bo'limi. Kerakli funksiyani tanlang:",
            reply_markup=get_settings_menu_keyboard()
        )
    await callback.answer()

@settings_router.callback_query(F.data == "admin:bot_commands_lang_select", IsAdmin())
async def bot_commands_lang_select_handler(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot):
    """Buyruqlarni o'zgartirish uchun til tanlash sahifasini ko'rsatish."""
    await state.clear()
    
    # Global buyruqlar bormi yoki yo'qligini tekshiramiz
    global_commands = await bot.get_my_commands(scope=BotCommandScopeDefault())
    
    msg_text_no = (
        "⚠️ <b>Botda hech qanday buyruqlar mavjud emas!</b>\n\n"
        "Botning menyu tugmasi ko'rinishi uchun iltimos buyruq kiriting."
    )
    
    msg_text_select = (
        "🌍 Qaysi til uchun bot buyruqlarini o'rnatmoqchisiz? Tanlang:\n\n"
        "<i>Eslatma: 'Barchasi' orqali o'rnatilgan buyruqlar boshqa tillar uchun standart bo'lib xizmat qiladi.</i>"
    )

    if not global_commands:
        # Bu birinchi marta o'rnatilayotganini belgilab qo'yamiz
        await state.update_data(is_initial_setup=True)
        if isinstance(event, types.CallbackQuery):
            await event.message.edit_text(msg_text_no, reply_markup=get_no_commands_keyboard(), parse_mode="HTML")
            await event.answer()
        else:
            await event.answer(msg_text_no, reply_markup=get_no_commands_keyboard(), parse_mode="HTML")
        return

    try:
        if isinstance(event, types.CallbackQuery):
            await event.message.edit_text(msg_text_select, reply_markup=get_language_selection_keyboard(has_global=True), parse_mode="HTML")
            await event.answer()
        else:
            await event.answer(msg_text_select, reply_markup=get_language_selection_keyboard(has_global=True), parse_mode="HTML")
    except:
        if isinstance(event, types.CallbackQuery):
            await event.message.answer(msg_text_select, reply_markup=get_language_selection_keyboard(has_global=True))
        else:
            await event.answer(msg_text_select, reply_markup=get_language_selection_keyboard(has_global=True))

@settings_router.callback_query(F.data.startswith("admin:bot_commands_start:"), IsAdmin())
async def bot_commands_start_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Bot buyruqlarini o'zgartirishni boshlash (til bo'yicha)."""
    lang_code = callback.data.split(':')[-1]
    await state.update_data(lang_code=lang_code)
    await state.set_state(SettingsStates.waiting_for_bot_commands)
    
    # Telegram API uchun language_code
    tg_lang_code = None if lang_code == "all" else lang_code
    if tg_lang_code and tg_lang_code in ['uzl', 'uzk']:
        tg_lang_code = 'uz'
    elif tg_lang_code:
        tg_lang_code = tg_lang_code[:2]

    display_lang = "BARCHASI (Default)" if lang_code == "all" else lang_code.upper()
    
    msg_text = (
        f"📝 <b>Bot uchun buyruqlar ro'yxatini yuboring" + (f" ({display_lang})" if lang_code != "all" else "") + " :</b>\n\n"
        "<code>buyruq1 - Tavsif</code>\n"
        "<code>buyruq2 - Boshqa tavsif</code>\n\n"
        "Roʻyxatni boʻsh qoldirish uchun /empty ni yuboring"
    )
    
    try:
        await callback.message.edit_text(msg_text, reply_markup=get_commands_input_nav_keyboard(), parse_mode="HTML")
    except:
        await callback.message.answer(msg_text, reply_markup=get_commands_input_nav_keyboard(), parse_mode="HTML")
    
    await callback.answer()

@settings_router.message(SettingsStates.waiting_for_bot_commands, IsAdmin())
async def bot_commands_handler(message: types.Message, state: FSMContext, bot: Bot):
    """Bot buyruqlarini yangilash."""
    from aiogram import Bot
    
    commands_text = message.text.strip()
    
    if not commands_text:
        await message.answer("❌ Xatolik! Buyruqlar matni bo'sh bo'lmasligi kerak.")
        return
    
    try:
        # Parse commands from text
        commands_list = []
        if commands_text != "/empty":
            lines = commands_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                parts = line.split('-', 1)
                if len(parts) == 2:
                    command = parts[0].strip().replace('/', '')
                    description = parts[1].strip()
                    if command and description:
                        commands_list.append(BotCommand(command=command, description=description))
                elif len(parts) == 1 and parts[0].strip():
                    command = parts[0].strip().replace('/', '')
                    if command:
                        # Tavsif berilmasa buyruq nomini tavsif sifatida ishlatamiz
                        commands_list.append(BotCommand(command=command, description=command))
            
            if not commands_list:
                await message.answer("❌ Xatolik! Hech qanday buyruq topilmadi. Iltimos, buyruqlarni to'g'ri formatda yozing.")
                return
        
        # Set the commands for various scopes to ensure they show up everywhere
        state_data = await state.get_data()
        lang_code = state_data.get('lang_code', None)
        is_initial_setup = state_data.get('is_initial_setup', False)
        
        tg_lang_codes = []
        is_empty_cmd = (commands_text == "/empty")

        if is_initial_setup or (lang_code == "all" and is_empty_cmd):
            # Butunlay o'chirish yoki birinchi marta o'rnatish - hamma tilni qamrab olamiz
            import os
            from xdata_handlers.translator import BASE_DIR
            locales_dir = os.path.join(BASE_DIR, "language_packs")
            tg_lang_codes = [None] # Default scope
            if os.path.exists(locales_dir):
                for file in os.listdir(locales_dir):
                    if file.endswith(".json"):
                        l_code = file[:-5]
                        l_code = 'uz' if l_code in ['uzl', 'uzk'] else l_code[:2]
                        if l_code not in tg_lang_codes:
                            tg_lang_codes.append(l_code)
        elif lang_code == "all":
            # Standart (Default) ni tanlaganda faqat default scope uchun
            tg_lang_codes = [None]
        else:
            # Muayyan til uchun (Masalan: UZ)
            tg_l = 'uz' if lang_code in ['uzl', 'uzk'] else lang_code[:2]
            tg_lang_codes = [tg_l]
        
        for code in tg_lang_codes:
            try:
                await bot.set_my_commands(commands_list, scope=BotCommandScopeDefault(), language_code=code)
                await bot.set_my_commands(commands_list, scope=BotCommandScopeAllPrivateChats(), language_code=code)
                await bot.set_my_commands(commands_list, scope=BotCommandScopeAllGroupChats(), language_code=code)
                await bot.set_my_commands(commands_list, scope=BotCommandScopeAllChatAdministrators(), language_code=code)
            except Exception as e:
                logger.warning(f"Failed to set commands for language {code}: {e}")
        
        await message.answer(f"✅ Buyruqlar muvaffaqiyatli o'zgartirildi!")
        
        # O'zgartirishdan so'ng holatni tozalaymiz
        await state.clear()
        return await bot_commands_lang_select_handler(message, state, bot)
        
    except Exception as e:
        logger.error(f"Error setting bot commands: {e}")
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
        await state.clear()
        await message.answer("Sozlamalar bo'limiga qaytildi.", reply_markup=ReplyKeyboardRemove())
        await message.answer("⚙️ Sozlamalar bo'limi. Kerakli funksiyani tanlang:", reply_markup=get_settings_menu_keyboard())

# --- BIO (TARJIMAI HOL) HANDLERS ---

@settings_router.callback_query(F.data == "admin:bot_bio_lang_select", IsAdmin())
async def bot_bio_lang_select_handler(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot):
    """Tarjimai hol uchun til tanlash."""
    await state.clear()
    global_bio = await bot.get_my_short_description()
    
    msg_no = "⚠️ <b>Botda hali tarjimai hol (Bio) mavjud emas!</b>\n\nIltimos, avval standart tarjimai holni kiriting."
    msg_select = "🌍 Qaysi til uchun <b>Tarjimai hol (Bio)</b> o'rnatmoqchisiz?"

    if not global_bio or not global_bio.short_description:
        await state.update_data(is_initial_setup=True)
        keyboard = get_no_commands_keyboard(mode="bio", text="Bio")
        if isinstance(event, types.CallbackQuery):
            await event.message.edit_text(msg_no, reply_markup=keyboard, parse_mode="HTML")
            await event.answer()
        else:
            await event.answer(msg_no, reply_markup=keyboard, parse_mode="HTML")
        return

    keyboard = get_language_selection_keyboard(has_global=True, mode="bio")
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(msg_select, reply_markup=keyboard, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(msg_select, reply_markup=keyboard, parse_mode="HTML")

@settings_router.callback_query(F.data.startswith("admin:bot_bio_start:"), IsAdmin())
async def bot_bio_start_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    lang_code = callback.data.split(':')[-1]
    await state.update_data(lang_code=lang_code)
    await state.set_state(SettingsStates.waiting_for_bot_bio)
    
    tg_lang = None if lang_code == "all" else (lang_code[:2] if lang_code not in ['uzl', 'uzk'] else 'uz')
    current = await bot.get_my_short_description(language_code=tg_lang)
    curr_text = current.short_description if current else "Mavjud emas"
    
    msg = (
        f"👤 <b>Tarjimai holni yuboring ({lang_code.upper()}):</b>\n\n"
        f"Hozirgi: <code>{curr_text}</code>\n\n"
        "O'chirish uchun /empty yuboring."
    )
    await callback.message.edit_text(msg, reply_markup=get_commands_input_nav_keyboard("bio"), parse_mode="HTML")

@settings_router.message(SettingsStates.waiting_for_bot_bio, IsAdmin())
async def bot_bio_handler(message: types.Message, state: FSMContext, bot: Bot):
    text = message.text.strip()
    if not text: return
    if text in ["🏠 Asosiy panel", "🔙 Orqaga"]: return # Skip nav buttons if any
    
    data = await state.get_data()
    lang_code = data.get('lang_code')
    is_initial = data.get('is_initial_setup', False)
    
    if text == "/empty": text = ""
    
    tg_codes = []
    is_empty_bio = (message.text.strip() == "/empty")
    
    if is_initial or (lang_code == "all" and is_empty_bio):
        import os
        from xdata_handlers.translator import BASE_DIR
        tg_codes = [None]
        locales = os.path.join(BASE_DIR, "language_packs")
        if os.path.exists(locales):
            for f in os.listdir(locales):
                if f.endswith(".json"):
                    c = f[:-5]
                    c = 'uz' if c in ['uzl', 'uzk'] else c[:2]
                    if c not in tg_codes: tg_codes.append(c)
    elif lang_code == "all":
        tg_codes = [None]
    else:
        c = 'uz' if lang_code in ['uzl', 'uzk'] else lang_code[:2]
        tg_codes = [c]

    for c in tg_codes:
        try: await bot.set_my_short_description(short_description=text, language_code=c)
        except: pass
        
    await message.answer("✅ Tarjimai hol muvaffaqiyatli o'zgartirildi!")
    await state.clear()
    return await bot_bio_lang_select_handler(message, state, bot)

# --- DESCRIPTION (TAVSIF) HANDLERS ---

@settings_router.callback_query(F.data == "admin:bot_desc_lang_select", IsAdmin())
async def bot_desc_lang_select_handler(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot):
    """Tavsif uchun til tanlash."""
    await state.clear()
    global_desc = await bot.get_my_description()
    
    msg_no = "⚠️ <b>Botda hali tavsif (Description) mavjud emas!</b>\n\nIltimos, avval standart tavsifni kiriting."
    msg_select = "🌍 Qaysi til uchun <b>Tavsif (Description)</b> o'rnatmoqchisiz?"

    if not global_desc or not global_desc.description:
        await state.update_data(is_initial_setup=True)
        keyboard = get_no_commands_keyboard(mode="desc", text="Tavsif")
        if isinstance(event, types.CallbackQuery):
            await event.message.edit_text(msg_no, reply_markup=keyboard, parse_mode="HTML")
            await event.answer()
        else:
            await event.answer(msg_no, reply_markup=keyboard, parse_mode="HTML")
        return

    keyboard = get_language_selection_keyboard(has_global=True, mode="desc")
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(msg_select, reply_markup=keyboard, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(msg_select, reply_markup=keyboard, parse_mode="HTML")

@settings_router.callback_query(F.data.startswith("admin:bot_desc_start:"), IsAdmin())
async def bot_desc_start_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    lang_code = callback.data.split(':')[-1]
    await state.update_data(lang_code=lang_code)
    await state.set_state(SettingsStates.waiting_for_bot_desc)
    
    tg_lang = None if lang_code == "all" else (lang_code[:2] if lang_code not in ['uzl', 'uzk'] else 'uz')
    current = await bot.get_my_description(language_code=tg_lang)
    curr_text = current.description if current else "Mavjud emas"
    
    msg = (
        f"ℹ️ <b>Tavsifni yuboring ({lang_code.upper()}):</b>\n\n"
        f"Hozirgi: <code>{curr_text}</code>\n\n"
        "O'chirish uchun /empty yuboring."
    )
    await callback.message.edit_text(msg, reply_markup=get_commands_input_nav_keyboard("desc"), parse_mode="HTML")

@settings_router.message(SettingsStates.waiting_for_bot_desc, IsAdmin())
async def bot_desc_handler(message: types.Message, state: FSMContext, bot: Bot):
    text = message.text.strip()
    if not text: return
    if text in ["🏠 Asosiy panel", "🔙 Orqaga"]: return

    data = await state.get_data()
    lang_code = data.get('lang_code')
    is_initial = data.get('is_initial_setup', False)
    
    if text == "/empty": text = ""
    
    tg_codes = []
    is_empty_desc = (message.text.strip() == "/empty")

    if is_initial or (lang_code == "all" and is_empty_desc):
        import os
        from xdata_handlers.translator import BASE_DIR
        tg_codes = [None]
        locales = os.path.join(BASE_DIR, "language_packs")
        if os.path.exists(locales):
            for f in os.listdir(locales):
                if f.endswith(".json"):
                    c = f[:-5]
                    c = 'uz' if c in ['uzl', 'uzk'] else c[:2]
                    if c not in tg_codes: tg_codes.append(c)
    elif lang_code == "all":
        tg_codes = [None]
    else:
        c = 'uz' if lang_code in ['uzl', 'uzk'] else lang_code[:2]
        tg_codes = [c]

    for c in tg_codes:
        try: await bot.set_my_description(description=text, language_code=c)
        except: pass
        
    await message.answer("✅ Tavsif muvaffaqiyatli o'zgartirildi!")
    await state.clear()
    return await bot_desc_lang_select_handler(message, state, bot)

# --- NAME (BOT NOMI) HANDLERS ---

@settings_router.callback_query(F.data == "admin:bot_name_lang_select", IsAdmin())
async def bot_name_lang_select_handler(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot):
    """Bot nomi uchun til tanlash."""
    await state.clear()
    global_name = await bot.get_my_name()
    
    msg_select = "🌍 Qaysi til uchun <b>Bot nomini</b> o'rnatmoqchisiz?"

    keyboard = get_language_selection_keyboard(has_global=True, mode="name")
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(msg_select, reply_markup=keyboard, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(msg_select, reply_markup=keyboard, parse_mode="HTML")

@settings_router.callback_query(F.data.startswith("admin:bot_name_start:"), IsAdmin())
async def bot_name_start_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    lang_code = callback.data.split(':')[-1]
    await state.update_data(lang_code=lang_code)
    await state.set_state(SettingsStates.waiting_for_bot_name)
    
    tg_lang = None if lang_code == "all" else (lang_code[:2] if lang_code not in ['uzl', 'uzk'] else 'uz')
    current = await bot.get_my_name(language_code=tg_lang)
    curr_text = current.name if current else "Mavjud emas"
    
    msg = (
        f"🏷 <b>Bot nomini yuboring ({lang_code.upper()}):</b>\n\n"
        f"Hozirgi: <code>{curr_text}</code>\n\n"
        "O'chirish uchun /empty yuboring."
    )
    await callback.message.edit_text(msg, reply_markup=get_commands_input_nav_keyboard("name"), parse_mode="HTML")

@settings_router.message(SettingsStates.waiting_for_bot_name, IsAdmin())
async def bot_name_handler(message: types.Message, state: FSMContext, bot: Bot):
    text = message.text.strip()
    if not text: return
    if text in ["🏠 Asosiy panel", "🔙 Orqaga"]: return

    data = await state.get_data()
    lang_code = data.get('lang_code')
    is_initial = data.get('is_initial_setup', False)
    
    if text == "/empty": text = ""
    
    tg_codes = []
    is_empty_name = (text == "")
    
    if is_initial or (lang_code == "all" and is_empty_name):
        import os
        from xdata_handlers.translator import BASE_DIR
        tg_codes = [None]
        locales = os.path.join(BASE_DIR, "language_packs")
        if os.path.exists(locales):
            for f in os.listdir(locales):
                if f.endswith(".json"):
                    c = f[:-5]
                    c = 'uz' if c in ['uzl', 'uzk'] else c[:2]
                    if c not in tg_codes: tg_codes.append(c)
    elif lang_code == "all":
        tg_codes = [None]
    else:
        c = 'uz' if lang_code in ['uzl', 'uzk'] else lang_code[:2]
        tg_codes = [c]

    for c in tg_codes:
        try: await bot.set_my_name(name=text, language_code=c)
        except: pass
        
    await message.answer("✅ Bot nomi muvaffaqiyatli o'zgartirildi!")
    await state.clear()
    return await bot_name_lang_select_handler(message, state, bot)