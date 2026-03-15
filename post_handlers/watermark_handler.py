import logging
import asyncio
import os
from PIL import Image
from aiogram import Router, F, types, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from xdata_handlers import config
from xdata_handlers.translator import get_text
from xdata_handlers.database import get_user_language
from post_handlers.post_handler import PostCreation
from post_handlers.xinline_keyboard import generate_post_keyboard

logger = logging.getLogger(__name__)

async def apply_watermark(bot: Bot, base_file_id: str, watermark_file_id: str) -> str:
    """
    Base image ga watermark rasmmi qo'shadi va yangi file_id qaytaradi.
    Eslatma: Bu funksiya vaqtinchalik fayllardan foydalanadi.
    """
    tmp_base = f"tmp_base_{base_file_id}.jpg"
    tmp_wm = f"tmp_wm_{watermark_file_id}.png"
    tmp_out = f"tmp_out_{base_file_id}.jpg"

    try:
        # Fayllarni yuklab olish
        base_file = await bot.get_file(base_file_id)
        watermark_file = await bot.get_file(watermark_file_id)
        
        await bot.download_file(base_file.file_path, tmp_base)
        await bot.download_file(watermark_file.file_path, tmp_wm)

        # Pillow orqali qayta ishlash
        with Image.open(tmp_base) as base:
            base = base.convert("RGBA")
            with Image.open(tmp_wm) as wm:
                wm = wm.convert("RGBA")
                
                # Suv belgisini o'lchamini moslashtirish (rasm kengligining 15% qismi)
                wm_width = int(base.width * 0.15)
                wm_height = int(wm.height * (wm_width / wm.width))
                wm = wm.resize((wm_width, wm_height), Image.Resampling.LANCZOS)
                
                # Joylashuv: Pastki o'ng burchak
                position = (base.width - wm_width - 20, base.height - wm_height - 20)
                
                # Overlay
                overlay = Image.new('RGBA', base.size, (0,0,0,0))
                overlay.paste(wm, position, mask=wm)
                
                combined = Image.alpha_composite(base, overlay)
                final = combined.convert("RGB")
                final.save(tmp_out, "JPEG", quality=95)

        # Yangi rasmni Telegram ga yuklash
        from aiogram.types import FSInputFile
        photo = FSInputFile(tmp_out)
        
        storage_channel = config.STORAGE_CHANNEL_ID
        sent_msg = await bot.send_photo(chat_id=storage_channel, photo=photo, caption="Watermarked Image")
        
        return sent_msg.photo[-1].file_id

    except Exception as e:
        logger.error(f"apply_watermark error: {e}")
        return base_file_id
    finally:
        # Vaqtinchalik fayllarni o'chirish
        for f in [tmp_base, tmp_wm, tmp_out]:
            if os.path.exists(f):
                os.remove(f)

watermark_router = Router()

async def show_watermark_settings(message: Message, state: FSMContext):
    """Suv belgisi sozlamalarini ko'rsatadi"""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    data = await state.get_data()
    post_data = data.get('post_data', {})
    watermark_enabled = post_data.get('watermark_enabled', False)
    watermark_file_id = post_data.get('watermark_file_id')

    text = "<b>💧 Suv belgisi sozlamalari</b>\n\n"
    if watermark_file_id:
        status = "✅ Yoqilgan" if watermark_enabled else "❌ O'chirilgan"
        text += f"Holati: {status}\n\nSuv belgisini o'zgartirish uchun yangi rasm yuboring yoki quyidagi tugmalardan foydalaning:"
    else:
        text += "Sizda hali suv belgisi o'rnatilmagan. Iltimos, suv belgisi sifatida ishlatiladigan rasmni yuboring."

    builder = InlineKeyboardBuilder()
    if watermark_file_id:
        toggle_text = "❌ O'chirish" if watermark_enabled else "✅ Yoqish"
        builder.button(text=toggle_text, callback_data="wm_toggle")
        builder.button(text="✨ Suv belgisini qo'llash", callback_data="wm_apply")
        builder.button(text="🖼 Rasmni o'zgartirish", callback_data="wm_change")
    
    builder.button(text=get_text('back_btn', lang), callback_data="wm_back")
    builder.adjust(1)

    await message.answer(text, reply_markup=builder.as_markup())
    await state.set_state(PostCreation.waiting_for_watermark_settings)

