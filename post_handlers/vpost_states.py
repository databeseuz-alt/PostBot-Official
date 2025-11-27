#--- START OF FILE vpost_stats.py ---

from aiogram.fsm.state import State, StatesGroup

class PostCreation(StatesGroup):
    # Asosiy jarayon
    waiting_for_content = State()
    configuring_post = State()
    waiting_for_edit_code = State()

    # Tugmalar bilan ishlash
    waiting_for_button_text = State()
    waiting_for_button_url = State()
    managing_button = State()
    editing_button_text = State()
    editing_button_url = State()

    # Postga nom berish
    waiting_for_post_name = State()

class PostSending(StatesGroup):
    # Kanal qo'shish jarayoni uchun
    waiting_for_channel_info = State()
    # Postni yuborish jarayoni uchun
    choosing_channel_to_send = State()
    confirming_post_send = State()

#--- END OF FILE vpost_stats.py ---
