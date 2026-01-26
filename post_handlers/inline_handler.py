#--- START OF FILE post_handlers/inline_handler.py ---

import logging
from aiogram import Router, types, Bot

from post_handlers.xinline_keyboard import generate_final_keyboard
from xdata_handlers.database import get_post_from_db, get_user_language
from xdata_handlers.translator import get_text

inline_router = Router()

#=============================================================================
# INLINE REJIM HANDLERI
#=============================================================================

@inline_router.inline_query()
async def inline_query_handler(query: types.InlineQuery, bot: Bot):
    post_code = query.query.strip()
    results = []
    
    # Get user language for localization
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
                    "type": "photo", "id": post_code, "photo_file_id": file_id,
                    "title": get_text('inline_photo_post', user_lang), "caption": caption, "parse_mode": parse_mode,
                    "reply_markup": keyboard_dict
                })
            elif content_type == 'video' and file_id:
                results.append({
                    "type": "video", "id": post_code, "video_file_id": file_id,
                    "title": get_text('inline_video_post', user_lang), "caption": caption, "parse_mode": parse_mode,
                    "reply_markup": keyboard_dict
                })
            elif content_type == 'audio' and file_id:
                 results.append({
                    "type": "audio", "id": post_code, "audio_file_id": file_id,
                    "title": content.get('title') or get_text('inline_music', user_lang),
                    "performer": content.get('performer') or get_text('inline_unknown_artist', user_lang),
                    "caption": caption, "parse_mode": parse_mode, "reply_markup": keyboard_dict
                })
            elif content_type == 'document' and file_id:
                results.append({
                    "type": "document", "id": post_code, "document_file_id": file_id,
                    "title": content.get('file_name') or get_text('inline_document', user_lang),
                    "caption": caption, "parse_mode": parse_mode, "reply_markup": keyboard_dict
                })
            elif content_type == 'video_note' and file_id:
                results.append({
                    "type": "video", "id": post_code, "video_file_id": file_id,
                    "title": get_text('inline_video_note', user_lang), "caption": None, "parse_mode": parse_mode,
                    "reply_markup": keyboard_dict
                })
            elif content_type == 'voice' and file_id:
                results.append({
                    "type": "voice", 
                    "id": post_code, 
                    "voice_file_id": file_id,
                    "title": get_text('inline_voice_message', user_lang), 
                    "caption": caption, 
                    "parse_mode": parse_mode, 
                    "reply_markup": keyboard_dict
                })

        except Exception as e:
            logging.error(f"Inline natija yasashda xatolik: {post_code} - {e}")

    if not results:
        results.append({
            "type": "article", "id": "not_found", "title": get_text('inline_post_not_found', user_lang),
            "description": get_text('inline_post_not_found_desc', user_lang).format(post_code=post_code),
            "input_message_content": {"message_text": get_text('inline_post_not_found_message', user_lang).format(post_code=post_code)}
        })

    await bot.answer_inline_query(inline_query_id=query.id, results=results, cache_time=0, is_personal=True)

#--- END OF FILE post_handlers/inline_handler.py ---
