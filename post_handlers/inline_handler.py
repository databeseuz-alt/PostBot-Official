#--- START OF FILE inline_handler.py ---

import logging
from aiogram import Router, types, Bot
from aiogram.exceptions import TelegramBadRequest

from post_handlers.xinline_keyboard import generate_final_keyboard
from xdata_handlers.database import get_post_from_db

inline_router = Router()

#=============================================================================
# INLINE REJIM HANDLERI
#=============================================================================

@inline_router.inline_query()
async def inline_query_handler(query: types.InlineQuery, bot: Bot):
    post_code = query.query.strip()
    results = []

    def get_keyboard_as_dict(keyboard_markup):
        if not keyboard_markup:
            return None
        return keyboard_markup.model_dump(exclude_none=True)

    if not post_code:
        results.append({
            "type": "article",
            "id": "help_msg",
            "title": "Postni yuborish",
            "description": "Iltimos, botdan olgan postingiz kodini kiriting.",
            "input_message_content": {
                "message_text": "Post yaratish uchun botga o'ting. Keyin uning kodini bu yerga joylang."
            }
        })
        try:
    return await bot.answer_inline_query(inline_query_id=query.id, results=results, cache_time=1)
        except TelegramBadRequest as e:
            if "query is too old" in str(e) or "query ID is invalid" in str(e):
                logging.warning(f"Inline query eski: {query.id}")
                return
            raise

    post_data_from_db = await get_post_from_db(post_code)

    if post_data_from_db:
        content = post_data_from_db.get('post_content', {})
        buttons_matrix = post_data_from_db.get('buttons_matrix', [])

        keyboard_markup = generate_final_keyboard(buttons_matrix)
        keyboard_dict = get_keyboard_as_dict(keyboard_markup)

        content_type = content.get('content_type')
        file_id = content.get('file_id')
        caption = content.get('caption')
        parse_mode = content.get('parse_mode')
        disable_preview = content.get('disable_web_page_preview', False)

        try:
            if content_type == 'text':
                results.append({
                    "type": "article",
                    "id": post_code,
                    "title": "Postni yuborish",
                    "description": "Postni yuborish uchun shu yerga bosing",
                    "input_message_content": {
                        "message_text": content.get('text', ''),
                        "parse_mode": parse_mode,
                        "disable_web_page_preview": disable_preview
                    },
                    "reply_markup": keyboard_dict
                })
            elif content_type == 'photo' and file_id:
                results.append({
                    "type": "photo", "id": post_code, "photo_file_id": file_id,
                    "title": "Rasmli post", "caption": caption, "parse_mode": parse_mode,
                    "reply_markup": keyboard_dict
                })
            elif content_type == 'video' and file_id:
                results.append({
                    "type": "video", "id": post_code, "video_file_id": file_id,
                    "title": "Videoli post", "caption": caption, "parse_mode": parse_mode,
                    "reply_markup": keyboard_dict
                })
            elif content_type == 'audio' and file_id:
                 results.append({
                    "type": "audio", "id": post_code, "audio_file_id": file_id,
                    "title": content.get('title') or "Musiqa",
                    "performer": content.get('performer') or "Noma'lum ijrochi",
                    "caption": caption, "parse_mode": parse_mode, "reply_markup": keyboard_dict
                })
            elif content_type == 'document' and file_id:
                results.append({
                    "type": "document", "id": post_code, "document_file_id": file_id,
                    "title": content.get('file_name') or "Hujjat",
                    "caption": caption, "parse_mode": parse_mode, "reply_markup": keyboard_dict
                })
            elif content_type == 'video_note' and file_id:
                results.append({
                    "type": "video", "id": post_code, "video_file_id": file_id,
                    "title": "Aylana video", "caption": None, "parse_mode": parse_mode,
                    "reply_markup": keyboard_dict
                })
        except Exception as e:
            logging.error(f"Inline natija yasashda xatolik: {post_code} - {e}")

    if not results:
        results.append({
            "type": "article", "id": "not_found", "title": "Post topilmadi",
            "description": f"'{post_code}' kodli post mavjud emas.",
            "input_message_content": {"message_text": f"'{post_code}' kodli postni topa olmadim."}
        })

    try:
    await bot.answer_inline_query(inline_query_id=query.id, results=results, cache_time=0, is_personal=True)
    except TelegramBadRequest as e:
        if "query is too old" in str(e) or "query ID is invalid" in str(e):
            logging.warning(f"Inline query eski: {query.id}")
            return
        raise

#--- END OF FILE inline_handler.py ---
