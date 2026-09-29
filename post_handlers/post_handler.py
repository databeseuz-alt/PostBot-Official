import re
import html
import logging

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
from xdata_handlers.database import get_user_language, get_user_post_settings, get_user_auto_signature
from xdata_handlers.translator import get_text
from post_handlers.localize_filter import LocalizedText

logger = logging.getLogger(__name__)

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

    waiting_for_media_settings = State()
    waiting_for_paid_price = State()
    waiting_for_location = State()

    waiting_for_watermark_settings = State()
    waiting_for_watermark_photo = State()

    waiting_for_delete_timer = State()
    waiting_for_reply_setting = State()

    waiting_for_reply_message_id = State()
    waiting_for_auto_delete_time = State()

def clean_text_for_default_mode(text: str | None) -> str | None:
    """Matndan barcha HTML va Markdown formatlash belgilarini olib tashlaydi."""
    if not text:
        return None

    cleaned_text = text
    
    # Custom emoji larni vaqtincha saqlash
    import re
    emoji_pattern = r'<tg-emoji[^>]*>.*?</tg-emoji>'
    emoji_matches = re.findall(emoji_pattern, cleaned_text)
    emoji_placeholders = []
    
    # Emoji larni vaqtincha placeholder bilan almashtirish
    for i, emoji_match in enumerate(emoji_matches):
        placeholder = f"__EMOJI_PLACEHOLDER_{i}__"
        emoji_placeholders.append(emoji_match)
        cleaned_text = cleaned_text.replace(emoji_match, placeholder, 1)
    
    if BeautifulSoup:
        soup = BeautifulSoup(cleaned_text, 'html.parser')
        cleaned_text = soup.get_text()
    else:
        cleaned_text = re.sub(r'<[^>]+>', '', cleaned_text)

    markdown_chars = ['*', '_', '~', '`', '|']
    for char in markdown_chars:
        cleaned_text = cleaned_text.replace(char, '')

    # Placeholder larni asl emoji larga qaytarish
    for i, emoji_match in enumerate(emoji_placeholders):
        placeholder = f"__EMOJI_PLACEHOLDER_{i}__"
        cleaned_text = cleaned_text.replace(placeholder, emoji_match)

    return cleaned_text

async def apply_auto_signature(user_id: int, text: str | None) -> str | None:
    """Foydalanuvchining avto imzosini matnga qo'shadi.
    Agar imzo allaqachon mavjud bo'lsa, qayta qo'shmaydi."""
    if not text:
        return text
    
    try:
        settings = await get_user_auto_signature(user_id)
        
        if not settings or not settings.get('enabled'):
            return text
        
        signature = settings.get('text', '').strip()
        if not signature:
            return text
        
        position = settings.get('position', 'bottom')
        newline = settings.get('newline', True)
        
        separator = '\n\n' if newline else '\n'
        
        # Tekshirish: imzo allaqachon mavjudmi?
        text_stripped = text.rstrip()
        signature_stripped = signature.strip()
        
        if position == 'top':
            # Yuqorida imzo borligini tekshirish
            if text_stripped.startswith(signature_stripped):
                return text
            return f"{signature}{separator}{text}"
        else:  # bottom
            # Pastda imzo borligini tekshirish
            if text_stripped.endswith(signature_stripped):
                return text
            return f"{text}{separator}{signature}"
    except Exception:
        return text


async def maybe_apply_auto_signature(user_id: int, post_data: dict) -> dict:
    """Post ma'lumotlariga avto imzoni qo'llaydi (agar yoqilgan bo'lsa).
    Agar allaqachon imzolangan bo'lsa, qayta imzolamaydi."""
    if not post_data:
        return post_data
    
    content_type = post_data.get('content_type', 'text')
    
    if content_type == 'text':
        current_text = post_data.get('text')
        if current_text:
            # Asl matnni saqlash (faqat birinchi marta)
            if 'original_text' not in post_data:
                post_data['original_text'] = current_text
            signed_text = await apply_auto_signature(user_id, current_text)
            post_data['text'] = signed_text
    else:
        # Media uchun caption ga qo'shish
        current_caption = post_data.get('caption')
        if current_caption:
            # Asl caption ni saqlash (faqat birinchi marta)
            if 'original_caption' not in post_data:
                post_data['original_caption'] = current_caption
            signed_caption = await apply_auto_signature(user_id, current_caption)
            post_data['caption'] = signed_caption
    
    return post_data


def validate_and_fix_html(html_text: str) -> str:
    """
    HTML matnni tekshiradi va xatolarni tuzatadi.
    Noto'g'ri HTML teglarini olib tashlaydi va parse qilinishini ta'minlaydi.
    """
    if not html_text:
        return ""
    
    # Noto'g'ri tugash teglarini topish va tuzatish
    import re
    
    # Custom emoji uchun maxsus usul - ularni vaqtincha almashtirish
    emoji_pattern = r'<tg-emoji[^>]*>.*?</tg-emoji>'
    emoji_matches = re.findall(emoji_pattern, html_text)
    emoji_placeholders = []
    
    # Emoji larni vaqtincha placeholder bilan almashtirish
    for i, emoji_match in enumerate(emoji_matches):
        placeholder = f"__EMOJI_PLACEHOLDER_{i}__"
        emoji_placeholders.append(emoji_match)
        html_text = html_text.replace(emoji_match, placeholder, 1)
    
    # Oddiy HTML validation - ochiq teglarni topish
    tag_pattern = r'<(/?)([a-zA-Z][a-zA-Z0-9]*)(?:\s+[^>]*)?>'
    
    def replace_invalid_tags(match):
        full_tag = match.group(0)
        is_closing = match.group(1) == '/'
        tag_name = match.group(2).lower()
        
        # Ruxsat etilgan teglar ro'yxati (tg-emoji dan tashqari)
        allowed_tags = {
            'b', 'i', 'u', 's', 'code', 'pre', 'a', 'tg-spoiler',
            'blockquote', 'strong', 'em'
        }
        
        # Agar teg ruxsat etilgan bo'lmasa, uni olib tashlash
        if tag_name not in allowed_tags:
            return ""
        
        # Tegning to'g'ri formatlanishini tekshirish
        if '<' in full_tag and '>' not in full_tag:
            return ""
        
        return full_tag
    
    # Noto'g'ri teglarni tozalash (placeholder larni o'zgartirmaslik uchun)
    html_text = re.sub(tag_pattern, replace_invalid_tags, html_text)
    
    # Ortib qolgan ochiq teglarni yopish (tg-emoji dan tashqari)
    tag_stack = []
    tag_pattern_clean = r'<(/?)([a-zA-Z][a-zA-Z0-9]*)[^>]*>'
    
    for match in re.finditer(tag_pattern_clean, html_text):
        is_closing = match.group(1) == '/'
        tag_name = match.group(2).lower()
        
        if not is_closing and tag_name in ['b', 'i', 'u', 's', 'code', 'pre', 'blockquote']:
            tag_stack.append(tag_name)
        elif is_closing and tag_stack and tag_stack[-1] == tag_name:
            tag_stack.pop()
    
    # Ochiq qolgan teglarni yopish
    for tag in reversed(tag_stack):
        html_text += f'</{tag}>'
    
    # HTML entitiylarini to'g'rilash
    html_text = html.unescape(html_text)
    
    # Placeholder larni asl emoji larga qaytarish
    for i, emoji_match in enumerate(emoji_placeholders):
        placeholder = f"__EMOJI_PLACEHOLDER_{i}__"
        html_text = html_text.replace(placeholder, emoji_match)
    
    return html_text

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
                # Premium emojilarni shunchaki oddiy emoji sifatida qoldiramiz
                # Shunday qilib o'rtada xato yozuvlar chiqib qolmaydi
                tag_start, tag_end = "", ""

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

    final_html = "".join(res)
    return validate_and_fix_html(final_html)

