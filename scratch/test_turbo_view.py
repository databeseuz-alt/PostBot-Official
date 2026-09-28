import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from xdata_handlers.config import BOT_TOKEN

EMOJI_CIRC_EMPTY = "5321100107603556331"
EMOJI_CIRC_CHECK = "5321505741494856875"

async def test():
    bot = Bot(token=BOT_TOKEN)
    user_id = 8599958572
    try:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="⚡ Ha, turbo rejim yoqildi",
            callback_data="test_turbo",
            icon_custom_emoji_id=EMOJI_CIRC_CHECK
        )
        builder.button(
            text="🚀 Hozir chop etish",
            callback_data="test_now",
            icon_custom_emoji_id=EMOJI_CIRC_CHECK
        )
        builder.button(
            text="⏰ Jadval bo'yicha",
            callback_data="test_schedule",
            icon_custom_emoji_id=EMOJI_CIRC_EMPTY
        )
        builder.button(
            text="❌ Bekor qilish",
            callback_data="test_cancel"
        )
        builder.adjust(1, 2, 1)
        
        msg = await bot.send_message(
            chat_id=user_id,
            text="<tg-emoji emoji-id=\"5321505741494856875\">🟡</tg-emoji> <b>Turbo rejim yangilandi!</b>\nTugmalarni ko'ring:",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        print("Sent successfully! Message ID:", msg.message_id)
    except Exception as e:
        print("Error:", e)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(test())
