from aiogram import Router, types
import logging
from xdata_handlers.database import set_absolute_views, get_connection, release_connection

logger = logging.getLogger(__name__)
analytics_router = Router()

@analytics_router.channel_post()
@analytics_router.edited_channel_post()
async def track_views(message: types.Message):
    """Kanalga kelayotgan xabarlar/tahrirlarni ko'rishlarni sanash uchun kuzatadi."""
    # Check if views attribute exists and is not None
    views = getattr(message, 'views', None)
    if not views:
        return
    
    def _get_post_code(chat_id, msg_id):
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT post_code FROM send_posts WHERE channel_id = %s AND message_id = %s",
                (chat_id, msg_id)
            )
            row = cursor.fetchone()
            return row[0] if row else None
        except:
            return None
        finally:
            if conn: release_connection(conn)
    
    import asyncio
    p_code = await asyncio.to_thread(_get_post_code, message.chat.id, message.message_id)
    
    if p_code:
        await set_absolute_views(p_code, message.chat.id, views)
        logger.debug(f"Views updated for {p_code}: {views}")
