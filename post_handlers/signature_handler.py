"""
Avto Imzo (Auto Signature) handler'lari
Foydalanuvchilar uchun avtomatik imzo funksiyasi
"""

from aiogram import Router, F, types
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from xdata_handlers.translator import get_text
from post_handlers.localize_filter import LocalizedText
from xdata_handlers.database import (
    get_user_auto_signature,
    toggle_auto_signature,
    update_auto_signature_text,
    get_user_language,
    get_user_sent_posts
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
async def show_auto_signature_settings(callback: CallbackQuery, state: FSMContext):
    """Avto imzo sozlamalari menyusini ko'rsatadi (callback orqali)"""
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    
    # State dan ma'lumot olish - agar avtoimzo matn kiritish rejimidan kelgan bo'lsa
    current_state = await state.get_state()
    data = await state.get_data()
    
    # Agar AutoSignatureState.enter_text holatida bo'lsa (matn kiritishdan orqaga qaytish)
    if current_state == 'AutoSignatureState:enter_text':
        post_data = data.get('post_data', {})
        buttons_matrix = data.get('buttons_matrix', [])
        
        # Avtoimzo state ni tozalash
        await state.clear()
        
        # Agar post ma'lumotlari mavjud bo'lsa, ularni qayta tiklash
        if post_data:
            await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)
            from post_handlers.post_handler import PostCreation
            await state.set_state(PostCreation.configuring_post)
            
            # Postni qayta chizish
            chat_id = post_data.get('chat_id')
            message_id = post_data.get('message_id')
            
            if chat_id and message_id:
                try:
                    from post_handlers.xinline_keyboard import generate_post_keyboard
                    new_keyboard = generate_post_keyboard(buttons_matrix, lang)
                    
                    content_type = post_data.get('content_type', 'text')
                    if content_type == 'text':
                        post_text = post_data.get('text', '')
                        await callback.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=post_text,
                            reply_markup=new_keyboard,
                            parse_mode='HTML'
                        )
                    else:
                        caption = post_data.get('caption', '')
                        await callback.bot.edit_message_caption(
                            chat_id=chat_id,
                            message_id=message_id,
                            caption=caption,
                            reply_markup=new_keyboard,
                            parse_mode='HTML'
                        )
                    logger.info(f"Post qayta chizildi orqaga tugmasidan so'ng: user_id={user_id}")
                except Exception as e:
                    logger.error(f"Postni qayta chizishda xatolik: {e}")
    
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
async def toggle_auto_signature_handler(callback: CallbackQuery, state: FSMContext):
    """Avto imzoni yoqish/o'chirish va shu sessiyadagi postni tahrirlash"""
    import json
    import logging
    from post_handlers.post_handler import apply_auto_signature, PostCreation
    from post_handlers.xinline_keyboard import generate_post_keyboard
    
    logger = logging.getLogger(__name__)
    
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    bot = callback.bot
    
    # Holatni o'zgartirish
    new_state = await toggle_auto_signature(user_id)
    
    # Yangilangan sozlamalarni olish
    settings = await get_user_auto_signature(user_id)
    
    # FSM dan joriy sessiya post ma'lumotlarini olish
    data = await state.get_data()
    post_data = data.get('post_data', {})
    buttons_matrix = data.get('buttons_matrix', [])
    
    # Agar post mavjud bo'lsa va imzo matni bor bo'lsa, postni tahrirlash
    if post_data and settings.get('text'):
        try:
            content_type = post_data.get('content_type', 'text')
            chat_id = post_data.get('chat_id')
            message_id = post_data.get('message_id')
            
            if content_type == 'text':
                current_text = post_data.get('text', '')
                original_text = post_data.get('original_text', current_text)
                
                if new_state:
                    # Yoqilgan - imzoni qo'shish
                    new_text = await apply_auto_signature(user_id, original_text)
                else:
                    # O'chirilgan - imzoni olib tashlash
                    signature = settings.get('text', '').strip()
                    if signature and original_text.rstrip().endswith(signature.rstrip()):
                        new_text = original_text.rstrip()
                        for sep in ['\n\n', '\n', '']:
                            check = sep + signature
                            if new_text.endswith(check):
                                new_text = new_text[:-len(check)].rstrip()
                                break
                    else:
                        new_text = original_text
                
                post_data['text'] = new_text
                
                # Postni tahrirlash
                if chat_id and message_id and new_text != current_text:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=new_text,
                        parse_mode='HTML'
                    )
            else:
                # Media postlar uchun caption
                current_caption = post_data.get('caption', '')
                original_caption = post_data.get('original_caption', current_caption)
                
                if new_state:
                    # Yoqilgan - imzoni qo'shish
                    new_caption = await apply_auto_signature(user_id, original_caption)
                else:
                    # O'chirilgan - imzoni olib tashlash
                    signature = settings.get('text', '').strip()
                    if signature and original_caption.rstrip().endswith(signature.rstrip()):
                        new_caption = original_caption.rstrip()
                        for sep in ['\n\n', '\n', '']:
                            check = sep + signature
                            if new_caption.endswith(check):
                                new_caption = new_caption[:-len(check)].rstrip()
                                break
                    else:
                        new_caption = original_caption
                
                post_data['caption'] = new_caption
                
                # Caption ni tahrirlash
                if chat_id and message_id and new_caption != current_caption:
                    await bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=message_id,
                        caption=new_caption,
                        parse_mode='HTML'
                    )
            
            # State yangilash
            await state.update_data(post_data=post_data)
            
        except Exception as e:
            logger.error(f"Postni tahrirlashda xatolik: {e}")
    
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
    """Yangi imzo qo'shishni bekor qilish - faqat matn kiritish jarayonini to'xtatadi"""
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    
    # State dan faqat avtoimzo bilan bog'liq ma'lumotlarni olish
    data = await state.get_data()
    post_data = data.get('post_data', {})
    buttons_matrix = data.get('buttons_matrix', [])
    settings_message_id = data.get('settings_message_id')
    
    # Avtoimzo bilan bog'liq state ma'lumotlarini tozalash
    keys_to_remove = ['auto_sig_source', 'is_new_signature', 'settings_message_id']
    for key in keys_to_remove:
        if key in data:
            del data[key]
    
    # Faqat avtoimzo state ni tozalash, post_data va buttons_matrix ni saqlash
    await state.clear()
    
    # Agar post ma'lumotlari mavjud bo'lsa, ularni qayta tiklash
    if post_data:
        await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)
        # Post yaratish holatiga qaytarish
        from post_handlers.post_handler import PostCreation
        await state.set_state(PostCreation.configuring_post)
        
        # Postni qayta chizish (agar mavjud bo'lsa)
        chat_id = post_data.get('chat_id')
        message_id = post_data.get('message_id')
        
        if chat_id and message_id:
            try:
                from post_handlers.xinline_keyboard import generate_post_keyboard
                new_keyboard = generate_post_keyboard(buttons_matrix, lang)
                
                content_type = post_data.get('content_type', 'text')
                if content_type == 'text':
                    post_text = post_data.get('text', '')
                    await callback.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=post_text,
                        reply_markup=new_keyboard,
                        parse_mode='HTML'
                    )
                else:
                    caption = post_data.get('caption', '')
                    await callback.bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=message_id,
                        caption=caption,
                        reply_markup=new_keyboard,
                        parse_mode='HTML'
                    )
                logger.info(f"Post qayta chizildi bekor qilishdan so'ng: user_id={user_id}")
            except Exception as e:
                logger.error(f"Postni qayta chizishda xatolik: {e}")
    
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


