import json
import glob
import os

new_translations = {
    "uzl": {
        "add_to_bundle_btn": "📁 To'plamga qo'shish",
        "choose_bundle_to_add": "📁 <b>Qaysi to'plamga qo'shilsin?</b>\n\nKanalni qo'shmoqchi bo'lgan to'plamni tanlang:",
        "channel_added_to_bundle_success": "✅ <b>{channel_name}</b> kanali <b>«{bundle_name}»</b> to'plamiga muvaffaqiyatli qo'shildi!",
        "add_channels_to_bundle_btn": "➕ Kanal qo'shish",
        "bundle_channels_updated_success": "✅ To'plam kanallari muvaffaqiyatli yangilandi!",
        "bundle_no_channels_yet": "<i>Ushbu to'plamda hali kanallar yo'q.</i>",
        "bundle_channel_already_in_all": "ℹ️ Ushbu kanal barcha mavjud to'plamlarga qo'shilgan!",
        "channel_not_in_any_bundle": "⚠️ Ushbu kanal birorta ham to'plamga kiritilmagan."
    },
    "uzk": {
        "add_to_bundle_btn": "📁 Тўпламга қўшиш",
        "choose_bundle_to_add": "📁 <b>Қайси тўпламга қўшилсин?</b>\n\nКанални қўшмоқчи бўлган тўпламни танланг:",
        "channel_added_to_bundle_success": "✅ <b>{channel_name}</b> канали <b>«{bundle_name}»</b> тўпламига муваффақиятли қўшилди!",
        "add_channels_to_bundle_btn": "➕ Канал қўшиш",
        "bundle_channels_updated_success": "✅ Тўплам каналлари муваффақиятли янгиланди!",
        "bundle_no_channels_yet": "<i>Ушбу тўпламда ҳали каналлар йўқ.</i>",
        "bundle_channel_already_in_all": "ℹ️ Ушбу канал барча мавжуд тўпламларга қўшилган!",
        "channel_not_in_any_bundle": "⚠️ Ушбу канал бирорта ҳам тўпламга киритилмаган."
    },
    "ru": {
        "add_to_bundle_btn": "📁 Добавить в набор",
        "choose_bundle_to_add": "📁 <b>В какой набор добавить?</b>\n\nВыберите набор, в который хотите добавить канал:",
        "channel_added_to_bundle_success": "✅ Канал <b>{channel_name}</b> успешно добавлен в набор <b>«{bundle_name}»</b>!",
        "add_channels_to_bundle_btn": "➕ Добавить каналы",
        "bundle_channels_updated_success": "✅ Каналы набора успешно обновлены!",
        "bundle_no_channels_yet": "<i>В этом наборе пока нет каналов.</i>",
        "bundle_channel_already_in_all": "ℹ️ Этот канал уже добавлен во все доступные наборы!",
        "channel_not_in_any_bundle": "⚠️ Этот канал пока не входит ни в один набор."
    },
    "en": {
        "add_to_bundle_btn": "📁 Add to collection",
        "choose_bundle_to_add": "📁 <b>Which collection to add to?</b>\n\nSelect the collection you want to add the channel to:",
        "channel_added_to_bundle_success": "✅ Channel <b>{channel_name}</b> successfully added to collection <b>«{bundle_name}»</b>!",
        "add_channels_to_bundle_btn": "➕ Add channels",
        "bundle_channels_updated_success": "✅ Collection channels successfully updated!",
        "bundle_no_channels_yet": "<i>There are no channels in this collection yet.</i>",
        "bundle_channel_already_in_all": "ℹ️ This channel is already in all available collections!",
        "channel_not_in_any_bundle": "⚠️ This channel is not included in any collection yet."
    },
    "tr": {
        "add_to_bundle_btn": "📁 Koleksiyona ekle",
        "choose_bundle_to_add": "📁 <b>Hangi koleksiyona eklensin?</b>\n\nKanalı eklemek istediğiniz koleksiyonu seçin:",
        "channel_added_to_bundle_success": "✅ <b>{channel_name}</b> kanalı <b>«{bundle_name}»</b> koleksiyonuna başarıyla eklendi!",
        "add_channels_to_bundle_btn": "➕ Kanal ekle",
        "bundle_channels_updated_success": "✅ Koleksiyon kanalları başarıyla güncellendi!",
        "bundle_no_channels_yet": "<i>Bu koleksiyonda henüz kanal yok.</i>",
        "bundle_channel_already_in_all": "ℹ️ Bu kanal zaten tüm mevcut koleksiyonlara eklenmiş!",
        "channel_not_in_any_bundle": "⚠️ Bu kanal henüz hiçbir koleksiyona dahil değil."
    },
    "kz": {
        "add_to_bundle_btn": "📁 Топтамаға қосу",
        "choose_bundle_to_add": "📁 <b>Қай топтамаға қосылсын?</b>\n\nАрнаны қосқыңыз келетін топтаманы таңдаңыз:",
        "channel_added_to_bundle_success": "✅ <b>{channel_name}</b> арнасы <b>«{bundle_name}»</b> топтамасына сәтті қосылды!",
        "add_channels_to_bundle_btn": "➕ Арна қосу",
        "bundle_channels_updated_success": "✅ Топтама арналары сәтті жаңартылды!",
        "bundle_no_channels_yet": "<i>Бұл топтамада әзірге арналар жоқ.</i>",
        "bundle_channel_already_in_all": "ℹ️ Бұл арна барлық қолжетімді топтамаларға қосылған!",
        "channel_not_in_any_bundle": "⚠️ Бұл арна әзірге ешбір топтамаға қосылмаған."
    },
    "kg": {
        "add_to_bundle_btn": "📁 Топтомго кошуу",
        "choose_bundle_to_add": "📁 <b>Кайсы топтомго кошулсун?</b>\n\nКаналды кошкуңуз келген топтомду тандаңыз:",
        "channel_added_to_bundle_success": "✅ <b>{channel_name}</b> каналы <b>«{bundle_name}»</b> топтомуна ийгиликтүү кошулду!",
        "add_channels_to_bundle_btn": "➕ Канал кошуу",
        "bundle_channels_updated_success": "✅ Топтом каналдары ийгиликтүү жаңыртылды!",
        "bundle_no_channels_yet": "<i>Бул топтомдо азырынча каналдар жок.</i>",
        "bundle_channel_already_in_all": "ℹ️ Бул канал бардык жеткиликтүү топтомдорго кошулган!",
        "channel_not_in_any_bundle": "⚠️ Бул канал азырынча эч бир топтомго киргизилген эмес."
    },
    "tj": {
        "add_to_bundle_btn": "📁 Ба коллексия илова кардан",
        "choose_bundle_to_add": "📁 <b>Ба кадом коллексия илова шавад?</b>\n\nКоллексияеро интихоб кунед, ки мехоҳед каналро илова кунед:",
        "channel_added_to_bundle_success": "✅ Канали <b>{channel_name}</b> бо муваффақият ба коллексияи <b>«{bundle_name}»</b> илова шуд!",
        "add_channels_to_bundle_btn": "➕ Илова кардани канал",
        "bundle_channels_updated_success": "✅ Каналҳои коллексия бо муваффақият нав карда шуданд!",
        "bundle_no_channels_yet": "<i>Дар ин коллексия ҳоло каналҳо нестанд.</i>",
        "bundle_channel_already_in_all": "ℹ️ Ин канал аллакай ба ҳамаи коллексияҳо илова шудааст!",
        "channel_not_in_any_bundle": "⚠️ Ин канал ҳоло ба ягон коллексия дохил нашудааст."
    },
    "tk": {
        "add_to_bundle_btn": "📁 Ýygynda goşmak",
        "choose_bundle_to_add": "📁 <b>Haýsy ýygynda goşulsyn?</b>\n\nKanal goşmak isleýän ýygyndyňyzy saýlaň:",
        "channel_added_to_bundle_success": "✅ <b>{channel_name}</b> kanaly <b>«{bundle_name}»</b> ýygyndysyna üstünlikli goşuldy!",
        "add_channels_to_bundle_btn": "➕ Kanal goşmak",
        "bundle_channels_updated_success": "✅ Ýygyndy kanallary üstünlikli täzelendi!",
        "bundle_no_channels_yet": "<i>Bu ýygyndyda entek kanal ýok.</i>",
        "bundle_channel_already_in_all": "ℹ️ Bu kanal eýýäm ähli elýeterli ýygyndylara goşuldy!",
        "channel_not_in_any_bundle": "⚠️ Bu kanal entek hiç bir ýygynda goşulmadyk."
    },
    "az": {
        "add_to_bundle_btn": "📁 Topluya əlavə et",
        "choose_bundle_to_add": "📁 <b>Hansı topluya əlavə edilsin?</b>\n\nKanalı əlavə etmək istədiyiniz toplunu seçin:",
        "channel_added_to_bundle_success": "✅ <b>{channel_name}</b> kanalı <b>«{bundle_name}»</b> toplusuna uğurla əlavə edildi!",
        "add_channels_to_bundle_btn": "➕ Kanal əlavə et",
        "bundle_channels_updated_success": "✅ Toplu kanalları uğurla yeniləndi!",
        "bundle_no_channels_yet": "<i>Bu topluda hələ kanal yoxdur.</i>",
        "bundle_channel_already_in_all": "ℹ️ Bu kanal artıq bütün mövcud toplulara əlavə edilib!",
        "channel_not_in_any_bundle": "⚠️ Bu kanal hələ heç bir topluya daxil edilməyib."
    },
    "de": {
        "add_to_bundle_btn": "📁 Zur Sammlung hinzufügen",
        "choose_bundle_to_add": "📁 <b>Zu welcher Sammlung hinzufügen?</b>\n\nWählen Sie die Sammlung aus:",
        "channel_added_to_bundle_success": "✅ Kanal <b>{channel_name}</b> wurde erfolgreich zur Sammlung <b>«{bundle_name}»</b> hinzugefügt!",
        "add_channels_to_bundle_btn": "➕ Kanäle hinzufügen",
        "bundle_channels_updated_success": "✅ Sammlungskanäle erfolgreich aktualisiert!",
        "bundle_no_channels_yet": "<i>In dieser Sammlung gibt es noch keine Kanäle.</i>",
        "bundle_channel_already_in_all": "ℹ️ Dieser Kanal ist bereits in allen Sammlungen vorhanden!",
        "channel_not_in_any_bundle": "⚠️ Dieser Kanal gehört noch zu keiner Sammlung."
    },
    "es": {
        "add_to_bundle_btn": "📁 Añadir a colección",
        "choose_bundle_to_add": "📁 <b>¿A qué colección añadir?</b>\n\nSeleccione la colección:",
        "channel_added_to_bundle_success": "✅ ¡Canal <b>{channel_name}</b> añadido con éxito a la colección <b>«{bundle_name}»</b>!",
        "add_channels_to_bundle_btn": "➕ Añadir canales",
        "bundle_channels_updated_success": "✅ ¡Canales de la colección actualizados con éxito!",
        "bundle_no_channels_yet": "<i>Aún no hay canales en esta colección.</i>",
        "bundle_channel_already_in_all": "ℹ️ ¡Este canal ya está en todas las colecciones disponibles!",
        "channel_not_in_any_bundle": "⚠️ Este canal aún no pertenece a ninguna colección."
    },
    "fr": {
        "add_to_bundle_btn": "📁 Ajouter à la collection",
        "choose_bundle_to_add": "📁 <b>À quelle collection ajouter ?</b>\n\nSélectionnez la collection :",
        "channel_added_to_bundle_success": "✅ Chaîne <b>{channel_name}</b> ajoutée avec succès à la collection <b>«{bundle_name}»</b> !",
        "add_channels_to_bundle_btn": "➕ Ajouter des chaînes",
        "bundle_channels_updated_success": "✅ Chaînes de la collection mises à jour avec succès !",
        "bundle_no_channels_yet": "<i>Il n'y a pas encore de chaînes dans cette collection.</i>",
        "bundle_channel_already_in_all": "ℹ️ Cette chaîne est déjà présente dans toutes les collections disponibles !",
        "channel_not_in_any_bundle": "⚠️ Cette chaîne ne fait encore partie d'aucune collection."
    },
    "it": {
        "add_to_bundle_btn": "📁 Aggiungi alla raccolta",
        "choose_bundle_to_add": "📁 <b>A quale raccolta aggiungere?</b>\n\nSeleziona la raccolta:",
        "channel_added_to_bundle_success": "✅ Canale <b>{channel_name}</b> aggiunto con successo alla raccolta <b>«{bundle_name}»</b>!",
        "add_channels_to_bundle_btn": "➕ Aggiungi canali",
        "bundle_channels_updated_success": "✅ Canali della raccolta aggiornati con successo!",
        "bundle_no_channels_yet": "<i>Non ci sono ancora canali in questa raccolta.</i>",
        "bundle_channel_already_in_all": "ℹ️ Questo canale è già presente in tutte le raccolte disponibili!",
        "channel_not_in_any_bundle": "⚠️ Questo canale non è ancora incluso in nessuna raccolta."
    },
    "ar": {
        "add_to_bundle_btn": "📁 إضافة إلى المجموعة",
        "choose_bundle_to_add": "📁 <b>إلى أي مجموعة تريد الإضافة؟</b>\n\nاختر المجموعة التي ترغب في إضافة القناة إليها:",
        "channel_added_to_bundle_success": "✅ تم بنجاح إضافة القناة <b>{channel_name}</b> إلى المجموعة <b>«{bundle_name}»</b>!",
        "add_channels_to_bundle_btn": "➕ إضافة قنوات",
        "bundle_channels_updated_success": "✅ تم تحديث قنوات المجموعة بنجاح!",
        "bundle_no_channels_yet": "<i>لا توجد قنوات في هذه المجموعة حتى الآن.</i>",
        "bundle_channel_already_in_all": "ℹ️ هذه القناة موجودة بالفعل في جميع المجموعات المتاحة!",
        "channel_not_in_any_bundle": "⚠️ هذه القناة غير مضافة إلى أي مجموعة حتى الآن."
    }
}

for lang_code, keys in new_translations.items():
    path = f"language_packs/{lang_code}.json"
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data.update(keys)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Updated {path}")

print("All language packs updated successfully.")
