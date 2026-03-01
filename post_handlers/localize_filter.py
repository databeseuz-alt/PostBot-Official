
import logging
from typing import Union, Dict, Any

from aiogram.filters import Filter
from aiogram.types import Message

from xdata_handlers.translator import translations

logger = logging.getLogger(__name__)

class LocalizedText(Filter):
    """
    Bu filtr matnning kalit so'zi (key) bo'yicha barcha mavjud tillardagi
    tarjimalarni tekshiradi. Agar foydalanuvchi yuborgan matn shu
    tarjimalardan biriga mos kelsa, True qaytaradi.
    """
    def __init__(self, key: str):
        self.key = key

    async def __call__(self, message: Message) -> Union[bool, Dict[str, Any]]:
        if not isinstance(message.text, str):
            return False

        possible_texts = {
            lang_data.get(self.key)
            for lang_data in translations.values()
            if self.key in lang_data
        }

        return message.text in possible_texts

