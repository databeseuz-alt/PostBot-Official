import logging
import os
import json
import asyncio
from pathlib import Path
from typing import Dict

from aiogram.types import Message
from aiogram import Bot
import html

# Logger sozlamalari
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
translations: Dict[str, Dict[str, str]] = {}

def escape_html(text: str) -> str:
    """HTML maxsus belgilarini escape qiladi."""
    if not text:
        return ""
    return html.escape(str(text))

async def safe_answer(message: Message, text: str, bot: Bot = None, parse_mode: str = None, **kwargs):
    """
    Xavfsiz xabar yuborish - HTML parsing xatolarini boshqaradi.
    """
    from aiogram.errors import TelegramBadRequest
    try:
        await message.answer(text, parse_mode=parse_mode, **kwargs)
    except TelegramBadRequest as e:
        # Agar HTML parsing xatolik bo'lsa, parse_mode=siz qayta urinib ko'rish
        if "can't parse entities" in str(e):
            logger.warning(f"HTML parsing xatolik, parse_mode=None bilan qayta yuborilmoqda")
            try:
                await message.answer(text, parse_mode=None, **kwargs)
            except Exception as e2:
                logger.error(f"Xatolik: {e2}")
        else:
            raise

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

def get_all_translations(key: str) -> set:
    """Barcha tillardagi ma'lum bir kalitning tarjimalarini set sifatida qaytaradi."""
    result = set()
    for lang_code in translations:
        text = translations.get(lang_code, {}).get(key)
        if text:
            import html
            result.add(text)
            
    # Asosiy til "uzl" uchun har doim qo'shish
    fallback = translations.get("uzl", {}).get(key)
    if fallback:
        result.add(fallback)
    
    # Kiritilgan belgi uz, ru, en da ham bo'lish ehtimoliga qarshi
    for manual_lang in ['uzl', 'ru', 'en']:
        man_text = get_text(key, manual_lang)
        if man_text:
            result.add(man_text)
            
    return result

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

def get_text_formatted(key: str, lang: str = "uzl", **kwargs) -> str:
    """
    Berilgan kalit bo'yicha tarjima matnini oladi va uni xavfsiz tarzda formatlaydi.
    
    Args:
        key: Tarjima kaliti
        lang: Til kodi (default: "uzl")
        **kwargs: Formatlash uchun qiymatlar
    
    Returns:
        Formatlangan tarjima matni
    """
    text = get_text(key, lang)
    if kwargs:
        return safe_format(text, **kwargs)
    return text

def log_error(
    level: str = "error",
    message: str = "",
    user_id: int = None,
    error_type: str = "GeneralError",
    exc_info: Exception = None
):
    """
    Xatolik yoki ogohlantirishni log qiladi.
    
    Args:
        level: "error", "warning", "info", "debug"
        message: Log xabari
        user_id: Foydalanuvchi ID (ixtiyoriy)
        error_type: Xato turi (ixtiyoriy)
        exc_info: Exception obyekti (ixtiyoriy)
    """
    import traceback
    
    log_message = message
    if user_id:
        log_message = f"[User: {user_id}] {message}"
    
    if exc_info:
        log_message += f" | Exception: {str(exc_info)}"
    
    if level == "error":
        logger.error(log_message)
    elif level == "warning":
        logger.warning(log_message)
    elif level == "info":
        logger.info(log_message)
    else:
        logger.debug(log_message)
    
    # Agar error bo'lsa, bazaga ham yozish
    if level == "error" and exc_info:
        try:
            from xdata_handlers.database import log_user_error
            # Xato matnini tayyorlash
            error_msg = f"{error_type}: {str(exc_info)}"
            asyncio.create_task(log_user_error(
                user_id=user_id,
                error_text=error_msg
            ))
        except:
            pass

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
