"""
Avto Imzo (Auto Signature) handler'lari
Foydalanuvchilar uchun avtomatik imzo funksiyasi
"""

from aiogram import Router, F, types
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from xdata_handlers.translator import get_text
from xdata_handlers.database import (
    get_user_auto_signature,
    toggle_auto_signature,
    update_auto_signature_text,
    get_user_language
)
from post_handlers.xinline_keyboard import (
    get_auto_signature_settings_kb,
    get_auto_signature_back_kb,
    get_auto_signature_cancel_kb
)

router = Router()


class AutoSignatureState(StatesGroup):
    """Avto imzo matnini kiritish uchun state"""
    enter_text = State()


def _normalize_lang(lang_code: str) -> str:
    """Til kodini normalize qiladi"""
    if not lang_code:
        return 'uzl'
    lang = lang_code[:2].lower()
    valid_langs = ['uz', 'ru', 'en', 'ar', 'az', 'de', 'es', 'fr', 'it', 'kg', 'kz', 'tj', 'tk', 'tr']
    if lang not in valid_langs:
        return 'uzl'
    return 'uzl' if lang == 'uz' else lang


def _build_settings_text(settings: dict, lang: str) -> str:
    """Sozlamalar matnini yaratadi - soddalashtirilgan"""
    signature_text = settings['text'] or '—'
    text = f"<b>✍️ avtoimzo sozlamalari :</b>\n\n<b>imzo: </b>{signature_text}"
    return text


@router.callback_query(F.data == "auto_sig_settings")
async def show_auto_signature_settings(callback: CallbackQuery):
    """Avto imzo sozlamalari menyusini ko'rsatadi (callback orqali)"""
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    
    # Foydalanuvchi sozlamalarini olish
    settings = await get_user_auto_signature(user_id)
    
    # Xabar matnini yaratish
    text = _build_settings_text(settings, lang)
    
    # Klaviaturani olish
    keyboard = get_auto_signature_settings_kb(settings, lang)
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        # Agar tahrirlash mumkin bo'lmasa, yangi xabar yuborish
        await callback.message.answer(text, reply_markup=keyboard)
    
    await callback.answer()


async def show_auto_signature_settings_reply(message: Message, state: FSMContext):
    """Avto imzo sozlamalari menyusini ko'rsatadi (reply button orqali)"""
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    # State ma'lumotlarini tekshirish
    data = await state.get_data()
    logger.info(f"show_auto_signature_settings_reply: user_id={user_id}, post_data_exists={bool(data.get('post_data'))}, state={await state.get_state()}")

    # Foydalanuvchi sozlamalarini olish
    settings = await get_user_auto_signature(user_id)

    # Agar imzo matni kiritilmagan bo'lsa, birinchi matn kiritishni so'rash
    if not settings.get('text'):
        await state.set_state(AutoSignatureState.enter_text)
        await state.update_data(auto_sig_source='reply_button', is_new_signature=True)
        
        logger.info(f"Yangi imzo matni kiritish rejimi: user_id={user_id}")

        text = "<b>imzo matnini kiriting :</b>\n\n<b>misol: </b><code>@channel_name | kanalga obuna bo'ling!</code>"
        keyboard = get_auto_signature_cancel_kb(lang)

        settings_msg = await message.answer(text, reply_markup=keyboard)
        await state.update_data(settings_message_id=settings_msg.message_id)
        return

    # Xabar matnini yaratish
    text = _build_settings_text(settings, lang)

    # Klaviaturani olish
    keyboard = get_auto_signature_settings_kb(settings, lang)

    # Yangi xabar yuborish
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "auto_sig_toggle")
async def toggle_auto_signature_handler(callback: CallbackQuery):
    """Avto imzoni yoqish/o'chirish"""
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    
    # Holatni o'zgartirish
    new_state = await toggle_auto_signature(user_id)
    
    # Yangilangan sozlamalarni olish
    settings = await get_user_auto_signature(user_id)
    
    # Xabar matnini yangilash
    text = _build_settings_text(settings, lang)
    keyboard = get_auto_signature_settings_kb(settings, lang)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    
    # Alert ko'rsatish
    if new_state:
        await callback.answer(get_text('auto_signature_enabled', lang))
    else:
        await callback.answer(get_text('auto_signature_disabled', lang))


@router.callback_query(F.data == "auto_sig_edit_text")
async def start_edit_signature_text(callback: CallbackQuery, state: FSMContext):
    """Imzo matnini o'zgartirishni boshlaydi"""
    lang = await get_user_language(callback.from_user.id)
    
    # State'ga o'tish va manba ni saqlash
    await state.set_state(AutoSignatureState.enter_text)
    await state.update_data(auto_sig_source='edit_button')
    
    text = "<b>imzo matniki kiriting :</b>\n\n<b>misol: </b><code>@channel_name | kanalga obuna bo'ling!</code>"
    keyboard = get_auto_signature_back_kb(lang)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    # Tahrirlash rejimida message_id o'zgarmaydi, saqlash shart emas
    await state.update_data(settings_message_id=callback.message.message_id)
    await callback.answer()


