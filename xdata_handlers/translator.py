#--- START OF FILE translator.py ---

import json
from typing import Dict
import os
from pathlib import Path
import logging

#=============================================================================
# TARJIMALARNI YUKLASH VA BOSHQARISH
#=============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
translations: Dict[str, Dict[str, str]] = {}

def load_translations():
    """language_paks papkasidagi barcha .json fayllarni avtomatik o'qiydi va `translations` lug'atiga yuklaydi."""
    locales_dir = os.path.join(BASE_DIR, "language_paks")

    if not os.path.exists(locales_dir):
        logging.error(f"Tarjimalar papkasi topilmadi: {locales_dir}")
        return

    for filename in os.listdir(locales_dir):
        if filename.endswith(".json"):
            lang_code = filename[:-5] # .json kengaytmasini olib tashlaymiz
            file_path = os.path.join(locales_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    translations[lang_code] = json.load(f)
                    logging.info(f"'{lang_code}' tili muvaffaqiyatli yuklandi.")
            except FileNotFoundError:
                logging.warning(f"Tarjima fayli topilmadi: {file_path}")
            except json.JSONDecodeError:
                logging.error(f"JSON faylni o'qishda xatolik: {file_path}")

def get_text(key: str, lang: str = "uzl") -> str:
    """
    Berilgan kalit va til kodi bo'yicha matnni qaytaradi.
    Agar tarjima topilmasa, standart til (uzl) bo'yicha qidiradi.
    Agar u ham topilmasa, kalitning o'zini qaytaradi.
    """
    # Agar so'ralgan til mavjud bo'lmasa, standart tilga o'tamiz
    if lang not in translations:
        lang = "uzl"

    # Avval so'ralgan (yoki standart) tildan matnni qidiramiz
    text = translations.get(lang, {}).get(key)

    # Agar matn topilmasa va joriy til standart tildan farqli bo'lsa, standart tildan qidirib ko'ramiz
    if text is None and lang != "uzl":
        text = translations.get("uzl", {}).get(key)

    # Agar hali ham topilmasa, kalitning o'zini qaytaramiz
    return text if text is not None else f"_{key}_"

load_translations()

#--- END OF FILE translator.py ---
