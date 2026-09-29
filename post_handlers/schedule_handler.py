from datetime import datetime, timedelta
import re
import html
import logging

logger = logging.getLogger(__name__)

from aiogram import Router, types, Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder

from xdata_handlers.database import (
    add_scheduled_post, get_user_language, get_post_from_db,
    mark_scheduled_post_as_sent, save_sent_post, get_channel_name,
    get_all_pending_scheduled_posts, get_user_scheduled_posts,
    get_scheduled_post_by_id, cancel_scheduled_post,
    reschedule_scheduled_post, set_post_repeat_interval,
    add_next_recurring_post,
)
from xdata_handlers.translator import get_text
from xdata_handlers.error_logger import log_bot_error
from post_handlers.send_handler import PostSending
from post_handlers.xinline_keyboard import PostSendCallbackFactory, get_post_management_keyboard, generate_final_keyboard
from post_handlers.post_handler import validate_and_fix_html
from post_handlers.localize_filter import LocalizedText
import pytz

def validate_html_content(content: str) -> str:
    """
    HTML kontentini validatsiya qilish va xatolarni tuzatish
    """
    if not content:
        return content

    return validate_and_fix_html(content)

LANG_TZ_MAP = {
    'uzl': 'Asia/Tashkent',
    'uzk': 'Asia/Tashkent',
    'ru': 'Europe/Moscow',
    'tr': 'Europe/Istanbul',
    'en': 'UTC',
    'az': 'Asia/Baku',
    'kg': 'Asia/Bishkek',
    'kz': 'Asia/Almaty',
    'tj': 'Asia/Dushanbe',
    'tk': 'Asia/Ashgabat'
}

def get_timezone_by_lang(lang: str) -> pytz.BaseTzInfo:
    """Tildan kelib chiqib pytz vaqt mintaqasini qaytaradi."""
    tz_name = LANG_TZ_MAP.get(lang, 'Asia/Tashkent')
    return pytz.timezone(tz_name)

def get_now_localized(lang: str) -> datetime:
    """Tilga mos lokal 'hozirgi' vaqtni qaytaradi."""
    tz = get_timezone_by_lang(lang)
    return datetime.now(tz)

def to_utc(dt: datetime, lang: str) -> datetime:
    """Lokal vaqtni UTC ga o'tkazadi."""
    if dt.tzinfo is None:
        tz = get_timezone_by_lang(lang)
        dt = tz.localize(dt)
    return dt.astimezone(pytz.UTC)

def parse_schedule_time_text(text: str) -> datetime | None:
    """Matnli vaqtni datetime ga o'giradi (mahalliy vaqt, tz-siz)."""
    formats = ["%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"]
    for fmt in formats:
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return None

def format_local_time(utc_dt: datetime, lang: str) -> str:
    """UTC vaqtni foydalanuvchi mahalliy vaqtiga o'girib, chiroyli ko'rinishda qaytaradi."""
    try:
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        local_dt = utc_dt.astimezone(get_timezone_by_lang(lang))
        return local_dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(utc_dt)


schedule_router = Router()


class ScheduleManage(StatesGroup):
    """Rejalashtirilgan postlarni boshqarish holatlari."""
    waiting_for_custom_time = State()      # yangi post uchun matnli vaqt kiritish
    waiting_for_reschedule_time = State()  # mavjud post vaqtini o'zgartirish


# ==================== TEZ VAQT TUGMALARI ====================

def get_schedule_quick_keyboard(lang: str) -> types.InlineKeyboardMarkup:
    """Rejalashtirish vaqtini tez tanlash uchun inline klaviatura."""
    tz = get_timezone_by_lang(lang)
    now = datetime.now(tz)

    plus1 = now + timedelta(hours=1)
    plus3 = now + timedelta(hours=3)
    tomorrow9 = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    tomorrow12 = (now + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)

    builder = types.InlineKeyboardBuilder()
    builder.button(text=f"⏱ +1 soat ({plus1.strftime('%H:%M')})", callback_data="sched_quick:1h")
    builder.button(text=f"⏱ +3 soat ({plus3.strftime('%H:%M')})", callback_data="sched_quick:3h")
    builder.button(text=f"🌅 Ertaga 09:00", callback_data="sched_quick:tom9")
    builder.button(text=f"☀️ Ertaga 12:00", callback_data="sched_quick:tom12")
    builder.button(text=get_text('sched_custom_input_btn', lang), callback_data="sched_quick:custom")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_repeat_choice_keyboard(lang: str) -> types.InlineKeyboardMarkup:
    """Takrorlash rejimini tanlash klaviaturasi."""
    builder = types.InlineKeyboardBuilder()
    builder.button(text=get_text('repeat_once_btn', lang), callback_data="sched_repeat:once")
    builder.button(text=get_text('repeat_daily_btn', lang), callback_data="sched_repeat:daily")
    builder.button(text=get_text('repeat_weekly_btn', lang), callback_data="sched_repeat:weekly")
    builder.adjust(1)
    return builder.as_markup()


