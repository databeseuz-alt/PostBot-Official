from datetime import datetime, timedelta
import re
import html
import logging

logger = logging.getLogger(__name__)

from aiogram import Router, types, Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from xdata_handlers.database import (
    add_scheduled_post, get_user_language, get_post_from_db, 
    mark_scheduled_post_as_sent, save_sent_post, get_channel_name
)
from xdata_handlers.translator import get_text
from post_handlers.send_handler import PostSending
from post_handlers.xinline_keyboard import PostSendCallbackFactory, get_post_management_keyboard, generate_final_keyboard
from post_handlers.post_handler import validate_and_fix_html
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

schedule_router = Router()

@schedule_router.callback_query(PostSendCallbackFactory.filter(F.action == "schedule_for_channel"))
async def start_scheduling_for_channel(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext):
    """Kanal tanlagandan keyin rejalashtirishni boshlaydi."""
    post_code = callback_data.post_code
    channel_id = callback_data.channel_id
    
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

    await state.update_data(schedule_post_code=post_code, schedule_channel_id=channel_id)
    await state.set_state(PostSending.choosing_schedule_time)

    lang = await get_user_language(callback.from_user.id)
    text = get_text('schedule_when_to_send', lang) + "\n\n" + get_text('schedule_enter_date_format', lang)

    await callback.message.edit_text(text, reply_markup=None, parse_mode="HTML")
    await callback.answer()

@schedule_router.message(StateFilter(PostSending.choosing_schedule_time))
async def process_custom_schedule_time(message: types.Message, state: FSMContext, bot: Bot):
    """Foydalanuvchi kiritgan vaqt matnini qabul qiladi."""
    lang = await get_user_language(message.from_user.id)
    text = message.text.strip()

    data = await state.get_data()
    post_code = data.get('schedule_post_code')

    formats = ["%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"]
    parsed_time = None

    for fmt in formats:
        try:
            parsed_time = datetime.strptime(text, fmt)
            break
        except ValueError:
            continue

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
    await _finalize_schedule(message, state, post_code, utc_time, text, lang, bot)

async def _finalize_schedule(message: types.Message, state: FSMContext, post_code: str, scheduled_time: datetime, display_time: str, lang: str, bot: Bot = None):
    """Rejalashtirishni yakunlaydi va bazaga yozadi."""
    data = await state.get_data()
    channel_id = data.get('schedule_channel_id') or data.get('selected_channel_id')
    channel_name = data.get('selected_channel_name')
    user_id = message.from_user.id

    if not channel_id:
        await message.answer(get_text('unknown_error', lang))
        return
    
    # Agar channel_name state'da bo'lmasa, bazadan olish
    if not channel_name:
        channel_name = await get_channel_name(user_id, channel_id)

    post_id = await add_scheduled_post(user_id, post_code, scheduled_time, channel_id=channel_id, channel_name=channel_name)

    if post_id:
        if bot:
            schedule_post_job(bot, post_id, user_id, post_code, channel_id, scheduled_time)

        confirmation_text = get_text('schedule_accepted_confirmation', lang).format(date=display_time)
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

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from xdata_handlers.database import (
    get_pending_scheduled_posts, mark_scheduled_post_as_sent,
    get_post_from_db, save_sent_post
)
from post_handlers.xinline_keyboard import generate_final_keyboard

scheduler = AsyncIOScheduler()

async def send_scheduled_post(bot: Bot, post_id: int, user_id: int, post_code: str, channel_id: int):
    """Rejalashtirilgan postni kanalga yuboradi."""
    if not channel_id:
        await mark_scheduled_post_as_sent(post_id)
        return

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

        try:
            channel_name = "kanal"
            try:
                chat = await bot.get_chat(channel_id)
                channel_name = chat.title
            except:
                pass

            user_lang = await get_user_language(user_id)
            await bot.send_message(
                user_id, 
                get_text('scheduled_post_sent', user_lang).format(post_code=post_code, channel_name=channel_name)
            )
        except Exception:
            pass

    except Exception:
        pass

def schedule_post_job(bot: Bot, post_id: int, user_id: int, post_code: str, channel_id: int, run_time: datetime):
    """APScheduler'ga yangi job qo'shadi."""
    import asyncio
    import pytz

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
    """Bazadan kutilayotgan postlarni o'qib, APScheduler'ga qo'shadi."""
    pending_posts = await get_pending_scheduled_posts()

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
