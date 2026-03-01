import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS_STR.split(',') if admin_id.strip().isdigit()]

FEEDBACK_RECIPIENT_ID_STR = os.getenv("FEEDBACK_RECIPIENT_ID")
FEEDBACK_RECIPIENT_ID = int(FEEDBACK_RECIPIENT_ID_STR) if FEEDBACK_RECIPIENT_ID_STR and FEEDBACK_RECIPIENT_ID_STR.isdigit() else None

STORAGE_CHANNEL_ID_STR = os.getenv("STORAGE_CHANNEL_ID")
STORAGE_CHANNEL_ID = int(STORAGE_CHANNEL_ID_STR) if STORAGE_CHANNEL_ID_STR and STORAGE_CHANNEL_ID_STR.lstrip('-').isdigit() else None

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

AI_SYSTEM_INSTRUCTION = """
Sen Telegram kanallar uchun post yozib beradigan professional SMM-yordamchisan.
Vazifang: Foydalanuvchi so'roviga mos sifatli, kreativ va o'qishli post tayyorlash.
Qoidalar:
1. Javobingda HECH QANDAY kirish so'zlari (masalan: "Albatta", "Mana siz so'ragan post", "Salom") bo'lmasin.
2. Natijada faqat tayyor post matni bo'lishi kerak.
3. Postni chiroyli formatlash (emoji, qalin harflar, ro'yxatlar) bilan yoz.
4. Agar foydalanuvchi biror narsani tushuntirishni so'rasa ham, qisqa va lo'nda javob ber.
5. Post so'ngida mavzuga mos 3-5 ta hashtag qo'sh.
Maqsad: Foydalanuvchi sening javobingni olib, o'zgarishsiz darhol kanalga joylay olishi kerak.
"""
