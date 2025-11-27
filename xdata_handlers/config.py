#--- START OF FILE config.py ---
import os
from dotenv import load_dotenv

# =============================================================================
# ATROF-MUHIT O'ZGARUVCHILARINI YUKLASH (.env)
# =============================================================================

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()


# =============================================================================
# BOTNING ASOSIY SOZLAMALARI
# =============================================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS_STR.split(',') if admin_id.strip().isdigit()]

# --- YANGI QO'SHILGAN O'ZGARUVCHI ---

FEEDBACK_RECIPIENT_ID_STR = os.getenv("FEEDBACK_RECIPIENT_ID")
FEEDBACK_RECIPIENT_ID = int(FEEDBACK_RECIPIENT_ID_STR) if FEEDBACK_RECIPIENT_ID_STR and FEEDBACK_RECIPIENT_ID_STR.isdigit() else None

# --- O'ZGARISH TUGADI ---

STORAGE_CHANNEL_ID_STR = os.getenv("STORAGE_CHANNEL_ID")
STORAGE_CHANNEL_ID = int(STORAGE_CHANNEL_ID_STR) if STORAGE_CHANNEL_ID_STR and STORAGE_CHANNEL_ID_STR.lstrip('-').isdigit() else None



# =============================================================================
# FAYL YO'LLARI VA MA'LUMOTLAR BAZASI
# =============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_PATH = os.path.join(BASE_DIR, "xdatabase.db")


# =============================================================================
# LOGLASH SOZLAMALARI
# =============================================================================

LOGGING_LEVEL = "INFO"
#--- END OF FILE config.py ---
