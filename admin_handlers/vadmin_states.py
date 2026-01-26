#--- START OF FILE vadmin_states.py ---
from aiogram.fsm.state import State, StatesGroup

# =============================================================================
# ADMIN BO'LIMI UCHUN HOLATLAR (STATES)
# =============================================================================

class AdminStates(StatesGroup):
    # Foydalanuvchini bloklash
    waiting_for_block_id = State()

    # Reklama yaratish
    waiting_for_ad_content = State()
    configuring_ad_post = State()
    waiting_for_ad_button_text = State()
    waiting_for_ad_button_url = State()
    managing_ad_button = State()

    # Foydalanuvchini qidirish
    waiting_for_user_query = State()
    viewing_user_profile = State() # --- YANGI QO'SHILDI ---

    # Kanalni ulash
    waiting_for_channel_forward = State()

    # --- YANGI QO'SHILGAN HOLATLAR ---
    # Admindan foydalanuvchiga xabar yuborish
    waiting_for_direct_message_user_id = State()
    waiting_for_direct_message_content = State()
    # --- O'ZGARISH TUGADI ---


class AdminGuideSettings(StatesGroup):
    waiting_for_guide_content = State()
    choosing_language = State()
#--- END OF FILE vadmin_states.py ---
