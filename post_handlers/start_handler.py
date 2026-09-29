import html
import logging

from aiogram import F, Router, types, Bot
from aiogram.filters import CommandStart, Command, StateFilter, CommandObject
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
from post_handlers.custom_emojis import EMOJI_SAVE, EMOJI_ADD_CHANNEL, EMOJI_CLOSE, clean_btn_text

start_router = Router()
logger = logging.getLogger(__name__)

async def check_user_has_language(user_id: int) -> bool:
    """Foydalanuvchi til tanlaganligini tekshiradi"""
    user_info = await get_user_info_from_db(user_id)
    if user_info and user_info.get('language'):
        return True
    return False

async def show_language_selection(event: types.Message | types.CallbackQuery):
    """Yangi foydalanuvchilar uchun til tanlash menyusi"""
    from post_handlers.lang_handler import get_language_keyboard
    keyboard = get_language_keyboard()
    text = "🌐 Iltimos, o'z tilingizni tanlang:\nПожалуйста, выберите ваш язык:\nPlease select your language:"
    if isinstance(event, types.CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await event.message.answer(text, reply_markup=keyboard)
    else:
        await event.answer(text, reply_markup=keyboard)

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
            await event.message.edit_text(start_text, reply_markup=main_menu_keyboard)
        except Exception:
            await event.message.answer(start_text, reply_markup=main_menu_keyboard)

@start_router.message(CommandStart(), StateFilter("*"), F.forward_from.is_(None))
async def cmd_start(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot, command: CommandObject = None):
    user = event.from_user

    from xdata_handlers.database import get_user_language
    
    current_lang = await get_user_language(user.id)
    if not current_lang:
        await show_language_selection(event)
        return

    is_member, text, keyboard = await check_user_membership(event.from_user, bot)

    if not is_member:
        if isinstance(event, types.Message):
            await event.answer(text, reply_markup=keyboard)
        elif isinstance(event, types.CallbackQuery):
            await event.message.answer(text, reply_markup=keyboard)
            try:
                await event.message.delete()
            except Exception:
                pass
        return

    # Check for bundle share deep link: /start bnd_<owner_id>_<bundle_id>
    if command and command.args and command.args.startswith("bnd_"):
        parts = command.args.split("_", 2)
        if len(parts) >= 3:
            try:
                owner_id = int(parts[1])
                bundle_id = parts[2]
                from xdata_handlers.database import get_user_channel_bundles, get_user_channels
                owner_bundles = await get_user_channel_bundles(owner_id)
                bundle = next((b for b in owner_bundles if b.get('id') == bundle_id), None)
                if bundle:
                    owner_channels = await get_user_channels(owner_id)
                    ch_map = {ch['channel_id']: ch['channel_name'] for ch in owner_channels}
                    channel_lines = [f"• {html.escape(ch_map.get(cid, str(cid)))}" for cid in bundle.get('channel_ids', [])]
                    channel_list_str = "\n".join(channel_lines) if channel_lines else get_text('bundle_no_channels_yet', current_lang)

                    import_text = get_text('bundle_shared_import_prompt', current_lang).format(
                        bundle_name=html.escape(bundle.get('name', "To'plam")),
                        count=len(bundle.get('channel_ids', [])),
                        channel_list=channel_list_str
                    )

                    builder = InlineKeyboardBuilder()
                    builder.button(
                        text=clean_btn_text(get_text('bundle_import_save_btn', current_lang)),
                        callback_data=f"bundle:import:{owner_id}:{bundle_id}",
                        icon_custom_emoji_id=EMOJI_SAVE
                    )
                    builder.button(
                        text=get_text('cancel_btn', current_lang),
                        callback_data="cancel_action"
                    )
                    builder.adjust(1)
                    await event.answer(import_text, reply_markup=builder.as_markup(), parse_mode="HTML")
                    return
            except Exception as e:
                logger.error(f"Error handling shared bundle deep link: {e}")

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


@start_router.callback_query(F.data == "check_subscription_again")
async def check_subscription_again(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    is_member, text, keyboard = await check_user_membership(callback.from_user, bot)
    lang = await get_user_language(callback.from_user.id)

    if is_member:
        await callback.answer()
        await show_main_menu(callback, state, bot)
    else:
        await callback.answer(get_text('join_alert_msg', lang), show_alert=True)

EMOJI_ID_CIRC_EMPTY = "5321100107603556331"
EMOJI_ID_CIRC_CHECK = "5321505741494856875"
EMOJI_ID_SQ_EMPTY = "5321564346323610109"
EMOJI_ID_SQ_CHECK = "5321513296342328913"

def get_turbo_mode_inline_kb(lang: str = 'uzl', is_enabled: bool = False, action: str = 'now'):
    """
    Turbo rejim inline klaviaturasi (Premium Custom Emojilar bilan).
    Matn o'zgarmaydi, faqat oldidagi emoji yangilanadi:
    O'chiq holatda:
    [ ⚪ ⚡ Turbo rejim ]
    [ ❌ Bekor qilish ]
    
    Yoqilgan holatda:
    [ 🟡 ⚡ Turbo rejim ]
    [ 🟡 🚀 Hozir chop etish ] [ ⚪ ⏰ Jadval bo'yicha ] (action='now' bo'lganda)
    [ ❌ Bekor qilish ]
    """
    builder = InlineKeyboardBuilder()
    cancel_text = get_text('cancel_btn', lang)
    turbo_text = get_text('turbo_mode_btn', lang)
    
    if not is_enabled:
        builder.button(
            text=turbo_text, 
            callback_data="turbo:toggle", 
            icon_custom_emoji_id=EMOJI_ID_SQ_EMPTY
        )
        builder.button(text=cancel_text, callback_data="cancel_action")
        builder.adjust(1, 1)
    else:
        builder.button(
            text=turbo_text, 
            callback_data="turbo:toggle", 
            icon_custom_emoji_id=EMOJI_ID_SQ_CHECK
        )
        
        now_icon = EMOJI_ID_CIRC_CHECK if action == 'now' else EMOJI_ID_CIRC_EMPTY
        schedule_icon = EMOJI_ID_CIRC_CHECK if action == 'schedule' else EMOJI_ID_CIRC_EMPTY
        
        now_text = get_text('turbo_now_btn', lang)
        schedule_text = get_text('turbo_schedule_btn', lang)
            
        builder.button(text=now_text, callback_data="turbo:action:now", icon_custom_emoji_id=now_icon)
        builder.button(text=schedule_text, callback_data="turbo:action:schedule", icon_custom_emoji_id=schedule_icon)
        builder.button(text=cancel_text, callback_data="cancel_action")
        builder.adjust(1, 2, 1)
        
    return builder.as_markup()

@start_router.message(LocalizedText('new_post_btn'))
@start_router.message(LocalizedText('cr_another_post_btn'))
@start_router.callback_query(F.data == "main:new_post")
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
            await event.answer(text, reply_markup=keyboard)
            return

    # Faqat yangi post yaratish jarayonida state ni tozalash
    current_state = await state.get_state()
    if current_state is None:
        await state.clear()
    
    lang = await get_user_language(user.id)

    # Foydalanuvchida ulangan kanallar bor-yo'qligini tekshirish
    from xdata_handlers.database import get_user_channels
    user_channels = await get_user_channels(user.id)
    if not user_channels:
        await state.clear()
        need_channel_text = get_text('need_channel_msg', lang)

        builder = InlineKeyboardBuilder()
        builder.button(
            text=clean_btn_text(get_text('add_new_channel_btn', lang)),
            callback_data="post:add_channel",
            icon_custom_emoji_id=EMOJI_ADD_CHANNEL
        )
        builder.button(
            text=clean_btn_text(get_text('cancel_btn', lang)),
            callback_data="cancel_action",
            icon_custom_emoji_id=EMOJI_CLOSE
        )
        builder.adjust(1, 1)
        
        target_msg = event.message if isinstance(event, types.CallbackQuery) else event
        await target_msg.answer(need_channel_text, reply_markup=builder.as_markup(), parse_mode="HTML")
        return

    user_settings = await get_user_post_settings(user.id)
    ai_assistant_enabled = user_settings.get('ai_assistant_enabled', False)

    content_text = get_text('content_msg', lang)
    if ai_assistant_enabled:
        content_text += get_text('ai_assistant_hint_msg', lang)

    # Inline Turbo rejim tugmasi bilan kontent so'rash xabari
    turbo_kb = get_turbo_mode_inline_kb(lang, is_enabled=False, action='now')
    target_msg = event.message if isinstance(event, types.CallbackQuery) else event
    content_message = await target_msg.answer(content_text, reply_markup=turbo_kb)

    await state.update_data(
        content_message_id=content_message.message_id,
        turbo_enabled=False,
        turbo_action='now'
    )

    await state.set_state(PostCreation.waiting_for_content)

@start_router.callback_query(F.data == "post:add_channel")
async def handle_post_add_channel(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await get_user_language(callback.from_user.id)
    from post_handlers.send_handler import PostSending
    await state.clear()
    await state.set_state(PostSending.waiting_for_channel_info)
    await state.update_data(from_post_creation=True)

    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('cancel_btn', lang), callback_data="cancel_action")

    add_channel_text = get_text('add_channel_msg', lang)
    try:
        await callback.message.edit_text(add_channel_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(add_channel_text, reply_markup=builder.as_markup(), parse_mode="HTML")

@start_router.callback_query(F.data == "turbo:toggle")
async def handle_turbo_toggle(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    turbo_enabled = not data.get('turbo_enabled', False)
    turbo_action = data.get('turbo_action', 'now')
    lang = await get_user_language(callback.from_user.id)

    await state.set_state(PostCreation.waiting_for_content)
    await state.update_data(turbo_enabled=turbo_enabled, turbo_action=turbo_action)
    
    new_kb = get_turbo_mode_inline_kb(lang, is_enabled=turbo_enabled, action=turbo_action)
    try:
        await callback.message.edit_reply_markup(reply_markup=new_kb)
    except Exception:
        pass

    await callback.answer()

@start_router.callback_query(F.data.startswith("turbo:action:"))
async def handle_turbo_action_change(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[2]  # 'now' or 'schedule'
    data = await state.get_data()
    current_action = data.get('turbo_action', 'now')
    turbo_enabled = data.get('turbo_enabled', False)
    lang = await get_user_language(callback.from_user.id)

    # Agar tugma allaqachon faol bo'lsa va ustiga bosilsa
    if turbo_enabled and current_action == action:
        alert_key = 'turbo_already_active_now' if action == 'now' else 'turbo_already_active_schedule'
        await callback.answer(get_text(alert_key, lang), show_alert=True)
        return

    await state.set_state(PostCreation.waiting_for_content)
    await state.update_data(turbo_action=action, turbo_enabled=True)
    
    new_kb = get_turbo_mode_inline_kb(lang, is_enabled=True, action=action)
    try:
        await callback.message.edit_reply_markup(reply_markup=new_kb)
    except Exception:
        pass

    await callback.answer()

@start_router.message(LocalizedText('edit_post_btn'))
@start_router.callback_query(F.data == "main:edit_post")
async def start_post_editing_process(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot):
    user = event.from_user
    lang = await get_user_language(user.id)

    # State ni tozalash va tahrirlash kodi kutilayotgan holatga o'tkazish
    await state.clear()
    await state.set_state(PostCreation.waiting_for_edit_code)

    # Foydalanuvchining postlarini olish
    user_posts = await get_posts_by_user(user.id)
    
    prompt_text = get_text('edit_section_prompt', lang)
    
    # Inline klaviatura yaratish
    builder = InlineKeyboardBuilder()
    
    if user_posts:
        prompt_text += f"\n\n{get_text('mycodes_header', lang)}"
        for post in user_posts[:10]:  # Maksimal 10 ta postni ko'rsatish
            post_name = post.get('name') or post.get('post_name') or f"Post {post.get('code')}"
            builder.button(
                text=f"📝 {post_name}",
                callback_data=f"edit_select:{post.get('code')}"
            )
        
    builder.button(
        text=clean_btn_text(get_text('cancel_btn', lang)),
        callback_data="cancel_action",
        icon_custom_emoji_id=EMOJI_CLOSE
    )
    builder.adjust(1)

    if isinstance(event, types.CallbackQuery):
        await event.answer()
    target_msg = event.message if isinstance(event, types.CallbackQuery) else event
    await target_msg.answer(prompt_text, parse_mode="HTML", reply_markup=builder.as_markup())

@start_router.message(LocalizedText('statistic_btn'))
@start_router.callback_query(F.data == "main:statistic")
async def handle_statistics_button(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot):
    """Statistika tugmasi bosilganda statistika sahifasini ko'rsatadi"""
    from post_handlers.statistic_handler import handle_generate_statistics
    if isinstance(event, types.CallbackQuery):
        await event.answer()
    await handle_generate_statistics(event, state, bot)

@start_router.message(LocalizedText('schedule_list_btn'))
@start_router.callback_query(F.data == "main:schedule_list")
async def handle_schedule_list_button(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot):
    """Jadval tugmasi: rejalashtirilgan postlar ro'yxatini ko'rsatadi"""
    from post_handlers.schedule_handler import show_scheduled_posts_for_message
    if isinstance(event, types.CallbackQuery):
        await event.answer()
    await show_scheduled_posts_for_message(event, state, bot)

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
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(text, reply_markup=keyboard)
            return

        await show_main_menu(callback, state, bot)

    except Exception:
        await callback.answer("Xatolik yuz berdi. Qayta urinib ko'ring.")

@start_router.message(StateFilter(None), F.text & ~F.text.startswith('/'))
async def handle_unknown_message(event: types.Message, state: FSMContext, bot: Bot):
    """Foydalanuvchi hech qanday holatda bo'lmaganda xabar yuborsa, asosiy menyuni ko'rsatadi"""
    user = event.from_user
    
    has_language = await check_user_has_language(user.id)
    
    if not has_language:
        await show_language_selection(event)
        return
    
    is_member, text, keyboard = await check_user_membership(user, bot)
    
    if not is_member:
        await event.answer(text, reply_markup=keyboard)
        return
    
    await show_main_menu(event, state, bot)


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
        PostCreation.waiting_for_paid_price,
        "BundleCreation:waiting_for_name",
        "BundleCreation:selecting_channels",
        "BundleCreation:editing_channels",
        "BundleCreation:waiting_for_rename"
    ),
    LocalizedText('cancel_btn')
)
@start_router.callback_query(F.data == "cancel_action")
async def cancel_action(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot):
    if isinstance(event, types.CallbackQuery):
        await event.answer()
    await state.clear()
    await show_main_menu(event, state, bot)

@start_router.message(F.text.in_([
    "❌ Turbo rejimdan chiqish",
    "❌ Турбо режимдан чиқиш",
    "❌ Выйти из турбо режима",
    "❌ Exit Turbo mode",
    "🏠 Bosh menyu",
    "🏠 Бош меню",
    "🏠 Главное меню",
    "🏠 Main menu",
    "Bosh menyu",
    "Бош меню",
    "Главное меню",
    "Main menu"
]))
async def handle_exit_turbo_mode(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    lang = await get_user_language(message.from_user.id)
    exit_text = get_text('exit_turbo_mode_msg', lang)
    await message.answer(exit_text)
    await show_main_menu(message, state, bot)