def get_repeat_change_keyboard(lang: str) -> types.InlineKeyboardMarkup:
    """Mavjud postning takrorlashini o'zgartirish klaviaturasi."""
    builder = types.InlineKeyboardBuilder()
    builder.button(text=get_text('repeat_none_btn', lang), callback_data="sched_rrepeat:none")
    builder.button(text=get_text('repeat_daily_btn', lang), callback_data="sched_rrepeat:daily")
    builder.button(text=get_text('repeat_weekly_btn', lang), callback_data="sched_rrepeat:weekly")
    builder.button(text=get_text('back_btn', lang), callback_data="schedules_list")
    builder.adjust(1)
    return builder.as_markup()


# ==================== REJALASHTIRISHNI BOSHLASH ====================

@schedule_router.callback_query(PostSendCallbackFactory.filter(F.action == "schedule_for_channel"))
async def start_scheduling_for_channel(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext):
    """Kanal yoki to'plam tanlagandan keyin rejalashtirishni boshlaydi: tez vaqt tugmalari ko'rsatiladi."""
    post_code = callback_data.post_code
    channel_id = callback_data.channel_id
    bundle_id = callback_data.bundle_id

    # post_code None bo'lsa, state dan olishga urinib ko'rish
    if not post_code:
        data = await state.get_data()
        post_code = data.get("post_code") or data.get("schedule_post_code")

    # Yana ham None bo'lsa, xabar berish
    if not post_code:
        lang = await get_user_language(callback.from_user.id)
        await callback.message.answer(get_text('post_code_missing_error', lang), parse_mode="HTML")
        await callback.answer()
        return

    if bundle_id:
        from xdata_handlers.database import get_user_channel_bundle_by_id
        bundle = await get_user_channel_bundle_by_id(callback.from_user.id, bundle_id)
        if bundle:
            await state.update_data(
                schedule_post_code=post_code,
                schedule_bundle_id=bundle_id,
                schedule_bundle_name=bundle.get('name'),
                schedule_channel_ids=bundle.get('channel_ids', [])
            )
        else:
            await state.update_data(schedule_post_code=post_code, schedule_channel_id=channel_id)
    else:
        await state.update_data(schedule_post_code=post_code, schedule_channel_id=channel_id)

    await state.set_state(ScheduleManage.waiting_for_custom_time)

    lang = await get_user_language(callback.from_user.id)
    text = get_text('schedule_when_to_send', lang) + "\n\n" + get_text('schedule_enter_date_format', lang)

    try:
        await callback.message.edit_text(text, reply_markup=get_schedule_quick_keyboard(lang), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_schedule_quick_keyboard(lang), parse_mode="HTML")
    await callback.answer()


