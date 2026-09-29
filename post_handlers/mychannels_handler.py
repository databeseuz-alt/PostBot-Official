import html
import logging

logger = logging.getLogger(__name__)

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from aiogram.fsm.state import State, StatesGroup
from xdata_handlers.database import (
    get_user_channels,
    remove_user_channel,
    get_user_language,
    get_user_channel_bundles,
    get_user_channel_bundle_by_id,
    save_user_channel_bundle,
    delete_user_channel_bundle
)
from post_handlers.send_handler import cmd_add_channel
from xdata_handlers.translator import get_text

mychannels_router = Router()

class BundleCreation(StatesGroup):
    waiting_for_name = State()
    selecting_channels = State()
    editing_channels = State()

class MyChannelsCallback(CallbackData, prefix="my_channels"):
    action: str
    channel_id: int | None = None

from post_handlers.localize_filter import LocalizedText

async def get_my_channels_keyboard(user_id: int):
    """Foydalanuvchi kanallari ro'yxati uchun inline klaviatura yaratadi."""
    builder = InlineKeyboardBuilder()
    user_channels = await get_user_channels(user_id)
    lang = await get_user_language(user_id)

    builder.button(
        text=get_text('add_new_channel_btn', lang),
        callback_data=MyChannelsCallback(action="add_new").pack()
    )
    builder.button(
        text=get_text('bundles_btn', lang),
        callback_data="bundle:list"
    )

    if user_channels:
        for channel in user_channels:
            builder.button(
                text=channel['channel_name'],
                callback_data=MyChannelsCallback(action="select", channel_id=channel['channel_id']).pack()
            )
        builder.button(
            text=get_text('back_btn', lang),
            callback_data="cancel_action"
        )
        ch_count = len(user_channels)
        sizes = [2]
        sizes.extend([2] * (ch_count // 2))
        if ch_count % 2 != 0:
            sizes.append(1)
        sizes.append(1)
        builder.adjust(*sizes)
    else:
        builder.button(
            text=get_text('back_btn', lang),
            callback_data="cancel_action"
        )
        builder.adjust(2, 1)

    return builder.as_markup()

def get_channel_manage_keyboard(channel_id: int, lang: str = 'uzl', can_add_to_bundle: bool = True):
    """Tanlangan kanalni boshqarish uchun inline klaviatura yaratadi."""
    builder = InlineKeyboardBuilder()
    if can_add_to_bundle:
        builder.button(
            text=get_text('add_to_bundle_btn', lang),
            callback_data=f"channel:add_to_bundle:{channel_id}"
        )
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
@mychannels_router.message(LocalizedText('my_channels_btn'))
async def cmd_my_channels(message: types.Message):
    """/mychannels buyrug'iga javob beradi va kanallar ro'yxatini ko'rsatadi."""
    user_id = message.from_user.id
    user_channels = await get_user_channels(user_id)
    lang = await get_user_language(user_id)

    if not user_channels:
        # Agar foydalanuvchi birorta kanal qo'shmagan bo'lsa - klaviatura bilan xabar yuborish
        builder = InlineKeyboardBuilder()
        builder.button(
            text=get_text('add_channel_btn', lang),
            callback_data=MyChannelsCallback(action="add_new").pack()
        )
        builder.button(
            text=get_text('bundles_btn', lang),
            callback_data="bundle:list"
        )
        builder.button(
            text=get_text('back_btn', lang),
            callback_data="cancel_action"
        )
        builder.adjust(2, 1)
        await message.answer(
            get_text('need_channel_msg', lang),
            reply_markup=builder.as_markup()
        )
        return

    keyboard = await get_my_channels_keyboard(user_id)
    await message.answer(
        get_text('choose_channel_msg', lang),
        reply_markup=keyboard
    )

@mychannels_router.callback_query(F.data == "main:my_channels")
async def handle_main_my_channels(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    user_channels = await get_user_channels(user_id)
    lang = await get_user_language(user_id)

    if not user_channels:
        builder = InlineKeyboardBuilder()
        builder.button(
            text=get_text('add_channel_btn', lang),
            callback_data=MyChannelsCallback(action="add_new").pack()
        )
        builder.button(
            text=get_text('bundles_btn', lang),
            callback_data="bundle:list"
        )
        builder.button(
            text=get_text('back_btn', lang),
            callback_data="cancel_action"
        )
        builder.adjust(2, 1)
        try:
            await callback.message.edit_text(
                get_text('need_channel_msg', lang),
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                get_text('need_channel_msg', lang),
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        return

    keyboard = await get_my_channels_keyboard(user_id)
    try:
        await callback.message.edit_text(
            get_text('choose_channel_msg', lang),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            get_text('choose_channel_msg', lang),
            reply_markup=keyboard,
            parse_mode="HTML"
        )

@mychannels_router.callback_query(MyChannelsCallback.filter(F.action == "add_new"))
async def handle_add_new_channel(callback: types.CallbackQuery, state: FSMContext):
    """'Yangi kanal qo'shish' tugmasi bosilganda kanal qo'shish jarayonini boshlaydi."""
    lang = await get_user_language(callback.from_user.id)
    from post_handlers.send_handler import PostSending
    await state.clear()
    await state.set_state(PostSending.waiting_for_channel_info)

    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('cancel_btn', lang), callback_data="cancel_action")

    add_channel_text = get_text('add_channel_msg', lang)
    try:
        await callback.message.edit_text(add_channel_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(add_channel_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@mychannels_router.callback_query(MyChannelsCallback.filter(F.action == "select"))
async def handle_select_channel(callback: types.CallbackQuery, callback_data: MyChannelsCallback):
    """Foydalanuvchi biror kanalni tanlaganda, boshqaruv menyusini ko'rsatadi."""
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    user_channels = await get_user_channels(user_id)
    ch = next((c for c in user_channels if c['channel_id'] == callback_data.channel_id), None)
    channel_name = ch['channel_name'] if ch else "Kanal"
    safe_channel_name = html.escape(channel_name)

    bundles = await get_user_channel_bundles(user_id)
    belonging_bundles = [b for b in bundles if callback_data.channel_id in b.get('channel_ids', [])]

    if belonging_bundles:
        b_names = ", ".join([html.escape(b['name']) for b in belonging_bundles])
        bundle_info = f"\n\n📁 <b>To'plamlar:</b> {b_names}"
    else:
        bundle_info = f"\n\n" + get_text('channel_not_in_any_bundle', lang)

    text = get_text('channel_action_msg', lang).format(channel_name=safe_channel_name) + bundle_info
    reply_markup = get_channel_manage_keyboard(callback_data.channel_id, lang, can_add_to_bundle=True)

    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode="HTML")
    await callback.answer()

@mychannels_router.callback_query(F.data.startswith("channel:add_to_bundle:"))
async def handle_channel_add_to_bundle(callback: types.CallbackQuery):
    """Kanalni biror to'plamga qo'shish."""
    channel_id = int(callback.data.split(":", 2)[2])
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    bundles = await get_user_channel_bundles(user_id)

    if not bundles:
        builder = InlineKeyboardBuilder()
        builder.button(text=get_text('create_bundle_btn', lang), callback_data="bundle:create")
        builder.button(
            text=get_text('back_btn', lang),
            callback_data=MyChannelsCallback(action="select", channel_id=channel_id).pack()
        )
        builder.adjust(1)
        try:
            await callback.message.edit_text(
                get_text('no_bundles_msg', lang),
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                get_text('no_bundles_msg', lang),
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        await callback.answer()
        return

    available_bundles = [b for b in bundles if channel_id not in b.get('channel_ids', [])]

    if not available_bundles:
        await callback.answer(get_text('bundle_channel_already_in_all', lang), show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for b in available_bundles:
        builder.button(
            text=f"📁 {b['name']}",
            callback_data=f"channel:assign_bundle:{channel_id}:{b['id']}"
        )
    builder.button(
        text=get_text('back_btn', lang),
        callback_data=MyChannelsCallback(action="select", channel_id=channel_id).pack()
    )
    builder.adjust(1)

    choose_text = get_text('choose_bundle_to_add', lang)
    try:
        await callback.message.edit_text(choose_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(choose_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@mychannels_router.callback_query(F.data.startswith("channel:assign_bundle:"))
async def handle_channel_assign_bundle(callback: types.CallbackQuery):
    """Kanalni tanlangan to'plamga biriktirish."""
    parts = callback.data.split(":")
    channel_id = int(parts[2])
    bundle_id = parts[3]
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    bundle = await get_user_channel_bundle_by_id(user_id, bundle_id)
    if not bundle:
        await callback.answer(get_text('unknown_error', lang), show_alert=True)
        return

    channel_ids = list(bundle.get('channel_ids', []))
    if channel_id not in channel_ids:
        channel_ids.append(channel_id)
        await save_user_channel_bundle(user_id, bundle['name'], channel_ids, bundle_id=bundle_id)

    user_channels = await get_user_channels(user_id)
    ch = next((c for c in user_channels if c['channel_id'] == channel_id), None)
    ch_name = ch['channel_name'] if ch else "Kanal"

    success_msg = get_text('channel_added_to_bundle_success', lang).format(
        channel_name=html.escape(ch_name),
        bundle_name=html.escape(bundle['name'])
    )
    await callback.answer(get_text('bundle_channels_updated_success', lang))
    await callback.message.answer(success_msg, parse_mode="HTML")

    # Qayta kanal menyusini ko'rsatish
    await handle_select_channel(callback, MyChannelsCallback(action="select", channel_id=channel_id))

@mychannels_router.callback_query(MyChannelsCallback.filter(F.action == "delete"))
async def handle_delete_channel(callback: types.CallbackQuery, callback_data: MyChannelsCallback, state: FSMContext):
    """Kanalni o'chirish tugmasi bosilganda uni bazadan o'chiradi."""
    success = await remove_user_channel(callback.from_user.id, callback_data.channel_id)
    lang = await get_user_language(callback.from_user.id)

    if success:
        await callback.answer()
        try:
            await callback.message.delete()
        except Exception:
            pass

        # 1. Yangi xabarda kanal o'chirildi xabari
        await callback.message.answer(get_text('delete_channel_success_msg', lang), parse_mode="HTML")

        # 2. Ortidan bosh menyuga qaytarish
        await state.clear()
        user = callback.from_user
        from xdata_handlers.database import add_or_update_user
        await add_or_update_user(user_id=user.id, nickname=user.full_name, username=user.username)
        from post_handlers.xreply_keyboard import get_main_menu
        safe_nickname = html.escape(user.full_name)
        start_text = get_text('welcome_msg', lang).format(nickname=safe_nickname)
        main_menu_keyboard = await get_main_menu(lang=lang, user_id=user.id)
        await callback.message.answer(start_text, reply_markup=main_menu_keyboard)
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


# ==================== KANALLAR TO'PLAMI (BUNDLES) ====================

async def get_bundles_list_keyboard(user_id: int, lang: str):
    """Foydalanuvchi to'plamlari ro'yxati klaviaturasi."""
    bundles = await get_user_channel_bundles(user_id)
    builder = InlineKeyboardBuilder()
    if bundles:
        for b in bundles:
            ch_count = len(b.get('channel_ids', []))
            builder.button(
                text=f"📁 {b['name']} ({ch_count})",
                callback_data=f"bundle:view:{b['id']}"
            )
    builder.button(
        text=get_text('create_bundle_btn', lang),
        callback_data="bundle:create"
    )
    builder.button(
        text=get_text('back_btn', lang),
        callback_data="bundle:back_to_channels"
    )
    builder.adjust(1)
    return builder.as_markup()

def get_bundle_channels_keyboard(user_channels: list, selected_ids: set, lang: str):
    """To'plam yaratishda kanallarni tanlash (checkbox) klaviaturasi."""
    builder = InlineKeyboardBuilder()
    for ch in user_channels:
        cid = ch['channel_id']
        is_sel = cid in selected_ids
        mark = "✅" if is_sel else "◻️"
        builder.button(
            text=f"{mark} {ch['channel_name']}",
            callback_data=f"bundle:toggle:{cid}"
        )
    builder.button(
        text=get_text('save_bundle_btn', lang),
        callback_data="bundle:save"
    )
    builder.button(
        text=get_text('cancel_btn', lang),
        callback_data="bundle:cancel"
    )
    sizes = [1] * len(user_channels) + [2]
    builder.adjust(*sizes)
    return builder.as_markup()

@mychannels_router.callback_query(F.data == "bundle:list")
async def handle_bundle_list(callback: types.CallbackQuery, state: FSMContext):
    """To'plamlar ro'yxatini ko'rsatadi."""
    await state.clear()
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    bundles = await get_user_channel_bundles(user_id)

    text = get_text('bundles_title', lang) if bundles else get_text('no_bundles_msg', lang)
    kb = await get_bundles_list_keyboard(user_id, lang)

    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@mychannels_router.callback_query(F.data == "bundle:back_to_channels")
async def handle_bundle_back_to_channels(callback: types.CallbackQuery, state: FSMContext):
    """To'plamlar menyusidan kanallar ro'yxatiga qaytish."""
    await state.clear()
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    keyboard = await get_my_channels_keyboard(user_id)
    try:
        await callback.message.edit_text(get_text('choose_channel_msg', lang), reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(get_text('choose_channel_msg', lang), reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

def get_bundle_channels_edit_keyboard(user_channels: list, selected_ids: set, bundle_id: str, lang: str):
    """To'plamdagi kanallarni tahrirlash/qo'shish klaviaturasi."""
    builder = InlineKeyboardBuilder()
    for ch in user_channels:
        cid = ch['channel_id']
        is_sel = cid in selected_ids
        mark = "✅" if is_sel else "◻️"
        builder.button(
            text=f"{mark} {ch['channel_name']}",
            callback_data=f"bundle:toggle_edit:{bundle_id}:{cid}"
        )
    builder.button(
        text=get_text('save_bundle_btn', lang),
        callback_data=f"bundle:save_edited:{bundle_id}"
    )
    builder.button(
        text=get_text('back_btn', lang),
        callback_data=f"bundle:view:{bundle_id}"
    )
    sizes = [1] * len(user_channels) + [2]
    builder.adjust(*sizes)
    return builder.as_markup()

@mychannels_router.callback_query(F.data.startswith("bundle:view:"))
async def handle_bundle_view(callback: types.CallbackQuery, state: FSMContext = None):
    """To'plam tafsilotlarini ko'rsatish."""
    if state:
        await state.clear()
    bundle_id = callback.data.split(":", 2)[2]
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    bundle = await get_user_channel_bundle_by_id(user_id, bundle_id)

    if not bundle:
        await callback.answer(get_text('unknown_error', lang), show_alert=True)
        return

    user_channels = await get_user_channels(user_id)
    ch_map = {ch['channel_id']: ch['channel_name'] for ch in user_channels}
    channel_lines = [f"• {html.escape(ch_map.get(cid, str(cid)))}" for cid in bundle.get('channel_ids', [])]
    channel_list_str = "\n".join(channel_lines) if channel_lines else get_text('bundle_no_channels_yet', lang)

    text = get_text('bundle_details', lang).format(
        bundle_name=html.escape(bundle.get('name', '')),
        count=len(bundle.get('channel_ids', [])),
        channel_list=channel_list_str
    )

    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text('add_channels_to_bundle_btn', lang),
        callback_data=f"bundle:edit_channels:{bundle_id}"
    )
    builder.button(
        text=get_text('delete_bundle_btn', lang),
        callback_data=f"bundle:delete:{bundle_id}"
    )
    builder.button(
        text=get_text('back_btn', lang),
        callback_data="bundle:list"
    )
    builder.adjust(1)

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@mychannels_router.callback_query(F.data.startswith("bundle:edit_channels:"))
async def handle_bundle_edit_channels(callback: types.CallbackQuery, state: FSMContext):
    """To'plam ichida mavjud kanallarni qo'shish/tahrirlash."""
    bundle_id = callback.data.split(":", 2)[2]
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    user_channels = await get_user_channels(user_id)

    if not user_channels:
        await callback.answer(get_text('need_channel_msg', lang), show_alert=True)
        return

    bundle = await get_user_channel_bundle_by_id(user_id, bundle_id)
    if not bundle:
        await callback.answer(get_text('unknown_error', lang), show_alert=True)
        return

    selected_ids = list(bundle.get('channel_ids', []))
    await state.set_state(BundleCreation.editing_channels)
    await state.update_data(
        editing_bundle_id=bundle_id,
        editing_bundle_name=bundle.get('name', "To'plam"),
        selected_channel_ids=selected_ids
    )

    kb = get_bundle_channels_edit_keyboard(user_channels, set(selected_ids), bundle_id, lang)
    prompt_text = get_text('bundle_select_channels', lang).format(bundle_name=html.escape(bundle.get('name', '')))

    try:
        await callback.message.edit_text(prompt_text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(prompt_text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@mychannels_router.callback_query(BundleCreation.editing_channels, F.data.startswith("bundle:toggle_edit:"))
async def handle_bundle_toggle_edit(callback: types.CallbackQuery, state: FSMContext):
    """To'plamni tahrirlashda kanalni tanlash yoki bekor qilish."""
    parts = callback.data.split(":")
    bundle_id = parts[2]
    channel_id = int(parts[3])

    data = await state.get_data()
    selected_set = set(data.get('selected_channel_ids', []))

    if channel_id in selected_set:
        selected_set.remove(channel_id)
    else:
        selected_set.add(channel_id)

    await state.update_data(selected_channel_ids=list(selected_set))
    user_channels = await get_user_channels(callback.from_user.id)
    lang = await get_user_language(callback.from_user.id)

    kb = get_bundle_channels_edit_keyboard(user_channels, selected_set, bundle_id, lang)
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass
    await callback.answer()

@mychannels_router.callback_query(BundleCreation.editing_channels, F.data.startswith("bundle:save_edited:"))
async def handle_bundle_save_edited(callback: types.CallbackQuery, state: FSMContext):
    """To'plam kanallarini yangilab saqlash."""
    bundle_id = callback.data.split(":", 2)[2]
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    data = await state.get_data()
    selected = data.get('selected_channel_ids', [])
    bundle_name = data.get('editing_bundle_name', "To'plam")

    await save_user_channel_bundle(user_id, bundle_name, selected, bundle_id=bundle_id)
    await state.clear()
    await callback.answer(get_text('bundle_channels_updated_success', lang))

    # Return to bundle view
    callback.data = f"bundle:view:{bundle_id}"
    await handle_bundle_view(callback, state)

@mychannels_router.callback_query(F.data.startswith("bundle:delete:"))
async def handle_bundle_delete(callback: types.CallbackQuery):
    """To'plamni o'chirish."""
    bundle_id = callback.data.split(":", 2)[2]
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await delete_user_channel_bundle(user_id, bundle_id)
    await callback.answer(get_text('bundle_deleted_success', lang))

    bundles = await get_user_channel_bundles(user_id)
    text = get_text('bundles_title', lang) if bundles else get_text('no_bundles_msg', lang)
    kb = await get_bundles_list_keyboard(user_id, lang)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

@mychannels_router.callback_query(F.data == "bundle:create")
async def handle_bundle_create(callback: types.CallbackQuery, state: FSMContext):
    """Yangi to'plam yaratishni boshlash (nom so'rash)."""
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    # 1 ta kanal bo'lsa ham yoki kanal bo'lmasa ham to'plam yaratish mumkin!
    await state.set_state(BundleCreation.waiting_for_name)
    await state.update_data(bundle_name="", selected_channel_ids=[])

    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('cancel_btn', lang), callback_data="bundle:cancel")

    prompt_text = get_text('bundle_enter_name', lang)
    try:
        await callback.message.edit_text(prompt_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(prompt_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@mychannels_router.message(BundleCreation.waiting_for_name)
async def handle_bundle_name_input(message: types.Message, state: FSMContext):
    """To'plam nomini qabul qilish va kanal tanlash oynasini ko'rsatish."""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    name = (message.text or "").strip()

    if not name or len(name) > 40:
        await message.answer(get_text('bundle_enter_name', lang), parse_mode="HTML")
        return

    user_channels = await get_user_channels(user_id)

    if not user_channels:
        # Kanal bo'lmasa ham to'plam darhol yaratiladi!
        await save_user_channel_bundle(user_id, name, [])
        await state.clear()
        success_text = get_text('bundle_created_success', lang).format(
            bundle_name=html.escape(name),
            count=0
        )
        await message.answer(success_text, parse_mode="HTML")
        kb = await get_bundles_list_keyboard(user_id, lang)
        await message.answer(get_text('bundles_title', lang), reply_markup=kb, parse_mode="HTML")
        return

    await state.set_state(BundleCreation.selecting_channels)
    await state.update_data(bundle_name=name, selected_channel_ids=[])

    kb = get_bundle_channels_keyboard(user_channels, set(), lang)
    text = get_text('bundle_select_channels', lang).format(bundle_name=html.escape(name))
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@mychannels_router.callback_query(BundleCreation.selecting_channels, F.data.startswith("bundle:toggle:"))
async def handle_bundle_toggle_channel(callback: types.CallbackQuery, state: FSMContext):
    """Kanalni to'plamga tanlash yoki bekor qilish."""
    channel_id = int(callback.data.split(":", 2)[2])
    data = await state.get_data()
    selected_set = set(data.get('selected_channel_ids', []))

    if channel_id in selected_set:
        selected_set.remove(channel_id)
    else:
        selected_set.add(channel_id)

    await state.update_data(selected_channel_ids=list(selected_set))
    user_channels = await get_user_channels(callback.from_user.id)
    lang = await get_user_language(callback.from_user.id)

    kb = get_bundle_channels_keyboard(user_channels, selected_set, lang)
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass
    await callback.answer()

@mychannels_router.callback_query(BundleCreation.selecting_channels, F.data == "bundle:save")
async def handle_bundle_save(callback: types.CallbackQuery, state: FSMContext):
    """To'plamni saqlash."""
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    data = await state.get_data()
    selected = data.get('selected_channel_ids', [])
    bundle_name = data.get('bundle_name', "To'plam")

    await save_user_channel_bundle(user_id, bundle_name, selected)
    await state.clear()
    await callback.answer()

    success_text = get_text('bundle_created_success', lang).format(
        bundle_name=html.escape(bundle_name),
        count=len(selected)
    )
    await callback.message.answer(success_text, parse_mode="HTML")

    # To'plamlar ro'yxatini ko'rsatish
    kb = await get_bundles_list_keyboard(user_id, lang)
    await callback.message.answer(get_text('bundles_title', lang), reply_markup=kb, parse_mode="HTML")

@mychannels_router.callback_query(F.data == "bundle:cancel")
async def handle_bundle_cancel(callback: types.CallbackQuery, state: FSMContext):
    """To'plam yaratishni bekor qilish."""
    await state.clear()
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    bundles = await get_user_channel_bundles(user_id)
    text = get_text('bundles_title', lang) if bundles else get_text('no_bundles_msg', lang)
    kb = await get_bundles_list_keyboard(user_id, lang)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()
