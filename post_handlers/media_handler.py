import asyncio
import logging

logger = logging.getLogger(__name__)

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from post_handlers.post_handler import PostCreation
from post_handlers.xinline_keyboard import get_media_settings_inline_kb
from post_handlers.xreply_keyboard import get_post_settings_kb
from post_handlers.localize_filter import LocalizedText
from xdata_handlers.database import get_user_language
from xdata_handlers.translator import get_text

media_router = Router()

@media_router.callback_query(PostCreation.waiting_for_media_settings, F.data == "media_toggle_position")
async def post_media_toggle_position(callback: types.CallbackQuery, state: FSMContext):
    """Post tahrirlashda joylashuvni almashtirish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    content_type = post_data.get('content_type', 'photo')
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))

    # Yangi qiymatni saqlash
    new_show_caption_above = not show_caption_above
    post_data['show_caption_above_media'] = new_show_caption_above
    await state.update_data(post_data=post_data)

    await state.set_state(PostCreation.waiting_for_media_settings)

    # Avval postni yangilash (yangi sozlamalar bilan)
    await redraw_post_with_callback(callback, state)

    # Keyin klaviaturani yangilash
    try:
        await callback.message.edit_reply_markup(
            reply_markup=get_media_settings_inline_kb(
                lang=lang,
                has_spoiler=has_spoiler,
                is_paid=is_paid,
                show_caption_above=new_show_caption_above,
                has_caption=has_caption,
                content_type=content_type,
                paid_price=post_data.get('paid_price', 1)
            )
        )
    except Exception:
        pass

    await callback.answer()

@media_router.callback_query(PostCreation.waiting_for_media_settings, F.data == "media_toggle_spoiler")
async def post_media_toggle_spoiler(callback: types.CallbackQuery, state: FSMContext):
    """Post tahrirlashda spoilerni yoqish/o'chirish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    content_type = post_data.get('content_type', 'photo')
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))

    post_data['has_spoiler'] = not has_spoiler
    await state.update_data(post_data=post_data)

    await state.set_state(PostCreation.waiting_for_media_settings)

    await callback.message.edit_reply_markup(
        reply_markup=get_media_settings_inline_kb(
            lang=lang,
            has_spoiler=not has_spoiler,
            is_paid=is_paid,
            show_caption_above=show_caption_above,
            has_caption=has_caption,
            content_type=content_type,
            paid_price=post_data.get('paid_price', 1)
        )
    )

    await redraw_post_with_callback(callback, state)
    await callback.answer()

@media_router.callback_query(PostCreation.waiting_for_media_settings, F.data == "media_toggle_paid")
async def post_media_toggle_paid(callback: types.CallbackQuery, state: FSMContext):
    """Post tahrirlashda pulli mediani yoqish/o'chirish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    content_type = post_data.get('content_type', 'photo')
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))

    new_paid = not is_paid
    post_data['is_paid'] = new_paid

    if new_paid:
        # Pulli media yoqilganda spoiler o'chiriladi
        post_data['has_spoiler'] = False
        has_spoiler = False
        if not post_data.get('paid_price'):
            post_data['paid_price'] = 1  # Default narx

    await state.update_data(post_data=post_data)
    await state.set_state(PostCreation.waiting_for_media_settings)

    # Faqat callback notification ko'rsatiladi
    status_text = "✅ Pulli media yoqildi" if new_paid else "❌ Pulli media o'chirildi"
    await callback.answer(status_text, show_alert=False)

    # Postni yangilash - o'chirmasdan tahrirlashga harakat qilish
    await redraw_post_with_callback(callback, state)

    # Media sozlamalari uchun state ni qayta tiklash (redraw_post_with_callback o'zgartirgan bo'lishi mumkin)
    await state.set_state(PostCreation.waiting_for_media_settings)

    # Media sozlamalari xabarini o'chirib yangidan yuborish (post bilan birga)
    chat_id = callback.message.chat.id
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    try:
        await callback.bot.send_message(
            chat_id=chat_id,
            text=get_text('media_settings_msg', lang),
            reply_markup=get_media_settings_inline_kb(
                lang=lang,
                has_spoiler=has_spoiler,
                is_paid=new_paid,
                show_caption_above=show_caption_above,
                has_caption=has_caption,
                content_type=content_type,
                paid_price=post_data.get('paid_price', 1)
            )
        )
    except Exception:
        pass

@media_router.message(
    PostCreation.waiting_for_media_settings,
    LocalizedText('media_settings_btn')
)
async def open_media_settings(message: Message, state: FSMContext):
    """Media sozlamalari menyusini ochish - inline klaviatura"""
    await open_media_settings_from_reply(message, state)

async def open_media_settings_from_reply(message: Message, state: FSMContext):
    """Media sozlamalari menyusini ochish - reply tugmadan chaqirish uchun"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(message.from_user.id)

    content_type = post_data.get('content_type', 'photo')
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))

    await state.set_state(PostCreation.waiting_for_media_settings)

    await message.answer(
        get_text('media_settings_msg', lang),
        reply_markup=get_media_settings_inline_kb(
            lang=lang,
            has_spoiler=has_spoiler,
            is_paid=is_paid,
            show_caption_above=show_caption_above,
            has_caption=has_caption,
            content_type=content_type,
            paid_price=post_data.get('paid_price', 1)
        )
    )


