import html
import logging
from typing import Callable, Dict, Any, Awaitable
from datetime import datetime, timedelta

from aiogram import BaseMiddleware, Bot
from aiogram.types import Message

from xdata_handlers.translator import get_text
from xdata_handlers.database import get_user_language, get_now
from xdata_handlers import config

logger = logging.getLogger(__name__)

USER_DATA = {}

THROTTLE_TIME_SECONDS = 0
SPAM_MESSAGE_LIMIT = 100
BAN_DURATION_MINUTES = 5


class AntiFloodMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:

        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id
        current_time = get_now()
        bot: Bot = data.get('bot')
        lang = await get_user_language(user_id)

        if user_id not in USER_DATA:
            USER_DATA[user_id] = {
                'last_message_time': current_time,
                'last_message_text': event.text,
                'spam_count': 1,
                'banned_until': None
            }
            return await handler(event, data)

        user = USER_DATA[user_id]

        if user['banned_until'] and user['banned_until'] > current_time:
            return
        elif user['banned_until'] and user['banned_until'] <= current_time:
            user['banned_until'] = None

        time_diff = (current_time - user['last_message_time']).total_seconds()
        if time_diff < THROTTLE_TIME_SECONDS:
            await event.answer(get_text('flood_warning', lang))
            return

        user['last_message_time'] = current_time

        if event.text and event.text == user['last_message_text']:
            user['spam_count'] += 1
        else:
            user['spam_count'] = 1
            user['last_message_text'] = event.text

        if user['spam_count'] >= SPAM_MESSAGE_LIMIT:
            user['banned_until'] = current_time + timedelta(minutes=BAN_DURATION_MINUTES)
            user['spam_count'] = 1

            ban_message = get_text('spam_ban_user', lang).format(minutes=BAN_DURATION_MINUTES)
            await event.answer(ban_message)

            safe_nickname = html.escape(event.from_user.full_name)
            safe_spam_message = html.escape(event.text or "")

            admin_notification = (
                f"🚫 <b>Foydalanuvchi spam uchun vaqtinchalik bloklandi!</b>\n\n"
                f"<b>Foydalanuvchi:</b> {safe_nickname}\n"
                f"<b>ID:</b> <code>{user_id}</code>\n"
                f"<b>Username:</b> @{event.from_user.username or 'N/A'}\n"
                f"<b>Blok muddati:</b> {BAN_DURATION_MINUTES} daqiqa\n"
                f"<b>Spam xabari:</b> \"{safe_spam_message}\""
            )
            for admin_id in config.ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, admin_notification)
                except Exception:
                    pass
            return

        return await handler(event, data)
