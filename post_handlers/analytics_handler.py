from aiogram import F, Router, types
from aiogram.filters import StateFilter

from xdata_handlers.database import get_user_language
from post_handlers.localize_filter import LocalizedText

analytics_router = Router()

@analytics_router.message(LocalizedText('channel_stats_btn'), StateFilter(None))
async def show_statistics(message: types.Message):
    """📊 Statistika tugmasi."""
    user_id = message.from_user.id
    lang = await get_user_language(user_id)

    text = "⚠️ <b>Ushbu bo'lim vaqtinchalik o'chirilgan.</b>\n\nTez orada yangilanishlar bo'ladi!"
    await message.answer(text, parse_mode="HTML")
