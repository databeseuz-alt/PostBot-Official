import json
import os

TRANSLATIONS = {
    "uzl": {
        "add_channel_btn": "📢 Yangi kanal",
        "add_new_channel_btn": "📢 Yangi kanal",
        "add_channel_post_btn": "📢 Yangi kanal",
        "existing_bundles_btn": "📁 To'plamlar",
        "home_screen_btn": "🏠 Bosh ekran",
    },
    "uzk": {
        "add_channel_btn": "📢 Янги канал",
        "add_new_channel_btn": "📢 Янги канал",
        "add_channel_post_btn": "📢 Янги канал",
        "existing_bundles_btn": "📁 Тўпламлар",
        "home_screen_btn": "🏠 Бош экран",
    },
    "ru": {
        "add_channel_btn": "📢 Новый канал",
        "add_new_channel_btn": "📢 Новый канал",
        "add_channel_post_btn": "📢 Новый канал",
        "existing_bundles_btn": "📁 Наборы",
        "home_screen_btn": "🏠 Главный экран",
    },
    "en": {
        "add_channel_btn": "📢 New Channel",
        "add_new_channel_btn": "📢 New Channel",
        "add_channel_post_btn": "📢 New Channel",
        "existing_bundles_btn": "📁 Bundles",
        "home_screen_btn": "🏠 Home screen",
    },
    "tr": {
        "add_channel_btn": "📢 Yeni Kanal",
        "add_new_channel_btn": "📢 Yeni Kanal",
        "add_channel_post_btn": "📢 Yeni Kanal",
        "existing_bundles_btn": "📁 Paketler",
        "home_screen_btn": "🏠 Ana ekran",
    },
    "tk": {
        "add_channel_btn": "📢 Täze kanal",
        "add_new_channel_btn": "📢 Täze kanal",
        "add_channel_post_btn": "📢 Täze kanal",
        "existing_bundles_btn": "📁 Bukjalar",
        "home_screen_btn": "🏠 Baş sahypa",
    },
    "tj": {
        "add_channel_btn": "📢 Канали нав",
        "add_new_channel_btn": "📢 Канали нав",
        "add_channel_post_btn": "📢 Канали нав",
        "existing_bundles_btn": "📁 Маҷмӯаҳо",
        "home_screen_btn": "🏠 Экрани асосӣ",
    },
    "kz": {
        "add_channel_btn": "📢 Жаңа арна",
        "add_new_channel_btn": "📢 Жаңа арна",
        "add_channel_post_btn": "📢 Жаңа арна",
        "existing_bundles_btn": "📁 Топтамалар",
        "home_screen_btn": "🏠 Басты экран",
    },
    "kg": {
        "add_channel_btn": "📢 Жаңы канал",
        "add_new_channel_btn": "📢 Жаңы канал",
        "add_channel_post_btn": "📢 Жаңы канал",
        "existing_bundles_btn": "📁 Топтомдор",
        "home_screen_btn": "🏠 Башкы экран",
    },
    "az": {
        "add_channel_btn": "📢 Yeni Kanal",
        "add_new_channel_btn": "📢 Yeni Kanal",
        "add_channel_post_btn": "📢 Yeni Kanal",
        "existing_bundles_btn": "📁 Dəstlər",
        "home_screen_btn": "🏠 Əsas ekran",
    },
    "de": {
        "add_channel_btn": "📢 Neuer Kanal",
        "add_new_channel_btn": "📢 Neuer Kanal",
        "add_channel_post_btn": "📢 Neuer Kanal",
        "existing_bundles_btn": "📁 Bündel",
        "home_screen_btn": "🏠 Startbildschirm",
    },
    "fr": {
        "add_channel_btn": "📢 Nouvelle Chaîne",
        "add_new_channel_btn": "📢 Nouvelle Chaîne",
        "add_channel_post_btn": "📢 Nouvelle Chaîne",
        "existing_bundles_btn": "📁 Lots",
        "home_screen_btn": "🏠 Écran d'accueil",
    },
    "it": {
        "add_channel_btn": "📢 Nuovo Canale",
        "add_new_channel_btn": "📢 Nuovo Canale",
        "add_channel_post_btn": "📢 Nuovo Canale",
        "existing_bundles_btn": "📁 Pacchetti",
        "home_screen_btn": "🏠 Schermata iniziale",
    },
    "es": {
        "add_channel_btn": "📢 Nuevo Canal",
        "add_new_channel_btn": "📢 Nuevo Canal",
        "add_channel_post_btn": "📢 Nuevo Canal",
        "existing_bundles_btn": "📁 Paquetes",
        "home_screen_btn": "🏠 Pantalla principal",
    },
    "ar": {
        "add_channel_btn": "📢 قناة جديدة",
        "add_new_channel_btn": "📢 قناة جديدة",
        "add_channel_post_btn": "📢 قناة جديدة",
        "existing_bundles_btn": "📁 حزم",
        "home_screen_btn": "🏠 الشاشة الرئيسية",
    }
}

for lang, updates in TRANSLATIONS.items():
    filepath = os.path.join("language_packs", f"{lang}.json")
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        continue
    with open(filepath, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    for k, v in updates.items():
        data[k] = v
    with open(filepath, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=4)
        fp.write("\n")
    print(f"Updated {filepath}")
