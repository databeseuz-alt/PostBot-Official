from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from xdata_handlers.translator import get_text

features_router = Router()

IMPLEMENTED_FEATURES = ["smart_settings", "rich_editor", "first_reaction", "test_posts"]

def get_features_keyboard():
    builder = InlineKeyboardBuilder()
    
    buttons = [
        ("Aqlli sozlamalar", "feat:smart_settings"),
        ("Boy tahrirchi", "feat:rich_editor"),
        ("Birinchi reaksiya", "feat:first_reaction"),
        ("Test uslubidagi postlar", "feat:test_posts"),
        ("Avto imzo", "feat:auto_sig"),
        ("Suv belgilari", "feat:watermark"),
        ("Kompozit postlar", "feat:composite"),
        ("Nashr qilish sozlamalari", "feat:publish_settings"),
        ("Qiziqarli postlar", "feat:interesting"),
        ("🔥 Post shablonlari", "feat:templates"),
        ("🔥 Guruhli nashr", "feat:group_publish"),
        ("Jadval", "feat:schedule"),
        ("🔥 Turbo rejim", "feat:turbo"),
        ("Ko'p-post qilish", "feat:multi_post"),
        ("Takroriy", "feat:recurring"),
        ("Guruhlar va mavzular", "feat:groups_topics"),
        ("Xizmat xabarlari", "feat:service_msgs"),
        ("AI Yordamchisi", "feat:ai_assistant"),
        ("Homiylik postlari", "feat:sponsor_posts"),
        ("Post tahrirlash", "feat:edit_post")
    ]
    
    for text, callback_data in buttons:
        builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))
    
    builder.adjust(2)
    
    # Bottom button
    builder.row(InlineKeyboardButton(text="Boshlash 🚀", callback_data="start_bot"))
    
    return builder.as_markup()

async def show_features_menu(message: types.Message):
    text = get_text('features_msg', 'uzl')
    await message.answer(text, reply_markup=get_features_keyboard())

@features_router.callback_query(F.data == "show_features")
async def callback_show_features(callback: types.CallbackQuery):
    text = get_text('features_msg', 'uzl')
    await callback.message.edit_text(text, reply_markup=get_features_keyboard())
    await callback.answer()

def get_navigation_keyboard(current_feature: str):
    builder = InlineKeyboardBuilder()
    
    try:
        idx = IMPLEMENTED_FEATURES.index(current_feature)
        prev_idx = (idx - 1) % len(IMPLEMENTED_FEATURES)
        next_idx = (idx + 1) % len(IMPLEMENTED_FEATURES)
        
        prev_feat = IMPLEMENTED_FEATURES[prev_idx]
        next_feat = IMPLEMENTED_FEATURES[next_idx]
        
        builder.row(
            InlineKeyboardButton(text="← Oldingi", callback_data=f"feat:{prev_feat}"),
            InlineKeyboardButton(text="Keyingi →", callback_data=f"feat:{next_feat}")
        )
    except ValueError:
        # If not in implemented list, just show static buttons or back
        builder.row(
            InlineKeyboardButton(text="← Oldingi", callback_data="show_features"),
            InlineKeyboardButton(text="Keyingi →", callback_data="show_features")
        )

    builder.row(InlineKeyboardButton(text="Barcha xususiyatlar ↓", callback_data="show_features"))
    builder.row(InlineKeyboardButton(text="Boshlash 🚀", callback_data="start_bot"))
    return builder.as_markup()

@features_router.callback_query(F.data.startswith("feat:"))
async def handle_feature_details(callback: types.CallbackQuery):
    feature = callback.data.split(":")[1]
    bot_user = await callback.bot.get_me()
    guide_url = f"https://t.me/{bot_user.username}"
    
    content = ""
    if feature == "smart_settings":
        content = (
            "🤖 <b>Aqlli sozlamalar</b>\n\n"
            "Postni bir marta sozlang — va Posto har bir tafsilotni eslab qoladi.\n\n"
            "Bot hamma narsani eslab qoladi:\n"
            "✅ Imzo\n"
            "✅ tugmalar\n"
            "✅ suv belgisi\n"
            "✅ avtomatik o'chirish taymeri\n"
            "✅ avtomatik repost\n"
            "✅ birinchi reaksiya\n"
            "✅ barcha nashr sozlamalari\n\n"
            "🔥 Hatto postni bir nechta kanallarga nusxa ko'chirsangiz ham, har biri o'z sozlamalarini saqlab qoladi.\n\n"
            f"👉 {guide_url}"
        )
    elif feature == "rich_editor":
        content = (
            "<b>Boy tahrirchi</b>\n\n"
            "Postlaringizni xohlagan tarzda loyihalash uchun to'liq erkinlik:\n\n"
            "✅ Ko'p xabarli postlar\n"
            "✅ Albomlar — media almashtirish, fayllarni qayta tartiblash va boshqalar 🆕\n"
            "✅ Tugmalarni to'liq boshqarish — tahrirlash, o'chirish yoki qayta tartiblash 🆕\n"
            "✅ Media sozlamalari — matn ustida/ostida, spoiler ostida yashirish, pullik ko'rinish 🆕\n"
            "✅ Oldindan ko'rish pozitsiyasi — matn ustida yoki ostida 🆕\n"
            "✅ Rasmlarni oldindan ko'rinishga aylantirish — va orqaga 🆕"
        )
    elif feature == "first_reaction":
        content = (
            "💬 <b>Post ostidagi birinchi reaksiya</b>\n\n"
            "Bot tayyor reaksiya bilan postlarni nashr qilishi mumkin!\n"
            "❤️ , 👍 yoki boshqa birini tanlang.\n\n"
            "Post tahrirchisida reaksiyani bosing — u nashr qilingandan so'ng avtomatik ravishda paydo bo'ladi.\n\n"
            "Ushbu xususiyatdan kanalingizdagi ishtirokni oshirish uchun foydalaning."
        )
    elif feature == "test_posts":
        content = (
            "🍞 <b>Test uslubidagi postlar</b>\n\n"
            "Ushbu postlar sizga yangi obunachilarni jalb qilishga yordam beradi. Odamlar sirlar va intrigalarni yaxshi ko'radilar — ular keyingi nima bo'lishini ko'rishni xohlashadi.\n\n"
            "Hikoyaning oxirini yoki ichidagi bonusni yashiring — yoki postingizni rasm bilan qiziqarli testga aylantiring. Obunachi darhol to'g'ri yoki noto'g'ri ekanligini, boshqalar qanchalik bir xil variantni tanlaganini ko'radi va to'liq 📊 statistikani ochishi mumkin.\n\n"
            "Obuna yoki ko'tarilishsiz, bularning barchasi yashirin bo'lib qoladi.\n\n"
            "Ba'zilar uchun bu o'yin va hayajon. Boshqalar uchun — qiziqish. Siz uchun — kanal o'sishi!\n\n"
            f"👉 {guide_url}"
        )
    else:
        content = f"<b>{feature.replace('_', ' ').title()}</b> xususiyati haqida ma'lumot tez orada qo'shiladi."

    await callback.message.edit_text(content, reply_markup=get_navigation_keyboard(feature), disable_web_page_preview=True)
    await callback.answer()

@features_router.callback_query(F.data == "start_bot")
async def callback_start_bot(callback: types.CallbackQuery, state: FSMContext):
    from post_handlers.start_handler import cmd_start
    await callback.message.delete()
    await cmd_start(callback, state, callback.bot)
    await callback.answer()
