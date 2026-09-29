import re

# Telegram Premium Custom Emoji IDs
EMOJI_BUNDLE = "5877332341331857066"       # 📁 To'plamlar
EMOJI_ADD_CHANNEL = "5771868281212245617"  # 📢 Yangi kanal qo'shish (add channel)
EMOJI_CHANNEL = "5771695636411847302"      # 📢 Oddiy kanal (channel display)
EMOJI_DELETE = "5771868281212245617"       # 📢 O'chirish tugmasi
EMOJI_SAVE = "5843843420468024653"         # ⭐️ Saqlash tugmasi
EMOJI_SETTINGS = "5877260593903177342"     # ⚙️ Sozlamalar
EMOJI_EDIT = "5879841310902324730"         # ✏️ Tahrirlash tugmasi
EMOJI_CREATE = "6026349903863619779"       # 🪄 Yangi yaratish
EMOJI_STATISTIC = "5931472654660800739"    # 📊 Statistika
EMOJI_WAVE = "6023985511482268644"         # 👋 Xush kelibsiz (start)
EMOJI_WINK = "5458394638505223612"         # 😉 Start xabari
EMOJI_DOWN = "6023566962624306038"         # 👇 Pastga ko'rsatish
EMOJI_SMILE = "5458394638505223612"        # Alias

# HTML custom emoji tags for message texts
HTML_EMOJI_BUNDLE = '<tg-emoji emoji-id="5877332341331857066">📁</tg-emoji>'
HTML_EMOJI_ADD_CHANNEL = '<tg-emoji emoji-id="5771868281212245617">📢</tg-emoji>'
HTML_EMOJI_CHANNEL = '<tg-emoji emoji-id="5771695636411847302">📢</tg-emoji>'
HTML_EMOJI_DELETE = '<tg-emoji emoji-id="5771868281212245617">📢</tg-emoji>'
HTML_EMOJI_SAVE = '<tg-emoji emoji-id="5843843420468024653">⭐️</tg-emoji>'
HTML_EMOJI_SETTINGS = '<tg-emoji emoji-id="5877260593903177342">⚙️</tg-emoji>'
HTML_EMOJI_EDIT = '<tg-emoji emoji-id="5879841310902324730">✏️</tg-emoji>'
HTML_EMOJI_CREATE = '<tg-emoji emoji-id="6026349903863619779">🪄</tg-emoji>'
HTML_EMOJI_STATISTIC = '<tg-emoji emoji-id="5931472654660800739">📊</tg-emoji>'
HTML_EMOJI_WAVE = '<tg-emoji emoji-id="6023985511482268644">👋</tg-emoji>'
HTML_EMOJI_WINK = '<tg-emoji emoji-id="5458394638505223612">😉</tg-emoji>'
HTML_EMOJI_DOWN = '<tg-emoji emoji-id="6023566962624306038">👇</tg-emoji>'
HTML_EMOJI_SMILE = HTML_EMOJI_WINK

def clean_btn_text(text: str) -> str:
    """Tugma matnidan boshidagi standart emojilarni olib tashlaydi (icon_custom_emoji_id berilganda)."""
    if not text:
        return ""
    cleaned = re.sub(r'^[^\w\s\(\)\[\]\{\}\d]+\s*', '', str(text), flags=re.UNICODE)
    return cleaned.strip() if cleaned.strip() else str(text)
