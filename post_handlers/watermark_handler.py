import os
import tempfile
from io import BytesIO
from typing import Optional, Dict, Any

from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from post_handlers.post_handler import PostCreation
from post_handlers.xinline_keyboard import get_media_settings_inline_kb
from post_handlers.xreply_keyboard import get_post_settings_kb
from xdata_handlers.database import get_user_language
from xdata_handlers.translator import get_text
from post_handlers.localize_filter import LocalizedText

watermark_router = Router()

async def apply_and_redraw_watermark(callback_or_message, state, lang: str):
    """Watermark qo'llash va postni qayta chizish"""
    from post_handlers.reply_handler import redraw_post_with_callback, redraw_post_with_settings

    data = await state.get_data()
    post_data = data.get("post_data", {})

    watermark_type = post_data.get('watermark_type', 'text')

    watermark_text = post_data.get('watermark_text', '')
    if watermark_type == 'text' and not watermark_text:
        return

    watermark_image_file_id = post_data.get('watermark_image_file_id')
    if watermark_type == 'image' and not watermark_image_file_id:
        return

    watermark_position = post_data.get('watermark_position', 'bottom_right')
    watermark_transparency = post_data.get('watermark_transparency', 200)
    watermark_rotation = post_data.get('watermark_rotation', 0)
    watermark_scale = post_data.get('watermark_scale', 1.0)
    content_type = post_data.get('content_type', 'photo')

    if 'original_file_id' not in post_data and post_data.get('file_id'):
        post_data['original_file_id'] = post_data.get('file_id')
        await state.update_data(post_data=post_data)

    file_id = post_data.get('original_file_id') or post_data.get('file_id')

    if not file_id or content_type != 'photo':
        return

    if hasattr(callback_or_message, 'callback_query'):
        bot = callback_or_message.bot
    elif hasattr(callback_or_message, 'message'):
        bot = callback_or_message.message.bot
    else:
        bot = callback_or_message.bot

    watermark_bytes = post_data.get('watermark_bytes')

    try:
        if not watermark_bytes:
            file = await bot.get_file(file_id)
            file_bytes = await bot.download_file(file.file_path)
            media_bytes = file_bytes.read()
            post_data['watermark_bytes'] = media_bytes
            await state.update_data(post_data=post_data)
        else:
            media_bytes = watermark_bytes

        if watermark_type == 'text':
            processed_bytes = await apply_watermark_to_image(
                media_bytes, watermark_text, watermark_position,
                watermark_transparency, watermark_rotation, watermark_scale
            )
        else:
            wm_file = await bot.get_file(watermark_image_file_id)
            wm_file_bytes = await bot.download_file(wm_file.file_path)
            wm_bytes = wm_file_bytes.read()

            processed_bytes = await apply_image_watermark_to_image(
                media_bytes, wm_bytes, watermark_position,
                watermark_transparency, watermark_scale
            )

        if not processed_bytes:
            return

        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            tmp.write(processed_bytes)
            tmp_path = tmp.name

        from xdata_handlers import config

        if config.STORAGE_CHANNEL_ID:
            try:
                sent = await bot.send_photo(config.STORAGE_CHANNEL_ID, types.FSInputFile(tmp_path))
                new_file_id = sent.photo[-1].file_id
            finally:
                os.unlink(tmp_path)
        else:
            os.unlink(tmp_path)
            return

        if new_file_id:
            post_data['file_id'] = new_file_id
            post_data['watermark_applied'] = True
            await state.update_data(post_data=post_data)

            chat_id = post_data.get('chat_id')
            message_id = post_data.get('message_id')

            if chat_id and message_id:
                from aiogram.types import InputMediaPhoto
                caption = post_data.get('caption')
                parse_mode = post_data.get('parse_mode', 'HTML')
                has_spoiler = post_data.get('has_spoiler', False)
                show_caption_above = post_data.get('show_caption_above_media', False)

                media = InputMediaPhoto(
                    media=new_file_id,
                    caption=caption,
                    parse_mode=parse_mode,
                    has_spoiler=has_spoiler,
                    show_caption_above_media=show_caption_above
                )
                try:
                    await bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=message_id,
                        media=media
                    )
                except Exception:
                    pass
    except Exception:
        pass

WATERMARK_POSITIONS = {
    "top_left": "Yuqori chap",
    "top_center": "Yuqori o'rtada",
    "top_right": "Yuqori o'ng",
    "center_left": "Chap o'rtada",
    "center": "O'rtada",
    "center_right": "O'ng o'rtada",
    "bottom_left": "Past chap",
    "bottom_center": "Past o'rtada",
    "bottom_right": "Past o'ng"
}

