#--- START OF FILE post_handlers/schedule_handler.py ---
import logging
from datetime import datetime, timedelta
import re

from aiogram import Router, types, Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from xdata_handlers.database import add_scheduled_post, get_user_language
from xdata_handlers.translator import get_text
# from xdata_handlers.timezone_helper import get_timezone_by_lang, get_now_localized, to_utc # REMOVED
from post_handlers.vpost_states import PostSending
from post_handlers.xinline_keyboard import PostSendCallbackFactory, get_post_management_keyboard
import pytz

# --- TIMEZONE HELPER LOGIC MOVED HERE ---
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
# ----------------------------------------


schedule_router = Router()

#==================================================
# --- R E J A L A S H T I R I SH N I   B O SH L A SH ---
#==================================================

@schedule_router.callback_query(PostSendCallbackFactory.filter(F.action == "schedule_for_channel"))
async def start_scheduling_for_channel(callback: types.CallbackQuery, callback_data: PostSendCallbackFactory, state: FSMContext):
    """Kanal tanlagandan keyin rejalashtirishni boshlaydi."""
    post_code = callback_data.post_code
    channel_id = callback_data.channel_id
    
    # State ga post_code va channel_id ni saqlaymiz
    await state.update_data(schedule_post_code=post_code, schedule_channel_id=channel_id)
    await state.set_state(PostSending.choosing_schedule_time)
    
    # Tugmalarni olib tashlaymiz va matnni yangilaymiz
    lang = await get_user_language(callback.from_user.id)
    text = get_text('schedule_when_to_send', lang) + "\n\n" + get_text('schedule_enter_date_format', lang)
    
    await callback.message.edit_text(text, reply_markup=None, parse_mode="HTML")
    await callback.answer()

#==================================================
# --- Q O' L D A   V A Q T   K I R I T I SH ---
#==================================================

@schedule_router.message(StateFilter(PostSending.choosing_schedule_time))
async def process_custom_schedule_time(message: types.Message, state: FSMContext, bot: Bot):
    """Foydalanuvchi kiritgan vaqt matnini qabul qiladi."""
    lang = await get_user_language(message.from_user.id)
    text = message.text.strip()
    
    data = await state.get_data()
    post_code = data.get('schedule_post_code')
    
    # Formatlarni tekshiramiz (soniyalar bilan yoki soniyalarsiz)
    formats = ["%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"]
    parsed_time = None
    
    for fmt in formats:
        try:
            parsed_time = datetime.strptime(text, fmt)
            break
        except ValueError:
            continue
            
    if not parsed_time:
        # Xato bo'lsa qaytadan so'raymiz
        await message.answer(
            get_text('schedule_invalid_format_detailed', lang),
            parse_mode="HTML"
        )
        return

    # O'tib ketgan vaqtni tekshiramiz (lokal vaqtda)
    now_localized = get_now_localized(lang)
    
    # datetime.strptime qaytargan vaqtga timezone qo'shamiz
    tz = get_timezone_by_lang(lang)
    parsed_time = tz.localize(parsed_time)

    if parsed_time < now_localized:
        await message.answer(get_text('schedule_past_time', lang))
        return

    # UTC ga o'tkazamiz
    utc_time = to_utc(parsed_time, lang)
    await _finalize_schedule(message, state, post_code, utc_time, text, lang, bot)

#==================================================
# --- Y A K U N L A SH ---
#==================================================

async def _finalize_schedule(message: types.Message, state: FSMContext, post_code: str, scheduled_time: datetime, display_time: str, lang: str, bot: Bot = None):
    """Rejalashtirishni yakunlaydi va bazaga yozadi."""
    data = await state.get_data()
    channel_id = data.get('schedule_channel_id')
    user_id = message.from_user.id
    
    logging.info(f"Rejalashtirish: post_code={post_code}, channel_id={channel_id}, time={scheduled_time}")
    
    post_id = await add_scheduled_post(user_id, post_code, scheduled_time, channel_id=channel_id)
    
    if post_id:
        # APScheduler'ga job qo'shish
        if bot:
            schedule_post_job(bot, post_id, user_id, post_code, channel_id, scheduled_time)
        
        # Muvaffaqiyat xabari
        confirmation_text = get_text('schedule_accepted_confirmation', lang).format(date=display_time)
        await message.answer(confirmation_text, parse_mode="HTML")
        
        # MOVE EFFEKTI: Postni boshqarish panelini yangidan chiqaramiz (Hardcoded matn bilan)
        final_message = get_text('post_inline_code_usage', lang).format(post_code=post_code)
        
        # TUZATILDI: await qo'shildi
        inline_kb = await get_post_management_keyboard(post_code, lang)

        await message.answer(final_message, reply_markup=inline_kb, parse_mode="HTML")
        
        await state.clear()
    else:
        await message.answer(get_text('save_error', lang))

