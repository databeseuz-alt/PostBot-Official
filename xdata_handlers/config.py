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
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")