def format_user_info(user: types.User, lang: str = 'uzl') -> str:
    """Foydalanuvchi ma'lumotlarini formatlash."""
    nickname = html.escape(user.full_name)
    username = f"@{user.username}" if user.username else "mavjud emas"

    return (
        f"\n\n-------------------------------\n"
        f"👤 nickname: <code>{nickname}</code>\n"
        f"🆔 user iD: <code>{user.id}</code>\n"
        f"📎 username: <code>{username}</code>"
    )

async def validate_storage_channel(bot: Bot) -> bool:
    """STORAGE_CHANNEL_ID ni tekshiradi va bot unga kirish huquqiga ega ekanligini tekshiradi."""
    if not config.STORAGE_CHANNEL_ID:
        return False
    
    try:
        # Kanalga xabar yuborish orqali tekshirish
        test_message = await bot.send_message(config.STORAGE_CHANNEL_ID, "Test", disable_notification=True)
        await bot.delete_message(config.STORAGE_CHANNEL_ID, test_message.message_id)
        return True
    except Exception:
        return False

async def _get_permanent_file_id(bot: Bot, message: Message, lang: str = 'uzl') -> str | None:
    """Faqat permanent file_id olish, log kanaliga yuborish BAJARILMAYDI"""
    # Faqat message'dan file_id ni qaytarish
    if message.voice:
        return message.voice.file_id
    elif message.photo:
        return message.photo[-1].file_id
    elif message.video:
        return message.video.file_id
    elif message.audio:
        return message.audio.file_id
    elif message.document:
        return message.document.file_id
    elif message.video_note:
        return message.video_note.file_id
    elif message.sticker:
        return message.sticker.file_id
    elif message.animation:
        return message.animation.file_id
    return None

async def process_turbo_mode_if_enabled(message: Message, state: FSMContext, bot: Bot, post_data: dict, buttons_matrix: list, old_data: dict, lang: str) -> bool:
    """
    Agar turbo rejim yoqilgan bo'lsa:
    - Postni bazaga saqlaydi
    - Agar kanallar bo'lsa, kanal tanlash klaviaturasini chiqaradi
    - Aks holda kanal qo'shish taklifini chiqaradi
    - True qaytaradi (turbo rejim bajarilganligini bildirish uchun)
    """
    if not old_data.get('turbo_enabled', False):
        return False
        
    user_id = message.from_user.id
    turbo_action = old_data.get('turbo_action', 'now')
    
    from xdata_handlers.database import add_post_to_db, get_user_channels
    from post_handlers.send_handler import PostSending
    from post_handlers.xinline_keyboard import get_channel_list_keyboard, get_add_channel_with_post_keyboard
    
    post_code = await add_post_to_db(
        user_id,
        post_data,
        buttons_matrix,
        admin_ids=config.ADMIN_IDS
    )
    
    if not post_code:
        await message.answer(get_text('save_error', lang))
        return True
        
    user_channels = await get_user_channels(user_id)
    
    await state.set_state(PostSending.choosing_channel_to_send)
    await state.update_data(
        post_code=post_code,
        turbo_mode=True,
        turbo_action=turbo_action,
        schedule_post_code=post_code
    )
    
    if not user_channels:
        await message.answer(
            get_text('need_channel_msg', lang),
            reply_markup=get_add_channel_with_post_keyboard(post_code)
        )
    elif turbo_action == 'now' and len(user_channels) == 1:
        # Foydalanuvchida 1 ta kanal bo'lsa va turbo_action == 'now' bo'lsa:
        # 3 sekund kutilish va bekor qilish tugmasi bilan kanalga yuboriladi!
        ch = user_channels[0]
        from post_handlers.send_handler import start_turbo_countdown_and_send
        await start_turbo_countdown_and_send(
            bot=bot,
            user_id=user_id,
            post_code=post_code,
            channel_id=ch['channel_id'],
            channel_name=ch['channel_name'],
            lang=lang,
            state=state
        )
        return True
    elif turbo_action == 'schedule' and len(user_channels) == 1:
        # 1 ta kanal bo'lsa, to'g'ridan-to'g'ri jadval vaqtini so'raymiz
        from post_handlers.schedule_handler import ScheduleManage, get_schedule_quick_keyboard
        ch = user_channels[0]
        await state.update_data(schedule_post_code=post_code, schedule_channel_id=ch['channel_id'])
        await state.set_state(ScheduleManage.waiting_for_custom_time)
        text = get_text('schedule_when_to_send', lang) + "\n\n" + get_text('schedule_enter_date_format', lang)
        await message.answer(text, reply_markup=get_schedule_quick_keyboard(lang), parse_mode="HTML")
        return True
    else:
        turbo_title = get_text('turbo_choose_channel_now', lang) if turbo_action == 'now' else get_text('turbo_choose_channel_schedule', lang)
        
        await message.answer(
            turbo_title,
            reply_markup=get_channel_list_keyboard(user_channels, post_code),
            parse_mode="HTML"
        )
    return True

