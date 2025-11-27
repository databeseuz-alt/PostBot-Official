#--- START OF FILE vuser_states.py ---
from aiogram.fsm.state import State, StatesGroup

# =============================================================================
# FOYDALANUVCHI BO'LIMI UCHUN HOLATLAR (STATES)
# =============================================================================

class FeedbackState(StatesGroup):
    # Birinchi fikr-mulohazani kutish
    waiting_for_feedback = State()
    # Foydalanuvchi va admin o'rtasidagi muloqot
    chatting_with_admin = State()

class AdvertisingState(StatesGroup):
    # Reklama kontentini kutish
    waiting_for_ad_content = State()
    # Foydalanuvchi va admin o'rtasidagi muloqot
    chatting_with_admin = State()

# Kelajakda bu yerga foydalanuvchining boshqa holatlari
# (masalan, shaxsiy sozlamalar) qo'shilishi mumkin.
#--- END OF FILE vuser_states.py ---