@router.callback_query(F.data == "auto_sig_cancel_new")
async def cancel_new_signature(callback: CallbackQuery, state: FSMContext):
    """Yangi imzo qo'shishni bekor qilish"""
    await state.clear()
    
    text = "<b>✍️ avtoimzo qo'shish bekor qilindi</b>\n\nsiz xoxlagan vaqt yangi imzo qo'sha olasiz, imzo qo'shish uchun autoimzo tugmasini bosing"
    
    await callback.message.edit_text(text)
    await callback.answer()


@router.message(AutoSignatureState.enter_text)
async def save_signature_text(message: Message, state: FSMContext):
    """Foydalanuvchi kiritgan imzo matnini saqlaydi va postni yangilaydi"""
    from post_handlers.xinline_keyboard import generate_post_keyboard
    from post_handlers.post_handler import PostCreation, apply_auto_signature
    import logging
    logger = logging.getLogger(__name__)

    lang = await get_user_language(message.from_user.id)
    user_id = message.from_user.id
    text = message.text
    
    logger.info(f"save_signature_text chaqirildi: user_id={user_id}, text={text[:20]}...")

    # Matnni saqlash
    await update_auto_signature_text(user_id, text)

    # State'dan ma'lumot olish
    data = await state.get_data()
    source = data.get('auto_sig_source')
    post_data = data.get('post_data', {})
    buttons_matrix = data.get('buttons_matrix', [])
    settings_message_id = data.get('settings_message_id')
    
    logger.info(f"State ma'lumotlari: source={source}, post_data_exists={bool(post_data)}, buttons_count={len(buttons_matrix)}")

    # State'ni tozalash
    await state.clear()

    # Agar reply button yoki edit button'dan kelgan bo'lsa va post mavjud bo'lsa, postni yangilash
    if source in ('reply_button', 'edit_button') and post_data:
        # Post ma'lumotlarini yangilash
        content_type = post_data.get('content_type', 'text')

        # Avto imzoni qo'llash
        if content_type == 'text':
            # Asl matnni olish - faqat birinchi marta saqlangan bo'lsa
            if 'original_text' not in post_data:
                post_data['original_text'] = post_data.get('text', '')
            original_text = post_data['original_text']
            if original_text:
                signed_text = await apply_auto_signature(user_id, original_text)
                post_data['text'] = signed_text
        else:
            # Asl caption ni olish - faqat birinchi marta saqlangan bo'lsa
            if 'original_caption' not in post_data:
                post_data['original_caption'] = post_data.get('caption', '')
            original_caption = post_data['original_caption']
            if original_caption:
                signed_caption = await apply_auto_signature(user_id, original_caption)
                post_data['caption'] = signed_caption

        # Postni qayta chizish
        chat_id = post_data.get('chat_id')
        message_id = post_data.get('message_id')

        if chat_id and message_id:
            try:
                # Avvalgi postni o'chirish
                await message.bot.delete_message(chat_id=chat_id, message_id=message_id)

                # Yangi keyboard
                new_keyboard = generate_post_keyboard(buttons_matrix, lang)

                # Postni qayta yuborish
                file_id = post_data.get("file_id")
                caption = post_data.get("caption")
                post_text = post_data.get("text")
                parse_mode = post_data.get("parse_mode", 'HTML')
                has_spoiler = post_data.get('has_spoiler', False)

                sent_message = None

                if content_type == 'text':
                    sent_message = await message.bot.send_message(
                        chat_id=chat_id,
                        text=post_text or '',
                        reply_markup=new_keyboard,
                        parse_mode=parse_mode
                    )
                elif content_type == 'photo':
                    sent_message = await message.bot.send_photo(
                        chat_id=chat_id,
                        photo=file_id,
                        caption=caption,
                        reply_markup=new_keyboard,
                        parse_mode=parse_mode,
                        has_spoiler=has_spoiler
                    )
                elif content_type == 'video':
                    sent_message = await message.bot.send_video(
                        chat_id=chat_id,
                        video=file_id,
                        caption=caption,
                        reply_markup=new_keyboard,
                        parse_mode=parse_mode,
                        has_spoiler=has_spoiler
                    )

                if sent_message:
                    post_data['message_id'] = sent_message.message_id
                    await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)
                    await state.set_state(PostCreation.configuring_post)

            except Exception as e:
                logger.error(f"Postni yangilashda xatolik: {e}")  # Xatolikni log qilish

    # Avvalgi sozlamalar xabarini o'chirish (agar mavjud bo'lsa)
    if settings_message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=settings_message_id)
        except Exception:
            pass  # Xabar allaqachon o'chirilgan bo'lishi mumkin

    # Yangilangan sozlamalarni olish
    settings = await get_user_auto_signature(user_id)

    # Xabar matnini yaratish
    response_text = _build_settings_text(settings, lang)
    keyboard = get_auto_signature_settings_kb(settings, lang)

    # Postdan keyin yangi sozlamalar xabarini yuborish
    await message.answer(response_text, reply_markup=keyboard)


@router.callback_query(F.data == "settings_back")
async def back_to_settings(callback: CallbackQuery):
    """Post sozlamalari menyusiga qaytish (avto imzo endi faqat post yaratishda)"""
    await callback.message.delete()
    await callback.answer(get_text('back_to_settings_msg', await get_user_language(callback.from_user.id)))