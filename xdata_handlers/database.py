#--- START OF FILE database.py ---
import sqlite3
import json
import secrets
import string
import os
import logging
from datetime import datetime, timedelta, timezone
import asyncio
from typing import Literal, Optional
from collections import Counter

# Adminlarni filtrlash uchun config import qilinadi
from xdata_handlers import config

#==================================================
# --- M A ' L U M O T L A R   B A Z A S I   S O Z L A M A L A R I   V A   I SH G A   T U SH I R I SH ---
#==================================================
try:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, "xdatabase.db")
except NameError:
    DB_PATH = "xdatabase.db"

db_lock = asyncio.Lock()

# Yagona vaqt mintaqasi
TASHKENT_TZ = timezone(timedelta(hours=5))

def get_now() -> datetime:
    """Hozirgi vaqtni har doim Toshkent vaqti bilan qaytaradi."""
    return datetime.now(TASHKENT_TZ)

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''CREATE TABLE IF NOT EXISTS posts (
                            id INTEGER PRIMARY KEY,
                            post_code TEXT NOT NULL UNIQUE,
                            user_id INTEGER NOT NULL,
                            full_post_data TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            post_name TEXT
                         )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            user_id INTEGER PRIMARY KEY,
                            full_name TEXT,
                            username TEXT,
                            language_code TEXT,
                            is_blocked INTEGER DEFAULT 0,
                            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            show_guide_button INTEGER DEFAULT 1
                         )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS daily_stats (
                            stat_date TEXT PRIMARY KEY,
                            new_users INTEGER DEFAULT 0,
                            new_posts INTEGER DEFAULT 0
                         )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
                            key TEXT PRIMARY KEY,
                            value TEXT NOT NULL
                         )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS required_channels (
                            channel_id INTEGER PRIMARY KEY,
                            title TEXT NOT NULL,
                            username TEXT
                         )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS guide_content (
                            lang_code TEXT PRIMARY KEY,
                            content_type TEXT NOT NULL,
                            text_or_caption TEXT,
                            file_id TEXT
                         )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS feedbacks (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            message_id INTEGER NOT NULL,
                            chat_id INTEGER NOT NULL,
                            has_reply INTEGER DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                         )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS user_errors (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER,
                            error_text TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                         )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_channels (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            channel_id INTEGER NOT NULL,
                            channel_name TEXT NOT NULL,
                            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(user_id, channel_id)
                         )''')

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN last_activity_date TIMESTAMP;")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN ad_agreement_accepted INTEGER DEFAULT 0;")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN assigned_admin_id INTEGER DEFAULT NULL;")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN feedback_agreement_accepted INTEGER DEFAULT 0;")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN show_guide_button INTEGER DEFAULT 1;")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE posts ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE posts ADD COLUMN post_name TEXT;")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN default_parse_mode TEXT DEFAULT NULL;")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN default_disable_url_preview INTEGER DEFAULT 0;")
        except sqlite3.OperationalError:
            pass


        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('how_to_use_enabled', '1'))
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('last_ad_admin_index', '-1'))

        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"DBni ishga tushirishda xatolik: {e}")

#==================================================
# --- F E E D B A C K   B O' L I M I   U C H U N   Y A N G I   F U N K S I Y A L A R ---
#==================================================

async def accept_feedback_agreement(user_id: int):
    if user_id in config.ADMIN_IDS: return
    async with db_lock:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET feedback_agreement_accepted = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

#==================================================
# --- R E K L A M A   B O' L I M I   U C H U N   Y A N G I   F U N K S I Y A L A R ---
#==================================================

async def accept_ad_agreement(user_id: int):
    if user_id in config.ADMIN_IDS: return
    async with db_lock:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET ad_agreement_accepted = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

async def assign_admin_to_user(user_id: int, admin_ids: list) -> int | None:
    if not admin_ids:
        return None
    async with db_lock:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()

        cursor.execute("SELECT value FROM settings WHERE key = 'last_ad_admin_index'")
        last_index_row = cursor.fetchone()
        last_index = int(last_index_row[0]) if last_index_row else -1

        new_index = (last_index + 1) % len(admin_ids)
        assigned_admin = admin_ids[new_index]

        cursor.execute("UPDATE users SET assigned_admin_id = ? WHERE user_id = ?", (assigned_admin, user_id))
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'last_ad_admin_index'", (str(new_index),))

        conn.commit()
        conn.close()
        return assigned_admin

#==================================================
# --- F O Y D A L A N U V C H I   K A N A L L A R I   B I L A N   I SH L A SH ---
#==================================================

async def add_user_channel(user_id: int, channel_id: int, channel_name: str) -> bool:
    async with db_lock:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO user_channels (user_id, channel_id, channel_name, added_at) VALUES (?, ?, ?, ?)",
                (user_id, channel_id, channel_name, get_now())
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Foydalanuvchi kanalini qo'shishda xatolik: {e}")
            return False
        finally:
            if conn:
                conn.close()

async def get_user_channels(user_id: int) -> list[dict]:
    channels = []
    async with db_lock:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT channel_id, channel_name FROM user_channels WHERE user_id = ? ORDER BY added_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            for row in rows:
                channels.append({'channel_id': row[0], 'channel_name': row[1]})
            return channels
        except Exception as e:
            logging.error(f"Foydalanuvchi kanallarini olishda xatolik: {e}")
            return []
        finally:
            if conn:
                conn.close()

async def remove_user_channel(user_id: int, channel_id: int) -> bool:
    async with db_lock:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_channels WHERE user_id = ? AND channel_id = ?",
                (user_id, channel_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Foydalanuvchi kanalini o'chirishda xatolik: {e}")
            return False
        finally:
            if conn:
                conn.close()

#==================================================
# --- M A ' L U M O T L A R N I   Y O Z I SH   O P E R A T S I Y A L A R I ---
#==================================================

async def record_user_activity(user_id: int, username: str | None):
    async with db_lock:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_activity_date = ?, username = ? WHERE user_id = ?",
            (get_now(), username, user_id)
        )
        conn.commit()
        conn.close()

async def add_or_update_user(user_id: int, full_name: str, username: str | None = None, lang_code: str | None = None, admin_ids: list = []):
    async with db_lock:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, is_blocked FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        is_new_user = user_row is None
        current_time = get_now()

        if is_new_user:
            final_lang_code = lang_code if lang_code else 'uzl'
            cursor.execute("INSERT INTO users (user_id, full_name, username, language_code, join_date, last_activity_date) VALUES (?, ?, ?, ?, ?, ?)",
                           (user_id, full_name, username, final_lang_code, current_time, current_time))
            if user_id not in admin_ids:
                today = current_time.strftime('%Y-%m-%d')
                cursor.execute("INSERT OR IGNORE INTO daily_stats (stat_date) VALUES (?)", (today,))
                cursor.execute("UPDATE daily_stats SET new_users = new_users + 1 WHERE stat_date = ?", (today,))
        else:
            was_blocked = user_row[1] == 1
            update_parts = ["full_name = ?", "username = ?"]
            params = [full_name, username]

            if was_blocked:
                update_parts.append("is_blocked = 0")

            if lang_code:
                update_parts.append("language_code = ?")
                params.append(lang_code)

            params.append(user_id)
            update_query = f"UPDATE users SET {', '.join(update_parts)} WHERE user_id = ?"
            cursor.execute(update_query, tuple(params))

        conn.commit()
        conn.close()

async def log_feedback(user_id: int, message_id: int, chat_id: int):
    if user_id in config.ADMIN_IDS:
        return
    async with db_lock:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedbacks (user_id, message_id, chat_id, created_at) VALUES (?, ?, ?, ?)",
            (user_id, message_id, chat_id, get_now())
        )
        conn.commit()
        conn.close()

async def mark_feedback_as_replied(user_id: int):
    async with db_lock:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE feedbacks SET has_reply = 1 WHERE user_id = ? AND id = (SELECT MAX(id) FROM feedbacks WHERE user_id = ? AND has_reply = 0)",
            (user_id, user_id)
        )
        conn.commit()
        conn.close()

async def log_user_error(user_id: int | None, error_text: str):
    if user_id and user_id in config.ADMIN_IDS:
        return
    async with db_lock:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_errors (user_id, error_text, created_at) VALUES (?, ?, ?)",
            (user_id, error_text, get_now())
        )
        conn.commit()
        conn.close()

async def set_user_language(user_id: int, full_name: str, username: str | None, lang_code: str):
    await add_or_update_user(user_id, full_name, username, lang_code, admin_ids=config.ADMIN_IDS)

async def update_user_post_settings(user_id: int, parse_mode: Optional[str], url_preview_disabled: bool):
    async with db_lock:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET default_parse_mode = ?, default_disable_url_preview = ? WHERE user_id = ?",
                (parse_mode, int(url_preview_disabled), user_id)
            )
            conn.commit()
        except Exception as e:
            logging.error(f"Foydalanuvchi post sozlamalarini yangilashda xatolik: {e}")
        finally:
            if conn:
                conn.close()

async def block_user(user_id: int, admin_ids: list) -> bool:
    if user_id in admin_ids: return False
    async with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success
        except Exception as e:
            logging.error(f"Foydalanuvchini bloklashda xatolik: {e}")
            return False

async def unblock_user(user_id: int) -> bool:
    async with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (user_id,))
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success
        except Exception as e:
            logging.error(f"Foydalanuvchini blokdan chiqarishda xatolik: {e}")
            return False

def generate_post_code(length=5):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

async def add_post_to_db(user_id: int, post_data: dict, buttons_matrix: list, admin_ids: list) -> str | None:
    post_code = generate_post_code()
    full_post_json = json.dumps({'post_content': post_data, 'buttons_matrix': buttons_matrix})
    async with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            while True:
                cursor.execute("SELECT id FROM posts WHERE post_code = ?", (post_code,))
                if cursor.fetchone() is None: break
                post_code = generate_post_code()
            
            current_time = get_now()
            cursor.execute("INSERT INTO posts (post_code, user_id, full_post_data, created_at) VALUES (?, ?, ?, ?)", (post_code, user_id, full_post_json, current_time))
            if user_id not in admin_ids:
                today = current_time.strftime('%Y-%m-%d')
                cursor.execute("INSERT OR IGNORE INTO daily_stats (stat_date) VALUES (?)", (today,))
                cursor.execute("UPDATE daily_stats SET new_posts = new_posts + 1 WHERE stat_date = ?", (today,));
            conn.commit()
            conn.close()
            return post_code
        except Exception as e:
            logging.error(f"Postni bazaga qo'shishda xatolik: {e}")
            return None

async def update_post_in_db(post_code: str, post_data: dict, buttons_matrix: list) -> bool:
    full_post_json = json.dumps({'post_content': post_data, 'buttons_matrix': buttons_matrix})
    async with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("UPDATE posts SET full_post_data = ? WHERE post_code = ?", (full_post_json, post_code))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Postni yangilashda xatolik: {e}")
            return False

async def save_post_name(post_code: str, post_name: str) -> bool:
    async with db_lock:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("UPDATE posts SET post_name = ? WHERE post_code = ?", (post_name, post_code))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Post nomini saqlashda xatolik: {e}")
            return False

async def unsave_post_name(post_code: str, user_id: int) -> str | None:
    """Postning saqlangan nomini o'chiradi va eski nomini qaytaradi."""
    async with db_lock:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            
            cursor.execute("SELECT post_name FROM posts WHERE post_code = ? AND user_id = ?", (post_code, user_id))
            result = cursor.fetchone()
            
            if not result or result[0] is None:
                return None
                
            post_name = result[0]
            
            cursor.execute("UPDATE posts SET post_name = NULL WHERE post_code = ? AND user_id = ?", (post_code, user_id))
            conn.commit()
            
            return post_name
        except Exception as e:
            logging.error(f"Post nomini o'chirishda xatolik: {e}")
            return None
        finally:
            if conn:
                conn.close()

async def add_required_channel(channel_id: int, title: str, username: str | None = None):
    async with db_lock:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO required_channels (channel_id, title, username) VALUES (?, ?, ?)", (channel_id, title, username))
            conn.commit()
        except Exception as e:
            logging.error(f"Kanalni bazaga qo'shishda xatolik: {e}")
        finally:
            if conn: conn.close()

async def get_all_required_channels() -> list[dict]:
    channels = []
    async with db_lock:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT channel_id, title, username FROM required_channels")
            rows = cursor.fetchall()
            for row in rows:
                channels.append({'id': row[0], 'title': row[1], 'username': row[2]})
            return channels
        except Exception as e:
            logging.error(f"Bazadan kanallar ro'yxatini olishda xato: {e}")
            return []
        finally:
            if conn: conn.close()

async def remove_required_channel(channel_id: int):
    async with db_lock:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM required_channels WHERE channel_id = ?", (channel_id,))
            conn.commit()
        except Exception as e:
            logging.error(f"Kanalni o'chirishda xatolik: {e}")
        finally:
            if conn: conn.close()

async def set_guide_content(lang_code: str, content_type: str, text_or_caption: str | None, file_id: str | None):
    async with db_lock:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO guide_content (lang_code, content_type, text_or_caption, file_id) VALUES (?, ?, ?, ?)", (lang_code, content_type, text_or_caption, file_id))
            conn.commit()
        except Exception as e:
            logging.error(f"Yo'riqnoma kontentini o'rnatishda xatolik: {e}")
        finally:
            if conn: conn.close()

async def toggle_how_to_use_button(status: bool):
    async with db_lock:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("UPDATE settings SET value = ? WHERE key = ?", (str(int(status)), 'how_to_use_enabled'))
            conn.commit()
        except Exception as e:
            logging.error(f"Yo'riqnoma tugmasi holatini o'zgartirishda xatolik: {e}")
        finally:
            if conn: conn.close()

async def toggle_user_guide_setting(user_id: int, status: bool):
    async with db_lock:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET show_guide_button = ? WHERE user_id = ?", (int(status), user_id))
            conn.commit()
        except Exception as e:
            logging.error(f"Foydalanuvchi yo'riqnoma sozlamasini o'zgartirishda xatolik: {e}")
        finally:
            if conn: conn.close()

#==================================================
# --- M A ' L U M O T L A R N I   O' Q I SH   O P E R A T S I Y A L A R I ---
#==================================================

def _get_period_filter_params(period: Literal['daily', 'weekly', 'monthly', 'all'], date_column: str) -> tuple[str, list]:
    now = get_now()
    if period == 'daily':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'weekly':
        start_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'monthly':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        return "", []
    return f"AND {date_column} >= ?", [start_date]

async def check_feedback_agreement(user_id: int) -> bool:
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT feedback_agreement_accepted FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return bool(result and result[0] == 1)

async def check_ad_agreement(user_id: int) -> bool:
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT ad_agreement_accepted FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return bool(result and result[0] == 1)

async def get_assigned_admin(user_id: int) -> int | None:
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT assigned_admin_id FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

async def get_user_language(user_id: int) -> str:
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT language_code FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result and result[0] else "uzl"

async def get_user_post_settings(user_id: int) -> dict:
    settings = {
        'parse_mode': None,
        'disable_web_page_preview': False
    }
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT default_parse_mode, default_disable_url_preview FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            disable_preview_db_val = row[1] if row[1] is not None else 0
            settings['parse_mode'] = row[0]
            settings['disable_web_page_preview'] = bool(disable_preview_db_val)
    return settings

async def is_user_blocked(user_id: int, admin_ids: list) -> bool:
    if user_id in admin_ids: return False
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return bool(result and result[0] == 1)

async def get_detailed_user_stats(admin_ids: list) -> dict:
    stats = {'total': 0}
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # --- O'ZGARISH BOSHLANDI ---
        placeholders = ','.join('?' for _ in admin_ids)
        query = f"SELECT COUNT(user_id) FROM users WHERE user_id NOT IN ({placeholders})"
        cursor.execute(query, admin_ids)
        # --- O'ZGARISH TUGADI ---
        total_result = cursor.fetchone()
        stats['total'] = total_result[0] if total_result else 0
        conn.close()
    return stats

async def get_new_users_stats_extended(admin_ids: list) -> dict:
    stats = {'daily': 0, 'weekly': 0, 'monthly': 0}
    now = get_now()
    
    time_periods = {
        'daily': now.replace(hour=0, minute=0, second=0, microsecond=0),
        'weekly': (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0),
        'monthly': now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    }

    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # --- O'ZGARISH BOSHLANDI ---
        placeholders = ','.join('?' for _ in admin_ids)
        for period, start_time in time_periods.items():
            params = [start_time] + admin_ids
            query = f"SELECT COUNT(user_id) FROM users WHERE join_date >= ? AND user_id NOT IN ({placeholders})"
            cursor.execute(query, params)
            result = cursor.fetchone()
            stats[period] = result[0] if result else 0
        # --- O'ZGARISH TUGADI ---
        conn.close()
    return stats

async def get_language_distribution(admin_ids: list) -> dict:
    dist = {}
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # --- O'ZGARISH BOSHLANDI ---
        placeholders = ','.join('?' for _ in admin_ids)
        
        query_group = f"SELECT language_code, COUNT(user_id) FROM users WHERE user_id NOT IN ({placeholders}) GROUP BY language_code"
        cursor.execute(query_group, admin_ids)
        rows = cursor.fetchall()

        query_total = f"SELECT COUNT(user_id) FROM users WHERE user_id NOT IN ({placeholders})"
        cursor.execute(query_total, admin_ids)
        total_result = cursor.fetchone()
        total_users = total_result[0] if total_result else 0
        # --- O'ZGARISH TUGADI ---

        for row in rows:
            lang_code, count = row
            percentage = (count / total_users * 100) if total_users > 0 else 0
            dist[lang_code] = {'count': count, 'percentage': round(percentage, 2)}
        conn.close()
    return dist

async def get_posts_stats(admin_ids: list) -> dict:
    stats = {'total': 0, 'daily': 0, 'weekly': 0, 'monthly': 0}
    now = get_now()

    time_periods = {
        'daily': now.replace(hour=0, minute=0, second=0, microsecond=0),
        'weekly': (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0),
        'monthly': now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    }
    
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(id) FROM posts WHERE user_id NOT IN ({})".format(','.join('?' for _ in admin_ids)), admin_ids)
        total_result = cursor.fetchone()
        stats['total'] = total_result[0] if total_result else 0

        for period, start_time in time_periods.items():
            params = [start_time] + admin_ids
            cursor.execute(f"SELECT COUNT(id) FROM posts WHERE created_at >= ? AND user_id NOT IN ({','.join('?' for _ in admin_ids)})", params)
            result = cursor.fetchone()
            stats[period] = result[0] if result else 0
        conn.close()
    return stats

async def get_daily_stats_for_graph(days: int = 30) -> list:
    stats = []
    now = get_now()
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        start_date = (now - timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date_str = start_date.strftime('%Y-%m-%d')

        cursor.execute("SELECT stat_date, new_users, new_posts FROM daily_stats WHERE stat_date >= ? ORDER BY stat_date ASC", (start_date_str,))
        rows = cursor.fetchall()
        conn.close()

        db_stats = {row[0]: {'users': row[1], 'posts': row[2]} for row in rows}

        for i in range(days):
            current_date = start_date.date() + timedelta(days=i)
            current_date_db_str = current_date.strftime('%Y-%m-%d')
            current_date_display_str = current_date.strftime('%d.%m')
            
            db_entry = db_stats.get(current_date_db_str, {'users': 0, 'posts': 0})
            stats.append({
                'date': current_date_display_str,
                'new_users': db_entry['users'],
                'new_posts': db_entry['posts']
            })
    return stats

async def get_guide_content(lang_code: str) -> dict | None:
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT content_type, text_or_caption, file_id FROM guide_content WHERE lang_code = ?", (lang_code,))
        row = cursor.fetchone()
        if row:
            conn.close()
            return {'content_type': row[0], 'text_or_caption': row[1], 'file_id': row[2]}

        cursor.execute("SELECT content_type, text_or_caption, file_id FROM guide_content WHERE lang_code = 'uzl'")
        row_uz = cursor.fetchone()
        conn.close()
        if row_uz: return {'content_type': row_uz[0], 'text_or_caption': row_uz[1], 'file_id': row_uz[2]}

        return None

async def get_guide_button_settings(user_id: int) -> dict:
    settings = {'globally_enabled': True, 'user_enabled': True}
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT value FROM settings WHERE key = 'how_to_use_enabled'")
        global_res = cursor.fetchone()
        if global_res: settings['globally_enabled'] = bool(int(global_res[0]))

        if user_id not in config.ADMIN_IDS:
            cursor.execute("SELECT show_guide_button FROM users WHERE user_id = ?", (user_id,))
            user_res = cursor.fetchone()
            if user_res: settings['user_enabled'] = bool(int(user_res[0]))

        conn.close()
    return settings

async def get_users_for_export(admin_ids: list, period: str = 'all', user_ids: list = None) -> list:
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        query_parts = ["SELECT user_id, full_name, username, is_blocked, join_date FROM users"]
        params = []
        where_conditions = []

        if user_ids:
            user_placeholders = ','.join('?' for _ in user_ids)
            where_conditions.append(f"user_id IN ({user_placeholders})")
            params.extend(user_ids)
        else:
            # Agar aniq user_ids berilmagan bo'lsa, adminlarni filtrlaymiz
            placeholders = ','.join('?' for _ in admin_ids)
            where_conditions.append(f"user_id NOT IN ({placeholders})")
            params.extend(admin_ids)

        if where_conditions:
            query_parts.append("WHERE " + " AND ".join(where_conditions))

        period_filter_str, period_params = _get_period_filter_params(period, 'join_date')
        if period_filter_str:
            query_parts.append(period_filter_str.replace("AND", "AND" if where_conditions else "WHERE"))
            params.extend(period_params)

        query = " ".join(query_parts)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [{"user_id": r[0], "full_name": r[1], "username": r[2], "is_blocked": bool(r[3]), "join_date": r[4]} for r in rows]

async def get_posts_for_export(admin_ids: list, period: str = 'all') -> list:
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        query_parts = ["SELECT post_code, user_id FROM posts"]
        params = []
        where_conditions = []

        placeholders = ','.join('?' for _ in admin_ids)
        where_conditions.append(f"user_id NOT IN ({placeholders})")
        params.extend(admin_ids)

        period_filter_str, period_params = _get_period_filter_params(period, 'created_at')
        if period_filter_str:
            where_conditions.append(period_filter_str.replace("AND ", ""))
            params.extend(period_params)

        if where_conditions:
            query_parts.append("WHERE " + " AND ".join(where_conditions))

        query = " ".join(query_parts)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [{"post_code": r[0], "owner_user_id": r[1]} for r in rows]

async def get_user_settings_for_export(admin_ids: list, period: str = 'all') -> list:
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        query_parts = ["SELECT user_id, full_name, username, language_code, show_guide_button FROM users"]
        params = []
        
        placeholders = ','.join('?' for _ in admin_ids)
        where_conditions = [f"user_id NOT IN ({placeholders})"]
        params.extend(admin_ids)

        period_filter_str, period_params = _get_period_filter_params(period, 'join_date')
        if period_filter_str:
            where_conditions.append(period_filter_str.replace("AND ", ""))
            params.extend(period_params)

        query_parts.append("WHERE " + " AND ".join(where_conditions))
        query = " ".join(query_parts)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [{"user_id": r[0], "full_name": r[1], "username": r[2], "language": r[3], "show_guide_button": bool(r[4])} for r in rows]

async def get_post_creators_for_export(admin_ids: list, period: str = 'all') -> list:
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        where_conditions = []
        params = []

        placeholders = ','.join('?' for _ in admin_ids)
        where_conditions.append(f"u.user_id NOT IN ({placeholders})")
        params.extend(admin_ids)

        post_period_filter_str, post_period_params = _get_period_filter_params(period, 'p.created_at')
        if post_period_filter_str:
            where_conditions.append(post_period_filter_str.replace("AND ", ""))
            params.extend(post_period_params)

        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

        query = f"""
            SELECT
                u.user_id, u.full_name, u.username, u.is_blocked, u.join_date,
                GROUP_CONCAT(p.post_code, ', ')
            FROM users u
            INNER JOIN posts p ON u.user_id = p.user_id
            {where_clause}
            GROUP BY u.user_id
        """

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [{
            "user_id": r[0], "full_name": r[1], "username": r[2],
            "is_blocked": bool(r[3]), "join_date": r[4],
            "created_posts": r[5].split(', ') if r[5] else []
        } for r in rows]

async def find_user_by_id_or_username(query: str):
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if query.isdigit():
            cursor.execute("SELECT user_id, full_name, username, is_blocked, join_date FROM users WHERE user_id = ?", (int(query),))
        else:
            cursor.execute("SELECT user_id, full_name, username, is_blocked, join_date FROM users WHERE username = ?", (query.lstrip('@'),))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] in config.ADMIN_IDS:
            return None
            
        if row: return {"user_id": row[0], "full_name": row[1], "username": row[2], "is_blocked": bool(row[3]), "join_date": row[4]}
        return None

async def get_posts_by_user(user_id: int) -> list:
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT post_code, post_name FROM posts WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        posts = [{"code": row[0], "name": row[1]} for row in cursor.fetchall()]
        conn.close()
        return posts

async def get_blocked_users_with_info(admin_ids: list) -> list:
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        params = []
        where_conditions = ["is_blocked = 1"]
        
        placeholders = ','.join('?' for _ in admin_ids)
        where_conditions.append(f"user_id NOT IN ({placeholders})")
        params.extend(admin_ids)

        query = f"SELECT user_id, full_name FROM users WHERE {' AND '.join(where_conditions)}"
        cursor.execute(query, params)
        blocked_users = [{"user_id": row[0], "full_name": row[1]} for row in cursor.fetchall()]
        conn.close()
        return blocked_users

async def get_user_info_from_db(user_id: int):
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, full_name FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row: return {"user_id": row[0], "full_name": row[1]}
        return None

async def get_all_active_users(admin_ids: list) -> list:
    active_users = []
    async with db_lock:
        params = []
        where_conditions = ["is_blocked = 0"]
        
        placeholders = ','.join('?' for _ in admin_ids)
        where_conditions.append(f"user_id NOT IN ({placeholders})")
        params.extend(admin_ids)

        query = f"SELECT user_id FROM users WHERE {' AND '.join(where_conditions)}"
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(query, params)
            active_users = [item[0] for item in cursor.fetchall()]
            conn.close()
        except Exception as e:
            logging.error(f"Aktiv foydalanuvchilar ro'yxatini olishda xatolik: {e}")
    return active_users

async def get_post_from_db(post_code: str):
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT full_post_data FROM posts WHERE post_code = ?", (post_code,))
        result = cursor.fetchone()
        conn.close()
        if result: return json.loads(result[0])
        return None

async def check_post_owner(post_code: str, user_id: int) -> bool:
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM posts WHERE post_code = ?", (post_code,))
        result = cursor.fetchone()
        conn.close()
        return bool(result and result[0] == user_id)

async def get_today_posts_count() -> int:
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        today = get_now().strftime('%Y-%m-%d')
        cursor.execute("SELECT new_posts FROM daily_stats WHERE stat_date = ?", (today,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

async def get_feedbacks_by_user(user_id: int) -> list:
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT message_id, chat_id, has_reply, created_at FROM feedbacks WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [{"message_id": r[0], "chat_id": r[1], "has_reply": bool(r[2]), "created_at": r[3]} for r in rows]

async def get_errors_by_user(user_id: int) -> list:
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT error_text, created_at FROM user_errors WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [{"error_text": r[0], "created_at": r[1]} for r in rows]

#==================================================
# --- Y A N G I   S T A T I S T I K A   F U N K S I Y A L A R I ---
#==================================================

async def get_active_users_by_period(admin_ids: list) -> dict:
    stats = {'daily': 0, 'weekly': 0, 'monthly': 0}
    now = get_now()

    time_periods = {
        'daily': now.replace(hour=0, minute=0, second=0, microsecond=0),
        'weekly': (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0),
        'monthly': now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    }

    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # --- O'ZGARISH BOSHLANDI ---
        placeholders = ','.join('?' for _ in admin_ids)
        for period, start_time in time_periods.items():
            params = [start_time] + admin_ids
            query = f"SELECT COUNT(DISTINCT user_id) FROM users WHERE last_activity_date >= ? AND user_id NOT IN ({placeholders})"
            cursor.execute(query, params)
            result = cursor.fetchone()
            stats[period] = result[0] if result else 0
        # --- O'ZGARISH TUGADI ---
        conn.close()
    return stats

async def get_total_errors_count() -> int:
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(id) FROM user_errors")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

async def get_activity_heatmap_for_last_24h(admin_ids: list) -> str:
    now = get_now()
    start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # --- O'ZGARISH BOSHLANDI ---
        placeholders = ','.join('?' for _ in admin_ids)
        query = f"SELECT last_activity_date FROM users WHERE last_activity_date >= ? AND user_id NOT IN ({placeholders})"
        cursor.execute(query, [start_time] + admin_ids)
        # --- O'ZGARISH TUGADI ---
        rows = cursor.fetchall()
        conn.close()

    if not rows:
        return "Ma'lumot yo'q"

    hours = [datetime.fromisoformat(row['last_activity_date']).hour for row in rows]
    if not hours:
        return "Ma'lumot yo'q"

    hour_counts = Counter(hours)
    most_common_hours = hour_counts.most_common(3)

    if not most_common_hours:
        return "Ma'lumot yo'q"

    top_hours = sorted([h for h, c in most_common_hours])
    if len(top_hours) == 1:
        return f"{top_hours[0]:02d}:00 - {(top_hours[0] + 1) % 24:02d}:00"
    elif len(top_hours) == 2:
        return f"{top_hours[0]:02d}:00 - {top_hours[1]:02d}:00"
    else:
        return f"{top_hours[0]:02d}:00 - {top_hours[-1]:02d}:00"
#--- END OF FILE database.py ---