#==================================================
# --- S C H E D U L E R   ( A P S C H E D U L E R ) ---
#==================================================

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from xdata_handlers.database import (
    get_pending_scheduled_posts, mark_scheduled_post_as_sent,
    get_post_from_db
)
from post_handlers.xinline_keyboard import generate_final_keyboard

# Global scheduler instance
scheduler = AsyncIOScheduler()

async def send_scheduled_post(bot: Bot, post_id: int, user_id: int, post_code: str, channel_id: int):
    """Rejalashtirilgan postni kanalga yuboradi."""
    try:
        logging.info(f"APScheduler: Post yuborilmoqda - post_code={post_code}, channel_id={channel_id}")
        
        full_post = await get_post_from_db(post_code)
        if not full_post:
            logging.warning(f"Rejalashtirilgan post bazadan topilmadi: {post_code}")
            await mark_scheduled_post_as_sent(post_id)
            return

        post_content = full_post.get('post_content', {})
        buttons_matrix = full_post.get('buttons_matrix', [])
        keyboard = generate_final_keyboard(buttons_matrix)
        
        content_type = post_content.get('content_type')
        file_id = post_content.get('file_id')
        caption = post_content.get('caption', '')
        text = post_content.get('text', '')
        parse_mode = post_content.get('parse_mode')

        # Postni kanalga yuborish
        if content_type == 'text':
            await bot.send_message(channel_id, text, reply_markup=keyboard, parse_mode=parse_mode)
        elif content_type == 'photo':
            await bot.send_photo(channel_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode)
        elif content_type == 'video':
            await bot.send_video(channel_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode)
        elif content_type == 'audio':
            await bot.send_audio(channel_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode)
        elif content_type == 'document':
            await bot.send_document(channel_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode)
        elif content_type == 'voice':
            await bot.send_voice(channel_id, file_id, caption=caption, reply_markup=keyboard, parse_mode=parse_mode)
        elif content_type == 'video_note':
            await bot.send_video_note(channel_id, file_id, reply_markup=keyboard)
        
        await mark_scheduled_post_as_sent(post_id)
        
        # Foydalanuvchi vaqtinchalik tilini aniqlash va xabar berish
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
        except Exception as e:
            logging.error(f"Foydalanuvchiga xabar yuborishda xatolik: {e}")
            
    except Exception as e:
        logging.error(f"Rejalashtirilgan postni yuborishda xatolik: {e}")

def schedule_post_job(bot: Bot, post_id: int, user_id: int, post_code: str, channel_id: int, run_time: datetime):
    """APScheduler'ga yangi job qo'shadi."""
    import asyncio
    import pytz
    
    # --- TUZATILDI ---
    # Agar bazadan olingan vaqtda timezone (tzinfo) bo'lmasa, uni UTC ga aylantiramiz
    if run_time.tzinfo is None:
        run_time = pytz.utc.localize(run_time)
    # -----------------

    job_id = f"scheduled_post_{post_id}"
    
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    
    # Hozirgi vaqt bilan solishtirganda ham timezone-aware vaqt ishlatamiz
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
    logging.info(f"APScheduler: Job qo'shildi - {job_id} vaqt: {run_time}")

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
            run_time=post['scheduled_time']
        )
    
    logging.info(f"APScheduler: {len(pending_posts)} ta kutilayotgan post yuklandi.")

def start_scheduler(bot: Bot):
    """APScheduler'ni ishga tushiradi."""
    import asyncio
    
    if not scheduler.running:
        scheduler.start()
        logging.info("APScheduler ishga tushdi!")
    
    asyncio.create_task(load_pending_jobs(bot))

#--- END OF FILE post_handlers/schedule_handler.py ---