@watermark_router.callback_query(F.data == "wm_toggle", PostCreation.waiting_for_watermark_settings)
async def watermark_toggle(callback: CallbackQuery, state: FSMContext):
    """Suv belgisini yoqish/o'chirish"""
    data = await state.get_data()
    post_data = data.get('post_data', {})
    
    current_status = post_data.get('watermark_enabled', False)
    post_data['watermark_enabled'] = not current_status
    
    await state.update_data(post_data=post_data)
    
    # Menyu ni yangilash
    await callback.message.delete()
    await show_watermark_settings(callback.message, state)
    await callback.answer()

@watermark_router.callback_query(F.data == "wm_apply", PostCreation.waiting_for_watermark_settings)
async def apply_watermark_to_post(callback: CallbackQuery, state: FSMContext):
    """Suv belgisini joriy rasmga qo'llash"""
    data = await state.get_data()
    post_data = data.get('post_data', {})
    
    base_file_id = post_data.get('file_id')
    watermark_file_id = post_data.get('watermark_file_id')
    
    if not base_file_id or not watermark_file_id:
        await callback.answer("❌ Xatolik: Rasm yoki suv belgisi topilmadi", show_alert=True)
        return

    await callback.message.edit_text("⏳ Suv belgisi qo'shilmoqda, iltimos kuting...")
    
    new_file_id = await apply_watermark(callback.bot, base_file_id, watermark_file_id)
    
    if new_file_id and new_file_id != base_file_id:
        post_data['file_id'] = new_file_id
        post_data['original_file_id'] = base_file_id # Asl nusxani saqlab qo'yamiz
        await state.update_data(post_data=post_data)
        await callback.answer("✅ Suv belgisi muvaffaqiyatli qo'shildi!", show_alert=True)
    else:
        await callback.answer("❌ Suv belgisini qo'shishda xatolik yuz berdi", show_alert=True)
    
    await callback.message.delete()
    await show_watermark_settings(callback.message, state)

@watermark_router.callback_query(F.data == "wm_change", PostCreation.waiting_for_watermark_settings)
async def watermark_change(callback: CallbackQuery, state: FSMContext):
    """Yangi suv belgisi yuklashni so'rash"""
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    
    await callback.message.edit_text(
        "Iltimos, suv belgisi uchun yangi rasm yuboring:",
        reply_markup=InlineKeyboardBuilder().button(text=get_text('back_btn', lang), callback_data="wm_back").as_markup()
    )
    await state.set_state(PostCreation.waiting_for_watermark_photo)
    await callback.answer()

@watermark_router.callback_query(F.data == "wm_back", PostCreation.waiting_for_watermark_settings)
@watermark_router.callback_query(F.data == "wm_back", PostCreation.waiting_for_watermark_photo)
async def watermark_back(callback: CallbackQuery, state: FSMContext):
    """Post sozlamalariga qaytish"""
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    
    data = await state.get_data()
    post_data = data.get('post_data', {})
    buttons_matrix = data.get('buttons_matrix', [])
    
    await state.set_state(PostCreation.configuring_post)
    
    # Postni qayta chizish
    chat_id = post_data.get('chat_id')
    message_id = post_data.get('message_id')
    
    if chat_id and message_id:
        try:
            from post_handlers.xreply_keyboard import get_post_settings_kb
            
            content_type = post_data.get('content_type', 'photo')
            has_caption = bool(post_data.get('caption'))
            is_paid = post_data.get('is_paid', False)
            
            reply_markup = get_post_settings_kb(
                content_type=content_type,
                has_caption=has_caption,
                lang=lang,
                is_paid=is_paid
            )
            
            await callback.message.answer(
                get_text('back_to_settings_msg', lang),
                reply_markup=reply_markup
            )
            await callback.message.delete()
        except Exception as e:
            logger.error(f"Watermark back error: {e}")

    await callback.answer()

@watermark_router.message(F.photo, PostCreation.waiting_for_watermark_photo)
@watermark_router.message(F.photo, PostCreation.waiting_for_watermark_settings)
async def process_watermark_photo(message: Message, state: FSMContext):
    """Suv belgisi rasmini qabul qilish"""
    file_id = message.photo[-1].file_id
    
    data = await state.get_data()
    post_data = data.get('post_data', {})
    post_data['watermark_file_id'] = file_id
    post_data['watermark_enabled'] = True
    
    await state.update_data(post_data=post_data)
    
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    await message.answer("✅ Suv belgisi muvaffaqiyatli o'rnatildi va yoqildi!")
    await show_watermark_settings(message, state)
