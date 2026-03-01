from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_block_id = State()

    waiting_for_ad_content = State()
    configuring_ad_post = State()
    waiting_for_ad_button_text = State()
    waiting_for_ad_button_url = State()
    managing_ad_button = State()

    waiting_for_user_query = State()
    viewing_user_profile = State() # --- YANGI QO'SHILDI ---

    waiting_for_channel_forward = State()

    waiting_for_direct_message_user_id = State()
    waiting_for_direct_message_content = State()

class AdminGuideSettings(StatesGroup):
    waiting_for_guide_content = State()
    choosing_language = State()
