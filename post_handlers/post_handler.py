import logging
import re
import html
from typing import List, Dict

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup

from xdata_handlers import config
from post_handlers.xreply_keyboard import get_post_settings_kb
from post_handlers.xinline_keyboard import generate_post_keyboard
from xdata_handlers.database import get_user_language, get_user_post_settings
from xdata_handlers.translator import get_text
from post_handlers.localize_filter import LocalizedText

post_router = Router()

class PostCreation(StatesGroup):
    waiting_for_content = State()
    configuring_post = State()
    waiting_for_edit_code = State()

    waiting_for_button_text = State()
    waiting_for_button_url = State()
    managing_button = State()
    editing_button_text = State()
    editing_button_url = State()
    waiting_for_button_color = State()
    waiting_for_new_button_color = State()

    waiting_for_post_name = State()
    waiting_for_rename = State()

    waiting_for_button_type = State()
    waiting_for_text_btn_content_sub = State()
    waiting_for_text_btn_content_nonsub = State()
    waiting_for_text_btn_color = State()
    waiting_for_reactions = State()
    waiting_for_reaction_color = State()
    
    # Media sozlamalari uchun yangi holatlar
    waiting_for_media_settings = State()
    waiting_for_position = State()
    waiting_for_paid_price = State()
    waiting_for_location = State()
    waiting_for_quiz_answer = State()

    # Chop etish sozlamalari
    waiting_for_delete_timer = State()
    waiting_for_pin_setting = State()
    waiting_for_protect_setting = State()
    waiting_for_voice_setting = State()
    waiting_for_reply_setting = State()
    waiting_for_auto_repeat_setting = State()
    
    # Watermark sozlamalari
    waiting_for_watermark_text = State()
    waiting_for_watermark_image = State()


def clean_text_for_default_mode(text: str | None) -> str | None:
    """Matndan barcha HTML va Markdown formatlash belgilarini olib tashlaydi."""
    if not text:
        return None

    cleaned_text = text
    if BeautifulSoup:
        soup = BeautifulSoup(cleaned_text, 'html.parser')
        cleaned_text = soup.get_text()
    else:
        cleaned_text = re.sub(r'<[^>]+>', '', cleaned_text)
        logging.warning("Kutubxona topilmadi 'beautifulsoup4'. HTML tozalash to'liq ishlamasligi mumkin.")

    markdown_chars = ['*', '_', '~', '`', '|']
    for char in markdown_chars:
        cleaned_text = cleaned_text.replace(char, '')

    return cleaned_text

