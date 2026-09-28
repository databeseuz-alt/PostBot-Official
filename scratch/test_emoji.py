import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from xdata_handlers.config import BOT_TOKEN

async def test():
    bot = Bot(token=BOT_TOKEN)
    user_id = 8599958572
    try:
        btn = InlineKeyboardButton(text='Test Button', callback_data='test', icon_custom_emoji_id='5321505741494856875')
        kb = InlineKeyboardMarkup(inline_keyboard=[[btn]])
        msg = await bot.send_message(chat_id=user_id, text='Testing button custom emoji...', reply_markup=kb)
        print('SUCCESS sending button with icon_custom_emoji_id!')
        await asyncio.sleep(1)
        await bot.delete_message(chat_id=user_id, message_id=msg.message_id)
    except Exception as e:
        print('Button emoji error:', e)

    try:
        txt = 'Test text: <tg-emoji emoji-id="5321505741494856875">🟡</tg-emoji> Turbo rejim'
        msg2 = await bot.send_message(chat_id=user_id, text=txt, parse_mode='HTML')
        print('SUCCESS sending HTML tg-emoji in text!')
        await asyncio.sleep(1)
        await bot.delete_message(chat_id=user_id, message_id=msg2.message_id)
    except Exception as e:
        print('Text tg-emoji error:', e)
        
    await bot.session.close()

if __name__ == '__main__':
    asyncio.run(test())