# ==================== Reply Keyboard Button Handlers for AutoSignatureState ====================

async def cancel_signature_and_redirect(message: Message, state: FSMContext, target_handler_func):
    """Autoimzo jarayonini bekor qilib, boshqa handler ga yo'naltiradi"""
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    # State dan ma'lumot olish
    data = await state.get_data()
    post_data = data.get('post_data', {})
    buttons_matrix = data.get('buttons_matrix', [])
    settings_message_id = data.get('settings_message_id')
    
    logger.info(f"Autoimzo bekor qilindi reply tugma orqali: user_id={user_id}, handler={target_handler_func.__name__}")
    
    # Avtoimzo state ni tozalash
    await state.clear()
    
    # Agar post ma'lumotlari mavjud bo'lsa, ularni qayta tiklash
    if post_data:
        await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)
        from post_handlers.post_handler import PostCreation
        await state.set_state(PostCreation.configuring_post)
        
        # Postni qayta chizish
        chat_id = post_data.get('chat_id')
        message_id = post_data.get('message_id')
        
        if chat_id and message_id:
            try:
                from post_handlers.xinline_keyboard import generate_post_keyboard
                new_keyboard = generate_post_keyboard(buttons_matrix, lang)
                
                content_type = post_data.get('content_type', 'text')
                if content_type == 'text':
                    post_text = post_data.get('text', '')
                    await message.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=post_text,
                        reply_markup=new_keyboard,
                        parse_mode='HTML'
                    )
                else:
                    caption = post_data.get('caption', '')
                    await message.bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=message_id,
                        caption=caption,
                        reply_markup=new_keyboard,
                        parse_mode='HTML'
                    )
                logger.info(f"Post qayta chizildi reply tugma bosilganda: user_id={user_id}")
            except Exception as e:
                logger.error(f"Postni qayta chizishda xatolik: {e}")
    
    # Sozlamalar xabarini o'chirish
    if settings_message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=settings_message_id)
        except Exception:
            pass
    
    # Target handler ni chaqirish
    await target_handler_func(message, state)


