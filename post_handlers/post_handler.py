#--- START OF FILE post_handler.py ---
import logging
import re
from typing import List, Dict

# DIQQAT: Ushbu funksiya ishlashi uchun 'beautifulsoup4' kutubxonasi kerak.
# Uni "pip install beautifulsoup4" buyrug'i bilan o'rnating.
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

from xdata_handlers import config
from post_handlers.vpost_states import PostCreation
from post_handlers.xreply_keyboard import get_post_settings_kb
from post_handlers.xinline_keyboard import generate_post_keyboard
from xdata_handlers.database import get_user_language, get_user_post_settings
from xdata_handlers.translator import get_text
from post_handlers.localize_filter import LocalizedText

post_router = Router()

#==================================================
# --- Y O R D A M CHI   F U N K S I Y A L A R ---
#==================================================

def clean_text_for_default_mode(text: str | None) -> str | None:
    """Matndan barcha HTML va Markdown formatlash belgilarini olib tashlaydi."""
    if not text:
        return None

    cleaned_text = text
    # 1. HTML teglarni olib tashlash
    if BeautifulSoup:
        soup = BeautifulSoup(cleaned_text, 'html.parser')
        cleaned_text = soup.get_text()
    else:
        # Agar bs4 o'rnatilmagan bo'lsa, oddiy usul
        cleaned_text = re.sub(r'<[^>]+>', '', cleaned_text)
        logging.warning("Kutubxona topilmadi 'beautifulsoup4'. HTML tozalash to'liq ishlamasligi mumkin.")

    # 2. Asosiy Markdown belgilarini olib tashlash
    markdown_chars = ['*', '_', '~', '`', '|']
    for char in markdown_chars:
        cleaned_text = cleaned_text.replace(char, '')

    return cleaned_text

async def _get_permanent_file_id(bot: Bot, message: Message) -> str | None:
    if not config.STORAGE_CHANNEL_ID:
        logging.error("STORAGE_CHANNEL_ID konfiguratsiyada topilmadi!")
        return None

    try:
        if message.photo:
            sent_message = await bot.send_photo(config.STORAGE_CHANNEL_ID, message.photo[-1].file_id)
            return sent_message.photo[-1].file_id
        elif message.video:
            sent_message = await bot.send_video(config.STORAGE_CHANNEL_ID, message.video.file_id)
            return sent_message.video.file_id
        elif message.audio:
            sent_message = await bot.send_audio(config.STORAGE_CHANNEL_ID, message.audio.file_id)
            return sent_message.audio.file_id
        elif message.document:
            sent_message = await bot.send_document(config.STORAGE_CHANNEL_ID, message.document.file_id)
            return sent_message.document.file_id
        elif message.video_note:
            sent_message = await bot.send_video_note(config.STORAGE_CHANNEL_ID, message.video_note.file_id)
            return sent_message.video_note.file_id
        return None
    except Exception as e:
        logging.error(f"Faylni saqlash kanaliga yuborishda xatolik: {e}")
        return None

#==================================================
# --- P O S T   U CH U N   K O N T E N T N I   Q A B U L   Q I L I SH ---
#==================================================