async def handle_location_content(message: Message, state: FSMContext, bot: Bot, old_data: dict, lang: str):
    """Location kontentini qayta ishlash"""
    location = message.location
    if not location:
        return await message.answer(get_text('wrong_format', lang))

    await state.set_state(PostCreation.configuring_post)

    is_editing_session = 'editing_post_code' in old_data

    location_data = {
        'content_type': 'location',
        'latitude': location.latitude,
        'longitude': location.longitude,
        'title': getattr(location, 'title', None),
        'address': getattr(location, 'address', None),
        'parse_mode': 'HTML'
    }

    post_data = old_data.get('post_data', {})
    post_data.update(location_data)
    post_data['chat_id'] = message.chat.id

    buttons_matrix = old_data.get("buttons_matrix", [[{'is_placeholder': True}]])
    keyboard = generate_post_keyboard(buttons_matrix, lang)

    location_text = f"📍 Joylashuv\n\nKenglik: {location.latitude}\nUzunlik: {location.longitude}"
    if getattr(location, 'title', None):
        location_text += f"\nNomi: {getattr(location, 'title')}"
    if getattr(location, 'address', None):
        location_text += f"\nManzil: {getattr(location, 'address')}"

    settings_kb_kwargs = {
        "content_type": 'location',
        "has_caption": False,
        "lang": lang,
        "is_paid": post_data.get('is_paid', False)
    }
    reply_markup = get_post_settings_kb(**settings_kb_kwargs)

    is_turbo = old_data.get('turbo_enabled', False)
    if is_turbo:
        await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)
        await process_turbo_mode_if_enabled(message, state, bot, post_data, buttons_matrix, old_data, lang)
        return

    if is_editing_session:
        await message.answer(get_text('content_updated', lang), reply_markup=reply_markup)
    else:
        await message.answer(get_text('content_received', lang), reply_markup=reply_markup)

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
                # Location va foydalanuvchi ma'lumotlarini bitta xabarda yuborish
                sent_location = await bot.send_location(
                    config.STORAGE_CHANNEL_ID,
                    latitude=location.latitude,
                    longitude=location.longitude
                )
                # Foydalanuvchi ma'lumotlarini reply sifatida yuborish
                if sent_location:
                    await bot.send_message(
                        config.STORAGE_CHANNEL_ID,
                        user_info_text,
                        parse_mode="HTML",
                        reply_to_message_id=sent_location.message_id
                    )
            except Exception:
                pass

async def handle_paid_media_content(message: Message, state: FSMContext, bot: Bot, old_data: dict, lang: str):
    """Pulli media kontentini qayta ishlash"""
    paid_media = getattr(message, 'paid_media', None)
    if not paid_media:
        return await message.answer(get_text('wrong_format', lang))

    await state.set_state(PostCreation.configuring_post)

    is_editing_session = 'editing_post_code' in old_data

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
        'caption': message.html_text if message.caption else None,
        'parse_mode': 'HTML',
        'is_paid': True,
        'chat_id': message.chat.id,
        'show_caption_above_media': getattr(message, 'show_caption_above_media', False)
    })

    buttons_matrix = old_data.get("buttons_matrix", [[{'is_placeholder': True}]])
    keyboard = generate_post_keyboard(buttons_matrix, lang)

    media_text = f"📦 Pulli media ({len(file_ids)} ta fayl)"
    if message.caption:
        media_text += f"\n\n{message.html_text}"

    settings_kb_kwargs = {
        "content_type": 'paid_media',
        "has_caption": bool(message.caption),
        "lang": lang,
        "is_paid": True # Pulli media bo'lgani uchun har doim True
    }
    reply_markup = get_post_settings_kb(**settings_kb_kwargs)

    is_turbo = old_data.get('turbo_enabled', False)
    if is_turbo:
        await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)
        await process_turbo_mode_if_enabled(message, state, bot, post_data, buttons_matrix, old_data, lang)
        return

    if is_editing_session:
        await message.answer(get_text('content_updated', lang), reply_markup=reply_markup)
    else:
        await message.answer(get_text('content_received', lang), reply_markup=reply_markup)

    try:
        from aiogram.types import InputPaidMediaPhoto, InputPaidMediaVideo

        input_media_list = []
        for media_type, file_id in zip(media_types, file_ids):
            if media_type == 'photo':
                input_media_list.append(InputPaidMediaPhoto(media=file_id))
            else:
                input_media_list.append(InputPaidMediaVideo(media=file_id))

        paid_price = post_data.get('paid_price', 1)

        preview_message = await bot.send_paid_media(
            chat_id=message.chat.id,
            star_count=paid_price,
            media=input_media_list,
            caption=message.html_text if message.caption else None,
            parse_mode='HTML',
            show_caption_above_media=post_data.get('show_caption_above_media', False),
            reply_markup=keyboard
        )

        if preview_message:
            post_data['message_id'] = preview_message.message_id
            post_data['chat_id'] = message.chat.id
            await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)

    except Exception:
        preview_message = await message.answer(media_text, reply_markup=keyboard, parse_mode='HTML')
        if preview_message:
            post_data['message_id'] = preview_message.message_id
            post_data['chat_id'] = preview_message.chat.id
            await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)

            if config.STORAGE_CHANNEL_ID and not is_editing_session:
                try:
                    user_info_text = format_user_info(message.from_user, lang)
                    # Paid media va foydalanuvchi ma'lumotlarini bitta xabarda yuborish
                    sent_media = await message.copy_to(config.STORAGE_CHANNEL_ID)
                    # Foydalanuvchi ma'lumotlarini reply sifatida yuborish
                    if sent_media:
                        await bot.send_message(
                            config.STORAGE_CHANNEL_ID,
                            user_info_text,
                            parse_mode="HTML",
                            reply_to_message_id=sent_media.message_id
                        )
                except Exception:
                    pass

async def handle_dice_content(message: Message, state: FSMContext, bot: Bot, old_data: dict, lang: str):
    """Dice kontentini qayta ishlash"""
    dice = message.dice
    if not dice:
        return await message.answer(get_text('wrong_format', lang))

    await state.set_state(PostCreation.configuring_post)

    is_editing_session = 'editing_post_code' in old_data

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

    dice_text = f"🎲 Dice: {dice_emoji} = {dice_value}"

    settings_kb_kwargs = {
        "content_type": 'dice',
        "has_caption": False,
        "lang": lang,
        "is_paid": post_data.get('is_paid', False)
    }
    reply_markup = get_post_settings_kb(**settings_kb_kwargs)

    is_turbo = old_data.get('turbo_enabled', False)
    if is_turbo:
        await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)
        await process_turbo_mode_if_enabled(message, state, bot, post_data, buttons_matrix, old_data, lang)
        return

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
                # Dice va foydalanuvchi ma'lumotlarini bitta xabarda yuborish
                sent_dice = await bot.send_dice(
                    config.STORAGE_CHANNEL_ID,
                    emoji=dice_emoji
                )
                # Foydalanuvchi ma'lumotlarini reply sifatida yuborish
                if sent_dice:
                    await bot.send_message(
                        config.STORAGE_CHANNEL_ID,
                        user_info_text,
                        parse_mode="HTML",
                        reply_to_message_id=sent_dice.message_id
                    )
            except Exception:
                pass