def get_html_text(text: str, entities: list) -> str:
    """
    Matn va entitylarni HTML formatiga o'tkazadi.
    Barcha Telegram formatlari qo'llab-quvvatlanadi:
    - bold, italic, underline, strikethrough
    - spoiler, code, pre (code blocks)
    - text_link, text_mention
    - custom_emoji (Premium emoji)
    - blockquote, expandable_blockquote
    - mention (@username), hashtag, cashtag
    - bot_command, url, email, phone_number
    """
    if not text:
        return ""
    if not entities:
        return html.escape(text)

    try:
        utf16_text = text.encode('utf-16-le')
    except Exception:
        return html.escape(text)
    
    boundaries = {0, len(utf16_text) // 2}
    for e in entities:
        boundaries.add(e.offset)
        boundaries.add(e.offset + e.length)
    
    sorted_boundaries = sorted(list(boundaries))
    
    res = []
    
    def get_text_slice(start, end):
        return utf16_text[start*2:end*2].decode('utf-16-le')
    
    for i in range(len(sorted_boundaries) - 1):
        start, end = sorted_boundaries[i], sorted_boundaries[i+1]
        segment_text = get_text_slice(start, end)
        
        if not segment_text:
            continue
            
        active_entities = [e for e in entities if e.offset <= start and (e.offset + e.length) >= end]
        
        active_entities.sort(key=lambda e: e.length)
        
        inner = html.escape(segment_text)
        
        for entity in active_entities:
            tag_start = ""
            tag_end = ""
            entity_type = entity.type
            
            if entity_type == "bold":
                tag_start, tag_end = "<b>", "</b>"
            
            elif entity_type == "italic":
                tag_start, tag_end = "<i>", "</i>"
            
            elif entity_type == "underline":
                tag_start, tag_end = "<u>", "</u>"
            
            elif entity_type == "strikethrough":
                tag_start, tag_end = "<s>", "</s>"
            
            elif entity_type == "spoiler":
                tag_start, tag_end = "<tg-spoiler>", "</tg-spoiler>"
            
            elif entity_type == "code":
                tag_start, tag_end = "<code>", "</code>"
            
            elif entity_type == "pre":
                lang_attr = f' language="{html.escape(entity.language)}"' if getattr(entity, 'language', None) else ""
                tag_start, tag_end = f"<pre{lang_attr}>", "</pre>"
            
            elif entity_type == "text_link":
                url = html.escape(entity.url) if entity.url else ""
                tag_start, tag_end = f'<a href="{url}">', "</a>"
            
            elif entity_type == "text_mention":
                user_id = entity.user.id if entity.user else 0
                tag_start, tag_end = f'<a href="tg://user?id={user_id}">', "</a>"
            
            elif entity_type == "url":
                url = html.escape(segment_text)
                inner = f'<a href="{url}">{inner}</a>'
                continue  # Tag qo'shmaslik uchun
            
            elif entity_type == "email":
                email = html.escape(segment_text)
                inner = f'<a href="mailto:{email}">{inner}</a>'
                continue
            
            elif entity_type == "phone_number":
                phone = html.escape(segment_text)
                inner = f'<a href="tel:{phone}">{inner}</a>'
                continue
            
            elif entity_type == "custom_emoji":
                emoji_id = getattr(entity, 'custom_emoji_id', '')
                tag_start, tag_end = f'<tg-emoji emoji-id="{emoji_id}">', "</tg-emoji>"
            
            elif entity_type == "blockquote":
                tag_start, tag_end = "<blockquote>", "</blockquote>"
            
            elif entity_type == "expandable_blockquote":
                tag_start, tag_end = "<blockquote expandable>", "</blockquote>"
            
            elif entity_type == "mention":
                username = segment_text.lstrip('@')
                inner = f'<a href="https://t.me/{html.escape(username)}">{inner}</a>'
                continue
            
            elif entity_type == "hashtag":
                pass
            
            elif entity_type == "cashtag":
                pass
            
            elif entity_type == "bot_command":
                pass
            
            if tag_start:
                inner = tag_start + inner + tag_end
        
        res.append(inner)
        
    return "".join(res)

def format_user_info(user: types.User, lang: str = 'uzl') -> str:
    """Foydalanuvchi ma'lumotlarini formatlash."""
    nickname = html.escape(user.full_name)
    username = f"@{user.username}" if user.username else "mavjud emas"
    
    return (
        f"\n-------------------------------\n"
        f"nickname : <code>{nickname}</code>\n"
        f"user iD : <code>{user.id}</code>\n"
        f"username : <code>{username}</code>"
    )

async def _get_permanent_file_id(bot: Bot, message: Message, lang: str = 'uzl') -> str | None:
    if not config.STORAGE_CHANNEL_ID:
        logging.error("STORAGE_CHANNEL_ID konfiguratsiyada topilmadi!")
        return None

    user_info_text = format_user_info(message.from_user, lang)

    try:
        # User ma'lumotlarini alohida yuborish kerakligini tekshirish
        original_caption = ""
        if message.caption:
            original_caption = message.html_text
        
        caption_to_send = original_caption
        send_user_info_separately = False
        
        if original_caption:
            if len(original_caption) + len(user_info_text) <= 1024:
                caption_to_send = original_caption + user_info_text
            else:
                send_user_info_separately = True
        else:
            send_user_info_separately = True

        if message.voice:
            sent_message = await bot.send_voice(config.STORAGE_CHANNEL_ID, message.voice.file_id, caption=caption_to_send, parse_mode="HTML")
            if send_user_info_separately:
                await bot.send_message(config.STORAGE_CHANNEL_ID, user_info_text.strip(), parse_mode="HTML")
            return sent_message.voice.file_id

        elif message.photo:
            sent_message = await bot.send_photo(config.STORAGE_CHANNEL_ID, message.photo[-1].file_id, caption=caption_to_send, parse_mode="HTML")
            if send_user_info_separately:
                await bot.send_message(config.STORAGE_CHANNEL_ID, user_info_text.strip(), parse_mode="HTML")
            return sent_message.photo[-1].file_id

        elif message.video:
            sent_message = await bot.send_video(config.STORAGE_CHANNEL_ID, message.video.file_id, caption=caption_to_send, parse_mode="HTML")
            if send_user_info_separately:
                await bot.send_message(config.STORAGE_CHANNEL_ID, user_info_text.strip(), parse_mode="HTML")
            return sent_message.video.file_id

        elif message.audio:
            sent_message = await bot.send_audio(config.STORAGE_CHANNEL_ID, message.audio.file_id, caption=caption_to_send, parse_mode="HTML")
            if send_user_info_separately:
                await bot.send_message(config.STORAGE_CHANNEL_ID, user_info_text.strip(), parse_mode="HTML")
            return sent_message.audio.file_id

        elif message.document:
            sent_message = await bot.send_document(config.STORAGE_CHANNEL_ID, message.document.file_id, caption=caption_to_send, parse_mode="HTML")
            if send_user_info_separately:
                await bot.send_message(config.STORAGE_CHANNEL_ID, user_info_text.strip(), parse_mode="HTML")
            return sent_message.document.file_id

        elif message.video_note:
            sent_message = await bot.send_video_note(config.STORAGE_CHANNEL_ID, message.video_note.file_id)
            await bot.send_message(config.STORAGE_CHANNEL_ID, user_info_text.strip(), parse_mode="HTML")
            return sent_message.video_note.file_id

        elif message.sticker:
            sent_message = await bot.send_sticker(config.STORAGE_CHANNEL_ID, message.sticker.file_id)
            await bot.send_message(config.STORAGE_CHANNEL_ID, user_info_text.strip(), parse_mode="HTML")
            return sent_message.sticker.file_id

        elif message.animation:
            sent_message = await bot.send_animation(config.STORAGE_CHANNEL_ID, message.animation.file_id, caption=caption_to_send, parse_mode="HTML")
            if send_user_info_separately:
                await bot.send_message(config.STORAGE_CHANNEL_ID, user_info_text.strip(), parse_mode="HTML")
            return sent_message.animation.file_id

        return None
    except Exception as e:
        logging.error(f"Faylni saqlash kanaliga yuborishda xatolik: {e}")
        return None


async def handle_poll_content(message: Message, state: FSMContext, bot: Bot, old_data: dict, lang: str):
    """Poll/Quiz kontentini qayta ishlash"""
    poll = message.poll
    if not poll:
        return await message.answer(get_text('wrong_format', lang))
    
    await state.set_state(PostCreation.configuring_post)
    
    is_editing_session = 'editing_post_code' in old_data
    
    # Poll ma'lumotlarini yig'ish
    poll_data = {
        'content_type': 'poll',
        'poll_question': poll.question,
        'poll_options': [opt.text for opt in poll.options],
        'poll_is_quiz': poll.type == 'quiz',
        'poll_is_anonymous': poll.is_anonymous,
        'poll_allows_multiple_answers': poll.allows_multiple_answers,
        'poll_correct_option_id': poll.correct_option_id if poll.type == 'quiz' else None,
        'poll_explanation': getattr(poll, 'explanation', None),
        'parse_mode': 'HTML'
    }
    
    # Agar oldindan post_data bo'lsa, unga qo'shish
    post_data = old_data.get('post_data', {})
    post_data.update(poll_data)
    post_data['chat_id'] = message.chat.id
    
    buttons_matrix = old_data.get("buttons_matrix", [[{'is_placeholder': True}]])
    keyboard = generate_post_keyboard(buttons_matrix, lang)
    
    # Poll yoki Quiz ekanligini ko'rsatish
    poll_type_text = "📝 Viktorina" if poll.type == 'quiz' else "📊 So'rovnoma"
    
    # Javoblar ro'yxatini tuzish (HTML escaping qilish)
    options_text = "\n".join([f"{i+1}. {html.escape(str(opt))}" for i, opt in enumerate(poll_data['poll_options'])])
    
    preview_text = f"{poll_type_text}\n\n<b>{html.escape(poll.question)}</b>\n\n{options_text}"
    
    if poll.type == 'quiz' and poll.correct_option_id is not None:
        correct_answer = html.escape(str(poll_data['poll_options'][poll.correct_option_id]))
        preview_text += f"\n\n✅ To'g'ri javob: {correct_answer}"
    
    settings_kb_kwargs = {
        "content_type": 'poll',
        "has_caption": False,
        "lang": lang
    }
    reply_markup = get_post_settings_kb(**settings_kb_kwargs)
    
    if is_editing_session:
        await message.answer(get_text('content_updated', lang), reply_markup=reply_markup)
    else:
        await message.answer(get_text('content_received', lang), reply_markup=reply_markup)
    
    preview_message = await bot.send_poll(
        message.chat.id,
        question=poll.question,
        options=[opt.text for opt in poll.options],
        is_anonymous=poll.is_anonymous,
        allows_multiple_answers=poll.allows_multiple_answers,
        correct_option_id=poll.correct_option_id if poll.type == 'quiz' else None,
        type='quiz' if poll.type == 'quiz' else 'regular',
        explanation=getattr(poll, 'explanation', None),
        reply_markup=keyboard
    )
    
    if preview_message:
        post_data['message_id'] = preview_message.message_id
        post_data['chat_id'] = preview_message.chat.id
        await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)

        if config.STORAGE_CHANNEL_ID and not is_editing_session:
            try:
                user_info_text = format_user_info(message.from_user, lang)
                await message.copy_to(config.STORAGE_CHANNEL_ID)
                await bot.send_message(config.STORAGE_CHANNEL_ID, user_info_text, parse_mode="HTML")
            except Exception as e:
                logging.error(f"Postni log kanalga yuborishda xatolik: {e}")




