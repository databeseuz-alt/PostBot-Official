import asyncio
import threading
import os
from flask import Flask

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from xdata_handlers import config
from xdata_handlers.database import init_db
from xdata_handlers.translator import load_translations

from admin_handlers.admin_handler import admin_router
from admin_handlers.advertisement import ad_router
from admin_handlers.block_handler import block_router
from admin_handlers.channel_handler import channel_router
from admin_handlers.statistic_handler import statistic_router
from admin_handlers.database_handler import db_router

from post_handlers.start_handler import start_router
from post_handlers.lang_handler import lang_router
from post_handlers.post_handler import post_router
from post_handlers.button_handler import button_router
from post_handlers.reply_handler import reply_router, callback_router
from post_handlers.media_handler import media_router
from post_handlers.done_handler import done_router
from post_handlers.editp_handler import edit_post_router
from post_handlers.inline_handler import inline_router
from post_handlers.send_handler import send_router
from post_handlers.mychannels_handler import mychannels_router
from post_handlers.schedule_handler import schedule_router
from post_handlers.assistant_handler import ai_assistant_router
from post_handlers.watermark_handler import watermark_router
from post_handlers.signature_handler import router as auto_signature_router

from user_handlers.feedback_handler import feedback_router
from user_handlers.settings_handler import settings_router

from user_handlers.ad_handler import ad_router as user_ad_router

from admin_handlers.block_handler import BlockUserMiddleware
from admin_handlers.statsmiddleware import UserActivityMiddleware

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

async def main():

    await init_db()

    load_translations()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode='HTML')
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.update.middleware(UserActivityMiddleware())
    dp.update.middleware(BlockUserMiddleware())

    from user_handlers.errorlog_handler import error_handler
    dp.errors.register(error_handler)

    dp.include_router(admin_router)
    dp.include_router(ad_router)
    dp.include_router(block_router)
    dp.include_router(channel_router)
    dp.include_router(statistic_router)
    dp.include_router(db_router)

    dp.include_router(start_router)
    dp.include_router(ai_assistant_router) 

    dp.include_router(feedback_router)
    dp.include_router(settings_router)
    dp.include_router(user_ad_router)

    dp.include_router(lang_router)
    dp.include_router(post_router)
    dp.include_router(button_router)
    dp.include_router(reply_router)
    dp.include_router(callback_router)
    dp.include_router(media_router)
    dp.include_router(done_router)
    dp.include_router(edit_post_router)
    dp.include_router(inline_router)
    dp.include_router(send_router)
    dp.include_router(mychannels_router)
    dp.include_router(schedule_router)
    dp.include_router(watermark_router)
    dp.include_router(auto_signature_router)

    from post_handlers.schedule_handler import start_scheduler
    start_scheduler(bot)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":

    t = threading.Thread(target=run_web_server, daemon=True)
    t.start()

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception:
        pass
