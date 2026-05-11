import html
import logging
from aiogram import F, Router, types, Bot
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    ReplyKeyboardRemove, 
    InlineKeyboardButton, 
    LabeledPrice, 
    PreCheckoutQuery, 
    SuccessfulPayment,
    ContentType
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)

from xdata_handlers.database import get_user_language
from xdata_handlers.translator import get_text

donate_router = Router()

DONATE_ADMIN_ID = 8260387282


def get_donate_amount_kb(lang: str):
    """Donat miqdorlari inline tugmalari - Telegram Stars"""
    builder = InlineKeyboardBuilder()
    amounts = [10, 20, 30, 40, 50, 100]
    for amount in amounts:
        builder.add(InlineKeyboardButton(text=f"{amount} ⭐", callback_data=f"donate_stars:{amount}"))
    
    builder.adjust(3, 3)
    return builder.as_markup()


@donate_router.message(Command("donate"))
async def cmd_donate(message: types.Message, state: FSMContext, command: CommandObject):
    """Donate buyrug'i - donat sahifasini ko'rsatadi yoki to'g'ridan-to'g'ri to'lov yuboradi"""
    await state.clear()
    
    # Argument bormi? (masalan /donate 50)
    if command.args and command.args.isdigit():
        amount = int(command.args)
        if 1 <= amount <= 25000:
            return await send_donation_invoice(message, amount)

    remover_message = await message.answer("...", reply_markup=ReplyKeyboardRemove())
    await remover_message.delete()
    
    lang = await get_user_language(message.from_user.id)
    
    # Donat xabari
    donate_text = get_text('donate_msg', lang)
    
    await message.answer(
        donate_text,
        reply_markup=get_donate_amount_kb(lang),
        parse_mode="HTML"
    )


async def send_donation_invoice(message: types.Message, amount: int):
    """Telegram Stars orqali to'lov yuborish (Invoice)"""
    try:
        title = "Botni qo'llab-quvvatlash"
        description = f"Bot rivojlanishi uchun {amount} Telegram Stars donat qilish"
        payload = f"donate_{message.from_user.id}_{amount}"
        currency = "XTR"  # Telegram Stars valyutasi
        
        prices = [LabeledPrice(label="⭐ Donation", amount=amount)]
        
        await message.answer_invoice(
            title=title,
            description=description,
            payload=payload,
            provider_token="",  # Stars uchun bo'sh qoldiriladi
            currency=currency,
            prices=prices,
            start_parameter="donate"
        )
    except Exception as e:
        logger.error(f"Invoice yuborishda xatolik: {e}")
        await message.answer("❌ To'lov xabari yuborishda xatolik yuz berdi.")


@donate_router.callback_query(F.data.startswith("donate_stars:"))
async def handle_donate_stars(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    """Donat Stars tugmasi bosilganda - Invoice yuborish"""
    amount = int(callback.data.split(":")[1])
    await callback.message.delete()
    await send_donation_invoice(callback.message, amount)
    await callback.answer()


@donate_router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """To'lovni tasdiqlash uchun (10 soniya ichida javob berish shart)"""
    await pre_checkout_query.answer(ok=True)


@donate_router.message(F.successful_payment)
async def successful_payment_handler(message: types.Message, bot: Bot):
    """To'lov muvaffaqiyatli yakunlanganda bajariladigan amal"""
    payment = message.successful_payment
    amount = payment.total_amount
    user = message.from_user
    lang = await get_user_language(user.id)
    
    # Adminga xabar yuborish (Stars haqida)
    try:
        admin_info = (
            f"🌟 <b>YANGI DONAT (STARS)!</b> 🌟\n\n"
            f"👤 <b>Foydalanuvchi:</b> {user.full_name}\n"
            f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        )
        if user.username:
            admin_info += f"🔗 <b>Username:</b> @{user.username}\n"
        
        admin_info += f"💰 <b>Miqdor:</b> {amount} ⭐\n"
        admin_info += f"📝 <b>Payload:</b> <code>{payment.invoice_payload}</code>"
        
        await bot.send_message(DONATE_ADMIN_ID, admin_info, parse_mode="HTML")
        
        # Foydalanuvchiga rahmatnoma
        await message.answer(
            f"✅ <b>Rahmat!</b>\n\nSiz botni {amount} ⭐ bilan qo'llab-quvvatladingiz. "
            "Sizning yordamingiz botni yanada rivojlantirishga yordam beradi!",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Successful payment notify error: {e}")