async def handle_location_content(message: Message, state: FSMContext, bot: Bot, old_data: dict, lang: str):
    """Location kontentini qayta ishlash"""
    location = message.location
    if not location:
        return await message.answer(get_text('wrong_format', lang))
    
    await state.set_state(PostCreation.configuring_post)
    
    is_editing_session = 'editing_post_code' in old_data
    
    # Location ma'lumotlarini yig'ish
    location_data = {
        'content_type': 'location',
        'latitude': location.latitude,
        'longitude': location.longitude,
        'title': getattr(location, 'title', None),
        'address': getattr(location, 'address', None),
        'parse_mode': 'HTML'
    }
    
    # Agar oldindan post_data bo'lsa, unga qo'shish
    post_data = old_data.get('post_data', {})
    post_data.update(location_data)
    post_data['chat_id'] = message.chat.id
    
    buttons_matrix = old_data.get("buttons_matrix", [[{'is_placeholder': True}]])
    keyboard = generate_post_keyboard(buttons_matrix, lang)
    
    # Location ko'rsatish
    location_text = f"📍 Joylashuv\n\nKenglik: {location.latitude}\nUzunlik: {location.longitude}"
    if getattr(location, 'title', None):
        location_text += f"\nNomi: {getattr(location, 'title')}"
    if getattr(location, 'address', None):
        location_text += f"\nManzil: {getattr(location, 'address')}"
    
    settings_kb_kwargs = {
        "content_type": 'location',
        "has_caption": False,
        "lang": lang
    }
    reply_markup = get_post_settings_kb(**settings_kb_kwargs)
    
    if is_editing_session:
        await message.answer(get_text('content_updated', lang), reply_markup=reply_markup)
    else:
        await message.answer(get_text('content_received', lang), reply_markup=reply_markup)
    
    # Location yuborish (preview)
    preview_message = await bot.send_location(
        message.chat.id,
        latitude=location.latitude,
        longitude=location.longitude,
        reply_markup=keyboard
    )
    
    if preview_message:
        post_data['message_id'] = preview_message.message_id
        post_data['chat_id'] = preview_message.chat.id
        await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)

        if config.STORAGE_CHANNEL_ID and not is_editing_session:
            try:
                user_info_text = format_user_info(message.from_user, lang)
                await message.copy_to(config.STORAGE_CHANNEL_ID)
                await bot.send_message(config.STORAGE_CHANNEL_ID, user_info_text, parse_mode="HTML")
            except Exception as e:
                logging.error(f"Postni log kanalga yuborishda xatolik: {e}")