class WatermarkCallbackFactory(CallbackData, prefix="wm"):
    action: str
    position: Optional[str] = None
    value: Optional[str] = None

def get_watermark_settings_inline_kb(lang: str, current_position: str = "bottom_right", watermark_text: str = "", 
                                      transparency: int = 200, rotation: int = 0, scale: float = 1.0,
                                      watermark_type: str = "text"):
    """Watermark sozlamalari uchun inline klaviatura"""
    builder = InlineKeyboardBuilder()

    builder.button(text="✏️ Tahrirlash", callback_data=WatermarkCallbackFactory(action="edit_watermark"))

    position_text = get_text('watermark_position_btn', lang)
    builder.button(text=position_text, callback_data=WatermarkCallbackFactory(action="select_position"))

    transparency_text = get_text('watermark_transparency_btn', lang)
    builder.button(text=f"{transparency_text}: {transparency}%", callback_data=WatermarkCallbackFactory(action="select_transparency"))

    rotation_text = get_text('watermark_rotation_btn', lang)
    builder.button(text=f"{rotation_text}: {rotation}°", callback_data=WatermarkCallbackFactory(action="select_rotation"))

    scale_text = get_text('watermark_scale_btn', lang)
    builder.button(text=f"{scale_text}: {int(scale*100)}%", callback_data=WatermarkCallbackFactory(action="select_scale"))

    builder.button(text=get_text('back_btn', lang), callback_data="back_to_settings_menu")

    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()

def get_watermark_position_kb(lang: str, current_position: str = "bottom_right"):
    """Watermark joylashuvini tanlash klaviaturasi"""
    builder = InlineKeyboardBuilder()

    positions = [
        ("top_left", "↖️"),
        ("top_center", "⬆️"),
        ("top_right", "↗️"),
        ("center_left", "⬅️"),
        ("center", "⏺️"),
        ("center_right", "➡️"),
        ("bottom_left", "↙️"),
        ("bottom_center", "⬇️"),
        ("bottom_right", "↘️")
    ]

    for pos_key, emoji in positions:
        marker = "✅ " if pos_key == current_position else ""
        builder.button(text=f"{marker}{emoji}", callback_data=WatermarkCallbackFactory(action="set_position", position=pos_key))

    builder.button(text=get_text('back_btn', lang), callback_data=WatermarkCallbackFactory(action="back_to_settings"))

    builder.adjust(3, 3, 3, 1)
    return builder.as_markup()

def get_watermark_transparency_kb(lang: str, current_transparency: int = 200):
    """Watermark shaffofligini tanlash klaviaturasi"""
    builder = InlineKeyboardBuilder()

    transparencies = [50, 100, 150, 200, 225, 255]

    for trans in transparencies:
        marker = "✅ " if trans == current_transparency else ""
        builder.button(text=f"{marker}{trans}%", callback_data=WatermarkCallbackFactory(action="set_transparency", value=str(trans)))

    builder.button(text=get_text('back_btn', lang), callback_data=WatermarkCallbackFactory(action="back_to_settings"))

    builder.adjust(3, 3, 1)
    return builder.as_markup()

def get_watermark_rotation_kb(lang: str, current_rotation: int = 0):
    """Watermark burilishini tanlash klaviaturasi"""
    builder = InlineKeyboardBuilder()

    rotations = [0, 45, 90, 135, 180, 225, 270, 315]

    for rot in rotations:
        marker = "✅ " if rot == current_rotation else ""
        builder.button(text=f"{marker}{rot}°", callback_data=WatermarkCallbackFactory(action="set_rotation", value=str(rot)))

    builder.button(text=get_text('back_btn', lang), callback_data=WatermarkCallbackFactory(action="back_to_settings"))

    builder.adjust(4, 4, 1)
    return builder.as_markup()

def get_watermark_scale_kb(lang: str, current_scale: float = 1.0):
    """Watermark kattalashtirishini tanlash klaviaturasi"""
    builder = InlineKeyboardBuilder()

    scales = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

    for sc in scales:
        marker = "✅ " if sc == current_scale else ""
        builder.button(text=f"{marker}{int(sc*100)}%", callback_data=WatermarkCallbackFactory(action="set_scale", value=str(sc)))

    builder.button(text=get_text('back_btn', lang), callback_data=WatermarkCallbackFactory(action="back_to_settings"))

    builder.adjust(3, 3, 1)
    return builder.as_markup()