async def redraw_post_with_callback(callback: types.CallbackQuery, state: FSMContext):
    """Postni yangilangan sozlamalar bilan qayta chizish (callback uchun) - o'chirmasdan tahrirlash"""
    from post_handlers.xinline_keyboard import generate_post_keyboard

    data = await state.get_data()
    buttons_matrix = data.get("buttons_matrix", [])
    post_data = data.get("post_data", {})
    if not post_data:
        return

    chat_id = post_data.get("chat_id")
    message_id = post_data.get("message_id")

    user_id = callback.from_user.id if callback.from_user else post_data.get("user_id")
    lang = await get_user_language(user_id)

    new_keyboard = generate_post_keyboard(buttons_matrix, lang)

    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))
    content_type = post_data.get('content_type', 'text')

    file_id = post_data.get("file_id")
    caption = post_data.get("caption")
    parse_mode = post_data.get("parse_mode", 'HTML')

    if not chat_id or not message_id:
        return

    # Asl holatni tekshirish (paid media o'zgarganmi?)
    was_paid = post_data.get('was_paid', False)
    paid_state_changed = was_paid != is_paid

    try:
        if is_paid and content_type in ['photo', 'video']:
            # Pulli media uchun - agar holat o'zgarmagan bo'lsa, faqat caption ni tahrirlash
            if not paid_state_changed:
                try:
                    await callback.bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=message_id,
                        caption=caption,
                        parse_mode=parse_mode,
                        reply_markup=new_keyboard,
                        show_caption_above_media=show_caption_above
                    )
                    return
                except Exception:
                    # Agar tahrirlash ishlamasa, hech narsa qilmaymiz (post o'chirilmaydi)
                    return
            try:
                await callback.bot.delete_message(chat_id, message_id)
            except Exception:
                pass
            await send_new_post_with_settings(callback.message, state, post_data, new_keyboard)
            # Joriy holatni saqlash
            post_data['was_paid'] = is_paid
            await state.update_data(post_data=post_data)
            await state.set_state(PostCreation.configuring_post)
            return

        if content_type == 'photo':
            from aiogram.types import InputMediaPhoto
            media = InputMediaPhoto(
                media=file_id,
                caption=caption,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
            await callback.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=new_keyboard
            )
        elif content_type == 'video':
            from aiogram.types import InputMediaVideo
            media = InputMediaVideo(
                media=file_id,
                caption=caption,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
            await callback.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=new_keyboard
            )
        elif content_type == 'audio':
            from aiogram.types import InputMediaAudio
            media = InputMediaAudio(
                media=file_id,
                caption=caption,
                parse_mode=parse_mode
            )
            await callback.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=new_keyboard
            )
        elif content_type == 'document':
            from aiogram.types import InputMediaDocument
            media = InputMediaDocument(
                media=file_id,
                caption=caption,
                parse_mode=parse_mode
            )
            await callback.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=new_keyboard
            )
        elif content_type == 'animation':
            from aiogram.types import InputMediaAnimation
            media = InputMediaAnimation(
                media=file_id,
                caption=caption,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
            await callback.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=new_keyboard
            )
        elif content_type == 'text':
            await callback.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=caption or post_data.get('text', ''),
                parse_mode=parse_mode,
                reply_markup=new_keyboard
            )
        elif content_type == 'location':
            try:
                await callback.bot.delete_message(chat_id, message_id)
            except Exception:
                pass
            await send_new_post_with_settings(callback.message, state, post_data, new_keyboard)
        elif content_type == 'dice':
            try:
                await callback.bot.delete_message(chat_id, message_id)
            except Exception:
                pass
            await send_new_post_with_settings(callback.message, state, post_data, new_keyboard)
        else:
            await callback.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=new_keyboard
            )

        # Muvaffaqiyatli tahrirlashdan so'ng holatni saqlash
        if not is_paid:
            post_data['was_paid'] = False
            await state.update_data(post_data=post_data)

    except Exception:
        # Xatolik yuz berganda - o'chirib yangidan yuborish
        try:
            await callback.bot.delete_message(chat_id, message_id)
        except Exception:
            pass
        await send_new_post_with_settings(callback.message, state, post_data, new_keyboard)
        # Yangi xabar yuborilgandan so'ng holatni saqlash
        post_data['was_paid'] = is_paid
        await state.update_data(post_data=post_data)