async def handle_poll_content(message: Message, state: FSMContext, bot: Bot, old_data: dict, lang: str):
    """Poll kontentini qayta ishlash"""
    poll = message.poll
    if not poll:
        return await message.answer(get_text('wrong_format', lang))

    await state.set_state(PostCreation.configuring_post)

    is_editing_session = 'editing_post_code' in old_data

    poll_data = {
        'content_type': 'poll',
        'poll_id': poll.id,
        'question': poll.question,
        'options': [option.text for option in poll.options],
        'is_anonymous': poll.is_anonymous,
        'type': poll.type,
        'allows_multiple_answers': poll.allows_multiple_answers,
        'correct_option_id': poll.correct_option_id,
        'explanation': poll.explanation,
        'explanation_entities': poll.explanation_entities,
        'open_period': poll.open_period,
        'close_date': poll.close_date,
        'is_closed': poll.is_closed,
        'parse_mode': 'HTML',
        'chat_id': message.chat.id
    }

    post_data = old_data.get('post_data', {})
    post_data.update(poll_data)
    
    # If sending new poll content, reset buttons_matrix for new poll
    if message.content_type == 'poll':
        buttons_matrix = [[{'is_placeholder': True}]]
    else:
        buttons_matrix = old_data.get("buttons_matrix", [[{'is_placeholder': True}]])
    keyboard = generate_post_keyboard(buttons_matrix, lang)

    poll_text = f"📊 So'rovnoma: {poll.question}\n\n"
    for i, option in enumerate(poll.options, 1):
        poll_text += f"{i}. {option.text}\n"

    settings_kb_kwargs = {
        "content_type": 'poll',
        "has_caption": False,
        "lang": lang,
        "is_paid": post_data.get('is_paid', False)
    }
    reply_markup = get_post_settings_kb(**settings_kb_kwargs)

    is_turbo = old_data.get('turbo_enabled', False)
    if is_turbo:
        await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)
        await process_turbo_mode_if_enabled(message, state, bot, post_data, buttons_matrix, old_data, lang)
        return

    if is_editing_session:
        await message.answer(get_text('content_updated', lang), reply_markup=reply_markup)
    else:
        await message.answer(get_text('content_received', lang), reply_markup=reply_markup)

    try:
        logger.debug(f"Poll yuborish: chat_id={message.chat.id}, question={poll.question}")
        preview_message = await bot.send_poll(
            chat_id=message.chat.id,
            question=poll.question,
            options=[option.text for option in poll.options],
            is_anonymous=poll.is_anonymous,
            type=poll.type,
            allows_multiple_answers=poll.allows_multiple_answers,
            correct_option_id=poll.correct_option_id,
            explanation=poll.explanation,
            explanation_entities=poll.explanation_entities,
            open_period=poll.open_period,
            close_date=poll.close_date,
            is_closed=poll.is_closed,
            reply_markup=keyboard
        )
        logger.debug(f"Poll yuborildi: message_id={preview_message.message_id}, chat_id={preview_message.chat.id}")

        if preview_message:
            post_data['message_id'] = preview_message.message_id
            post_data['chat_id'] = preview_message.chat.id
            await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)

            if config.STORAGE_CHANNEL_ID and not is_editing_session:
                # STORAGE_CHANNEL_ID ni tekshirish
                is_valid_channel = await validate_storage_channel(bot)
                if is_valid_channel:
                    try:
                        user_info_text = format_user_info(message.from_user, lang)
                        # Poll va foydalanuvchi ma'lumotlarini bitta xabarda yuborish
                        sent_poll = await bot.send_poll(
                            config.STORAGE_CHANNEL_ID,
                            question=poll.question,
                            options=[option.text for option in poll.options],
                            is_anonymous=poll.is_anonymous,
                            type=poll.type,
                            allows_multiple_answers=poll.allows_multiple_answers,
                            correct_option_id=poll.correct_option_id,
                            explanation=poll.explanation,
                            explanation_entities=poll.explanation_entities,
                            open_period=poll.open_period,
                            close_date=poll.close_date,
                            is_closed=poll.is_closed,
                            reply_markup=keyboard
                        )
                        # Foydalanuvchi ma'lumotlarini reply sifatida yuborish
                        if sent_poll:
                            await bot.send_message(
                                config.STORAGE_CHANNEL_ID,
                                user_info_text,
                                parse_mode="HTML",
                                reply_to_message_id=sent_poll.message_id
                            )
                    except Exception as e:
                        # Xatolikni bazaga yozish
                        from xdata_handlers.database import log_user_error
                        error_msg = f"Poll yuborishda xatolik: {str(e)}"
                        await log_user_error(message.from_user.id, error_msg)
                else:
                    # STORAGE_CHANNEL_ID noto'g'ri yoki botda huquqi yo'q
                    from xdata_handlers.database import log_user_error
                    error_msg = f"Poll yuborishda xatolik: STORAGE_CHANNEL_ID noto'g'ri yoki botda huquqi yo'q"
                    await log_user_error(message.from_user.id, error_msg)
        else:
            # preview_message None bo'lsa ham xatolikni yozish
            from xdata_handlers.database import log_user_error
            await log_user_error(message.from_user.id, "Poll yuborishda xabar yaratilmadi")
    except Exception as e:
        preview_message = await message.answer(poll_text, reply_markup=keyboard, parse_mode='HTML')
        if preview_message:
            post_data['message_id'] = preview_message.message_id
            post_data['chat_id'] = preview_message.chat.id
            await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)
        else:
            # preview_message None bo'lsa ham xatolikni yozish
            from xdata_handlers.database import log_user_error
            await log_user_error(message.from_user.id, f"Pollni oddiy xabar sifatida yuborishda xatolik: {str(e)}")

    # Poll uchun tugmalarni qo'shish
    if preview_message:
        try:
            await bot.edit_message_reply_markup(
                chat_id=preview_message.chat.id,
                message_id=preview_message.message_id,
                reply_markup=keyboard
            )
        except Exception as e:
            error_str = str(e).lower()
            if "message is not modified" in error_str:
                # Bu xatolikni bazaga yozmaymiz, chunki bu normal holat
                pass
            else:
                # Boshqa xatoliklar uchun bazaga yozish
                from xdata_handlers.database import log_user_error
                error_msg = f"Pollga tugma qo'shishda xatolik: {str(e)}"
                await log_user_error(message.from_user.id, error_msg)
    else:
        # preview_message None bo'lsa ham xatolikni yozish
        from xdata_handlers.database import log_user_error
        await log_user_error(message.from_user.id, "Pollga tugma qo'shishda xabar topilmadi")

    # Poll uchun tugmalarni qo'shish (qo'shimcha tekshiruv)
    if preview_message and not is_editing_session:
        try:
            await bot.edit_message_reply_markup(
                chat_id=preview_message.chat.id,
                message_id=preview_message.message_id,
                reply_markup=keyboard
            )
        except Exception as e:
            error_str = str(e).lower()
            if "message is not modified" in error_str:
                # Bu xatolikni bazaga yozmaymiz, chunki bu normal holat
                pass
            else:
                # Boshqa xatoliklar uchun bazaga yozish
                from xdata_handlers.database import log_user_error
                error_msg = f"Pollga tugma qo'shishda qo'shimcha xatolik: {str(e)}"
                await log_user_error(message.from_user.id, error_msg)