async def apply_watermark_to_image(image_bytes: bytes, watermark_text: str, position: str = "bottom_right", 
                                   transparency: int = 200, rotation: int = 0, scale: float = 1.0) -> bytes:
    """
    Rasmga watermark qo'shish
    Pillow kutubxonasi talab qilinadi: pip install Pillow
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return image_bytes

    try:
        image = Image.open(BytesIO(image_bytes))

        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        base_font_size = max(12, min(image.width, image.height) // 25)
        font_size = int(base_font_size * scale)

        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

        draw_temp = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        bbox = draw_temp.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        padding = 15
        positions = {
            "top_left": (padding, padding),
            "top_center": ((image.width - text_width) // 2, padding),
            "top_right": (image.width - text_width - padding, padding),
            "center_left": (padding, (image.height - text_height) // 2),
            "center": ((image.width - text_width) // 2, (image.height - text_height) // 2),
            "center_right": (image.width - text_width - padding, (image.height - text_height) // 2),
            "bottom_left": (padding, image.height - text_height - padding),
            "bottom_center": ((image.width - text_width) // 2, image.height - text_height - padding),
            "bottom_right": (image.width - text_width - padding, image.height - text_height - padding)
        }

        x, y = positions.get(position, positions["bottom_right"])

        text_layer = Image.new('RGBA', (text_width + 20, text_height + 20), (255, 255, 255, 0))
        text_draw = ImageDraw.Draw(text_layer)

        shadow_alpha = min(255, int(transparency * 0.6))
        shadow_color = (0, 0, 0, shadow_alpha)
        text_draw.text((10, 10), watermark_text, font=font, fill=shadow_color)

        text_color = (255, 255, 255, transparency)
        text_draw.text((10, 10), watermark_text, font=font, fill=text_color)

        if rotation != 0:
            text_layer = text_layer.rotate(-rotation, expand=False, fillcolor=(0, 0, 0, 0))

        txt_layer = Image.new('RGBA', image.size, (255, 255, 255, 0))
        txt_layer.paste(text_layer, (x - 10, y - 10), text_layer)

        watermarked = Image.alpha_composite(image, txt_layer)

        output = BytesIO()
        if watermarked.mode == 'RGBA':
            watermarked = watermarked.convert('RGB')
        watermarked.save(output, format='JPEG' if image_bytes.startswith(b'\xff\xd8') else 'PNG', quality=95)
        output.seek(0)

        return output.getvalue()

    except Exception:
        return image_bytes

async def apply_image_watermark_to_image(main_image_bytes: bytes, watermark_image_bytes: bytes, 
                                        position: str = "bottom_right", transparency: int = 255, 
                                        scale: float = 1.0) -> bytes:
    """
    Rasmga rasm watermark qo'shish (sticker/gif dan)
    """
    try:
        from PIL import Image
    except ImportError:
        return main_image_bytes

    try:
        main_image = Image.open(BytesIO(main_image_bytes))
        if main_image.mode != 'RGBA':
            main_image = main_image.convert('RGBA')

        watermark_image = Image.open(BytesIO(watermark_image_bytes))
        if watermark_image.mode != 'RGBA':
            watermark_image = watermark_image.convert('RGBA')

        base_size = min(main_image.width, main_image.height) // 5
        wm_width = int(base_size * scale)
        wm_height = int(watermark_image.height * (wm_width / watermark_image.width))
        watermark_image = watermark_image.resize((wm_width, wm_height), Image.LANCZOS)

        if transparency < 255:
            alpha = watermark_image.split()[3]
            alpha = alpha.point(lambda p: p * (transparency / 255))
            watermark_image.putalpha(alpha)

        padding = 15
        positions = {
            "top_left": (padding, padding),
            "top_center": ((main_image.width - wm_width) // 2, padding),
            "top_right": (main_image.width - wm_width - padding, padding),
            "center_left": (padding, (main_image.height - wm_height) // 2),
            "center": ((main_image.width - wm_width) // 2, (main_image.height - wm_height) // 2),
            "center_right": (main_image.width - wm_width - padding, (main_image.height - wm_height) // 2),
            "bottom_left": (padding, main_image.height - wm_height - padding),
            "bottom_center": ((main_image.width - wm_width) // 2, main_image.height - wm_height - padding),
            "bottom_right": (main_image.width - wm_width - padding, main_image.height - wm_height - padding)
        }

        x, y = positions.get(position, positions["bottom_right"])

        watermarked = Image.new('RGBA', main_image.size, (0, 0, 0, 0))
        watermarked.paste(main_image, (0, 0))
        watermarked.paste(watermark_image, (x, y), watermark_image)

        output = BytesIO()
        if watermarked.mode == 'RGBA':
            watermarked = watermarked.convert('RGB')
        watermarked.save(output, format='JPEG' if main_image_bytes.startswith(b'\xff\xd8') else 'PNG', quality=95)
        output.seek(0)

        return output.getvalue()

    except Exception:
        return main_image_bytes

async def apply_watermark_to_video(video_bytes: bytes, watermark_text: str, position: str = "bottom_right") -> bytes:
    """
    Videoga watermark qo'shish
    FFmpeg talab qilinadi
    """
    return video_bytes

async def process_media_with_watermark(bot: Bot, file_id: str, watermark_text: str, position: str, content_type: str, 
                              transparency: int = 200, rotation: int = 0, scale: float = 1.0) -> Optional[str]:
    """
    Mediani watermark bilan qayta ishlash va yangi file_id qaytarish
    """
    try:
        file = await bot.get_file(file_id)
        file_bytes = await bot.download_file(file.file_path)

        media_bytes = file_bytes.read()

        if content_type == 'photo':
            processed_bytes = await apply_watermark_to_image(media_bytes, watermark_text, position, transparency, rotation, scale)
        elif content_type == 'video':
            processed_bytes = await apply_watermark_to_video(media_bytes, watermark_text, position)
        else:
            return file_id

        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg' if content_type == 'photo' else '.mp4') as tmp:
            tmp.write(processed_bytes)
            tmp_path = tmp.name

        from xdata_handlers import config

        if not config.STORAGE_CHANNEL_ID:
            os.unlink(tmp_path)
            return file_id

        try:
            if content_type == 'photo':
                sent = await bot.send_photo(config.STORAGE_CHANNEL_ID, types.FSInputFile(tmp_path))
                new_file_id = sent.photo[-1].file_id
            elif content_type == 'video':
                sent = await bot.send_video(config.STORAGE_CHANNEL_ID, types.FSInputFile(tmp_path))
                new_file_id = sent.video.file_id
            else:
                new_file_id = file_id

            return new_file_id
        finally:
            os.unlink(tmp_path)

    except Exception:
        return None

@watermark_router.callback_query(WatermarkCallbackFactory.filter(F.action == "set_text"))
async def prompt_watermark_text(callback: types.CallbackQuery, state: FSMContext):
    """Watermark matnini kiritishni so'rash"""
    lang = await get_user_language(callback.from_user.id)

    await state.set_state(PostCreation.waiting_for_watermark_text)

    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('back_btn', lang), callback_data=WatermarkCallbackFactory(action="back_to_settings"))

    await callback.message.edit_text(
        get_text('watermark_enter_text', lang),
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@watermark_router.message(PostCreation.waiting_for_watermark_text)
async def set_watermark_text(message: Message, state: FSMContext):
    """Watermark matnini yoki rasmni saqlash - avtomatik aniqlash"""
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})

    watermark_file_id = None
    watermark_image_type = None

    if message.photo:
        watermark_file_id = message.photo[-1].file_id
        watermark_image_type = 'photo'
    elif message.sticker:
        watermark_file_id = message.sticker.file_id
        watermark_image_type = 'sticker'
    elif message.animation:
        watermark_file_id = message.animation.file_id
        watermark_image_type = 'animation'
    elif message.text:
        watermark_text = message.text.strip()

        if len(watermark_text) > 50:
            await message.answer("❌ Watermark matni 50 belgidan oshmasligi kerak.")
            return

        post_data['watermark_text'] = watermark_text
        post_data['watermark_type'] = 'text'
    else:
        await message.answer("❌ Iltimos, matn, rasm, sticker yoki GIF yuboring.")
        return

    if watermark_file_id:
        post_data['watermark_image_file_id'] = watermark_file_id
        post_data['watermark_image_type'] = watermark_image_type
        post_data['watermark_type'] = 'image'
        post_data.setdefault('watermark_position', 'bottom_right')
        post_data.setdefault('watermark_transparency', 255)
        post_data.setdefault('watermark_rotation', 0)
        post_data.setdefault('watermark_scale', 1.0)
    else:
        post_data.setdefault('watermark_position', 'bottom_right')
        post_data.setdefault('watermark_transparency', 200)
        post_data.setdefault('watermark_rotation', 0)
        post_data.setdefault('watermark_scale', 1.0)

    post_data['watermark_enabled'] = True

    if 'original_file_id' not in post_data and post_data.get('file_id'):
        post_data['original_file_id'] = post_data.get('file_id')

    post_data['watermark_bytes'] = None

    await state.update_data(post_data=post_data)
    await state.set_state(PostCreation.configuring_post)

    await apply_and_redraw_watermark(message, state, lang)

    data = await state.get_data()
    post_data = data.get("post_data", {})

    position = post_data.get('watermark_position', 'bottom_right')
    watermark_text = post_data.get('watermark_text', '')
    transparency = post_data.get('watermark_transparency', 200)
    rotation = post_data.get('watermark_rotation', 0)
    scale = post_data.get('watermark_scale', 1.0)
    watermark_type = post_data.get('watermark_type', 'text')

    if watermark_type == 'image':
        msg = get_text('watermark_image_saved', lang)
    else:
        msg = get_text('watermark_text_saved', lang)

    chat_id = post_data.get('chat_id')
    message_id = post_data.get('message_id')

    if chat_id and message_id:
        try:
            await message.bot.delete_message(chat_id, message_id)

            from post_handlers.reply_handler import send_new_post_with_settings
            from post_handlers.xinline_keyboard import generate_post_keyboard

            buttons_matrix = data.get("buttons_matrix", [])
            new_keyboard = generate_post_keyboard(buttons_matrix, lang)

            await send_new_post_with_settings(message, state, post_data, new_keyboard)

            data = await state.get_data()
            post_data = data.get("post_data", {})
            chat_id = post_data.get('chat_id')
            message_id = post_data.get('message_id')
        except Exception:
            pass

    if chat_id and message_id:
        try:
            await message.answer(
                msg,
                reply_markup=get_watermark_settings_inline_kb(lang, position, watermark_text, transparency, rotation, scale, watermark_type=watermark_type)
            )
        except Exception:
            pass
    else:
        await message.answer(
            msg,
            reply_markup=get_watermark_settings_inline_kb(lang, position, watermark_text, transparency, rotation, scale, watermark_type=watermark_type)
        )