@schedule_router.callback_query(F.data.startswith("sched_quick:"))
async def handle_quick_schedule_time(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Tez vaqt tugmalarini qayta ishlaydi (yangi rejalashtirish va reschedule oqimlari)."""
    option = callback.data.split(":")[1]
    lang = await get_user_language(callback.from_user.id)
    data = await state.get_data()
    tz = get_timezone_by_lang(lang)
    now = datetime.now(tz)

    reschedule_post_id = data.get('reschedule_post_id')

    if option == "custom":
        # Reschedule oqimida holat allaqachon waiting_for_reschedule_time, faqat matn so'raymiz
        if not reschedule_post_id:
            await state.set_state(ScheduleManage.waiting_for_custom_time)
        try:
            await callback.message.edit_text(
                get_text('schedule_enter_date_format', lang),
                reply_markup=None,
                parse_mode="HTML"
            )
        except Exception:
            pass
        await callback.answer()
        return

    parsed_time = None
    if option == "1h":
        parsed_time = now + timedelta(hours=1)
    elif option == "3h":
        parsed_time = now + timedelta(hours=3)
    elif option == "tom9":
        parsed_time = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    elif option == "tom12":
        parsed_time = (now + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)

    if not parsed_time:
        await callback.answer(get_text('unknown_error', lang), show_alert=True)
        return

    # Reschedule oqimi: mavjud post vaqtini to'g'ridan-to'g'ri yangilaymiz
    if reschedule_post_id:
        await callback.answer()
        await _finalize_reschedule(callback.message, state, reschedule_post_id, parsed_time, parsed_time.strftime("%d.%m.%Y %H:%M"), lang, bot)
        return

    display_time = parsed_time.strftime("%d.%m.%Y %H:%M")
    utc_time = to_utc(parsed_time, lang)

    await state.update_data(
        pending_schedule_time=utc_time.isoformat(),
        pending_display_time=display_time
    )
    await state.set_state(None)

    text = get_text('sched_repeat_question', lang).format(time=display_time)
    try:
        await callback.message.edit_text(text, reply_markup=get_repeat_choice_keyboard(lang), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_repeat_choice_keyboard(lang), parse_mode="HTML")
    await callback.answer()


@schedule_router.message(StateFilter(PostSending.choosing_schedule_time))
async def process_custom_schedule_time(message: types.Message, state: FSMContext, bot: Bot):
    """Foydalanuvchi kiritgan vaqt matnini qabul qiladi (eski oqim bilan moslik uchun)."""
    lang = await get_user_language(message.from_user.id)
    text = message.text.strip()

    data = await state.get_data()
    post_code = data.get('schedule_post_code')

    parsed_time = parse_schedule_time_text(text)
    if not parsed_time:
        await message.answer(
            get_text('schedule_invalid_format_detailed', lang),
            parse_mode="HTML"
        )
        return

    now_localized = get_now_localized(lang)
    tz = get_timezone_by_lang(lang)
    parsed_time = tz.localize(parsed_time)

    if parsed_time < now_localized:
        await message.answer(get_text('schedule_past_time', lang))
        return

    utc_time = to_utc(parsed_time, lang)
    display_time = parsed_time.strftime("%d.%m.%Y %H:%M")

    await state.update_data(
        pending_schedule_time=utc_time.isoformat(),
        pending_display_time=display_time
    )
    await state.set_state(None)

    repeat_text = get_text('sched_repeat_question', lang).format(time=display_time)
    await message.answer(repeat_text, reply_markup=get_repeat_choice_keyboard(lang), parse_mode="HTML")


@schedule_router.message(ScheduleManage.waiting_for_custom_time, LocalizedText('cancel_btn'))
@schedule_router.message(ScheduleManage.waiting_for_reschedule_time, LocalizedText('cancel_btn'))
@schedule_router.message(StateFilter(PostSending.choosing_schedule_time), LocalizedText('cancel_btn'))
async def schedule_cancel(message: types.Message, state: FSMContext, bot: Bot):
    """Rejalashtirish oqimlarida bekor qilish — asosiy menyuga qaytish."""
    from post_handlers.start_handler import show_main_menu
    await state.clear()
    await show_main_menu(message, state, bot)


@schedule_router.message(ScheduleManage.waiting_for_custom_time, F.text)
async def process_custom_time_new_flow(message: types.Message, state: FSMContext, bot: Bot):
    """Yangi oqim: matnli vaqt kiritilganda takrorlash tanlovini ko'rsatadi."""
    lang = await get_user_language(message.from_user.id)
    text = message.text.strip()

    parsed_time = parse_schedule_time_text(text)
    if not parsed_time:
        await message.answer(
            get_text('schedule_invalid_format_detailed', lang),
            parse_mode="HTML"
        )
        return

    now_localized = get_now_localized(lang)
    tz = get_timezone_by_lang(lang)
    parsed_time = tz.localize(parsed_time)

    if parsed_time < now_localized:
        await message.answer(get_text('schedule_past_time', lang))
        return

    utc_time = to_utc(parsed_time, lang)
    display_time = parsed_time.strftime("%d.%m.%Y %H:%M")

    await state.update_data(
        pending_schedule_time=utc_time.isoformat(),
        pending_display_time=display_time
    )
    await state.set_state(None)

    repeat_text = get_text('sched_repeat_question', lang).format(time=display_time)
    await message.answer(repeat_text, reply_markup=get_repeat_choice_keyboard(lang), parse_mode="HTML")


@schedule_router.callback_query(F.data.startswith("sched_repeat:"))
async def handle_repeat_choice(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Takrorlash tanlovi: rejalashtirishni yakunlaydi."""
    repeat = callback.data.split(":")[1]  # once | daily | weekly
    if repeat not in ("once", "daily", "weekly"):
        repeat = "once"

    lang = await get_user_language(callback.from_user.id)
    data = await state.get_data()

    post_code = data.get('schedule_post_code') or data.get('post_code')
    time_iso = data.get('pending_schedule_time')
    display_time = data.get('pending_display_time')

    if not post_code or not time_iso:
        await callback.answer(get_text('post_code_missing_error', lang), show_alert=True)
        return

    utc_time = datetime.fromisoformat(time_iso)
    await callback.answer()

    await _finalize_schedule(
        message=callback.message,
        state=state,
        post_code=post_code,
        scheduled_time=utc_time,
        display_time=display_time,
        lang=lang,
        bot=bot,
        repeat=None if repeat == "once" else repeat
    )


async def _finalize_schedule(message: types.Message, state: FSMContext, post_code: str, scheduled_time: datetime, display_time: str, lang: str, bot: Bot = None, repeat: str = None):
    """Rejalashtirishni yakunlaydi va bazaga yozadi."""
    data = await state.get_data()
    schedule_channel_ids = data.get('schedule_channel_ids')
    user_id = message.from_user.id if message.from_user else message.chat.id

    if schedule_channel_ids:
        bundle_name = data.get('schedule_bundle_name') or "To'plam"
        success_count = 0
        for ch_id in schedule_channel_ids:
            ch_name = await get_channel_name(user_id, ch_id)
            post_id = await add_scheduled_post(
                user_id, post_code, scheduled_time,
                channel_id=ch_id, channel_name=ch_name,
                repeat_interval=repeat
            )
            if post_id:
                success_count += 1
                if bot:
                    schedule_post_job(bot, post_id, user_id, post_code, ch_id, scheduled_time)

        if success_count > 0:
            repeat_suffix = ""
            if repeat == "daily":
                repeat_suffix = "\n🔁 " + get_text('repeat_daily_note', lang)
            elif repeat == "weekly":
                repeat_suffix = "\n🔁 " + get_text('repeat_weekly_note', lang)

            import html
            safe_bname = html.escape(bundle_name)
            confirmation_text = (
                f"✅ <b>Post «{safe_bname}» to'plamidagi {success_count} ta kanal uchun rejalashtirildi!</b>\n"
                f"📅 <b>Vaqt:</b> {display_time}{repeat_suffix}"
            )
            await message.answer(confirmation_text, parse_mode="HTML")

            bot_info = await bot.get_me()
            final_message = get_text('post_saved_msg', lang).format(
                post_code=post_code,
                bot_username=bot_info.username
            )
            inline_kb = await get_post_management_keyboard(post_code, lang)
            await message.answer(final_message, reply_markup=inline_kb, parse_mode="HTML")
            await state.clear()
        else:
            await message.answer(get_text('save_error', lang))
        return

    channel_id = data.get('schedule_channel_id') or data.get('selected_channel_id')
    channel_name = data.get('selected_channel_name')

    if not channel_id:
        await message.answer(get_text('unknown_error', lang))
        return

    # Agar channel_name state'da bo'lmasa, bazadan olish
    if not channel_name:
        channel_name = await get_channel_name(user_id, channel_id)

    post_id = await add_scheduled_post(
        user_id, post_code, scheduled_time,
        channel_id=channel_id, channel_name=channel_name,
        repeat_interval=repeat
    )

    if post_id:
        if bot:
            schedule_post_job(bot, post_id, user_id, post_code, channel_id, scheduled_time)

        repeat_suffix = ""
        if repeat == "daily":
            repeat_suffix = "\n🔁 " + get_text('repeat_daily_note', lang)
        elif repeat == "weekly":
            repeat_suffix = "\n🔁 " + get_text('repeat_weekly_note', lang)

        confirmation_text = get_text('schedule_accepted_confirmation', lang).format(date=display_time) + repeat_suffix
        await message.answer(confirmation_text, parse_mode="HTML")

        bot_info = await bot.get_me()
        final_message = get_text('post_saved_msg', lang).format(
            post_code=post_code,
            bot_username=bot_info.username
        )

        inline_kb = await get_post_management_keyboard(post_code, lang)

        await message.answer(final_message, reply_markup=inline_kb, parse_mode="HTML")

        await state.clear()
    else:
        await message.answer(get_text('save_error', lang))


# ==================== REJALASHTIRILGAN POSTLAR RO'YXATI ====================

@schedule_router.callback_query(F.data == "schedules_list")
async def show_scheduled_posts_list(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Foydalanuvchining rejalashtirilgan postlari ro'yxatini ko'rsatadi."""
    await state.clear()
    lang = await get_user_language(callback.from_user.id)

    try:
        posts = await get_user_scheduled_posts(callback.from_user.id)
        await _render_schedules(callback.message, posts, lang, edit=True)
    except Exception as e:
        await log_bot_error("show_scheduled_posts_list", e, user_id=callback.from_user.id)
        await callback.answer(get_text('unknown_error', lang), show_alert=True)
    await callback.answer()


async def show_scheduled_posts_for_message(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot, user_id: int = None):
    """Asosiy menyu tugmasi orqali ro'yxatni ko'rsatish (start_handler delegatsiya qiladi)."""
    if user_id is None:
        user_id = event.from_user.id
    target_message = event.message if isinstance(event, types.CallbackQuery) else event
    is_edit = isinstance(event, types.CallbackQuery)
    await state.clear()
    lang = await get_user_language(user_id)

    try:
        posts = await get_user_scheduled_posts(user_id)
        await _render_schedules(target_message, posts, lang, edit=is_edit)
    except Exception as e:
        await log_bot_error("show_scheduled_posts_for_message", e, user_id=user_id)
        await target_message.answer(get_text('unknown_error', lang))


async def _render_schedules(target: types.Message, posts: list, lang: str, edit: bool):
    """Ro'yxatni matn + inline klaviatura sifatida chizadi."""
    if not posts:
        text = get_text('sched_list_empty', lang)
        builder = types.InlineKeyboardBuilder()
        builder.button(text=get_text('back_btn', lang), callback_data="sched_back_main")
        builder.adjust(1)
        markup = builder.as_markup()
    else:
        text = get_text('sched_list_title', lang).format(count=len(posts)) + "\n"
        builder = types.InlineKeyboardBuilder()

        for post in posts[:10]:
            local_time = format_local_time(post['schedule_time'], lang)
            repeat_mark = ""
            if post.get('repeat_interval') == 'daily':
                repeat_mark = " 🔁"
            elif post.get('repeat_interval') == 'weekly':
                repeat_mark = " 🔁7️⃣"

            channel = post.get('channel_name') or str(post.get('channel_id') or '—')
            text += get_text('sched_list_item', lang).format(
                code=post['post_code'],
                time=local_time,
                channel=html.escape(str(channel)[:24]),
                repeat=repeat_mark
            )

            builder.button(text=f"⏰ {post['post_code']}", callback_data=f"sched_mgmt:time:{post['id']}")
            builder.button(text=f"🔁", callback_data=f"sched_mgmt:repeat:{post['id']}")
            builder.button(text=f"❌", callback_data=f"sched_mgmt:cancel:{post['id']}")

        builder.button(text=get_text('back_btn', lang), callback_data="sched_back_main")
        builder.adjust(3)

        markup = builder.as_markup()

    if edit:
        try:
            await target.edit_text(text, reply_markup=markup, parse_mode="HTML")
            return
        except Exception:
            pass
    await target.answer(text, reply_markup=markup, parse_mode="HTML")


@schedule_router.callback_query(F.data == "sched_back_main")
async def sched_back_to_main(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Ro'yxatdan asosiy menyuga qaytish."""
    from post_handlers.start_handler import show_main_menu
    await callback.answer()
    await show_main_menu(callback, state, bot)


@schedule_router.callback_query(F.data.startswith("sched_mgmt:cancel:"))
async def handle_cancel_scheduled(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Rejalashtirilgan postni bekor qiladi."""
    post_id = int(callback.data.split(":")[2])
    lang = await get_user_language(callback.from_user.id)

    success = await cancel_scheduled_post(post_id, callback.from_user.id)

    if success:
        # APScheduler'dagi jobni ham o'chirish
        try:
            job_id = f"scheduled_post_{post_id}"
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
        except Exception as e:
            await log_bot_error("cancel_job_removal", e, user_id=callback.from_user.id)

        await callback.answer(get_text('sched_cancelled_alert', lang), show_alert=True)
    else:
        await callback.answer(get_text('unknown_error', lang), show_alert=True)

    # Ro'yxatni yangilash
    posts = await get_user_scheduled_posts(callback.from_user.id)
    await _render_schedules(callback.message, posts, lang, edit=True)


@schedule_router.callback_query(F.data.startswith("sched_mgmt:time:"))
async def handle_reschedule_start(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Rejalashtirilgan post vaqtini o'zgartirishni boshlaydi."""
    post_id = int(callback.data.split(":")[2])
    lang = await get_user_language(callback.from_user.id)

    row = await get_scheduled_post_by_id(post_id, callback.from_user.id)
    if not row or row['status'] != 'pending':
        await callback.answer(get_text('sched_not_found_alert', lang), show_alert=True)
        return

    await state.update_data(reschedule_post_id=post_id)
    await state.set_state(ScheduleManage.waiting_for_reschedule_time)

    text = get_text('sched_reschedule_prompt', lang).format(
        code=row['post_code'],
        time=format_local_time(row['schedule_time'], lang)
    )

    try:
        await callback.message.edit_text(text, reply_markup=get_schedule_quick_keyboard(lang), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_schedule_quick_keyboard(lang), parse_mode="HTML")
    await callback.answer()


@schedule_router.callback_query(F.data.startswith("sched_mgmt:repeat:"))
async def handle_repeat_change_start(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Mavjud postning takrorlash rejimini o'zgartirish."""
    post_id = int(callback.data.split(":")[2])
    lang = await get_user_language(callback.from_user.id)

    row = await get_scheduled_post_by_id(post_id, callback.from_user.id)
    if not row or row['status'] != 'pending':
        await callback.answer(get_text('sched_not_found_alert', lang), show_alert=True)
        return

    await state.update_data(repeat_change_post_id=post_id)

    current = row.get('repeat_interval') or 'none'
    current_text = {
        'daily': get_text('repeat_daily_btn', lang),
        'weekly': get_text('repeat_weekly_btn', lang),
        'none': get_text('repeat_none_btn', lang),
    }.get(current, current)

    text = get_text('sched_repeat_change_prompt', lang).format(
        code=row['post_code'],
        current=current_text
    )

    try:
        await callback.message.edit_text(text, reply_markup=get_repeat_change_keyboard(lang), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_repeat_change_keyboard(lang), parse_mode="HTML")
    await callback.answer()


@schedule_router.callback_query(F.data.startswith("sched_rrepeat:"))
async def handle_repeat_change_apply(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Takrorlash rejimini saqlaydi."""
    value = callback.data.split(":")[1]
    lang = await get_user_language(callback.from_user.id)

    data = await state.get_data()
    post_id = data.get('repeat_change_post_id')

    if not post_id:
        await callback.answer(get_text('unknown_error', lang), show_alert=True)
        return

    repeat_value = None if value == 'none' else value
    if repeat_value not in (None, 'daily', 'weekly'):
        repeat_value = None

    success = await set_post_repeat_interval(post_id, callback.from_user.id, repeat_value)

    if success:
        await callback.answer(get_text('sched_updated_alert', lang), show_alert=True)
    else:
        await callback.answer(get_text('unknown_error', lang), show_alert=True)

    await state.clear()

    posts = await get_user_scheduled_posts(callback.from_user.id)
    await _render_schedules(callback.message, posts, lang, edit=True)


# Reschedule oqimida ham sched_quick:* tugmalari ishlaydi (handle_quick_schedule_time ichida hal qilinadi)


@schedule_router.message(ScheduleManage.waiting_for_reschedule_time, F.text)
async def process_reschedule_time(message: types.Message, state: FSMContext, bot: Bot):
    """Reschedule uchun matnli vaqt kiritish."""
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    post_id = data.get('reschedule_post_id')

    if not post_id:
        await state.clear()
        await message.answer(get_text('unknown_error', lang))
        return

    parsed_time = parse_schedule_time_text(message.text.strip())
    if not parsed_time:
        await message.answer(get_text('schedule_invalid_format_detailed', lang), parse_mode="HTML")
        return

    tz = get_timezone_by_lang(lang)
    parsed_time = tz.localize(parsed_time)

    if parsed_time < get_now_localized(lang):
        await message.answer(get_text('schedule_past_time', lang))
        return

    await _finalize_reschedule(message, state, post_id, parsed_time, parsed_time.strftime("%d.%m.%Y %H:%M"), lang, bot)


async def _finalize_reschedule(message: types.Message, state: FSMContext, post_id: int, local_time: datetime, display_time: str, lang: str, bot: Bot):
    """Vaqt o'zgartirishni yakunlaydi: bazani va APScheduler jobini yangilaydi."""
    data = await state.get_data()
    user_id = message.from_user.id if message.from_user else message.chat.id

    row = await get_scheduled_post_by_id(post_id, user_id)
    if not row or row['status'] != 'pending':
        await state.clear()
        await message.answer(get_text('sched_not_found_alert', lang), show_alert=False)
        return

    utc_time = to_utc(local_time, lang)
    success = await reschedule_scheduled_post(post_id, user_id, utc_time)

    if not success:
        await message.answer(get_text('unknown_error', lang))
        return

    # APScheduler jobini yangi vaqtga ko'chirish
    if bot:
        schedule_post_job(
            bot, post_id, user_id, row['post_code'], row['channel_id'], utc_time
        )

    await state.clear()

    confirm = get_text('sched_updated_msg', lang).format(
        code=row['post_code'],
        time=display_time
    )
    builder = types.InlineKeyboardBuilder()
    builder.button(text=get_text('sched_back_to_list_btn', lang), callback_data="schedules_list")
    builder.adjust(1)
    await message.answer(confirm, reply_markup=builder.as_markup(), parse_mode="HTML")


# ==================== APSCHEDULER ====================

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

scheduler = AsyncIOScheduler()


async def send_scheduled_post(bot: Bot, post_id: int, user_id: int, post_code: str, channel_id: int):
    """Rejalashtirilgan postni kanalga yuboradi. Xatolik bo'lsa foydalanuvchiga xabar beradi."""
    if not channel_id:
        await mark_scheduled_post_as_sent(post_id)
        return

    # Takrorlash ma'lumotini yuborish oldidan bazadan o'qish (o'zgartirilgan bo'lishi mumkin)
    pending_row = await get_scheduled_post_by_id(post_id, user_id)
    repeat_interval = pending_row.get('repeat_interval') if pending_row else None
    scheduled_time = pending_row.get('schedule_time') if pending_row else None

    try:
        full_post = await get_post_from_db(post_code)
        if not full_post:
            await mark_scheduled_post_as_sent(post_id)
            return

        post_content = full_post.get('post_content', {})
        buttons_matrix = full_post.get('buttons_matrix', [])
        keyboard = generate_final_keyboard(buttons_matrix)

        content_type = post_content.get('content_type')
        file_id = post_content.get('file_id')
        caption = post_content.get('caption', '')
        text = post_content.get('text', '')
        parse_mode = post_content.get('parse_mode', 'HTML')
        disable_preview = post_content.get('disable_web_page_preview', False)  # Standart yoqilgan

        # HTML kontentini validatsiya qilish
        if parse_mode == 'HTML':
            if text:
                text = validate_html_content(text)
            if caption:
                caption = validate_html_content(caption)

        has_spoiler = post_content.get('has_spoiler', False)
        show_caption_above = post_content.get('show_caption_above_media', False)

        sent_message = None

        if post_content.get('is_paid', False) and content_type in ['photo', 'video']:
            stars = post_content.get('paid_price', 1)
            from aiogram.types import InputPaidMediaPhoto, InputPaidMediaVideo
            if content_type == 'photo':
                media_list = [InputPaidMediaPhoto(media=file_id)]
            else:
                media_list = [InputPaidMediaVideo(media=file_id)]

            sent_message = await bot.send_paid_media(
                chat_id=channel_id,
                star_count=stars,
                media=media_list,
                caption=caption,
                parse_mode=parse_mode,
                show_caption_above_media=show_caption_above,
                reply_markup=keyboard
            )
        elif content_type == 'text':
            sent_message = await bot.send_message(channel_id, text, reply_markup=keyboard, parse_mode=parse_mode, disable_web_page_preview=disable_preview)
        elif content_type == 'photo':
            sent_message = await bot.send_photo(
                channel_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode,
                has_spoiler=has_spoiler, show_caption_above_media=show_caption_above
            )
        elif content_type == 'video':
            sent_message = await bot.send_video(
                channel_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode,
                has_spoiler=has_spoiler, show_caption_above_media=show_caption_above
            )
        elif content_type == 'audio':
            sent_message = await bot.send_audio(
                channel_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode
            )
        elif content_type == 'document':
            sent_message = await bot.send_document(
                channel_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode
            )
        elif content_type == 'voice':
            sent_message = await bot.send_voice(channel_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode)
        elif content_type == 'animation':
            sent_message = await bot.send_animation(
                channel_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode,
                has_spoiler=has_spoiler, show_caption_above_media=show_caption_above
            )
        elif content_type == 'video_note':
            sent_message = await bot.send_video_note(channel_id, file_id, reply_markup=keyboard)
        elif content_type == 'sticker':
            sent_message = await bot.send_sticker(channel_id, file_id, reply_markup=keyboard)
        elif content_type == 'dice':
            sent_message = await bot.send_dice(
                channel_id,
                emoji=post_content.get('dice_emoji', '🎲'),
                reply_markup=keyboard
            )
        elif content_type == 'location':
            sent_message = await bot.send_location(
                channel_id,
                latitude=post_content.get('latitude'),
                longitude=post_content.get('longitude'),
                reply_markup=keyboard
            )
        elif content_type == 'paid_media':
            from aiogram.types import InputPaidMediaPhoto, InputPaidMediaVideo
            media_types = post_content.get('paid_media_types', [])
            file_ids = post_content.get('paid_media_file_ids', [])
            paid_price = post_content.get('paid_price', 1)

            input_media_list = []
            for media_type, f_id in zip(media_types, file_ids):
                if media_type == 'photo':
                    input_media_list.append(InputPaidMediaPhoto(media=f_id))
                else:
                    input_media_list.append(InputPaidMediaVideo(media=f_id))

            sent_message = await bot.send_paid_media(
                chat_id=channel_id,
                star_count=paid_price,
                media=input_media_list,
                caption=caption,
                parse_mode=parse_mode,
                show_caption_above_media=show_caption_above,
                reply_markup=keyboard
            )

        if sent_message:
            try:
                chat = await bot.get_chat(channel_id)
                channel_name = chat.title
            except Exception:
                channel_name = None
            await save_sent_post(
                post_code=post_code,
                user_id=user_id,
                channel_id=channel_id,
                channel_name=channel_name,
                message_id=sent_message.message_id
            )

        await mark_scheduled_post_as_sent(post_id)

        # Takroriy post: keyingi nusxani rejalashtirish
        if repeat_interval in ('daily', 'weekly'):
            await _schedule_next_recurring(
                bot, post_code, user_id, channel_id, repeat_interval, scheduled_time
            )

        try:
            channel_name = "kanal"
            try:
                chat = await bot.get_chat(channel_id)
                channel_name = chat.title
            except Exception:
                pass

            user_lang = await get_user_language(user_id)
            await bot.send_message(
                user_id,
                get_text('scheduled_post_sent', user_lang).format(post_code=post_code, channel_name=channel_name)
            )
        except Exception as e:
            await log_bot_error("scheduled_post_user_notification", e, user_id=user_id)

    except Exception as e:
        # Xatolik haqida log + admin + foydalanuvchiga xabar
        await log_bot_error("send_scheduled_post", e, user_id=user_id, notify_admin=True, bot=bot)
        try:
            user_lang = await get_user_language(user_id)
            await bot.send_message(
                user_id,
                get_text('sched_send_failed', user_lang).format(post_code=post_code)
            )
        except Exception:
            pass


async def _schedule_next_recurring(bot: Bot, post_code: str, user_id: int, channel_id: int, repeat_interval: str, scheduled_time: datetime):
    """Takroriy postning keyingi nusxasini bazaga yozadi va job qo'shadi."""
    try:
        now_utc = datetime.now(pytz.UTC)

        if scheduled_time is None:
            scheduled_time = now_utc
        elif scheduled_time.tzinfo is None:
            scheduled_time = pytz.utc.localize(scheduled_time)

        delta = timedelta(days=1) if repeat_interval == 'daily' else timedelta(weeks=1)

        # Vaqt mutanosibligini saqlash: 09:00 da chiqadigan post doim 09:00 da chiqadi
        next_time = scheduled_time + delta
        while next_time <= now_utc:
            next_time += delta

        channel_name = None
        try:
            chat = await bot.get_chat(channel_id)
            channel_name = chat.title
        except Exception:
            pass

        new_id = await add_next_recurring_post(
            post_code, user_id, channel_id, channel_name, next_time, repeat_interval
        )
        if new_id:
            schedule_post_job(bot, new_id, user_id, post_code, channel_id, next_time)
    except Exception as e:
        await log_bot_error("schedule_next_recurring", e, user_id=user_id, notify_admin=True, bot=bot)


def schedule_post_job(bot: Bot, post_id: int, user_id: int, post_code: str, channel_id: int, run_time: datetime):
    """APScheduler'ga yangi job qo'shadi."""
    import asyncio

    if run_time.tzinfo is None:
        run_time = pytz.utc.localize(run_time)

    if not channel_id:
        return

    job_id = f"scheduled_post_{post_id}"

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    if run_time <= datetime.now(pytz.UTC):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(send_scheduled_post(bot, post_id, user_id, post_code, channel_id))
        except RuntimeError:
            asyncio.create_task(send_scheduled_post(bot, post_id, user_id, post_code, channel_id))
        return

    scheduler.add_job(
        send_scheduled_post,
        trigger=DateTrigger(run_date=run_time),
        id=job_id,
        args=[bot, post_id, user_id, post_code, channel_id],
        replace_existing=True
    )

async def load_pending_jobs(bot: Bot):
    """Bazadan barcha kutilayotgan postlarni o'qib, APScheduler'ga qo'shadi.

    MUHIM: vaqt filtri yo'q — kelajakdagi postlar ham yuklanishi shart
    (eski versiyada faqat o'tib ketgan postlar olingani uchun bot qayta
    ishga tushganda rejalashtirilgan postlar yo'qolardi).
    """
    pending_posts = await get_all_pending_scheduled_posts()
    logger.info(f"Rejalashtirilgan {len(pending_posts)} ta post scheduler'ga yuklanmoqda...")

    for post in pending_posts:
        schedule_post_job(
            bot=bot,
            post_id=post['id'],
            user_id=post['user_id'],
            post_code=post['post_code'],
            channel_id=post['channel_id'],
            run_time=post['schedule_time']
        )

def start_scheduler(bot: Bot):
    """APScheduler'ni ishga tushiradi."""
    import asyncio

    if not scheduler.running:
        scheduler.start()

    asyncio.create_task(load_pending_jobs(bot))