async def send_new_post_with_settings(message: types.Message, state: FSMContext, post_data: dict, keyboard):
    """Postni yangi xabar sifatida yuborish va sozlamalarni ko'rsatish"""

    content_type = post_data.get('content_type', 'text')
    file_id = post_data.get('file_id')
    caption = post_data.get('caption')
    text = post_data.get('text')
    parse_mode = post_data.get('parse_mode', 'HTML')
    disable_preview = post_data.get('disable_web_page_preview', False)
    has_spoiler = post_data.get('has_spoiler', False)
    show_caption_above = post_data.get('show_caption_above_media', False)

    lang = await get_user_language(message.from_user.id)

    sent_message = None

    try:
        if content_type == 'text':
            sent_message = await message.answer(
                text or '',
                reply_markup=keyboard,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview
            )
        elif content_type == 'photo':
            is_paid = post_data.get('is_paid', False)
            paid_price = post_data.get('paid_price', 1)
            if is_paid:
                # Pulli media sifatida yuborish
                from aiogram.types import InputPaidMediaPhoto
                sent_message = await message.answer_paid_media(
                    star_count=paid_price,
                    media=[InputPaidMediaPhoto(media=file_id)],
                    caption=caption,
                    parse_mode=parse_mode,
                    show_caption_above_media=show_caption_above,
                    reply_markup=keyboard
                )
            else:
                sent_message = await message.answer_photo(
                    file_id,
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode=parse_mode,
                    has_spoiler=has_spoiler,
                    show_caption_above_media=show_caption_above
                )
        elif content_type == 'video':
            is_paid = post_data.get('is_paid', False)
            paid_price = post_data.get('paid_price', 1)
            if is_paid:
                # Pulli media sifatida yuborish
                from aiogram.types import InputPaidMediaVideo
                sent_message = await message.answer_paid_media(
                    star_count=paid_price,
                    media=[InputPaidMediaVideo(media=file_id)],
                    caption=caption,
                    parse_mode=parse_mode,
                    show_caption_above_media=show_caption_above,
                    reply_markup=keyboard
                )
            else:
                sent_message = await message.answer_video(
                    file_id,
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode=parse_mode,
                    has_spoiler=has_spoiler,
                    show_caption_above_media=show_caption_above
                )
        elif content_type == 'audio':
            sent_message = await message.answer_audio(
                file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'document':
            sent_message = await message.answer_document(
                file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'voice':
            sent_message = await message.answer_voice(
                file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
        elif content_type == 'video_note':
            sent_message = await message.answer_video_note(
                file_id,
                reply_markup=keyboard
            )
        elif content_type == 'animation':
            sent_message = await message.answer_animation(
                file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode=parse_mode,
                has_spoiler=has_spoiler,
                show_caption_above_media=show_caption_above
            )
        elif content_type == 'sticker':
            sent_message = await message.answer_sticker(
                file_id,
                reply_markup=keyboard
            )
        elif content_type == 'location':
            sent_message = await message.answer_location(
                latitude=post_data.get('latitude', 0),
                longitude=post_data.get('longitude', 0),
                reply_markup=keyboard
            )
        elif content_type == 'dice':
            sent_message = await message.answer_dice(
                emoji=post_data.get('dice_emoji', '🎲'),
                reply_markup=keyboard
            )
        elif content_type == 'paid_media':
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

            sent_message = await message.answer_paid_media(
                star_count=paid_price,
                media=input_media_list,
                caption=caption,
                parse_mode=parse_mode,
                show_caption_above_media=show_caption_above,
                reply_markup=keyboard
            )

        if sent_message:
            post_data['message_id'] = sent_message.message_id
            post_data['chat_id'] = sent_message.chat.id
            await state.update_data(post_data=post_data)

    except Exception:
        pass


@media_router.callback_query(PostCreation.waiting_for_media_settings, F.data == "media_set_price")
async def media_set_price_handler(callback: types.CallbackQuery, state: FSMContext):
    """Media narxini o'rnatish - faqat orqaga tugmasi bilan"""
    lang = await get_user_language(callback.from_user.id)

    # Orqaga tugmasini yaratish
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('back_btn', lang), callback_data="back_to_media_settings")
    keyboard = builder.as_markup()

    # Xabarni tahrirlash - o'chirib yangi yuborish o'rniga
    try:
        await callback.message.edit_text(
            get_text('enter_media_price_msg', lang),
            reply_markup=keyboard
        )
    except Exception:
        # Agar tahrirlash mumkin bo'lmasa (masalan, media xabar), yangi xabar yuborish
        try:
            await callback.message.delete()
        except Exception:
            pass
        prompt_msg = await callback.message.answer(
            get_text('enter_media_price_msg', lang),
            reply_markup=keyboard
        )
        await state.update_data(price_prompt_message_id=prompt_msg.message_id)

    await state.set_state(PostCreation.waiting_for_paid_price)
    await callback.answer()


@media_router.callback_query(PostCreation.waiting_for_paid_price, F.data == "back_to_media_settings")
async def back_from_price_setting(callback: types.CallbackQuery, state: FSMContext):
    """Narx o'rnatishdan media sozlamalariga qaytish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    content_type = post_data.get('content_type', 'photo')
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))

    # Xabarni tahrirlash (o'chirib qayta yubormasdan)
    await callback.message.edit_text(
        get_text('media_settings_msg', lang),
        reply_markup=get_media_settings_inline_kb(
            lang=lang,
            has_spoiler=has_spoiler,
            is_paid=is_paid,
            show_caption_above=show_caption_above,
            has_caption=has_caption,
            content_type=content_type,
            paid_price=post_data.get('paid_price', 1)
        )
    )

    await state.set_state(PostCreation.waiting_for_media_settings)
    await callback.answer()


@media_router.message(PostCreation.waiting_for_paid_price)
async def process_paid_price(message: Message, state: FSMContext):
    """Foydalanuvchi kiritgan narxni qayta ishlash"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(message.from_user.id)

    # Tekshirish - raqammi
    try:
        if not message.text:
            raise ValueError("None text")
        price = int(message.text.strip())
        if price < 1 or price > 25000:
            raise ValueError("Noto'g'ri diapazon")
    except ValueError:
        await message.answer(get_text('invalid_price_msg', lang))
        return

    # Narxni saqlash
    post_data['paid_price'] = price
    await state.update_data(post_data=post_data)

    # Foydalanuvchi xabarini o'chirish
    try:
        await message.delete()
    except Exception:
        pass

    # Narx soragan xabarni o'chirish (agar saqlangan bo'lsa)
    price_prompt_message_id = data.get('price_prompt_message_id')
    if price_prompt_message_id:
        try:
            await message.bot.delete_message(message.chat.id, price_prompt_message_id)
        except Exception:
            pass

    # Tepadagi postni o'chirish
    chat_id = post_data.get('chat_id')
    message_id = post_data.get('message_id')
    if chat_id and message_id:
        try:
            await message.bot.delete_message(chat_id, message_id)
        except Exception:
            pass

    # Yangi post yuborish (yangi narx bilan)
    from post_handlers.xinline_keyboard import generate_post_keyboard
    buttons_matrix = data.get('buttons_matrix', [])
    new_keyboard = generate_post_keyboard(buttons_matrix, lang)

    content_type = post_data.get('content_type', 'photo')
    file_id = post_data.get('file_id')
    caption = post_data.get('caption')
    parse_mode = post_data.get('parse_mode', 'HTML')
    show_caption_above = post_data.get('show_caption_above_media', False)

    sent_message = None

    try:
        if content_type == 'photo':
            from aiogram.types import InputPaidMediaPhoto
            sent_message = await message.answer_paid_media(
                star_count=price,
                media=[InputPaidMediaPhoto(media=file_id)],
                caption=caption,
                parse_mode=parse_mode,
                show_caption_above_media=show_caption_above,
                reply_markup=new_keyboard
            )
        elif content_type == 'video':
            from aiogram.types import InputPaidMediaVideo
            sent_message = await message.answer_paid_media(
                star_count=price,
                media=[InputPaidMediaVideo(media=file_id)],
                caption=caption,
                parse_mode=parse_mode,
                show_caption_above_media=show_caption_above,
                reply_markup=new_keyboard
            )

        if sent_message:
            post_data['message_id'] = sent_message.message_id
            post_data['chat_id'] = sent_message.chat.id
            await state.update_data(post_data=post_data)

    except Exception:
        pass

    # Media sozlamalarini darhol ko'rsatish (muvaffaqiyat xabarisiz)
    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    has_caption = bool(post_data.get('caption'))

    # State ni avval o'rnatish (handler routing uchun)
    await state.set_state(PostCreation.waiting_for_media_settings)

    await message.answer(
        get_text('media_settings_msg', lang),
        reply_markup=get_media_settings_inline_kb(
            lang=lang,
            has_spoiler=has_spoiler,
            is_paid=is_paid,
            show_caption_above=show_caption_above,
            has_caption=has_caption,
            content_type=content_type,
            paid_price=price
        )
    )