@router.message(AutoSignatureState.enter_text, LocalizedText('preview_btn'))
async def handle_preview_button_in_signature(message: Message, state: FSMContext):
    """Autoimzo matn kiritishda Ko'rish tugmasi bosilganda"""
    from post_handlers.reply_handler import preview_post_handler
    from aiogram import Bot
    bot = message.bot
    await cancel_signature_and_redirect(message, state, lambda m, s: preview_post_handler(m, s, bot))


@router.message(AutoSignatureState.enter_text, LocalizedText('settings_btn'))
async def handle_settings_button_in_signature(message: Message, state: FSMContext):
    """Autoimzo matn kiritishda Sozlamalar tugmasi bosilganda"""
    from post_handlers.reply_handler import settings_menu_handler
    await cancel_signature_and_redirect(message, state, settings_menu_handler)


@router.message(AutoSignatureState.enter_text, LocalizedText('get_buttons_btn'))
async def handle_buttons_button_in_signature(message: Message, state: FSMContext):
    """Autoimzo matn kiritishda Tugma (+ Qo'shish) tugmasi bosilganda"""
    from post_handlers.reply_handler import get_buttons_handler
    await cancel_signature_and_redirect(message, state, get_buttons_handler)


@router.message(AutoSignatureState.enter_text, LocalizedText('auto_signature_btn'))
async def handle_auto_sig_button_in_signature(message: Message, state: FSMContext):
    """Autoimzo matn kiritishda Avto imzo tugmasi bosilganda - settings ko'rsatadi"""
    await cancel_signature_and_redirect(message, state, show_auto_signature_settings_reply)


@router.message(AutoSignatureState.enter_text, LocalizedText('back_btn'))
async def handle_back_button_in_signature(message: Message, state: FSMContext):
    """Autoimzo matn kiritishda Orqaga tugmasi bosilganda"""
    import logging
    logger = logging.getLogger(__name__)
    
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    # State dan ma'lumot olish
    data = await state.get_data()
    post_data = data.get('post_data', {})
    buttons_matrix = data.get('buttons_matrix', [])
    settings_message_id = data.get('settings_message_id')
    
    logger.info(f"Autoimzo bekor qilindi Orqaga tugmasi orqali: user_id={user_id}")
    
    # Avtoimzo state ni tozalash
    await state.clear()
    
    # Agar post ma'lumotlari mavjud bo'lsa, ularni qayta tiklash
    if post_data:
        await state.update_data(post_data=post_data, buttons_matrix=buttons_matrix)
        from post_handlers.post_handler import PostCreation
        await state.set_state(PostCreation.configuring_post)
        
        # Postni qayta chizish
        chat_id = post_data.get('chat_id')
        message_id = post_data.get('message_id')
        
        if chat_id and message_id:
            try:
                from post_handlers.xinline_keyboard import generate_post_keyboard
                new_keyboard = generate_post_keyboard(buttons_matrix, lang)
                
                content_type = post_data.get('content_type', 'text')
                if content_type == 'text':
                    post_text = post_data.get('text', '')
                    await message.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=post_text,
                        reply_markup=new_keyboard,
                        parse_mode='HTML'
                    )
                else:
                    caption = post_data.get('caption', '')
                    await message.bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=message_id,
                        caption=caption,
                        reply_markup=new_keyboard,
                        parse_mode='HTML'
                    )
                logger.info(f"Post qayta chizildi Orqaga tugmasidan so'ng: user_id={user_id}")
            except Exception as e:
                logger.error(f"Postni qayta chizishda xatolik: {e}")
    
    # Sozlamalar xabarini o'chirish
    if settings_message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=settings_message_id)
        except Exception:
            pass
    
    # Orqaga qaytish xabarini yuborish
    await message.answer(get_text('back_btn', lang))