@post_router.message(
    PostCreation.waiting_for_content,
    F.forward_origin
)
async def handle_forwarded_message(message: types.Message, state: FSMContext, bot: Bot):
    """Boshqa kanaldan forward qilingan xabarlarni qabul qilish"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    # Emoji-only validation - warn if user forwards only emojis without text
    if message.content_type == 'text' and message.text:
        text = message.text.strip()
        import re
        text_without_emojis = re.sub(r'[\U0001F000-\U0001F9FF]|[\U0001F600-\U0001F64F]|[\U0001F300-\U0001F5FF]|[\U0001F680-\U0001F6FF]|[\U0001F1E0-\U0001F1FF]', '', text)
        text_without_emojis = text_without_emojis.replace('🔵', '').replace('🔴', '').replace('🟢', '').replace(' ', '')
        if not text_without_emojis:
            return await message.answer(get_text('emoji_only_warning', lang))
    
    forward_origin = message.forward_origin
    
    if forward_origin.type == "channel":
        # Forward qilingan xabarni to'g'ridan-to'g'ri qayta ishlash
        # Admin huquqi talab qilinmaydi!
        await state.set_state(PostCreation.configuring_post)
        
        old_data = await state.get_data()
        is_editing_session = 'editing_post_code' in old_data
        post_data = old_data.get('post_data', {})
        
        message_has_spoiler = False
        message_caption_above = getattr(message, 'show_caption_above_media', False)
        
        if message.content_type == 'photo' and message.photo:
            message_has_spoiler = getattr(message.photo[-1], 'has_spoiler', False) or getattr(message, 'has_media_spoiler', False)
        elif message.content_type == 'video' and message.video:
            message_has_spoiler = getattr(message.video, 'has_spoiler', False) or getattr(message, 'has_media_spoiler', False)
        elif message.content_type == 'animation' and message.animation:
            message_has_spoiler = getattr(message.animation, 'has_spoiler', False) or getattr(message, 'has_media_spoiler', False)
        
        new_text = message.html_text if message.text else None
        new_caption = message.html_text if message.caption else None
        is_incoming_media = message.content_type != 'text' and message.content_type != 'dice'
        
        # Media types that don't support captions
        media_without_caption = ('video_note', 'sticker', 'location', 'voice', 'dice')
        
        # Post data ni to'ldirish
        if message.content_type == 'text':
            post_data['content_type'] = 'text'
            post_data['text'] = new_text
        elif message.content_type in ('photo', 'video', 'animation', 'document', 'audio', 'voice', 'video_note', 'sticker'):
            file_id = await _get_permanent_file_id(bot, message, lang)
            post_data['content_type'] = message.content_type
            post_data['file_id'] = file_id
            post_data['caption'] = new_caption
            post_data['has_spoiler'] = message_has_spoiler
        elif message.content_type == 'location':
            location = message.location
            if location:
                post_data['content_type'] = 'location'
                post_data['latitude'] = location.latitude
                post_data['longitude'] = location.longitude
                post_data['title'] = getattr(location, 'title', None)
                post_data['address'] = getattr(location, 'address', None)
        elif message.content_type == 'voice':
            file_id = await _get_permanent_file_id(bot, message, lang)
            post_data['content_type'] = 'voice'
            post_data['file_id'] = file_id
            post_data['caption'] = new_caption
        elif message.content_type == 'video_note':
            file_id = await _get_permanent_file_id(bot, message, lang)
            post_data['content_type'] = 'video_note'
            post_data['file_id'] = file_id
        elif message.content_type == 'sticker':
            file_id = await _get_permanent_file_id(bot, message, lang)
            post_data['content_type'] = 'sticker'
            post_data['file_id'] = file_id
        elif message.content_type == 'poll':
            poll = message.poll
            if poll:
                post_data['content_type'] = 'poll'
                post_data['question'] = poll.question
                post_data['options'] = [opt.text for opt in poll.options]
                post_data['is_anonymous'] = poll.is_anonymous
                post_data['allows_multiple_answers'] = poll.allows_multiple_answers
        elif message.content_type == 'dice':
            dice = message.dice
            if dice:
                post_data['content_type'] = 'dice'
                post_data['emoji'] = dice.emoji
                post_data['value'] = dice.value
        else:
            await message.answer(
                get_text('wrong_format', lang),
                parse_mode="HTML"
            )
            return
        
        post_data['chat_id'] = message.chat.id
        
        buttons_matrix = old_data.get("buttons_matrix", [[{'is_placeholder': True}]])
        keyboard = generate_post_keyboard(buttons_matrix, lang)
        
        # Forward ma'lumotlarini saqlash (keyinchalik foydalanish uchun)
        post_data['forward_from_chat_id'] = forward_origin.chat.id
        post_data['forward_from_message_id'] = forward_origin.message_id
        
        # AVVAL "content received" xabarini yuborish
        settings_kb_kwargs = {
            "content_type": post_data.get('content_type', 'text'),
            "has_caption": bool(new_caption),
            "lang": lang,
            "is_paid": post_data.get('is_paid', False)
        }
        reply_markup = get_post_settings_kb(**settings_kb_kwargs)
        
        is_turbo = old_data.get('turbo_enabled', False)
        if is_turbo:
            await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)
            await process_turbo_mode_if_enabled(message, state, bot, post_data, buttons_matrix, old_data, lang)
            return

        await message.answer(
            get_text('content_received', lang),
            reply_markup=reply_markup
        )
        
        # Preview yuborish
        if message.content_type == 'photo' and message.photo:
            file_id = post_data.get('file_id')
            if file_id:
                preview_message = await bot.send_photo(
                    message.chat.id,
                    photo=file_id,
                    caption=new_caption,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
            else:
                await message.answer(
                    get_text('content_received', lang),
                    reply_markup=get_post_settings_kb(content_type='photo', has_caption=bool(new_caption), lang=lang, is_paid=False)
                )
                return
        elif message.content_type == 'video' and message.video:
            file_id = post_data.get('file_id')
            if file_id:
                preview_message = await bot.send_video(
                    message.chat.id,
                    video=file_id,
                    caption=new_caption,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
            else:
                await message.answer(
                    get_text('content_received', lang),
                    reply_markup=get_post_settings_kb(content_type='video', has_caption=bool(new_caption), lang=lang, is_paid=False)
                )
                return
        elif message.content_type == 'animation' and message.animation:
            file_id = post_data.get('file_id')
            if file_id:
                preview_message = await bot.send_animation(
                    message.chat.id,
                    animation=file_id,
                    caption=new_caption,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
            else:
                await message.answer(
                    get_text('content_received', lang),
                    reply_markup=get_post_settings_kb(content_type='animation', has_caption=bool(new_caption), lang=lang, is_paid=False)
                )
                return
        elif message.content_type == 'document' and message.document:
            file_id = post_data.get('file_id')
            if file_id:
                preview_message = await bot.send_document(
                    message.chat.id,
                    document=file_id,
                    caption=new_caption,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
            else:
                await message.answer(
                    get_text('content_received', lang),
                    reply_markup=get_post_settings_kb(content_type='document', has_caption=bool(new_caption), lang=lang, is_paid=False)
                )
                return
        elif message.content_type == 'audio' and message.audio:
            file_id = post_data.get('file_id')
            if file_id:
                preview_message = await bot.send_audio(
                    message.chat.id,
                    audio=file_id,
                    caption=new_caption,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
            else:
                await message.answer(
                    get_text('content_received', lang),
                    reply_markup=get_post_settings_kb(content_type='audio', has_caption=bool(new_caption), lang=lang, is_paid=False)
                )
                return
        elif message.content_type == 'voice' and message.voice:
            file_id = post_data.get('file_id')
            if file_id:
                preview_message = await bot.send_voice(
                    message.chat.id,
                    voice=file_id,
                    caption=new_caption,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
            else:
                await message.answer(
                    get_text('content_received', lang),
                    reply_markup=get_post_settings_kb(content_type='voice', has_caption=bool(new_caption), lang=lang, is_paid=False)
                )
                return
        elif message.content_type == 'video_note' and message.video_note:
            file_id = post_data.get('file_id')
            if file_id:
                preview_message = await bot.send_video_note(
                    message.chat.id,
                    video_note=file_id,
                    reply_markup=keyboard
                )
            else:
                await message.answer(
                    get_text('content_received', lang),
                    reply_markup=get_post_settings_kb(content_type='video_note', has_caption=False, lang=lang, is_paid=False)
                )
                return
        elif message.content_type == 'sticker' and message.sticker:
            file_id = post_data.get('file_id')
            if file_id:
                preview_message = await bot.send_sticker(
                    message.chat.id,
                    sticker=file_id,
                    reply_markup=keyboard
                )
            else:
                await message.answer(
                    get_text('content_received', lang),
                    reply_markup=get_post_settings_kb(content_type='sticker', has_caption=False, lang=lang, is_paid=False)
                )
                return
        elif message.content_type == 'location':
            location = message.location
            preview_message = await bot.send_location(
                message.chat.id,
                latitude=location.latitude,
                longitude=location.longitude,
                reply_markup=keyboard
            )
        elif message.content_type == 'poll':
            poll = message.poll
            preview_message = await bot.send_poll(
                message.chat.id,
                question=poll.question,
                options=[opt.text for opt in poll.options],
                is_anonymous=poll.is_anonymous,
                allows_multiple_answers=poll.allows_multiple_answers,
                reply_markup=keyboard
            )
        elif message.content_type == 'dice':
            dice = message.dice
            preview_message = await bot.send_dice(
                message.chat.id,
                emoji=dice.emoji,
                reply_markup=keyboard
            )
        else:
            preview_message = await bot.send_message(
                message.chat.id,
                text=new_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
        
        if preview_message:
            post_data['message_id'] = preview_message.message_id
            post_data['chat_id'] = preview_message.chat.id
        
        await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)
        
        if is_turbo:
            await process_turbo_mode_if_enabled(message, state, bot, post_data, buttons_matrix, old_data, lang)
            return
        
        settings_kb_kwargs = {
            "content_type": post_data.get('content_type', 'text'),
            "has_caption": bool(new_caption),
            "lang": lang,
            "is_paid": post_data.get('is_paid', False)
        }
        reply_markup = get_post_settings_kb(**settings_kb_kwargs)
        
        # Storage channel ga saqlash (faqat matn va caption uchun, media uchun file_id kerak)
        if config.STORAGE_CHANNEL_ID and not is_editing_session and message.content_type == 'text':
            try:
                user_info_text = format_user_info(message.from_user, lang)
                sent = await bot.send_message(
                    config.STORAGE_CHANNEL_ID,
                    text=new_text,
                    parse_mode='HTML'
                )
                if sent:
                    await bot.send_message(
                        config.STORAGE_CHANNEL_ID,
                        user_info_text,
                        parse_mode="HTML",
                        reply_to_message_id=sent.message_id
                    )
            except Exception as e:
                logger.warning(f"Storage kanalga saqlashda xatolik: {e}")
                
    elif forward_origin.type == "user":
        await message.answer(
            get_text('forward_from_user_not_supported', lang),
            parse_mode="HTML"
        )
    elif forward_origin.type == "hidden_user":
        await message.answer(
            get_text('forward_from_hidden_not_supported', lang),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            get_text('forward_not_supported', lang),
            parse_mode="HTML"
        )


@post_router.message(
    PostCreation.waiting_for_content,
    ~LocalizedText('back_btn')
)
async def universal_content_handler(message: Message, state: FSMContext, bot: Bot, is_forwarded: bool = False):
    old_data = await state.get_data()
    lang = await get_user_language(message.from_user.id)

    if message.media_group_id:
        return await message.answer(get_text('albums_not_supported', lang))
    
    # Emoji-only validation - warn if user sends only emojis without text
    if message.content_type == 'text' and message.text:
        text = message.text.strip()
        import re
        # Remove emoji characters and check if anything remains
        text_without_emojis = re.sub(r'[\U0001F000-\U0001F9FF]|[\U0001F600-\U0001F64F]|[\U0001F300-\U0001F5FF]|[\U0001F680-\U0001F6FF]|[\U0001F1E0-\U0001F1FF]', '', text)
        # Also remove common symbols like 🔵🔴🟢 and spaces
        text_without_emojis = text_without_emojis.replace('🔵', '').replace('🔴', '').replace('🟢', '').replace(' ', '')
        if not text_without_emojis:
            return await message.answer(get_text('emoji_only_warning', lang))

    supported_types = ('text', 'photo', 'video', 'audio', 'document', 'video_note', 'voice', 'sticker', 'animation', 'paid_media', 'dice', 'location', 'poll')
    if message.content_type not in supported_types:
        return await message.answer(get_text('wrong_format', lang))


    if message.content_type == 'paid_media':
        return await handle_paid_media_content(message, state, bot, old_data, lang)

    if message.content_type == 'dice':
        return await handle_dice_content(message, state, bot, old_data, lang)

    if message.content_type == 'location':
        return await handle_location_content(message, state, bot, old_data, lang)

    if message.content_type == 'poll':
        return await handle_poll_content(message, state, bot, old_data, lang)

    await state.set_state(PostCreation.configuring_post)

    is_editing_session = 'editing_post_code' in old_data
    post_data = old_data.get('post_data', {})

    message_has_spoiler = False
    message_caption_above = getattr(message, 'show_caption_above_media', False)

    if message.content_type == 'photo' and message.photo:
        message_has_spoiler = getattr(message.photo[-1], 'has_spoiler', False) or getattr(message, 'has_media_spoiler', False)
    elif message.content_type == 'video' and message.video:
        message_has_spoiler = getattr(message.video, 'has_spoiler', False) or getattr(message, 'has_media_spoiler', False)
    elif message.content_type == 'animation' and message.animation:
        message_has_spoiler = getattr(message.animation, 'has_spoiler', False) or getattr(message, 'has_media_spoiler', False)

    new_text = message.html_text if message.text else None
    new_caption = message.html_text if message.caption else None
    is_incoming_media = message.content_type != 'text' and message.content_type != 'dice'

    is_delete_media = message.text == get_text('delete_media_btn', lang)
    is_delete_text = message.text == get_text('delete_text_btn', lang)
    is_action = is_delete_media or is_delete_text

    # Media types that don't support captions
    media_without_caption = ('video_note', 'sticker', 'location', 'voice', 'dice')
    
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
            old_content_type = post_data.get('content_type', 'text')
            
            # Handle: user sends text but old content was media without caption (video_note, sticker, location, etc.)
            # In this case, delete old media and show only text
            if not is_incoming_media and old_content_type in media_without_caption:
                # User is sending text, but old content was media that doesn't support text
                # Delete old media and use only text
                post_data['content_type'] = 'text'
                post_data['text'] = new_text
                post_data['caption'] = None
                post_data['file_id'] = None
            elif not is_incoming_media and old_content_type == 'poll':
                # User is sending text but old content was a poll
                # Replace poll question with the new text
                # Keep the existing options and other poll settings
                post_data['question'] = new_text
                
                # Check if user sends "anonim so'rov" - make it anonymous
                if new_text and 'anonim' in new_text.lower():
                    post_data['is_anonymous'] = True
            elif not is_incoming_media and old_content_type not in ('text', 'poll'):
                # User is sending text to media that supports caption
                # Convert to caption
                post_data['content_type'] = old_content_type  # Keep same content type
                post_data['caption'] = new_text
                post_data['text'] = None
            elif is_incoming_media:
                # Handle: user sends new media
                # If switching from old media to new media, clear old file_id
                if old_content_type != 'text' and old_content_type != message.content_type:
                    # User is replacing one media with another - clear old file_id
                    post_data['file_id'] = None
                
                # If old content had text and new media doesn't support caption, delete text
                if message.content_type in media_without_caption and post_data.get('text'):
                    # New media doesn't support caption, delete old text
                    post_data['text'] = None
                
                # Also clear caption if new media doesn't support captions (e.g., sticker replaces photo+caption)
                if message.content_type in media_without_caption and post_data.get('caption'):
                    post_data['caption'] = None
                
                if post_data.get('content_type') == 'text' and post_data.get('text') and new_caption is None:
                    if message.content_type not in media_without_caption:
                        post_data['caption'] = post_data['text']
                        post_data['text'] = None

                post_data['content_type'] = message.content_type
                if new_caption is not None and message.content_type not in media_without_caption:
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

    if is_incoming_media:
        if message_has_spoiler:
            post_data['has_spoiler'] = True
        if message_caption_above:
            post_data['show_caption_above_media'] = True

    post_data['chat_id'] = message.chat.id

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

        has_spoiler = post_data.get('has_spoiler', False)
        show_caption_above = post_data.get('show_caption_above_media', False)

        media_kwargs = {
            "reply_markup": keyboard,
            "parse_mode": post_data.get('parse_mode', 'HTML'),
        }

        # HTML matnini validatsiya qilish
        if post_data.get('parse_mode', 'HTML') == 'HTML':
            text_content = post_data.get('text') or post_data.get('caption', '')
            if text_content:
                validated_text = validate_and_fix_html(text_content)
                if post_data.get('text'):
                    post_data['text'] = validated_text
                if post_data.get('caption'):
                    post_data['caption'] = validated_text

        current_type = post_data.get('content_type', 'text')
        if current_type in ['photo', 'video', 'animation']:
            media_kwargs["has_spoiler"] = has_spoiler
            media_kwargs["show_caption_above_media"] = show_caption_above

        settings_kb_kwargs = {
            "content_type": post_data['content_type'],
            "has_caption": bool(post_data.get('caption')),
            "lang": lang,
            "is_paid": post_data.get('is_paid', False)
        }
        reply_markup = get_post_settings_kb(**settings_kb_kwargs)

        is_turbo = old_data.get('turbo_enabled', False)
        if not is_turbo:
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
        
        # Avto imzoni qo'llash
        post_data = await maybe_apply_auto_signature(message.from_user.id, post_data)
        # Yangilangan caption ni olish
        caption = post_data.get('caption') if current_type != 'text' else None
        # Text uchun ham yangilash
        if current_type == 'text':
            text = post_data.get('text')

        if is_turbo:
            await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)
            await process_turbo_mode_if_enabled(message, state, bot, post_data, buttons_matrix, old_data, lang)
            return

        if current_type == 'location':
            preview_message = await bot.send_location(
                message.chat.id, 
                latitude=post_data['latitude'], 
                longitude=post_data['longitude'],
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
                    sent_message = None

                    if is_incoming_media:
                        # Media uchun caption ga user_info qo'shish
                        new_caption = (caption or "") + user_info_text
                        # Telegram caption limit 1024
                        if len(new_caption) > 1024:
                            new_caption = (caption or "")[:900] + "..." + user_info_text

                        if current_type == 'photo':
                            sent_message = await bot.send_photo(
                                config.STORAGE_CHANNEL_ID, file_id, caption=new_caption,
                                parse_mode='HTML', show_caption_above_media=show_caption_above
                            )
                        elif current_type == 'video':
                            sent_message = await bot.send_video(
                                config.STORAGE_CHANNEL_ID, file_id, caption=new_caption,
                                parse_mode='HTML', show_caption_above_media=show_caption_above
                            )
                        elif current_type == 'audio':
                            sent_message = await bot.send_audio(
                                config.STORAGE_CHANNEL_ID, file_id, caption=new_caption,
                                parse_mode='HTML'
                            )
                        elif current_type == 'document':
                            sent_message = await bot.send_document(
                                config.STORAGE_CHANNEL_ID, file_id, caption=new_caption,
                                parse_mode='HTML'
                            )
                        elif current_type == 'voice':
                            sent_message = await bot.send_voice(
                                config.STORAGE_CHANNEL_ID, file_id, caption=new_caption,
                                parse_mode='HTML'
                            )
                        elif current_type == 'animation':
                            sent_message = await bot.send_animation(
                                config.STORAGE_CHANNEL_ID, file_id, caption=new_caption,
                                parse_mode='HTML', show_caption_above_media=show_caption_above
                            )
                        elif current_type == 'video_note':
                            # Video note caption qo'llamaydi, reply sifatida yuboramiz
                            sent_message = await bot.send_video_note(
                                config.STORAGE_CHANNEL_ID, file_id
                            )
                            if sent_message:
                                await bot.send_message(
                                    config.STORAGE_CHANNEL_ID, user_info_text,
                                    parse_mode="HTML", reply_to_message_id=sent_message.message_id
                                )
                        elif current_type == 'sticker':
                            # Sticker caption qo'llamaydi, reply sifatida yuboramiz
                            sent_message = await bot.send_sticker(
                                config.STORAGE_CHANNEL_ID, file_id
                            )
                            if sent_message:
                                await bot.send_message(
                                    config.STORAGE_CHANNEL_ID, user_info_text,
                                    parse_mode="HTML", reply_to_message_id=sent_message.message_id
                                )
                    elif current_type == 'text':
                        # Matn uchun user_info ni qo'shish
                        original_text = post_data.get('text') or ""
                        total_text = original_text + user_info_text
                        
                        if len(total_text) <= 4096:
                            # Hammasi bitta xabarga sig'adi
                            await bot.send_message(config.STORAGE_CHANNEL_ID, total_text, parse_mode="HTML")
                        else:
                            # Matn juda uzun - qisqartirib, oxiriga user_info qo'shish
                            # User_info uzunligini hisobga olib qisqartirish
                            truncate_length = 4096 - len(user_info_text) - 10  # 10 ta belgi zaxira
                            truncated_text = original_text[:truncate_length] + "...\n\n"
                            final_text = truncated_text + user_info_text
                            await bot.send_message(config.STORAGE_CHANNEL_ID, final_text, parse_mode="HTML")
                except Exception:
                    pass
                
                # Storage channel dan yangi file_id ni olish va saqlash
                if sent_message:
                    storage_file_id = None
                    if current_type == 'photo' and sent_message.photo:
                        storage_file_id = sent_message.photo[-1].file_id
                    elif current_type == 'video' and sent_message.video:
                        storage_file_id = sent_message.video.file_id
                    elif current_type == 'audio' and sent_message.audio:
                        storage_file_id = sent_message.audio.file_id
                    elif current_type == 'document' and sent_message.document:
                        storage_file_id = sent_message.document.file_id
                    elif current_type == 'voice' and sent_message.voice:
                        storage_file_id = sent_message.voice.file_id
                    elif current_type == 'animation' and sent_message.animation:
                        storage_file_id = sent_message.animation.file_id
                    elif current_type == 'video_note' and sent_message.video_note:
                        storage_file_id = sent_message.video_note.file_id
                    elif current_type == 'sticker' and sent_message.sticker:
                        storage_file_id = sent_message.sticker.file_id
                    
                    if storage_file_id:
                        post_data['storage_file_id'] = storage_file_id

        if is_turbo:
            await process_turbo_mode_if_enabled(message, state, bot, post_data, buttons_matrix, old_data, lang)
            return

    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        if "can't parse entities" in error_msg:
            # HTML parsing xatolik bo'lsa, parse_mode ni o'zgartirib qayta urinish
            try:
                # Parse_mode ni o'zgartirish
                post_data['parse_mode'] = None
                
                # Matnni tozalash
                text_content = post_data.get('text') or post_data.get('caption', '')
                if text_content:
                    # HTML teglarini olib tashlash
                    clean_text = clean_text_for_default_mode(text_content)
                    if post_data.get('text'):
                        post_data['text'] = clean_text
                    if post_data.get('caption'):
                        post_data['caption'] = clean_text
                
                # Xabarni qayta yuborish urinishi
                message_kwargs = {
                    "reply_markup": keyboard,
                    "parse_mode": None,
                    "disable_web_page_preview": post_data.get('disable_web_page_preview', False)
                }
                
                if post_data.get('content_type') == 'text':
                    preview_message = await message.answer(
                        post_data.get('text', ''), 
                        **message_kwargs
                    )
                else:
                    # Media uchun qayta urinish
                    current_type = post_data.get('content_type', 'text')
                    file_id = post_data.get('file_id')
                    caption = post_data.get('caption')
                    
                    if current_type == 'photo' and file_id:
                        preview_message = await bot.send_photo(
                            message.chat.id, file_id, caption=caption, **message_kwargs
                        )
                    elif current_type == 'video' and file_id:
                        preview_message = await bot.send_video(
                            message.chat.id, file_id, caption=caption, **message_kwargs
                        )
                    elif current_type == 'document' and file_id:
                        preview_message = await bot.send_document(
                            message.chat.id, file_id, caption=caption, **message_kwargs
                        )
                    elif current_type == 'audio' and file_id:
                        preview_message = await bot.send_audio(
                            message.chat.id, file_id, caption=caption, **message_kwargs
                        )
                    elif current_type == 'animation' and file_id:
                        preview_message = await bot.send_animation(
                            message.chat.id, file_id, caption=caption, **message_kwargs
                        )
                
                if preview_message:
                    post_data['message_id'] = preview_message.message_id
                    post_data['chat_id'] = preview_message.chat.id
                    await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)
                    
                    if is_turbo:
                        await process_turbo_mode_if_enabled(message, state, bot, post_data, buttons_matrix, old_data, lang)
                        return

                    # Success message
                    await message.answer(get_text('content_received', lang), reply_markup=get_post_settings_kb(
                        content_type=post_data['content_type'],
                        has_caption=bool(post_data.get('caption')),
                        lang=lang,
                        is_paid=post_data.get('is_paid', False)
                    ))
                    return
                    
            except Exception:
                pass
            
            # Agar qayta urinish ham xato bersa, xatolik xabarini ko'rsatish
            error_mode = f"<code>{post_data.get('parse_mode', 'HTML')}</code>"
            await message.answer(get_text('parse_mode_error_user', lang).format(error_mode=error_mode))
        else:
            await message.answer(get_text('save_error', lang))
    except Exception:
        await message.answer(get_text('save_error', lang))