@watermark_router.callback_query(WatermarkCallbackFactory.filter(F.action == "edit_watermark"))
async def edit_watermark(callback: types.CallbackQuery, state: FSMContext):
    """Watermarkni tahrirlash - yangi matn yoki rasm kiritish"""
    lang = await get_user_language(callback.from_user.id)

    await state.set_state(PostCreation.waiting_for_watermark_text)

    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('back_btn', lang), callback_data=WatermarkCallbackFactory(action="back_to_settings"))

    await callback.message.edit_text(
        get_text('watermark_enter_text', lang),
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@watermark_router.message(PostCreation.waiting_for_watermark_image)
async def set_watermark_image(message: Message, state: FSMContext):
    """Watermark rasm/sticker/gif ni saqlash"""
    from aiogram.types import PhotoSize, Sticker, Animation

    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    post_data = data.get("post_data", {})

    watermark_file_id = None
    watermark_type = 'photo'

    if message.photo:
        watermark_file_id = message.photo[-1].file_id
        watermark_type = 'photo'
    elif message.sticker:
        watermark_file_id = message.sticker.file_id
        watermark_type = 'sticker'
    elif message.animation:
        watermark_file_id = message.animation.file_id
        watermark_type = 'animation'
    else:
        await message.answer("❌ Iltimos, rasm, sticker yoki GIF yuboring.")
        return

    post_data['watermark_image_file_id'] = watermark_file_id
    post_data['watermark_image_type'] = watermark_type
    post_data['watermark_type'] = 'image'

    post_data.setdefault('watermark_position', 'bottom_right')
    post_data.setdefault('watermark_transparency', 255)
    post_data.setdefault('watermark_rotation', 0)
    post_data.setdefault('watermark_scale', 1.0)

    if 'original_file_id' not in post_data and post_data.get('file_id'):
        post_data['original_file_id'] = post_data.get('file_id')

    post_data['watermark_bytes'] = None  # Yangilash uchun

    await state.update_data(post_data=post_data)
    await state.set_state(PostCreation.configuring_post)

    await apply_and_redraw_watermark(message, state, lang)

    position = post_data.get('watermark_position', 'bottom_right')
    watermark_text = post_data.get('watermark_text', '')
    transparency = post_data.get('watermark_transparency', 255)
    rotation = post_data.get('watermark_rotation', 0)
    scale = post_data.get('watermark_scale', 1.0)

    chat_id = post_data.get('chat_id')
    message_id = post_data.get('message_id')

    if chat_id and message_id:
        try:
            await message.bot.delete_message(chat_id, message_id)

            from post_handlers.reply_handler import send_new_post_with_settings
            from post_handlers.xinline_keyboard import generate_post_keyboard

            data = await state.get_data()
            buttons_matrix = data.get("buttons_matrix", [])
            new_keyboard = generate_post_keyboard(buttons_matrix, lang)

            await send_new_post_with_settings(message, state, post_data, new_keyboard)

            data = await state.get_data()
            post_data = data.get("post_data", {})
            chat_id = post_data.get('chat_id')
            message_id = post_data.get('message_id')
        except Exception:
            pass

    if chat_id and message_id:
        try:
            await message.answer(
                get_text('watermark_image_saved', lang),
                reply_markup=get_watermark_settings_inline_kb(lang, position, watermark_text, transparency, rotation, scale, watermark_type='image')
            )
        except Exception:
            pass
    else:
        await message.answer(
            get_text('watermark_image_saved', lang),
            reply_markup=get_watermark_settings_inline_kb(lang, position, watermark_text, transparency, rotation, scale, watermark_type='image')
        )

@watermark_router.callback_query(WatermarkCallbackFactory.filter(F.action == "select_position"))
async def select_watermark_position_menu(callback: types.CallbackQuery, state: FSMContext):
    """Watermark joylashuvini tanlash menyusi"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    current_position = post_data.get('watermark_position', 'bottom_right')

    await callback.message.edit_text(
        get_text('watermark_select_position', lang),
        reply_markup=get_watermark_position_kb(lang, current_position)
    )
    await callback.answer()

@watermark_router.callback_query(WatermarkCallbackFactory.filter(F.action == "set_position"))
async def set_watermark_position(callback: types.CallbackQuery, callback_data: WatermarkCallbackFactory, state: FSMContext):
    """Watermark joylashuvini o'rnatish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    position = callback_data.position
    post_data['watermark_position'] = position
    await state.update_data(post_data=post_data)

    await callback.answer(get_text('watermark_position_saved', lang))

    await apply_and_redraw_watermark(callback, state, lang)

    data = await state.get_data()
    post_data = data.get("post_data", {})
    watermark_type = post_data.get('watermark_type', 'text')

    watermark_text = post_data.get('watermark_text', '')
    transparency = post_data.get('watermark_transparency', 200)
    rotation = post_data.get('watermark_rotation', 0)
    scale = post_data.get('watermark_scale', 1.0)
    position = post_data.get('watermark_position', 'bottom_right')
    try:
        await callback.message.edit_text(
            get_text('watermark_info', lang),
            reply_markup=get_watermark_settings_inline_kb(lang, position, watermark_text, transparency, rotation, scale, watermark_type)
        )
    except Exception:
        pass

@watermark_router.callback_query(WatermarkCallbackFactory.filter(F.action == "select_transparency"))
async def select_watermark_transparency_menu(callback: types.CallbackQuery, state: FSMContext):
    """Watermark shaffofligini tanlash menyusi"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    current_transparency = post_data.get('watermark_transparency', 200)

    await callback.message.edit_text(
        get_text('watermark_select_transparency', lang),
        reply_markup=get_watermark_transparency_kb(lang, current_transparency)
    )
    await callback.answer()

@watermark_router.callback_query(WatermarkCallbackFactory.filter(F.action == "set_transparency"))
async def set_watermark_transparency(callback: types.CallbackQuery, callback_data: WatermarkCallbackFactory, state: FSMContext):
    """Watermark shaffofligini o'rnatish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    transparency = int(callback_data.value)
    post_data['watermark_transparency'] = transparency
    await state.update_data(post_data=post_data)

    await callback.answer(get_text('watermark_transparency_saved', lang))

    await apply_and_redraw_watermark(callback, state, lang)

    data = await state.get_data()
    post_data = data.get("post_data", {})

    position = post_data.get('watermark_position', 'bottom_right')
    watermark_text = post_data.get('watermark_text', '')
    rotation = post_data.get('watermark_rotation', 0)
    scale = post_data.get('watermark_scale', 1.0)
    transparency = post_data.get('watermark_transparency', 200)
    watermark_type = post_data.get('watermark_type', 'text')
    try:
        await callback.message.edit_text(
            get_text('watermark_info', lang),
            reply_markup=get_watermark_settings_inline_kb(lang, position, watermark_text, transparency, rotation, scale, watermark_type)
        )
    except Exception:
        pass

@watermark_router.callback_query(WatermarkCallbackFactory.filter(F.action == "select_rotation"))
async def select_watermark_rotation_menu(callback: types.CallbackQuery, state: FSMContext):
    """Watermark burilishini tanlash menyusi"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    current_rotation = post_data.get('watermark_rotation', 0)

    await callback.message.edit_text(
        get_text('watermark_select_rotation', lang),
        reply_markup=get_watermark_rotation_kb(lang, current_rotation)
    )
    await callback.answer()

@watermark_router.callback_query(WatermarkCallbackFactory.filter(F.action == "set_rotation"))
async def set_watermark_rotation(callback: types.CallbackQuery, callback_data: WatermarkCallbackFactory, state: FSMContext):
    """Watermark burilishini o'rnatish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    rotation = int(callback_data.value)
    post_data['watermark_rotation'] = rotation
    await state.update_data(post_data=post_data)

    await callback.answer(get_text('watermark_rotation_saved', lang))

    await apply_and_redraw_watermark(callback, state, lang)

    data = await state.get_data()
    post_data = data.get("post_data", {})

    position = post_data.get('watermark_position', 'bottom_right')
    watermark_text = post_data.get('watermark_text', '')
    transparency = post_data.get('watermark_transparency', 200)
    scale = post_data.get('watermark_scale', 1.0)
    rotation = post_data.get('watermark_rotation', 0)
    watermark_type = post_data.get('watermark_type', 'text')
    try:
        await callback.message.edit_text(
            get_text('watermark_info', lang),
            reply_markup=get_watermark_settings_inline_kb(lang, position, watermark_text, transparency, rotation, scale, watermark_type)
        )
    except Exception:
        pass

@watermark_router.callback_query(WatermarkCallbackFactory.filter(F.action == "select_scale"))
async def select_watermark_scale_menu(callback: types.CallbackQuery, state: FSMContext):
    """Watermark kattalashtirishini tanlash menyusi"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    current_scale = post_data.get('watermark_scale', 1.0)

    await callback.message.edit_text(
        get_text('watermark_select_scale', lang),
        reply_markup=get_watermark_scale_kb(lang, current_scale)
    )
    await callback.answer()

@watermark_router.callback_query(WatermarkCallbackFactory.filter(F.action == "set_scale"))
async def set_watermark_scale(callback: types.CallbackQuery, callback_data: WatermarkCallbackFactory, state: FSMContext):
    """Watermark kattalashtirishini o'rnatish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    scale = float(callback_data.value)
    post_data['watermark_scale'] = scale
    await state.update_data(post_data=post_data)

    await callback.answer(get_text('watermark_scale_saved', lang))

    await apply_and_redraw_watermark(callback, state, lang)

    data = await state.get_data()
    post_data = data.get("post_data", {})

    position = post_data.get('watermark_position', 'bottom_right')
    watermark_text = post_data.get('watermark_text', '')
    transparency = post_data.get('watermark_transparency', 200)
    rotation = post_data.get('watermark_rotation', 0)
    scale = post_data.get('watermark_scale', 1.0)
    watermark_type = post_data.get('watermark_type', 'text')
    try:
        await callback.message.edit_text(
            get_text('watermark_info', lang),
            reply_markup=get_watermark_settings_inline_kb(lang, position, watermark_text, transparency, rotation, scale, watermark_type)
        )
    except Exception:
        pass

@watermark_router.callback_query(WatermarkCallbackFactory.filter(F.action == "back_to_settings"))
async def back_to_watermark_settings(callback: types.CallbackQuery, state: FSMContext):
    """Watermark sozlamalariga qaytish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    current_position = post_data.get('watermark_position', 'bottom_right')
    watermark_text = post_data.get('watermark_text', '')
    transparency = post_data.get('watermark_transparency', 200)
    rotation = post_data.get('watermark_rotation', 0)
    scale = post_data.get('watermark_scale', 1.0)
    watermark_type = post_data.get('watermark_type', 'text')

    await state.set_state(PostCreation.configuring_post)

    try:
        await callback.message.edit_text(
            get_text('watermark_info', lang),
            reply_markup=get_watermark_settings_inline_kb(lang, current_position, watermark_text, transparency, rotation, scale, watermark_type)
        )
    except Exception:
        pass
    await callback.answer()

@watermark_router.callback_query(F.data == "back_to_media_settings")
async def back_to_media_settings(callback: types.CallbackQuery, state: FSMContext):
    """Media sozlamalariga qaytish"""
    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    has_spoiler = post_data.get('has_spoiler', False)
    is_paid = post_data.get('is_paid', False)
    show_caption_above = post_data.get('show_caption_above_media', False)
    has_caption = bool(post_data.get('caption'))
    content_type = post_data.get('content_type', 'photo')

    await state.set_state(PostCreation.waiting_for_media_settings)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        get_text('media_settings_msg', lang),
        reply_markup=get_media_settings_inline_kb(
            lang, has_spoiler, show_caption_above, has_caption, content_type, is_paid
        )
    )
    await callback.answer()

@watermark_router.callback_query(F.data == "back_to_post_settings")
async def back_to_post_settings(callback: types.CallbackQuery, state: FSMContext):
    """Post sozlamalariga (asosiy menyuga) qaytish"""
    from post_handlers.xreply_keyboard import get_post_settings_kb

    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    content_type = post_data.get('content_type', 'text')
    has_caption = bool(post_data.get('caption'))
    is_paid = post_data.get('is_paid', False)

    await state.set_state(PostCreation.configuring_post)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        get_text('back_to_settings_msg', lang),
        reply_markup=get_post_settings_kb(content_type, has_caption, lang, is_paid=is_paid)
    )
    await callback.answer()

@watermark_router.callback_query(F.data == "back_to_settings_menu")
async def back_to_settings_menu_from_watermark(callback: types.CallbackQuery, state: FSMContext):
    """Watermark sozlamalaridan sozlamalar menyusiga qaytish"""
    from post_handlers.xinline_keyboard import get_settings_menu_inline_kb

    data = await state.get_data()
    post_data = data.get("post_data", {})
    lang = await get_user_language(callback.from_user.id)

    content_type = post_data.get('content_type', 'photo')

    await state.set_state(PostCreation.waiting_for_media_settings)

    await callback.message.edit_text(
        get_text('select_settings_msg', lang),
        reply_markup=get_settings_menu_inline_kb(lang=lang, content_type=content_type)
    )

    await callback.answer()

async def watermark_settings_handler(event: types.Message | types.CallbackQuery, state: FSMContext):
    """Watermark sozlamalarini ochish - to'g'ridan-to'g'ri matn so'rash"""
    lang = await get_user_language(event.from_user.id)
    bot = event.bot if isinstance(event, types.Message) else event.message.bot

    await state.set_state(PostCreation.waiting_for_watermark_text)

    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('back_btn', lang), callback_data="back_to_post_settings")

    text = get_text('watermark_enter_text', lang)
    reply_markup = builder.as_markup()

    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text, reply_markup=reply_markup)
        await event.answer()
    else:
        await event.answer(text, reply_markup=reply_markup)

