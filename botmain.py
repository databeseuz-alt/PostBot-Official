import asyncio
import logging
import threading
import os
from flask import Flask

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

#==================================================
# --- YADRO KOMPONENTLARINI IMPORT QILISH ---
#==================================================
from xdata_handlers import config
from xdata_handlers.database import init_db
from xdata_handlers.translator import load_translations

#==================================================
# --- ROUTERLARNI IMPORT QILISH ---
#==================================================
# Admin bo'limi
from admin_handlers.admin_handler import admin_router
from admin_handlers.advertisement import ad_router
from admin_handlers.block_handler import block_router
from admin_handlers.channel_handler import channel_router
from admin_handlers.statistic_handler import statistic_router
from admin_handlers.database_handler import db_router

# Postlar bilan ishlash bo'limi
from post_handlers.start_handler import start_router
from post_handlers.lang_handler import lang_router
from post_handlers.post_handler import post_router
from post_handlers.button_handler import button_router
from post_handlers.reply_handler import reply_router
from post_handlers.done_handler import done_router
from post_handlers.editp_handler import edit_post_router
from post_handlers.inline_handler import inline_router
from post_handlers.send_handler import send_router
from post_handlers.mychannels_handler import mychannels_router

# Foydalanuvchi bo'limi
from user_handlers.feedback_handler import feedback_router
from user_handlers.settings_handler import settings_router
from user_handlers.errorlog_handler import error_router
from user_handlers.ad_handler import ad_router as user_ad_router

#==================================================
# --- MIDDLEWARE'LARNI IMPORT QILISH ---
#==================================================
from admin_handlers.block_handler import BlockUserMiddleware
from admin_handlers.security_handler import AntiFloodMiddleware
from admin_handlers.statsmiddleware import UserActivityMiddleware

#==================================================
# --- RENDER UCHUN FLASK SERVER (FAKE SERVER) ---
#==================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web_server():
    # Render PORT environment o'zgaruvchisini beradi, bo'lmasa 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

#==================================================
# --- BOT BUYRUQLARINI O'RNATISH FUNKSIYASI ---
#==================================================
async def set_bot_commands(bot: Bot):
    """Bot uchun buyruqlar menyusini o'rnatadi."""
    # Eski buyruqlarni tozalash
    await bot.delete_my_commands()
    
    # Yangi buyruqlarni o'rnatish
    commands = [
        BotCommand(command="addchannel", description="add a new channel"),
        BotCommand(command="mychannels", description="edit your channels"),
        BotCommand(command="feedback", description="report an error")
    ]
    await bot.set_my_commands(commands)

#==================================================
# --- BOT TAVSIFINI O'RNATISH FUNKSIYASI ---
#==================================================
async def set_bot_description(bot: Bot):
    """Bot uchun tavsif va qisqa ma'lumotlarni o'rnatadi."""
    # Qisqa tavsif (Profil uchun)
    short_desc = "✍️ Create pro posts with buttons!"
    await bot.set_my_short_description(short_description=short_desc)

    # To'liq tavsif (Startdan oldin ko'rinadigan qism)
    full_desc = (
        "🚀 Create pro posts with buttons!\n"
        "✨ Add inline links to any media.\n"
        "🔡 HTML & Markdown V2 supported.\n"
        "📢 Easy multi-channel management.\n"
        "🌍 Supports 10 different languages."
    )
    await bot.set_my_description(description=full_desc)


async def main():
    #==================================================
    # --- BOSHLANG'ICH SOZLASH ---
    #==================================================
    logging.basicConfig(level=config.LOGGING_LEVEL)
    init_db()
    load_translations()

    #==================================================
    # --- AIOGRAM OBYEKTLARINI YARATISH ---
    #==================================================
    
    # PROXYSIZ ULANISH (Session ishlatilmaydi)
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode='HTML')
    )
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    #==================================================
    # --- MIDDLEWARE'LARNI ULASH ---
    #==================================================
    
    # 1. Har qanday holatda foydalanuvchi faolligini qayd etish
    dp.update.middleware(UserActivityMiddleware())
    # 2. Faollik qayd etilgandan so'ng, foydalanuvchi bloklanganligini tekshirish
    dp.update.middleware(BlockUserMiddleware())
    # 3. Faqat xabarlar uchun flood-nazorat
    dp.message.middleware(AntiFloodMiddleware())


    #==================================================
    # --- BARCHA ROUTERLARNI ULASH ---
    #==================================================
    # Xatoliklarni tutuvchi router eng birinchi ulanishi kerak
    dp.include_router(error_router)

    # Admin routerlari
    dp.include_router(admin_router)
    dp.include_router(ad_router)
    dp.include_router(block_router)
    dp.include_router(channel_router)
    dp.include_router(statistic_router)
    dp.include_router(db_router)

    # Foydalanuvchi routerlari
    dp.include_router(feedback_router)
    dp.include_router(settings_router)
    dp.include_router(user_ad_router)

    # Post routerlari (keng qamrovli bo'lgani uchun oxirida)
    dp.include_router(start_router)
    dp.include_router(lang_router)
    dp.include_router(post_router)
    dp.include_router(button_router)
    dp.include_router(reply_router)
    dp.include_router(done_router)
    dp.include_router(edit_post_router)
    dp.include_router(inline_router)
    dp.include_router(send_router)
    dp.include_router(mychannels_router)

    #==================================================
    # --- BOTNI ISHGA TUSHIRISH ---
    #==================================================

    # Bot buyruqlari va tavsiflarini o'rnatamiz
    await set_bot_commands(bot)
    await set_bot_description(bot)

    logging.info("Bot ishga tushmoqda (Polling)...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Web serverni alohida potokda ishga tushiramiz (Render uchun)
    t = threading.Thread(target=run_web_server)
    t.start()

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
    except Exception as e:
        logging.error(f"Botda kutilmagan xatolik: {e}", exc_info=True)