@post_router.message(
    PostCreation.waiting_for_content,
    ~LocalizedText('btn_back_from_button')
)
async def universal_content_handler(message: Message, state: FSMContext, bot: Bot):
    old_data = await state.get_data()
    lang = await get_user_language(message.from_user.id)

    if message.media_group_id:
        return await message.answer("Albomlar hozircha qo'llab-quvvatlanmaydi.")

    supported_types = ('text', 'photo', 'video', 'audio', 'document', 'video_note')
    if message.content_type not in supported_types:
        return await message.answer(get_text('wrong_format', lang))

    await state.set_state(PostCreation.configuring_post)

    is_editing_session = 'editing_post_code' in old_data
    post_data = old_data.get('post_data', {})

    if not is_editing_session:
        user_settings = await get_user_post_settings(message.from_user.id)
        post_data.setdefault('parse_mode', user_settings.get('parse_mode'))
        post_data.setdefault('disable_web_page_preview', user_settings.get('disable_web_page_preview', False))

    current_parse_mode = post_data.get('parse_mode')

    # Tanlangan parse_mode ga qarab to'g'ri matn turini saqlaymiz
    text_content, caption_content = None, None

    if message.text is not None or message.caption is not None:
        if current_parse_mode == 'HTML':
            # .html_text ham matn, ham izohlar uchun ishlaydi
            text_content = message.html_text
            caption_content = message.html_text
        elif current_parse_mode == 'MarkdownV2':
            # .md_text ham matn, ham izohlar uchun ishlaydi
            text_content = message.md_text
            caption_content = message.md_text
        else: # None
            text_to_clean = message.text or message.caption
            cleaned_text = clean_text_for_default_mode(text_to_clean)
            if message.text:
                text_content = cleaned_text
            if message.caption:
                caption_content = cleaned_text

    # Eski entities ma'lumotlarini tozalaymiz va yangi matnni saqlaymiz
    post_data.pop('entities', None)
    post_data.pop('caption_entities', None)

    post_data.update({
        'chat_id': message.chat.id,
        'content_type': message.content_type,
        'text': text_content,
        'caption': caption_content
    })

    buttons_matrix = old_data.get("buttons_matrix", [[{'is_placeholder': True}]])
    keyboard = generate_post_keyboard(buttons_matrix)
    preview_message = None

    try:
        if is_editing_session and post_data.get('message_id'):
            try:
                await bot.delete_message(post_data['chat_id'], post_data['message_id'])
            except Exception:
                pass

        # Yuborish uchun parametrlarni tayyorlaymiz. Endi faqat parse_mode ishlatiladi.
        message_kwargs = {
            "reply_markup": keyboard,
            "parse_mode": post_data.get('parse_mode'),
            "disable_web_page_preview": post_data['disable_web_page_preview']
        }
        media_kwargs = {
            "reply_markup": keyboard,
            "parse_mode": post_data.get('parse_mode')
        }

        if message.text is not None:
            preview_message = await message.answer(post_data['text'], **message_kwargs)
        else:
            permanent_file_id = await _get_permanent_file_id(bot, message)
            if not permanent_file_id:
                return await message.answer(get_text('save_error', lang))

            post_data.update({
                'file_id': permanent_file_id,
                'title': getattr(message.audio, 'title', None),
                'performer': getattr(message.audio, 'performer', None),
                'file_name': getattr(message.document, 'file_name', None)
            })

            caption_for_sending = post_data.get('caption')

            if message.photo:
                preview_message = await bot.send_photo(message.chat.id, permanent_file_id, caption=caption_for_sending, **media_kwargs)
            elif message.video:
                preview_message = await bot.send_video(message.chat.id, permanent_file_id, caption=caption_for_sending, **media_kwargs)
            elif message.audio:
                preview_message = await bot.send_audio(message.chat.id, permanent_file_id, caption=caption_for_sending, **media_kwargs)
            elif message.document:
                preview_message = await bot.send_document(message.chat.id, permanent_file_id, caption=caption_for_sending, **media_kwargs)
            elif message.video_note:
                preview_message = await bot.send_video_note(message.chat.id, permanent_file_id, reply_markup=keyboard)

        if preview_message:
            post_data['message_id'] = preview_message.message_id
            await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)

            settings_kb_kwargs = {
                "content_type": post_data['content_type'],
                "has_caption": bool(post_data.get('caption'))
            }
            reply_markup = get_post_settings_kb(**settings_kb_kwargs)

            if is_editing_session:
                await message.answer(get_text('content_updated', lang), reply_markup=reply_markup)
            else:
                await message.answer(get_text('content_received', lang), reply_markup=reply_markup)

    except TelegramBadRequest as e:
        if "can't parse entities" in str(e).lower():
            error_mode = f"<code>{current_parse_mode or 'None'}</code>"
            await message.answer(f"⚠️ <b>Xatolik:</b> Siz yuborgan matn tanlangan {error_mode} formatiga mos kelmadi. Iltimos, belgilarni to'g'rilab, qaytadan yuboring.")
        else:
            logging.error(f"Postni qabul qilishda Telegram xatoligi: {e}")
            await message.answer(get_text('save_error', lang))
    except Exception as e:
        logging.error(f"Postni qabul qilishda kutilmagan xatolik: {e}")
        await message.answer(get_text('save_error', lang))
#--- END OF FILE post_handler.py ---