@router.message(AutoSignatureState.enter_text, LocalizedText('done_btn'))
async def handle_done_button_in_signature(message: Message, state: FSMContext):
    """Autoimzo matn kiritishda Tayyor tugmasi bosilganda"""
    from post_handlers.done_handler import done_post_creation
    from aiogram import Bot
    bot = message.bot
    await cancel_signature_and_redirect(message, state, lambda m, s: done_post_creation(m, s, bot))


@router.message(AutoSignatureState.enter_text, LocalizedText('cancel_btn'))
async def handle_cancel_button_in_signature(message: Message, state: FSMContext):
    """Autoimzo matn kiritishda Bekor qilish tugmasi bosilganda"""
    from post_handlers.reply_handler import cancel_post_creation_callback
    # Bekor qilish callback sifatida ishlaydi, lekin message ni ham qayta ishlamiz
    lang = await get_user_language(message.from_user.id)
    from post_handlers.xreply_keyboard import get_main_menu
    await state.clear()
    await message.answer("❌ Post bekor qilindi", reply_markup=get_main_menu(lang, message.from_user.id))


@router.message(AutoSignatureState.enter_text, LocalizedText('edit_content_btn'))
async def handle_edit_content_button_in_signature(message: Message, state: FSMContext):
    """Autoimzo matn kiritishda Postni tahrirlash tugmasi bosilganda"""
    from post_handlers.reply_handler import edit_content_handler
    await cancel_signature_and_redirect(message, state, edit_content_handler)


@router.message(AutoSignatureState.enter_text, LocalizedText('media_settings_btn'))
async def handle_media_settings_button_in_signature(message: Message, state: FSMContext):
    """Autoimzo matn kiritishda Media tugmasi bosilganda"""
    from post_handlers.reply_handler import media_settings_reply_handler
    await cancel_signature_and_redirect(message, state, media_settings_reply_handler)


@router.message(AutoSignatureState.enter_text, LocalizedText('watermark_btn'))
async def handle_watermark_button_in_signature(message: Message, state: FSMContext):
    """Autoimzo matn kiritishda Suv belgisi tugmasi bosilganda"""
    from post_handlers.reply_handler import watermark_reply_handler
    await cancel_signature_and_redirect(message, state, watermark_reply_handler)


@router.message(AutoSignatureState.enter_text, LocalizedText('quiz_btn'))
async def handle_quiz_button_in_signature(message: Message, state: FSMContext):
    """Autoimzo matn kiritishda Viktorina tugmasi bosilganda"""
    from post_handlers.reply_handler import quiz_reply_handler
    await cancel_signature_and_redirect(message, state, quiz_reply_handler)


@router.message(AutoSignatureState.enter_text, LocalizedText('edit_confirm_btn'))
async def handle_edit_confirm_button_in_signature(message: Message, state: FSMContext):
    """Autoimzo matn kiritishda Tahrirlashni tasdiqlash tugmasi bosilganda"""
    from post_handlers.done_handler import done_post_creation
    from aiogram import Bot
    bot = message.bot
    await cancel_signature_and_redirect(message, state, lambda m, s: done_post_creation(m, s, bot))