async def handle_paid_media_content(message: Message, state: FSMContext, bot: Bot, old_data: dict, lang: str):
    """Pulli media kontentini qayta ishlash"""
    paid_media = getattr(message, 'paid_media', None)
    if not paid_media:
        return await message.answer(get_text('wrong_format', lang))
    
    await state.set_state(PostCreation.configuring_post)
    
    is_editing_session = 'editing_post_code' in old_data
    
    # Pulli media ma'lumotlarini yig'ish
    media_types = []
    file_ids = []
    
    for media in paid_media:
        if hasattr(media, 'photo'):
            media_types.append('photo')
            file_ids.append(media.photo[-1].file_id)
        elif hasattr(media, 'video'):
            media_types.append('video')
            file_ids.append(media.video.file_id)
    
    post_data = old_data.get('post_data', {})
    post_data.update({
        'content_type': 'paid_media',
        'paid_media_types': media_types,
        'paid_media_file_ids': file_ids,
        'caption': message.caption.html_text if message.caption else None,
        'parse_mode': 'HTML',
        'is_paid': True,
        'chat_id': message.chat.id,
        'show_caption_above_media': getattr(message, 'show_caption_above_media', False)
    })
    
    buttons_matrix = old_data.get("buttons_matrix", [[{'is_placeholder': True}]])
    keyboard = generate_post_keyboard(buttons_matrix, lang)
    
    # Media ko'rsatish
    media_text = f"📦 Pulli media ({len(file_ids)} ta fayl)"
    if message.caption:
        media_text += f"\n\n{message.caption.html_text}"
    
    settings_kb_kwargs = {
        "content_type": 'paid_media',
        "has_caption": bool(message.caption),
        "lang": lang
    }
    reply_markup = get_post_settings_kb(**settings_kb_kwargs)
    
    if is_editing_session:
        await message.answer(get_text('content_updated', lang), reply_markup=reply_markup)
    else:
        await message.answer(get_text('content_received', lang), reply_markup=reply_markup)
    
    # Pulli mediani yuborish (preview)
    try:
        from aiogram.types import InputPaidMediaPhoto, InputPaidMediaVideo
        
        input_media_list = []
        for media_type, file_id in zip(media_types, file_ids):
            if media_type == 'photo':
                input_media_list.append(InputPaidMediaPhoto(media=file_id))
            else:
                input_media_list.append(InputPaidMediaVideo(media=file_id))
        
        # Narxni sozlash kerak - default 1 stars
        paid_price = post_data.get('paid_price', 1)
        
        preview_message = await bot.send_paid_media(
            chat_id=message.chat.id,
            star_count=paid_price,
            media=input_media_list,
            caption=message.caption.html_text if message.caption else None,
            parse_mode='HTML',
            show_caption_above_media=post_data.get('show_caption_above_media', False),
            reply_markup=keyboard
        )
        
        if preview_message:
            post_data['message_id'] = preview_message.message_id
            post_data['chat_id'] = message.chat.id
            await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)
            
    except Exception as e:
        logging.error(f"Pulli mediani yuborishda xatolik: {e}")
        # Oddiy media sifatida yuborishga urinish
        preview_message = await message.answer(media_text, reply_markup=keyboard, parse_mode='HTML')
        if preview_message:
            post_data['message_id'] = preview_message.message_id
            post_data['chat_id'] = preview_message.chat.id
            await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)

            if config.STORAGE_CHANNEL_ID and not is_editing_session:
                try:
                    user_info_text = format_user_info(message.from_user, lang)
                    await message.copy_to(config.STORAGE_CHANNEL_ID)
                    await bot.send_message(config.STORAGE_CHANNEL_ID, user_info_text, parse_mode="HTML")
                except Exception as e:
                    logging.error(f"Postni log kanalga yuborishda xatolik: {e}")


