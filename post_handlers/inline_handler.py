from aiogram import Router, types, Bot
import logging

logger = logging.getLogger(__name__)

from post_handlers.xinline_keyboard import generate_final_keyboard
from xdata_handlers.database import get_post_from_db, get_user_language
from xdata_handlers.translator import get_text

inline_router = Router()

def has_reaction_buttons(buttons_matrix):
    """Tugmalar matritsasida reaksiya tugmalari borligini tekshirish."""
    if not buttons_matrix:
        return False
    for row in buttons_matrix:
        if not row:
            continue
        for btn in row:
            if btn and isinstance(btn, dict) and btn.get('type') == 'reaction':
                return True
    return False

@inline_router.inline_query()
async def inline_query_handler(query: types.InlineQuery, bot: Bot):
    post_code = query.query.strip()
    results = []

    user_lang = await get_user_language(query.from_user.id) if query.from_user else 'uzl'

    def get_keyboard_as_dict(keyboard_markup):
        if not keyboard_markup:
            return None
        return keyboard_markup.model_dump(exclude_none=True)

    if not post_code:
        results.append({
            "type": "article",
            "id": "help_msg",
            "title": get_text('inline_send_post', user_lang),
            "description": get_text('inline_enter_post_code', user_lang),
            "input_message_content": {
                "message_text": get_text('inline_use_bot_instructions', user_lang)
            }
        })
        return await bot.answer_inline_query(inline_query_id=query.id, results=results, cache_time=1)

    post_data_from_db = await get_post_from_db(post_code)

    if post_data_from_db:
        content = post_data_from_db.get('post_content', {})
        buttons_matrix = post_data_from_db.get('buttons_matrix', [])

        content_type = content.get('content_type')
        is_paid = content.get('is_paid', False)

        unsupported_inline = ['dice', 'paid_media', 'poll', 'quiz']
        if has_reaction_buttons(buttons_matrix) or content_type in unsupported_inline or is_paid:
            reject_title = get_text('inline_reaction_not_supported_title', user_lang)
            reject_desc = get_text('inline_reaction_not_supported_desc', user_lang)
            reject_msg = get_text('inline_reaction_not_supported_msg', user_lang)

            if content_type in unsupported_inline or is_paid:
                reject_title = "Dasturlanmagan format 🚫"
                reject_desc = "Bu format (Dice, Pulli Media) inline rejimda ishlamaydi."
                reject_msg = "Afsuski, Telegram ushbu formatni inline rejim orqali yuborishni qo'llab-quvvatlamaydi."

            results.append({
                "type": "article",
                "id": "reaction_not_supported",
                "title": reject_title,
                "description": reject_desc,
                "input_message_content": {
                    "message_text": get_text('inline_reaction_not_supported_msg', user_lang)
                }
            })
            return await bot.answer_inline_query(inline_query_id=query.id, results=results, cache_time=0, is_personal=True)

        keyboard_markup = generate_final_keyboard(buttons_matrix)
        keyboard_dict = get_keyboard_as_dict(keyboard_markup)

        content_type = content.get('content_type')
        file_id = content.get('file_id')
        caption = content.get('caption')
        parse_mode = content.get('parse_mode', 'HTML')
        disable_preview = content.get('disable_web_page_preview', False)  # Standart yoqilgan

        try:
            if content_type == 'text':
                results.append({
                    "type": "article",
                    "id": post_code,
                    "title": get_text('inline_send_post', user_lang),
                    "description": get_text('inline_click_to_send', user_lang),
                    "input_message_content": {
                        "message_text": content.get('text', ''),
                        "parse_mode": parse_mode,
                        "disable_web_page_preview": disable_preview
                    },
                    "reply_markup": keyboard_dict
                })
            elif content_type == 'photo' and file_id:
                results.append({
                    "type": "photo", 
                    "id": post_code, 
                    "photo_file_id": file_id, # Cached Photo formatida
                    "caption": caption, 
                    "parse_mode": parse_mode,
                    "reply_markup": keyboard_dict
                })
            elif content_type == 'video' and file_id:
                results.append({
                    "type": "video", 
                    "id": post_code, 
                    "video_file_id": file_id, # Cached Video formatida
                    "title": get_text('inline_video_post', user_lang), 
                    "caption": caption, 
                    "parse_mode": parse_mode,
                    "reply_markup": keyboard_dict
                })
            elif content_type == 'audio' and file_id:
                 results.append({
                    "type": "audio", 
                    "id": post_code, 
                    "audio_file_id": file_id,
                    "caption": caption, 
                    "parse_mode": parse_mode, 
                    "reply_markup": keyboard_dict
                })
            elif content_type == 'document' and file_id:
                results.append({
                    "type": "document", 
                    "id": post_code, 
                    "document_file_id": file_id,
                    "title": content.get('file_name') or get_text('inline_document', user_lang),
                    "caption": caption, 
                    "parse_mode": parse_mode, 
                    "reply_markup": keyboard_dict
                })
            elif content_type == 'video_note' and file_id:
                results.append({
                    "type": "video", 
                    "id": post_code, 
                    "video_file_id": file_id,
                    "title": get_text('inline_video_note', user_lang), 
                    "caption": None, 
                    "reply_markup": keyboard_dict
                })
            elif content_type == 'voice' and file_id:
                results.append({
                    "type": "voice", 
                    "id": post_code, 
                    "voice_file_id": file_id,
                    "title": get_text('inline_voice_message', user_lang), 
                    "caption": caption, 
                    "reply_markup": keyboard_dict
                })
            elif content_type == 'animation' and file_id:
                results.append({
                    "type": "gif", 
                    "id": post_code, 
                    "gif_file_id": file_id,
                    "title": get_text('inline_gif_post', user_lang), 
                    "caption": caption, 
                    "parse_mode": parse_mode,
                    "reply_markup": keyboard_dict
                })
            elif content_type == 'sticker' and file_id:
                results.append({
                    "type": "sticker", 
                    "id": post_code, 
                    "sticker_file_id": file_id,
                    "reply_markup": keyboard_dict
                })
            elif content_type == 'location':
                results.append({
                    "type": "location",
                    "id": post_code,
                    "latitude": content.get('latitude', 0.0),
                    "longitude": content.get('longitude', 0.0),
                    "title": content.get('title') or "Lokatsiya",
                    "reply_markup": keyboard_dict
                })

        except Exception:
            pass

    if not results:
        results.append({
            "type": "article", "id": "not_found", "title": get_text('inline_post_not_found', user_lang),
            "description": get_text('inline_post_not_found_desc', user_lang).format(post_code=post_code),
            "input_message_content": {"message_text": get_text('inline_post_not_found_message', user_lang).format(post_code=post_code)}
        })

    await bot.answer_inline_query(inline_query_id=query.id, results=results, cache_time=0, is_personal=True)
