
import json
from typing import Dict
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
translations: Dict[str, Dict[str, str]] = {}

def load_translations():
    """language_packs papkasidagi barcha .json fayllarni avtomatik o'qiydi va `translations` lug'atiga yuklaydi."""
    locales_dir = os.path.join(BASE_DIR, "language_packs")

    if not os.path.exists(locales_dir):
        return

    loaded_count = 0
    for filename in os.listdir(locales_dir):
        if filename.endswith(".json"):
            lang_code = filename[:-5] # .json kengaytmasini olib tashlaymiz
            file_path = os.path.join(locales_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    import re
                    content = re.sub(r'^\s*//.*$', '', content, flags=re.MULTILINE)
                    translations[lang_code] = json.loads(content)
                    loaded_count += 1
            except FileNotFoundError:
                pass
            except json.JSONDecodeError:
                pass

def get_text(key: str, lang: str = "uzl") -> str:
    """
    Berilgan kalit va til kodi bo'yicha matnni qaytaradi.
    Agar tarjima topilmasa, standart til (uzl) bo'yicha qidiradi.
    Agar u ham topilmasa, kalitning o'zini qaytaradi.
    """
    if lang not in translations:
        lang = "uzl"

    text = translations.get(lang, {}).get(key)

    if text is None and lang != "uzl":
        text = translations.get("uzl", {}).get(key)

    return text if text is not None else f"_{key}_"

def safe_format(text: str, **kwargs) -> str:
    """
    Matnni formatlashda xavfsiz usul. Agar formatlashda xatolik yuz bersa,
    asl matnni qaytaradi.
    """
    try:
        return text.format(**kwargs)
    except (KeyError, ValueError):
        try:
            return text.format(**{k: '' for k in kwargs})
        except:
            return text

def save_translation(lang_code: str, key: str, new_text: str) -> bool:
    """Tarjimani o'zgartiradi va faylga saqlaydi (JSON)."""
    locales_dir = os.path.join(BASE_DIR, "language_packs")
    file_path = os.path.join(locales_dir, f"{lang_code}.json")

    if lang_code not in translations:
        translations[lang_code] = {}
    translations[lang_code][key] = new_text

    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}

        data[key] = new_text

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return True
    except Exception:
        return False

load_translations()