async def handle_dice_content(message: Message, state: FSMContext, bot: Bot, old_data: dict, lang: str):
    """Dice kontentini qayta ishlash"""
    dice = message.dice
    if not dice:
        return await message.answer(get_text('wrong_format', lang))
    
    await state.set_state(PostCreation.configuring_post)
    
    is_editing_session = 'editing_post_code' in old_data
    
    # Dice emoji va qiymatini olish
    dice_emoji = dice.emoji
    dice_value = dice.value
    
    post_data = old_data.get('post_data', {})
    post_data.update({
        'content_type': 'dice',
        'dice_emoji': dice_emoji,
        'dice_value': dice_value,
        'parse_mode': 'HTML',
        'chat_id': message.chat.id
    })
    
    buttons_matrix = old_data.get("buttons_matrix", [[{'is_placeholder': True}]])
    keyboard = generate_post_keyboard(buttons_matrix, lang)
    
    # Dice ko'rsatish
    dice_text = f"🎲 Dice: {dice_emoji} = {dice_value}"
    
    settings_kb_kwargs = {
        "content_type": 'dice',
        "has_caption": False,
        "lang": lang
    }
    reply_markup = get_post_settings_kb(**settings_kb_kwargs)
    
    if is_editing_session:
        await message.answer(get_text('content_updated', lang), reply_markup=reply_markup)
    else:
        await message.answer(get_text('content_received', lang), reply_markup=reply_markup)
    
    preview_message = await message.answer_dice(emoji=dice_emoji, reply_markup=keyboard)
    
    if preview_message:
        post_data['message_id'] = preview_message.message_id
        post_data['chat_id'] = preview_message.chat.id
        await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)

        if config.STORAGE_CHANNEL_ID and not is_editing_session:
            try:
                user_info_text = format_user_info(message.from_user, lang)
                await message.copy_to(config.STORAGE_CHANNEL_ID)
                await bot.send_message(config.STORAGE_CHANNEL_ID, user_info_text, parse_mode="HTML")
            except Exception as e:
                logging.error(f"Postni log kanalga yuborishda xatolik: {e}")