@watermark_router.callback_query(F.data == "watermark_settings")
async def open_watermark_settings(callback: types.CallbackQuery, state: FSMContext):
    await watermark_settings_handler(callback, state)

async def apply_watermark_to_post(bot: Bot, post_data: dict) -> dict:
    """
    Post ma'lumotlariga watermark qo'llash
    Bu funksiya post yuborilishidan oldin chaqiriladi
    """
    if not post_data.get('watermark_enabled', False):
        return post_data

    watermark_text = post_data.get('watermark_text', '')
    watermark_position = post_data.get('watermark_position', 'bottom_right')
    watermark_transparency = post_data.get('watermark_transparency', 200)
    watermark_rotation = post_data.get('watermark_rotation', 0)
    watermark_scale = post_data.get('watermark_scale', 1.0)
    content_type = post_data.get('content_type', 'text')

    if 'original_file_id' not in post_data and post_data.get('file_id'):
        post_data['original_file_id'] = post_data.get('file_id')

    file_id = post_data.get('original_file_id') or post_data.get('file_id')

    if not watermark_text or not file_id:
        return post_data

    if content_type not in ['photo', 'video']:
        return post_data

    new_file_id = await process_media_with_watermark(
        bot, file_id, watermark_text, watermark_position, content_type,
        watermark_transparency, watermark_rotation, watermark_scale
    )

    if new_file_id:
        post_data['file_id'] = new_file_id
        post_data['watermark_applied'] = True

    return post_data