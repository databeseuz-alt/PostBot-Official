from aiogram.fsm.state import State, StatesGroup

class FeedbackState(StatesGroup):
    waiting_for_feedback = State()
    chatting_with_admin = State()

class AdvertisingState(StatesGroup):
    waiting_for_ad_content = State()
    chatting_with_admin = State()
