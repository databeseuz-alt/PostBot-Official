from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from xdata_handlers.translator import get_text

features_router = Router()

IMPLEMENTED_FEATURES = [
    "smart_settings", "rich_editor", "first_reaction", "test_posts", 
    "auto_sig", "watermark", "composite", "publish_settings", "interesting",
    "templates", "group_publish", "schedule", "turbo", "multi_post"
]

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
    elif feature == "interesting":
        content = (
            "<b>Qiziqarli postlar</b>\n\n"
            "Posto sizga postlaringizni ajralib turishi uchun zamonaviy Telegram xususiyatlaridan foydalanish imkonini beradi:\n\n"
            "✅ Premium emojilar\n"
            "✅ URL tugmalar (uzun havolalarni almashtirish uchun)\n"
            "✅ Reaksiya tugmalar\n"
            "✅ Yashirin davom\n"
            "✅ Test uslubidagi postlar (javob statistikasi bilan) 🆕\n"
            "✅ Matn ustida yoki ostida havola oldindan ko'rish\n"
            "✅ Maxsus izoh tugmasi\n"
            "✅ Kanallar uchun avtomatik imzo\n"
            "✅ Rasmlar, videolar, GIFlarda suv belgilari 🆕\n"
            "✅ Slayd-shoular 🆕\n"
            "✅ Pullik media 🆕"
        )
    elif feature == "publish_settings":
        content = (
            "<b>Nashr sozlamalari</b>\n\n"
            "✅ Avtomatik qayta joylash\n"
            "✅ Avto o'chirish\n"
            "✅ Taymer bo'yicha mahkamlash yoki yechish 🆕\n"
            "✅ Mahkamlangan postda ko'k tugma\n"
            "✅ Jim rejim\n"
            "✅ Kontentni nusxalashdan himoya qilish\n"
            "✅ Javob postlar\n"
            "✅ Izohlarni o'chirish 🆕\n"
            "✅ Reklama uchun \"Yuqoridagi vaqt\" 🆕"
        )
    elif feature == "watermark":
        content = (
            "💧 <b>Suv belgilari</b>\n\n"
            "Postlar o'g'irlanadi — lekin siznikilar emas. Suv belgisi bilan ismingiz har bir rasm, video yoki GIFda qoladi.\n\n"
            "✅ Matn yoki logotip suv belgisi\n"
            "✅ Opaqlik, o'lcham, joylashuv va boshqalarni sozlash\n"
            "✅ Turli shriftlar\n"
            "✅ Rang tanlash\n"
            "✅ Bir marta bosish shablonlari\n"
            "✅ Videoda animatsiyali harakat\n"
            "✅ Postlarga avtomatik qo'shilish"
        )
    elif feature == "composite":
        content = (
            "<b>Kompozit postlar</b>\n\n"
            "Botda siz postni butun xabarlar zanjiridan — ketma-ket 10 tagacha xabar — yaratishingiz mumkin.\n"
            "Shu tariqa, Telegram cheklovlarini chetlab o'tasiz va kontentingizni xohlagan uslubda formatlaysiz.\n\n"
            "🔥 <b>Uzun matn qismlarga bo'lingan</b> — matn devorini o'qishni osonlashtirish uchun bir nechta xabarga bo'ling.\n\n"
            "📊 <b>Asosiy post + qo'shimcha</b> — asosiy postingizni nashr qiling va darhol so'rovnoma yoki izohlar bo'limini qo'shing.\n\n"
            "🖼 <b>Albom + tugmalar</b> — Telegram albomlar ostida tugmalar qo'yishga ruxsat bermaydi.\n"
            "Yechim: avval albom, keyin tugmalar bilan alohida xabar. Birgalikda ular bitta nashr sifatida ishlaydi."
        )
    elif feature == "auto_sig":
        content = (
            "<b>Kanal imzosi</b>\n\n"
            "Postlaringizga imzolar qo'shing, shunda ular qayta joylashtirilganda muallifligingiz ko'rinib turadi.\n"
            "Posto bilan bu o'son — bot sizning imzongizni avtomatik ravishda qo'shadi.\n\n"
            "🆕 Siz bir nechta imzo variantlarini yaratishingiz va har bir post turi uchun mosini tanlashingiz mumkin."
        )
    elif feature == "turbo":
        content = (
            "🚀 <b>Turbo rejim — postlarni nol bosish bilan yarating</b>\n\n"
            "Buni boshqa joyda topa olmaysiz. Botga bir nechta draftlarni tashlang — va tamom.\n"
            "Bot ularni shabloningizdan foydalangan holda to'liq postlarga aylantiradi: tugmalar, imzo, suv belgisi qo'shadi, matnni qayta yozadi.\n\n"
            "Uchta rejim mavjud:\n"
            "1️⃣ Tezkor nashr qilish\n"
            "2️⃣ Jadval bo'yicha\n"
            "3️⃣ Aralash jadval\n\n"
            "Birinchi partiyadan so'ng, ikkinchi yoki uchinchi sini yuboring. Hech narsa bosishga hojat yo'q.\n\n"
            f"👉 {guide_url}"
        )
    elif feature == "multi_post":
        content = (
            "🔥 <b>Ko'p-post qilish</b>\n\n"
            "Ko'p-post qilish degani, bitta post bir vaqtning o'zida bir nechta kanallarda nashr qilinadi.\n\n"
            "🔥 Posto mo'jizasi: har bir kanal bir xil postni oladi, lekin o'z uslubida — noyob tugmalar, suv belgisi va havolalar bilan.\n\n"
            "Shuningdek, AI matnni qayta ishlash mavjud.\n"
            "Masalan, agar siz 10 ta tilda kanallar tarmog'ini boshqarsangiz, faqat bitta post yuklaysiz — va u avtomatik ravishda har bir kanal uchun 🌐 tarjima qilinadi.\n\n"
            "Yoki boshqa holat: siz oshpazlik kanallari tarmog'ini boshqarasiz. Botga bitta retsept yuborasiz va u barcha kanallarda nashr qilinadi — turli jadval va matn variantlari bilan.\n\n"
            "<b>Qo'llanmalar:</b>\n"
            "🗒 Imzo va tugmalarni o'zgartirish\n"
            "🗒 Qayta yozish yoki tarjima qilish\n"
            "🗒 Turli nashr vaqtlari"
        )
    elif feature == "schedule":
        content = (
            "<b>Jadval</b>\n\n"
            "Jadvalingizni bir marta sozlang — va bot avtomatik ravishda vaqt bo'shliqlarini to'ldiradi.\n\n"
            "Siz istalgan jadval uslubini tanlashingiz mumkin:\n"
            "✅ Har kuni yoki haftaning kunlariga bo'lingan jadval\n"
            "✅ Oddiy va homiylik postlari uchun alohida vaqtlar\n\n"
            "Jadval sizni rutindan ozod qiladi: kanal faqat siz oflayn bo'lsangiz ham faol qoladi.\n\n"
            "<b>Qo'llanmalar:</b>\n"
            "🗒 Post jadvali\n"
            "🗒 Kategoriya bo'yicha nashr qilish"
        )
    elif feature == "group_publish":
        content = (
            "<b>Guruhli nashr</b>\n\n"
            "Eski kanalingiz bormi? Postlarni yangi kanalingizga osonlik bilan ko'chiring.\n"
            "Ularni botga yo'naltiring — va bir necha kun yoki hafta uchun kontent rejangizni darhol to'ldirasiz.\n\n"
            "Nimalarni qilishingiz mumkin:\n"
            "✅ butun guruhni birgalikda tahrirlash\n"
            "✅ aralash tartibda nashr qilish\n"
            "✅ jadval bo'yicha taqsimlash\n\n"
            "Soatlab rutindan qutuling — hammasi bir zumda tayyor.\n\n"
            "👉 Guruhli nashr\n"
            "👉 Shablonlar"
        )
    elif feature == "templates":
        content = (
            "<b>Post shablonlari</b>\n\n"
            "🗒 Shablon sizning sevimli sozlamalaringiz va uslubingizni saqlaydi — va har safar post yaratganingizda ulardan foydalaniladi.\n\n"
            "Siz unda hamma narsani belgilashingiz mumkin:\n"
            "✅ tugmalar\n"
            "✅ kanal imzosi\n"
            "✅ suv belgisi\n"
            "✅ jadval\n"
            "✅ matn tarjimasi yoki qayta yozish\n"
            "✅ rasm yaratish\n"
            "✅ so'z almashtirish qoidalari\n"
            "✅ nashr sozlamalari\n\n"
            "Va eng muhimi — shablon o'zining nashr vaqti bilan kategoriya sifatida ishlashi mumkin.\n"
            "Ertalabki postlar, haftalik to'plamlar yoki yarim tunda uzun maqolalar — har birini alohida boshqaring.\n\n"
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