@post_router.message(
    PostCreation.waiting_for_content,
    ~LocalizedText('back_btn')
)
async def universal_content_handler(message: Message, state: FSMContext, bot: Bot):
    old_data = await state.get_data()
    lang = await get_user_language(message.from_user.id)

    if message.media_group_id:
        return await message.answer(get_text('albums_not_supported', lang))

    supported_types = ('text', 'photo', 'video', 'audio', 'document', 'video_note', 'voice', 'sticker', 'animation', 'poll', 'paid_media', 'dice', 'location')
    if message.content_type not in supported_types:
        return await message.answer(get_text('wrong_format', lang))

    # Poll/Quiz kontentini qabul qilish
    if message.content_type == 'poll' and message.poll:
        return await handle_poll_content(message, state, bot, old_data, lang)
    
    # Pulli media kontentini qabul qilish
    if message.content_type == 'paid_media':
        return await handle_paid_media_content(message, state, bot, old_data, lang)
    
    # Dice kontentini qabul qilish
    if message.content_type == 'dice':
        return await handle_dice_content(message, state, bot, old_data, lang)
    
    # Location kontentini qabul qilish
    if message.content_type == 'location':
        return await handle_location_content(message, state, bot, old_data, lang)

    await state.set_state(PostCreation.configuring_post)

    is_editing_session = 'editing_post_code' in old_data
    post_data = old_data.get('post_data', {})
    
    # Foydalanuvchi yuborgan mediada spoiler va caption joylashuvini tekshirish
    message_has_spoiler = False
    message_caption_above = getattr(message, 'show_caption_above_media', False)
    
    if message.content_type == 'photo' and message.photo:
        # Foto uchun spoiler tekshirish
        message_has_spoiler = getattr(message.photo[-1], 'has_spoiler', False) or getattr(message, 'has_media_spoiler', False)
    elif message.content_type == 'video' and message.video:
        # Video uchun spoiler tekshirish
        message_has_spoiler = getattr(message.video, 'has_spoiler', False) or getattr(message, 'has_media_spoiler', False)
    elif message.content_type == 'animation' and message.animation:
        # Animation uchun spoiler tekshirish
        message_has_spoiler = getattr(message.animation, 'has_spoiler', False) or getattr(message, 'has_media_spoiler', False)
    
    new_text = message.html_text if message.text else None
    new_caption = message.html_text if message.caption else None
    is_incoming_media = message.content_type != 'text' and message.content_type != 'poll' and message.content_type != 'dice'

    is_delete_media = message.text == get_text('delete_media_btn', lang)
    is_delete_text = message.text == get_text('delete_text_btn', lang)
    is_action = is_delete_media or is_delete_text

    if is_action and post_data:
        if is_delete_media:
            if post_data.get('content_type') != 'text' and post_data.get('caption'):
                post_data['content_type'] = 'text'
                post_data['text'] = post_data['caption']
                post_data['caption'] = None
                post_data['file_id'] = None
        elif is_delete_text:
            post_data['caption'] = None
            post_data['text'] = None
        
        is_incoming_media = False
    else:
        if post_data:
            if is_incoming_media:
                if post_data.get('content_type') == 'text' and post_data.get('text') and new_caption is None:
                    post_data['caption'] = post_data['text']
                    post_data['text'] = None
                
                post_data['content_type'] = message.content_type
                if new_caption is not None:
                    post_data['caption'] = new_caption
                    post_data['text'] = None
            else:
                if post_data.get('content_type') == 'text':
                    post_data['text'] = new_text
                else:
                    post_data['caption'] = new_text
        else:
            post_data = {
                'content_type': message.content_type,
                'text': new_text,
                'caption': new_caption,
                'parse_mode': 'HTML',
                'has_spoiler': message_has_spoiler,
                'show_caption_above_media': message_caption_above
            }
    
    # Agar yangi kelgan media bo'lsa va sozlamalar bo'lsa, post_data ga qo'shish
    if is_incoming_media:
        if message_has_spoiler:
            post_data['has_spoiler'] = True
        if message_caption_above:
            post_data['show_caption_above_media'] = True

    post_data['chat_id'] = message.chat.id

    # URL preview standart yoqilgan (enabled)
    post_data['disable_web_page_preview'] = False

    buttons_matrix = old_data.get("buttons_matrix", [[{'is_placeholder': True}]])
    keyboard = generate_post_keyboard(buttons_matrix, lang)
    preview_message = None

    try:
        if is_editing_session and post_data.get('message_id'):
            try:
                await bot.delete_message(post_data['chat_id'], post_data['message_id'])
            except Exception:
                pass

        message_kwargs = {
            "reply_markup": keyboard,
            "parse_mode": post_data.get('parse_mode', 'HTML'),
            "disable_web_page_preview": post_data['disable_web_page_preview']
        }
        
        # Media sozlamalarini olish
        has_spoiler = post_data.get('has_spoiler', False)
        show_caption_above = post_data.get('show_caption_above_media', False)
        
        # Asosiy media parametrlari
        media_kwargs = {
            "reply_markup": keyboard,
            "parse_mode": post_data.get('parse_mode', 'HTML'),
        }
        
        # has_spoiler va show_caption_above_media faqat photo, video, animation uchun
        current_type = post_data.get('content_type', 'text')
        if current_type in ['photo', 'video', 'animation']:
            media_kwargs["has_spoiler"] = has_spoiler
            media_kwargs["show_caption_above_media"] = show_caption_above

        settings_kb_kwargs = {
            "content_type": post_data['content_type'],
            "has_caption": bool(post_data.get('caption')),
            "lang": lang
        }
        reply_markup = get_post_settings_kb(**settings_kb_kwargs)
        
        if is_editing_session:
            await message.answer(get_text('content_updated', lang), reply_markup=reply_markup)
        else:
            await message.answer(get_text('content_received', lang), reply_markup=reply_markup)

        if is_incoming_media:
            permanent_file_id = await _get_permanent_file_id(bot, message, lang)
            if not permanent_file_id:
                return await message.answer(get_text('save_error', lang))

            post_data.update({
                'file_id': permanent_file_id,
                'title': getattr(message.audio, 'title', None),
                'performer': getattr(message.audio, 'performer', None),
                'file_name': getattr(message.document, 'file_name', None) or getattr(message.animation, 'file_name', None),
            })
            
            # Sticker qo'shimcha ma'lumotlarini saqlash
            if message.sticker:
                post_data.update({
                    'sticker_emoji': message.sticker.emoji,
                    'sticker_set_name': message.sticker.set_name,
                    'sticker_type': message.sticker.type,
                    'is_premium_sticker': bool(message.sticker.premium_animation),
                    'custom_emoji_id': message.sticker.custom_emoji_id,
                })

        current_type = post_data.get('content_type', 'text')
        file_id = post_data.get('file_id')
        caption = post_data.get('caption')

        if current_type == 'location':
            preview_message = await bot.send_location(
                message.chat.id, 
                latitude=post_data['latitude'], 
                longitude=post_data['longitude'],
                reply_markup=keyboard
            )
        elif current_type == 'poll':
            preview_message = await bot.send_poll(
                message.chat.id,
                question=post_data.get('poll_question', ''),
                options=post_data.get('poll_options', []),
                is_anonymous=post_data.get('poll_is_anonymous', True),
                allows_multiple_answers=post_data.get('poll_allows_multiple_answers', False),
                correct_option_id=post_data.get('poll_correct_option_id'),
                type='quiz' if post_data.get('poll_is_quiz', False) else 'regular',
                explanation=post_data.get('poll_explanation'),
                reply_markup=keyboard
            )
        elif current_type == 'dice':
            preview_message = await bot.send_dice(
                message.chat.id,
                emoji=post_data.get('dice_emoji', '🎲'),
                reply_markup=keyboard
            )
        elif current_type == 'text':
            preview_message = await message.answer(post_data['text'], **message_kwargs)
        elif current_type == 'photo':
            preview_message = await bot.send_photo(message.chat.id, file_id, caption=caption, **media_kwargs)
        elif current_type == 'video':
            preview_message = await bot.send_video(message.chat.id, file_id, caption=caption, **media_kwargs)
        elif current_type == 'audio':
            preview_message = await bot.send_audio(message.chat.id, file_id, caption=caption, **media_kwargs)
        elif current_type == 'document':
            preview_message = await bot.send_document(message.chat.id, file_id, caption=caption, **media_kwargs)
        elif current_type == 'voice':
            preview_message = await bot.send_voice(message.chat.id, file_id, caption=caption, **media_kwargs)
        elif current_type == 'video_note':
            preview_message = await bot.send_video_note(message.chat.id, file_id, reply_markup=keyboard)
        elif current_type == 'sticker':
            preview_message = await bot.send_sticker(message.chat.id, file_id, reply_markup=keyboard)
        elif current_type == 'animation':
            preview_message = await bot.send_animation(message.chat.id, file_id, caption=caption, **media_kwargs)
        elif current_type == 'paid_media':
            from aiogram.types import InputPaidMediaPhoto, InputPaidMediaVideo
            media_types = post_data.get('paid_media_types', [])
            file_ids = post_data.get('paid_media_file_ids', [])
            paid_price = post_data.get('paid_price', 1)
            
            input_media_list = []
            for media_type, f_id in zip(media_types, file_ids):
                if media_type == 'photo':
                    input_media_list.append(InputPaidMediaPhoto(media=f_id))
                else:
                    input_media_list.append(InputPaidMediaVideo(media=f_id))
            
            preview_message = await bot.send_paid_media(
                chat_id=message.chat.id,
                star_count=paid_price,
                media=input_media_list,
                caption=caption,
                parse_mode=post_data.get('parse_mode', 'HTML'),
                show_caption_above_media=post_data.get('show_caption_above_media', False),
                reply_markup=keyboard
            )

        if preview_message:
            post_data['message_id'] = preview_message.message_id
            post_data['chat_id'] = preview_message.chat.id
            await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)
            
            if config.STORAGE_CHANNEL_ID and not is_editing_session:
                try:
                    user_info_text = format_user_info(message.from_user, lang)
                    if is_incoming_media:
                        await message.copy_to(config.STORAGE_CHANNEL_ID)
                        await bot.send_message(config.STORAGE_CHANNEL_ID, user_info_text, parse_mode="HTML")
                    elif current_type == 'text':
                        total_text = (post_data.get('text') or "") + "\n\n" + user_info_text
                        if len(total_text) <= 4096:
                            await bot.send_message(config.STORAGE_CHANNEL_ID, total_text, parse_mode="HTML")
                        else:
                            await bot.send_message(config.STORAGE_CHANNEL_ID, post_data.get('text') or "", parse_mode="HTML")
                            await bot.send_message(config.STORAGE_CHANNEL_ID, user_info_text.strip(), parse_mode="HTML")
                except Exception as e:
                    logging.error(f"Postni log kanalga yuborishda xatolik: {e}")


    except TelegramBadRequest as e:
        if "can't parse entities" in str(e).lower():
            error_mode = f"<code>{post_data.get('parse_mode', 'HTML')}</code>"
            await message.answer(get_text('parse_mode_error_user', lang).format(error_mode=error_mode))
        else:
            logging.error(f"Postni qabul qilishda Telegram xatoligi: {e}")
            await message.answer(get_text('save_error', lang))
    except Exception as e:
        logging.error(f"Postni qabul qilishda kutilmagan xatolik: {e}")
        await message.answer(get_text('save_error', lang))
