import psycopg2
import psycopg2.pool
import json
import secrets
import string
import os
from datetime import datetime, timedelta, timezone
import asyncio
from typing import Optional, List, Dict, Any
from collections import Counter
from dotenv import dotenv_values
import logging

from xdata_handlers import config

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

TASHKENT_TZ = timezone(timedelta(hours=5))

_connection_pool = None

def _get_database_url() -> str | None:
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(dotenv_path):
        values = dotenv_values(dotenv_path, interpolate=False)
        return values.get("DATABASE_URL")
    return None

DB_URL = _get_database_url()

def _get_connection_pool():
    global _connection_pool
    if _connection_pool is None:
        db_url = _get_database_url() or DB_URL
        if not db_url:
            raise ValueError("DATABASE_URL topilmadi! Environment variables ni tekshiring.")
            
        connect_kwargs = {
            "sslmode": "require",
            "connect_timeout": 30,
        }
        
        try:
            _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                dsn=db_url,
                **connect_kwargs
            )
            logger.info("PostgreSQL connection pool yaratildi")
        except Exception as e:
            logger.error(f"Connection pool yaratishda xatolik: {e}")
            raise
    
    return _connection_pool

def get_now() -> datetime:
    """Hozirgi vaqtni har doim Toshkent vaqti bilan qaytaradi."""
    return datetime.now(TASHKENT_TZ)

def get_connection():
    """PostgreSQL bazasiga ulanish hosil qiladi (pool dan)."""
    try:
        pool = _get_connection_pool()
        conn = pool.getconn()
        conn.set_client_encoding('UTF8')
        # Toshkent vaqtini o'rnatish (UTC+5)
        cursor = conn.cursor()
        cursor.execute("SET TIME ZONE 'Asia/Tashkent'")
        cursor.close()
        return conn
    except Exception as e:
        logger.error(f"Ulanishda xatolik: {e}")
        # Fallback - to'g'ridan-to'g'ri ulanish
        db_url = _get_database_url() or DB_URL
        if not db_url:
            raise ValueError("DATABASE_URL topilmadi!")
        conn = psycopg2.connect(db_url, sslmode="require", connect_timeout=30)
        conn.set_client_encoding('UTF8')
        # Toshkent vaqtini o'rnatish (UTC+5)
        cursor = conn.cursor()
        cursor.execute("SET TIME ZONE 'Asia/Tashkent'")
        cursor.close()
        return conn

def release_connection(conn):
    """Ulanishni poolga qaytaradi."""
    try:
        pool = _get_connection_pool()
        pool.putconn(conn)
    except Exception:
        # Agar pool ishlamasa, to'g'ridan-to'g'ri yopamiz
        if conn:
            try:
                conn.close()
            except Exception:
                pass

def _normalize_language(language: str | None) -> str:
    """Til kodini normalize qiladi."""
    if not language:
        return 'uzl'  # Default til
    language = language.lower().strip()
    # 'uz' ni 'uzl' ga o'zgartirish
    if language == 'uz':
        return 'uzl'
    return language

async def set_user_language(user_id: int, nickname: str = None, username: str = None, language: str = 'uzl') -> bool:
    """Foydalanuvchi tilini o'rnatadi."""
    # Til kodini normalize qilish
    language = _normalize_language(language)
    
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, nickname, username, language)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    nickname = COALESCE(EXCLUDED.nickname, users.nickname),
                    username = COALESCE(EXCLUDED.username, users.username),
                    language = EXCLUDED.language;
            """, (user_id, nickname, username, language))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"set_user_language xatolik: {e}")
            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_all_active_users(admin_ids: List[int] = None) -> List[int]:
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            excluded_ids = admin_ids or []
            if excluded_ids:
                placeholders = ','.join(['%s'] * len(excluded_ids))
                cursor.execute(
                    f"SELECT user_id FROM users WHERE COALESCE(is_blocked, 0) = 0 AND user_id NOT IN ({placeholders})",
                    excluded_ids
                )
            else:
                cursor.execute("SELECT user_id FROM users WHERE COALESCE(is_blocked, 0) = 0")
            rows = cursor.fetchall()
            return [int(r[0]) for r in rows]
        except Exception:

            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_blocked_users_with_info(admin_ids: List[int] = None) -> List[Dict]:
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            excluded_ids = admin_ids or []
            if excluded_ids:
                placeholders = ','.join(['%s'] * len(excluded_ids))
                cursor.execute(
                    f"SELECT user_id, nickname, username FROM users WHERE COALESCE(is_blocked, 0) = 1 AND user_id NOT IN ({placeholders}) ORDER BY user_id DESC",
                    excluded_ids
                )
            else:
                cursor.execute(
                    "SELECT user_id, nickname, username FROM users WHERE COALESCE(is_blocked, 0) = 1 ORDER BY user_id DESC"
                )
            rows = cursor.fetchall()
            return [
                {
                    'user_id': row[0],
                    'nickname': row[1],
                    'username': row[2]
                }
                for row in rows
            ]
        except Exception:

            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def add_or_update_user(user_id: int, nickname: str = None, username: str = None, language: str = None):
    """Foydalanuvchini bazaga qo'shadi yoki ma'lumotlarini yangilaydi."""
    from xdata_handlers import config
    
    # Admin foydalanuvchilarni qo'shmaymiz
    if config.ADMIN_IDS and user_id in config.ADMIN_IDS:
        return
    
    return await _add_or_update_user_impl(user_id=user_id, nickname=nickname, username=username, language=language)

async def _add_or_update_user_impl(user_id: int, nickname: str, username: str, language: str = None):
    """Foydalanuvchini bazaga qo'shadi yoki ma'lumotlarini yangilaydi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Avval foydalanuvchi mavjudligini tekshiramiz
            cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            is_new_user = result is None
            
            if language is None:
                if is_new_user:
                    cursor.execute("""
                        INSERT INTO users (user_id, nickname, username, language, last_activity)
                        VALUES (%s, %s, %s, NULL, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id) DO UPDATE SET
                            nickname = EXCLUDED.nickname,
                            username = EXCLUDED.username,
                            last_activity = CURRENT_TIMESTAMP;
                    """, (user_id, nickname, username))
                else:
                    cursor.execute("""
                        INSERT INTO users (user_id, nickname, username, language, last_activity)
                        VALUES (%s, %s, %s, NULL, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id) DO UPDATE SET
                            nickname = EXCLUDED.nickname,
                            username = EXCLUDED.username,
                            last_activity = CURRENT_TIMESTAMP;
                    """, (user_id, nickname, username))
            else:
                if is_new_user:
                    cursor.execute("""
                        INSERT INTO users (user_id, nickname, username, language, last_activity)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id) DO UPDATE SET
                            nickname = EXCLUDED.nickname,
                            username = EXCLUDED.username,
                            language = EXCLUDED.language,
                            last_activity = CURRENT_TIMESTAMP;
                    """, (user_id, nickname, username, language))
                else:
                    cursor.execute("""
                        INSERT INTO users (user_id, nickname, username, language, last_activity)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id) DO UPDATE SET
                            nickname = EXCLUDED.nickname,
                            username = EXCLUDED.username,
                            language = EXCLUDED.language,
                            last_activity = CURRENT_TIMESTAMP;
                    """, (user_id, nickname, username, language))
            
            conn.commit()
            if is_new_user:
                logger.info(f"Yangi foydalanuvchi qo'shildi: {user_id}")
            return is_new_user
        except Exception as e:
            logger.error(f"add_or_update_user xatolik: {e}")
            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)




async def record_new_post():
    """Yangi post yaratilganda statistikaga qo'shadi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO bot_stats (stat_date, new_posts)
                VALUES (CURRENT_DATE, 1)
                ON CONFLICT (stat_date) DO UPDATE SET
                    new_posts = bot_stats.new_posts + 1
            """)
            
            conn.commit()
        except Exception as e:
            logger.error(f"record_new_post xatolik: {e}")
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_user_language(user_id: int) -> str:
    """Foydalanuvchi tilini oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT language FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            language = result[0] if result else 'uz'
            # Til kodini normalize qilish
            return _normalize_language(language)
        except Exception:
 
            return _normalize_language('uz')
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def is_user_blocked(user_id: int) -> bool:
    """Foydalanuvchi bloklanganligini tekshiradi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT is_blocked FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            return bool(result[0]) if result else False
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def block_user(user_id: int) -> bool:
    """Foydalanuvchini bloklaydi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_blocked = 1 WHERE user_id = %s", (user_id,))
            conn.commit()
            return True
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def unblock_user(user_id: int) -> bool:
    """Foydalanuvchini blokdan chiqaradi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_blocked = 0 WHERE user_id = %s", (user_id,))
            conn.commit()
            return True
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def add_user_channel(user_id: int, channel_id: int, channel_name: str, send_posts: bool = False) -> bool:
    """Foydalanuvchi kanalini qo'shadi."""
    # logger.info(f"[CHANNEL] add_user_channel called: user_id={user_id}, channel_id={channel_id}, channel_name={channel_name}")
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO channels (user_id, channel_id, channel_name, send_posts)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, channel_id) DO UPDATE SET
                    channel_name = EXCLUDED.channel_name,
                    send_posts = EXCLUDED.send_posts,
                    recorded_at = (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tashkent');
            """, (user_id, channel_id, channel_name, send_posts))
            conn.commit()
            # logger.info(f"[CHANNEL] Channel added successfully: user_id={user_id}, channel_id={channel_id}")
            return True
        except Exception as e:
            logger.error(f"[CHANNEL] Error adding channel: user_id={user_id}, channel_id={channel_id}, error={e}")
            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_user_channels(user_id: int) -> List[Dict]:
    """Foydalanuvchi kanallarini oladi."""
    # logger.info(f"[CHANNEL] get_user_channels called: user_id={user_id}")
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT channel_id, channel_name, send_posts, recorded_at
                FROM channels WHERE user_id = %s
            """, (user_id,))
            rows = cursor.fetchall()
            result = [
                {
                    'channel_id': row[0],
                    'channel_name': row[1], 
                    'send_posts': row[2],
                    'recorded_at': row[3]
                }
                for row in rows
            ]
            # logger.info(f"[CHANNEL] get_user_channels result: user_id={user_id}, count={len(result)}")
            return result
        except Exception as e:
            logger.error(f"[CHANNEL] Error getting user channels: user_id={user_id}, error={e}")
            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_user_channel_statistics(user_id: int, channel_id: int = None) -> Dict:
    """Foydalanuvchining kanallar statistikasini oladi."""
    # logger.info(f"[STATS] get_user_channel_statistics called: user_id={user_id}")
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            if channel_id is not None:
                channel_ids = [channel_id]
            else:
                # Foydalanuvchining kanallarini olish
                cursor.execute("""
                    SELECT channel_id FROM channels WHERE user_id = %s
                """, (user_id,))
                channel_rows = cursor.fetchall()
                
                if not channel_rows:
                    return {
                        'total_posts': 0,
                        'total_reactions': 0,
                        'total_shares': 0,
                        'top_reactions': []
                    }
                
                channel_ids = [row[0] for row in channel_rows]
            
            # Yuborilgan postlar sonini olish
            cursor.execute("""
                SELECT COUNT(*) FROM send_posts 
                WHERE user_id = %s AND channel_id = ANY(%s) AND status = 'sent'
            """, (user_id, channel_ids))
            total_posts = cursor.fetchone()[0] or 0
            
            # Yuborilgan postlar sonini olish
            cursor.execute("""
                SELECT COUNT(*) FROM send_posts 
                WHERE user_id = %s AND channel_id = ANY(%s) AND status = 'sent'
            """, (user_id, channel_ids))
            total_posts = cursor.fetchone()[0] or 0
            
            # Reaksiyalar sonini olish
            try:
                cursor.execute("""
                    SELECT COUNT(DISTINCT r.id) FROM reactions r
                    JOIN send_posts sp ON r.post_code = sp.post_code
                    WHERE sp.user_id = %s AND sp.channel_id = ANY(%s)
                """, (user_id, channel_ids))
                total_reactions = cursor.fetchone()[0] or 0
            except Exception:
                total_reactions = 0
            
            # Ulashishlar sonini olish
            try:
                cursor.execute("""
                    SELECT COALESCE(SUM(forward_count), 0) FROM send_posts 
                    WHERE user_id = %s AND channel_id = ANY(%s) AND status = 'sent'
                """, (user_id, channel_ids))
                total_shares = cursor.fetchone()[0] or 0
            except Exception:
                total_shares = 0
            
            # Top reaksiyalarni olish
            try:
                cursor.execute("""
                    SELECT r.reaction_emoji, COUNT(*) as cnt 
                    FROM reactions r
                    JOIN send_posts sp ON r.post_code = sp.post_code
                    WHERE sp.user_id = %s AND sp.channel_id = ANY(%s)
                    GROUP BY r.reaction_emoji 
                    ORDER BY cnt DESC 
                    LIMIT 5
                """, (user_id, channel_ids))
                reaction_rows = cursor.fetchall()
                top_reactions = [
                    {'emoji': row[0], 'count': row[1]} 
                    for row in reaction_rows if row[0]
                ]
            except Exception:
                top_reactions = []
            
            result = {
                'total_posts': total_posts,
                'total_reactions': total_reactions,
                'total_shares': total_shares,
                'top_reactions': top_reactions
            }
            # logger.info(f"[STATS] get_user_channel_statistics result: user_id={user_id}, stats={result}")
            return result
        except Exception as e:
            logger.error(f"[STATS] Error getting user channel statistics: user_id={user_id}, error={e}")
            return {
                'total_posts': 0,
                'total_views': 0,
                'total_reactions': 0,
                'total_shares': 0,
                'total_button_clicks': 0,
                'top_reactions': []
            }
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_channel_name(user_id: int, channel_id: int) -> str | None:
    """Kanal nomini user_id va channel_id bo'yicha qaytaradi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT channel_name FROM channels 
                WHERE user_id = %s AND channel_id = %s
            """, (user_id, channel_id))
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception:
            return None
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def remove_user_channel(user_id: int, channel_id: int) -> bool:
    """Foydalanuvchi kanalini o'chiradi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM channels WHERE user_id = %s AND channel_id = %s", (user_id, channel_id))
            conn.commit()
            return True
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def update_channel_post_code(user_id: int, channel_id: int, post_code: str) -> bool:
    """Kanalga post kodi ni yozadi."""
    # logger.info(f"[CHANNEL] update_channel_post_code: user_id={user_id}, channel_id={channel_id}, post_code={post_code}")
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE channels 
                SET send_posts = %s, recorded_at = (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tashkent')
                WHERE user_id = %s AND channel_id = %s
            """, (post_code, user_id, channel_id))
            conn.commit()
            # logger.info(f"[CHANNEL] Post code updated: channel_id={channel_id}, post_code={post_code}")
            return True
        except Exception as e:
            logger.error(f"[CHANNEL] Error updating post code: user_id={user_id}, channel_id={channel_id}, error={e}")
            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_user_bot_settings(user_id: int) -> Dict:
    """Foydalanuvchi bot sozlamalarini oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ai_assistant_enabled
                FROM bot_settings WHERE user_id = %s
            """, (user_id,))
            result = cursor.fetchone()
            if result:
                return {
                    'ai_assistant_enabled': result[0] or False
                }
            return {
                'ai_assistant_enabled': False
            }
        except Exception:

            return {
                'ai_assistant_enabled': False
            }
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def update_user_bot_settings(user_id: int, ai_assistant_enabled: bool = None) -> bool:
    """Foydalanuvchi bot sozlamalarini yangilaydi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            if ai_assistant_enabled is None:
                return False

            cursor.execute("""
                INSERT INTO bot_settings (user_id, ai_assistant_enabled)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET ai_assistant_enabled = EXCLUDED.ai_assistant_enabled;
            """, (user_id, ai_assistant_enabled))
            conn.commit()
            return True
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def add_scheduled_post(user_id: int, post_code: str, scheduled_time: datetime, channel_id: int = None, channel_name: str = None) -> int | None:
    """Rejalashtirilgan post qo'shadi va post_id qaytaradi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO send_posts (post_code, user_id, channel_id, channel_name, schedule_time, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
                RETURNING id
            """, (post_code, user_id, channel_id, channel_name, scheduled_time))
            post_id = cursor.fetchone()[0]
            conn.commit()
            return post_id
        except Exception:

            return None
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def save_sent_post(post_code: str, user_id: int, channel_id: int, channel_name: str = None, message_id: int = None) -> bool:
    """Yuborilgan postni saqlaydi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO send_posts (post_code, user_id, channel_id, channel_name, status, sent_at, message_id)
                VALUES (%s, %s, %s, %s, 'sent', %s, %s)
                ON CONFLICT (post_code, channel_id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    status = EXCLUDED.status,
                    sent_at = EXCLUDED.sent_at,
                    message_id = EXCLUDED.message_id,
                    channel_name = EXCLUDED.channel_name;
            """, (post_code, user_id, channel_id, channel_name, get_now(), message_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"save_sent_post xatolik: {e}")
            return False
        finally:
            if conn: release_connection(conn)
    
    success = await asyncio.to_thread(_sync)
    return success

async def get_scheduled_posts() -> List[Dict]:
    """Rejalashtirilgan postlarni oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, post_code, user_id, channel_id, schedule_time, status
                FROM send_posts 
                WHERE status = 'pending' AND schedule_time <= %s
                ORDER BY schedule_time ASC
            """, (get_now(),))
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'post_code': row[1],
                    'user_id': row[2],
                    'channel_id': row[3],
                    'schedule_time': row[4],
                    'status': row[5]
                }
                for row in rows
            ]
        except Exception:

            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def mark_scheduled_post_as_sent(post_id: int) -> bool:
    """Rejalashtirilgan postni yuborilgan deb belgilaydi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE send_posts SET status = 'sent', sent_at = %s WHERE id = %s", (get_now(), post_id))
            conn.commit()
            return True
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_user_sent_posts(user_id: int) -> List[Dict]:
    """Foydalanuvchining yuborilgan barcha postlarini oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sp.post_code, sp.channel_id, sp.channel_name, sp.message_id, sp.sent_at,
                       pi.full_post_data
                FROM send_posts sp
                LEFT JOIN post_info pi ON sp.post_code = pi.post_code
                WHERE sp.user_id = %s AND sp.status = 'sent' AND sp.message_id IS NOT NULL
                ORDER BY sp.sent_at DESC
            """, (user_id,))
            rows = cursor.fetchall()
            return [
                {
                    'post_code': row[0],
                    'channel_id': row[1],
                    'channel_name': row[2],
                    'message_id': row[3],
                    'sent_at': row[4],
                    'full_post_data': row[5]
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"get_user_sent_posts xatolik: {e}")
            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_pending_scheduled_posts() -> List[Dict]:
    """Kutilayotgan rejalashtirilgan postlarni oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, post_code, user_id, channel_id, schedule_time
                FROM send_posts 
                WHERE status = 'pending' AND schedule_time <= %s
                ORDER BY schedule_time ASC
            """, (get_now(),))
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'post_code': row[1],
                    'user_id': row[2],
                    'channel_id': row[3],
                    'schedule_time': row[4]
                }
                for row in rows
            ]
        except Exception:

            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def add_required_channel(channel_id: int, channel_name: str, username: str = None) -> bool:
    """Majburiy kanal qo'shadi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO req_channels (channel_id, channel_name, username)
                VALUES (%s, %s, %s)
                ON CONFLICT (channel_id) DO UPDATE SET
                    channel_name = EXCLUDED.channel_name,
                    username = EXCLUDED.username;
            """, (channel_id, channel_name, username))
            conn.commit()
            return True
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_required_channels() -> List[Dict]:
    """Majburiy kanallarni oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT channel_id, channel_name, username FROM req_channels")
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'title': row[1],
                    'username': row[2]
                }
                for row in rows
            ]
        except Exception:

            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_all_required_channels() -> List[Dict]:
    return await get_required_channels()

async def remove_required_channel(channel_id: int) -> bool:
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM req_channels WHERE channel_id = %s", (channel_id,))
            conn.commit()
            return True
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def add_reaction(button_index: int, reaction_emoji: str, 
                      user_id: int, chat_id: int, message_id: int) -> bool:
    """Reaksiya qo'shadi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reactions (button_index, reaction_emoji, user_id, chat_id, message_id)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (button_index, reaction_emoji, user_id, chat_id, message_id))
            conn.commit()
            return True
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_post_reactions(chat_id: int = None, message_id: int = None) -> List[Dict]:
    """Reaksiyalarni oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            if chat_id and message_id:
                cursor.execute("""
                    SELECT button_index, reaction_emoji, user_id, chat_id, message_id
                    FROM reactions WHERE chat_id = %s AND message_id = %s
                """, (chat_id, message_id))
            else:
                cursor.execute("""
                    SELECT button_index, reaction_emoji, user_id, chat_id, message_id
                    FROM reactions
                """)
            rows = cursor.fetchall()
            return [
                {
                    'button_index': row[0],
                    'reaction_emoji': row[1],
                    'user_id': row[2],
                    'chat_id': row[3],
                    'message_id': row[4]
                }
                for row in rows
            ]
        except Exception:

            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def add_or_update_reaction(button_index: int, reaction_emoji: str,
                                 user_id: int, chat_id: int, message_id: int) -> bool:
    return await add_reaction(
        button_index=button_index,
        reaction_emoji=reaction_emoji,
        user_id=user_id,
        chat_id=chat_id,
        message_id=message_id
    )

async def add_or_update_reaction_by_chat_message(user_id: int, chat_id: int, message_id: int, reaction_emoji: str) -> tuple:
    """Chat va message ID orqali reaksiya qo'shadi yoki yangilaydi.
    Returns: (status, old_reaction) - status: 'added', 'updated', 'already_voted', 'error'
    """
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT reaction_emoji FROM reactions 
                WHERE user_id = %s AND chat_id = %s AND message_id = %s
            """, (user_id, chat_id, message_id))
            existing = cursor.fetchone()

            if existing:
                old_reaction = existing[0]
                if old_reaction == reaction_emoji:
                    return ('already_voted', old_reaction)

                cursor.execute("""
                    UPDATE reactions SET reaction_emoji = %s 
                    WHERE user_id = %s AND chat_id = %s AND message_id = %s
                """, (reaction_emoji, user_id, chat_id, message_id))
                conn.commit()
                return ('updated', old_reaction)
            else:
                cursor.execute("""
                    INSERT INTO reactions (user_id, chat_id, message_id, reaction_emoji, button_index)
                    VALUES (%s, %s, %s, %s, 0)
                """, (user_id, chat_id, message_id, reaction_emoji))
                conn.commit()
                return ('added', None)
        except Exception as e:
            logger.error(f"add_or_update_reaction_by_chat_message xatolik: {e}")
            return ('error', None)
        finally:
            if conn: release_connection(conn)
    
    status, old_r = await asyncio.to_thread(_sync)
    
    return (status, old_r)

async def get_reaction_count(chat_id: int, message_id: int, button_index: int) -> int:
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM reactions WHERE chat_id = %s AND message_id = %s AND button_index = %s",
                (chat_id, message_id, button_index)
            )
            row = cursor.fetchone()
            return int(row[0] or 0) if row else 0
        except Exception:

            return 0
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_reaction_count_by_chat_message(chat_id: int, message_id: int, reaction_emoji: str) -> int:
    """Chat va message ID orqali reaksiya sonini oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM reactions WHERE chat_id = %s AND message_id = %s AND reaction_emoji = %s",
                (chat_id, message_id, reaction_emoji)
            )
            row = cursor.fetchone()
            return int(row[0] or 0) if row else 0
        except Exception:

            return 0
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

def generate_post_code(length: int = 5) -> str:
    """Unikal post kodini generatsiya qiladi."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

async def add_post_to_db(user_id: int, post_data: dict, buttons_matrix: list = None, post_name: str = None, admin_ids: List[int] = None) -> str | None:
    """Postni bazaga qo'shadi va unikal kod qaytaradi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            post_code = generate_post_code()

            while True:
                cursor.execute("SELECT id FROM post_info WHERE post_code = %s", (post_code,))
                if cursor.fetchone() is None: 
                    break
                post_code = generate_post_code()

            if isinstance(post_data, dict) and ('post_content' in post_data or 'buttons_matrix' in post_data):
                full_post_data = post_data
                if buttons_matrix is not None and 'buttons_matrix' not in full_post_data:
                    full_post_data = dict(full_post_data)
                    full_post_data['buttons_matrix'] = buttons_matrix
            else:
                full_post_data = {
                    'post_content': post_data,
                    'buttons_matrix': buttons_matrix or []
                }

            full_post_json = json.dumps(full_post_data, ensure_ascii=False)
            cursor.execute("""
                INSERT INTO post_info (post_code, user_id, full_post_data, post_name)
                VALUES (%s, %s, %s, %s)
            """, (post_code, user_id, full_post_json, post_name))

            conn.commit()
            return post_code
        except Exception:

            return None
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_post_from_db(post_code: str) -> dict | None:
    """Postni bazadan oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT full_post_data FROM post_info WHERE post_code = %s", (post_code,))
            result = cursor.fetchone()
            return json.loads(result[0]) if result else None
        except Exception:

            return None
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def check_post_owner(post_code: str, user_id: int) -> bool:
    """Post egasini tekshiradi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM post_info WHERE post_code = %s", (post_code,))
            result = cursor.fetchone()
            return result[0] == user_id if result else False
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_post_name(post_code: str) -> str | None:
    """Post nomini oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT post_name FROM post_info WHERE post_code = %s", (post_code,))
            result = cursor.fetchone()
            return result[0] if result and result[0] else None
        except Exception:

            return None
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def update_post_in_db(post_code: str, post_data: dict, buttons_matrix: list = None, post_name: str = None) -> bool:
    """Postni bazada yangilaydi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            if isinstance(post_data, dict) and ('post_content' in post_data or 'buttons_matrix' in post_data):
                full_post_data = post_data
                if buttons_matrix is not None and 'buttons_matrix' not in full_post_data:
                    full_post_data = dict(full_post_data)
                    full_post_data['buttons_matrix'] = buttons_matrix
            else:
                full_post_data = {
                    'post_content': post_data,
                    'buttons_matrix': buttons_matrix or []
                }

            updates = ["full_post_data = %s"]
            params = [json.dumps(full_post_data, ensure_ascii=False), post_code]

            if post_name is not None:
                updates.append("post_name = %s")
                params.insert(-1, post_name)

            cursor.execute(f"""
                UPDATE post_info SET {', '.join(updates)} 
                WHERE post_code = %s
            """, params)

            if buttons_matrix:
                for row in buttons_matrix:
                    for btn in row:
                        if btn and btn.get('type') == 'text_btn':
                            db_id = btn.get('db_id')
                            if db_id:
                                cursor.execute("""
                                    UPDATE text_buttons 
                                    SET post_code = %s, button_type = %s
                                    WHERE id = %s AND (post_code IS NULL OR post_code = '')
                                """, (post_code, 'text_btn', db_id))

            conn.commit()
            return True
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def update_post_message_id(post_code: str, message_id: int) -> bool:
    """Post message_id sini yangilaydi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE post_info SET message_id = %s WHERE post_code = %s", (message_id, post_code))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"update_post_message_id xatolik: {e}")
            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_post_code_from_chat_message(chat_id: int, message_id: int) -> tuple:
    """Chat va message ID dan post_code va channel_id ni oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT post_code, channel_id FROM send_posts WHERE channel_id = %s AND message_id = %s",
                (chat_id, message_id)
            )
            result = cursor.fetchone()
            return (result[0], result[1]) if result else (None, None)
        except Exception as e:
            logger.error(f"get_post_code_from_chat_message xatolik: {e}")
            return (None, None)
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def update_post_error(post_code: str, error_message: str) -> bool:
    """Post xatolik xabarini yangilaydi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE post_info SET error_message = %s WHERE post_code = %s", (error_message, post_code))
            conn.commit()
            return True
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def update_post_print_settings(post_code: str, print_settings: dict) -> bool:
    """Postning chop etish sozlamalarini yangilaydi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT full_post_data FROM post_info WHERE post_code = %s", (post_code,))
            result = cursor.fetchone()

            if not result:
                return False

            full_post_data = result[0] if result[0] else {}

            if isinstance(full_post_data, str):
                full_post_data = json.loads(full_post_data)

            if 'print_settings' not in full_post_data:
                full_post_data['print_settings'] = {}
            full_post_data['print_settings'].update(print_settings)

            cursor.execute(
                "UPDATE post_info SET full_post_data = %s WHERE post_code = %s",
                (json.dumps(full_post_data, ensure_ascii=False), post_code)
            )
            conn.commit()
            return True
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def save_post_name(post_code: str, post_name: str) -> bool:
    """Post nomini saqlaydi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE post_info SET post_name = %s WHERE post_code = %s", (post_name, post_code))
            conn.commit()
            return True
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def unsave_post_name(post_code: str, user_id: int = None) -> str | None:
    """Post nomini o'chiradi va qaytaradi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT post_name FROM post_info WHERE post_code = %s", (post_code,))
            result = cursor.fetchone()
            post_name = result[0] if result else None

            if post_name:
                cursor.execute("UPDATE post_info SET post_name = NULL WHERE post_code = %s", (post_code,))
                conn.commit()

            return post_name
        except Exception:

            return None
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_user_posts(user_id: int) -> List[Dict]:
    """Foydalanuvchi postlarini oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT post_code, post_name, message_id, error_message
                FROM post_info WHERE user_id = %s ORDER BY id DESC
            """, (user_id,))
            rows = cursor.fetchall()
            return [
                {
                    'post_code': row[0],
                    'post_name': row[1],
                    'message_id': row[2],
                    'error_message': row[3]
                }
                for row in rows
            ]
        except Exception:

            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_posts_by_user(user_id: int) -> List[Dict]:
    """Foydalanuvchi postlarini oladi (eski nom uchun moslik)."""
    posts = await get_user_posts(user_id)
    return [
        {
            'code': p.get('post_code'),
            'name': p.get('post_name'),
            'message_id': p.get('message_id'),
            'error_message': p.get('error_message')
        }
        for p in posts
    ]

async def get_user_post_settings(user_id: int) -> Dict:
    """Foydalanuvchi post sozlamalarini oladi."""
    settings = await get_user_bot_settings(user_id)
    return {
        'ai_assistant_enabled': settings.get('ai_assistant_enabled', False),
        'disable_web_page_preview': True,  # Har doim true - URL preview o'chirilgan
        'parse_mode': 'HTML',
        'enable_analytics': True,
        'default_language': await get_user_language(user_id)
    }

async def update_user_post_settings(user_id: int, settings: Dict = None, **kwargs) -> bool:
    """Foydalanuvchi post sozlamalarini yangilaydi."""
    merged: Dict[str, Any] = {}
    if settings:
        merged.update(settings)
    merged.update(kwargs)

    return await update_user_bot_settings(
        user_id=user_id,
        ai_assistant_enabled=merged.get('ai_assistant_enabled')
    )

async def create_text_button(*args, **kwargs) -> int | None:
    """Matnli tugma yaratadi."""
    if args and len(args) == 2 and not kwargs:
        button_type = None
        content_sub, content_nonsub = args
    else:
        button_type = kwargs.get('button_type')
        content_sub = kwargs.get('content_sub')
        content_nonsub = kwargs.get('content_nonsub')
        if args:
            button_type, content_sub, content_nonsub = args

    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            if button_type is not None:
                cursor.execute("""
                    INSERT INTO text_buttons (button_type, content_sub, content_nonsub)
                    VALUES (%s, %s, %s) RETURNING id
                """, (button_type, content_sub, content_nonsub))
            else:
                cursor.execute("""
                    INSERT INTO text_buttons (content_sub, content_nonsub)
                    VALUES (%s, %s) RETURNING id
                """, (content_sub, content_nonsub))
            btn_id = cursor.fetchone()[0]
            conn.commit()
            return btn_id
        except Exception:

            return None
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_text_button_content(btn_id: int) -> dict | None:
    """Matnli tugma kontentini oladi (post_code bilan birga)."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content_sub, content_nonsub, post_code
                FROM text_buttons WHERE id = %s
            """, (btn_id,))
            row = cursor.fetchone()
            return {
                'content_sub': row[0], 
                'content_nonsub': row[1],
                'post_code': row[2]
            } if row else None
        except Exception:
            return None
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def log_user_feedback(user_id: int, feedback_text: str) -> bool:
    """Foydalanuvchi feedbackini users jadvaliga yozadi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET feedback_text = %s 
                WHERE user_id = %s
            """, (feedback_text, user_id))
            conn.commit()
            return True
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def log_user_error(user_id: int, error_text: str) -> bool:
    """Foydalanuvchi xatosini users jadvaliga yozadi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET error_text = %s 
                WHERE user_id = %s
            """, (error_text, user_id))
            conn.commit()
            return True
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_feedbacks_by_user(user_id: int) -> List[Dict]:
    """Foydalanuvchi feedbacklarini oladi (users jadvalidan)."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT feedback_text 
                FROM users 
                WHERE user_id = %s AND feedback_text IS NOT NULL
            """, (user_id,))
            result = cursor.fetchone()
            if result and result[0]:
                return [
                    {
                        'feedback_text': result[0],
                        'has_reply': False
                    }
                ]
            return []
        except Exception:

            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_errors_by_user(user_id: int) -> List[Dict]:
    """Foydalanuvchi xatolarini oladi (users jadvalidan)."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT error_text 
                FROM users 
                WHERE user_id = %s AND error_text IS NOT NULL
            """, (user_id,))
            result = cursor.fetchone()
            if result and result[0]:
                return [
                    {
                        'error_text': result[0]
                    }
                ]
            return []
        except Exception:

            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def find_user_by_id_or_username(query: str) -> Dict | None:
    """Foydalanuvchini ID yoki username bo'yicha topadi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            if query.isdigit():
                cursor.execute("SELECT user_id, nickname, username, language, is_blocked, activate FROM users WHERE user_id = %s", (int(query),))
            else:
                username = query.lstrip('@')
                cursor.execute("SELECT user_id, nickname, username, language, is_blocked, activate FROM users WHERE username = %s", (username,))

            result = cursor.fetchone()
            if result:
                return {
                    'user_id': result[0],
                    'nickname': result[1],
                    'username': result[2],
                    'language': result[3],
                    'language_code': result[3],
                    'is_blocked': result[4],
                    'join_date': result[5],  # activate ustunidan olinadi
                    'last_activity_date': result[5]  # activate ustunidan olinadi
                }
            return None
        except Exception:

            return None
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_user_info_from_db(user_id: int) -> Dict | None:
    """Foydalanuvchi ma'lumotlarini bazadan oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, nickname, username, language, is_blocked
                FROM users WHERE user_id = %s
            """, (user_id,))
            result = cursor.fetchone()
            if result:
                return {
                    'user_id': result[0],
                    'nickname': result[1],
                    'username': result[2],
                    'language': result[3],
                    'is_blocked': result[4]
                }
            return None
        except Exception:

            return None
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_user_block_info(user_id: int) -> Dict | None:
    """Foydalanuvchi blok ma'lumotlarini oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, nickname, username, is_blocked
                FROM users WHERE user_id = %s
            """, (user_id,))
            result = cursor.fetchone()
            if result:
                return {
                    'user_id': result[0],
                    'nickname': result[1],
                    'username': result[2],
                    'is_blocked': result[3]
                }
            return None
        except Exception:

            return None
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_users_for_export(admin_ids: List[int], period: str = None) -> List[Dict]:
    """Eksport uchun foydalanuvchilar ro'yxatini oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            query = """
                SELECT user_id, nickname, username, language, is_blocked
                FROM users 
                WHERE user_id NOT IN (%s)
            """ % ','.join('%s' for _ in admin_ids)

            params = admin_ids

            if period:
                pass

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                {
                    'user_id': row[0],
                    'nickname': row[1],
                    'username': row[2],
                    'language': row[3],
                    'is_blocked': row[4]
                }
                for row in rows
            ]
        except Exception:

            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_post_creators_for_export(admin_ids: List[int], period: str = None) -> List[Dict]:
    """Post yaratgan foydalanuvchilarni eksport qilish."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            query = """
                SELECT DISTINCT u.user_id, u.nickname, u.username, u.language
                FROM users u
                INNER JOIN post_info p ON u.user_id = p.user_id
                WHERE u.user_id NOT IN (%s)
            """ % ','.join('%s' for _ in admin_ids)

            cursor.execute(query, admin_ids)
            rows = cursor.fetchall()
            return [
                {
                    'user_id': row[0],
                    'nickname': row[1],
                    'username': row[2],
                    'language': row[3]
                }
                for row in rows
            ]
        except Exception:

            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_user_settings_for_export(admin_ids: List[int], period: str = None) -> List[Dict]:
    """Foydalanuvchi sozlamalarini eksport qilish."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            query = """
                SELECT u.user_id, u.nickname, u.username, 
                       bs.ai_assistant_enabled
                FROM users u
                LEFT JOIN bot_settings bs ON u.user_id = bs.user_id
                WHERE u.user_id NOT IN (%s)
            """ % ','.join('%s' for _ in admin_ids)

            cursor.execute(query, admin_ids)
            rows = cursor.fetchall()
            return [
                {
                    'user_id': row[0],
                    'nickname': row[1],
                    'username': row[2],
                    'ai_assistant_enabled': row[3] or False
                }
                for row in rows
            ]
        except Exception:

            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def save_prompt(user_id: int, prompt_text: str) -> int | None:
    """Promptni saqlaydi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_prompts (user_id, prompt_text)
                VALUES (%s, %s) RETURNING id
            """, (user_id, prompt_text))
            prompt_id = cursor.fetchone()[0]
            conn.commit()
            return prompt_id
        except Exception:

            return None
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_user_prompts(user_id: int) -> List[Dict]:
    """Foydalanuvchi promptlarini oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, prompt_text, created_at 
                FROM ai_prompts WHERE user_id = %s 
                ORDER BY created_at DESC
            """, (user_id,))
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'prompt_text': row[1],
                    'created_at': row[2]
                }
                for row in rows
            ]
        except Exception:

            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def delete_prompt(prompt_id: int, user_id: int) -> bool:
    """Promptni o'chiradi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ai_prompts WHERE id = %s AND user_id = %s", (prompt_id, user_id))
            conn.commit()
            return True
        except Exception:

            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_prompt_by_id(prompt_id: int, user_id: int) -> Dict | None:
    """Promptni ID bo'yicha oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, prompt_text, created_at 
                FROM ai_prompts WHERE id = %s AND user_id = %s
            """, (prompt_id, user_id))
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'prompt_text': row[1],
                    'created_at': row[2]
                }
            return None
        except Exception:

            return None
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_language_stats(excluded_admin_ids: List[int] = None) -> dict:
    """Foydalanuvchilarning til statistikasini qaytaradi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            excluded_ids = excluded_admin_ids or []
            params: List[Any] = []
            where_parts = ["language IS NOT NULL"]
            if excluded_ids:
                where_parts.append("user_id NOT IN (" + ','.join(['%s'] * len(excluded_ids)) + ")")
                params.extend(excluded_ids)
            where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
            cursor.execute(f"SELECT language, COUNT(*) FROM users {where_sql} GROUP BY language", params)
            rows = cursor.fetchall()
            return {row[0]: int(row[1]) for row in rows}
        except Exception as e:
            logger.error(f"get_language_stats xatolik: {e}")
            return {}
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def get_total_errors_count() -> int:
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE error_text IS NOT NULL")
            row = cursor.fetchone()
            return int(row[0] or 0) if row else 0
        except Exception:

            return 0
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def init_db():
    """Bazani ishga tushirish uchun kerakli dastlabki ma'lumotlarni qo'shadi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS text_buttons (
                    id SERIAL PRIMARY KEY,
                    post_code TEXT,
                    button_type TEXT,
                    content_sub TEXT NOT NULL,
                    content_nonsub TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tashkent')
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_text_buttons_post_code 
                ON text_buttons(post_code)
            """)

            # Reaksiyalar (individual har bir foydalanuvchi uchun)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    message_id BIGINT NOT NULL,
                    reaction_emoji TEXT NOT NULL,
                    post_code TEXT,
                    button_index INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tashkent')
                )
            """)

            # Bot statistikasi (kunlik yangi va faol foydalanuvchilar)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_stats (
                    id SERIAL PRIMARY KEY,
                    stat_date DATE NOT NULL UNIQUE,
                    new_users INTEGER DEFAULT 0,
                    new_posts INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tashkent')
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bot_stats_date
                ON bot_stats(stat_date)
            """)

            conn.commit()
        except Exception:
            pass
        finally:
            if conn: release_connection(conn)
    await asyncio.to_thread(_sync)

async def record_bot_stat(stat_type: str):
    """Bot statistikasini yangilaydi (faqat yangi a'zolar)."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            if stat_type == "new":
                cursor.execute("""
                    INSERT INTO bot_stats (stat_date, new_users)
                    VALUES (CURRENT_DATE, 1)
                    ON CONFLICT (stat_date) DO UPDATE SET
                        new_users = bot_stats.new_users + 1
                """)
            
            conn.commit()
        except Exception as e:
            logger.error(f"record_bot_stat xatolik: {e}")
        finally:
            if conn: release_connection(conn)
    await asyncio.to_thread(_sync)


async def get_bot_stats(days: int = 30) -> dict:
    """Bot statistikasini qaytaradi (oxirgi N kun uchun)."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            from datetime import datetime, timezone, timedelta
            tashkent_offset = timedelta(hours=5)
            now_utc = datetime.now(timezone.utc)
            now_tashkent = now_utc.astimezone(timezone(tashkent_offset))
            
            # Bugun boshlanishi
            today_start = now_tashkent.replace(hour=0, minute=0, second=0, microsecond=0)
            # Hafta boshlanishi (dushanba)
            week_start = today_start - timedelta(days=today_start.weekday())
            # Oy boshlanishi
            month_start = today_start.replace(day=1)
            
            # Bugungi kun uchun stats (faqat yangi a'zolar va postlar)
            cursor.execute("""
                SELECT new_users, new_posts FROM bot_stats 
                WHERE stat_date = CURRENT_DATE
            """)
            today_row = cursor.fetchone()
            new_today = today_row[0] if today_row else 0
            posts_today = today_row[1] if today_row else 0
            
            # Shu hafta uchun stats
            cursor.execute("""
                SELECT COALESCE(SUM(new_users), 0), COALESCE(SUM(new_posts), 0) FROM bot_stats 
                WHERE stat_date >= %s
            """, (week_start.date(),))
            week_row = cursor.fetchone()
            new_week = week_row[0] if week_row else 0
            posts_week = week_row[1] if week_row else 0
            
            # Shu oy uchun stats
            cursor.execute("""
                SELECT COALESCE(SUM(new_users), 0), COALESCE(SUM(new_posts), 0) FROM bot_stats 
                WHERE stat_date >= %s
            """, (month_start.date(),))
            month_row = cursor.fetchone()
            new_month = month_row[0] if month_row else 0
            posts_month = month_row[1] if month_row else 0
            
            # Jami foydalanuvchilar (adminlarni chiqarib tashlaymiz)
            from xdata_handlers import config
            if config.ADMIN_IDS:
                admin_ids_str = ','.join(['%s'] * len(config.ADMIN_IDS))
                cursor.execute(f"SELECT COUNT(*) FROM users WHERE user_id NOT IN ({admin_ids_str})", config.ADMIN_IDS)
            else:
                cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0] or 0
            
            return {
                'total_users': total_users,
                'new_today': new_today,
                'new_week': new_week,
                'new_month': new_month,
                'posts_today': posts_today,
                'posts_week': posts_week,
                'posts_month': posts_month,
                'current_time': now_tashkent
            }
        except Exception as e:
            logger.error(f"get_bot_stats xatolik: {e}")
            return {
                'total_users': 0,
                'new_today': 0,
                'new_week': 0,
                'new_month': 0,
                'posts_today': 0,
                'posts_week': 0,
                'posts_month': 0,
                'current_time': None
            }
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)


# ============ AVTO IMZO FUNKSIYALARI (post_settings jadvalida) ============

def _parse_signature_value(signature_str: str | None) -> tuple[bool, str]:
    """Signature qiymatini parse qiladi. Format: 'TRUE|FALSE ["text"]'
    Returns: (enabled, text)
    """
    if not signature_str:
        return False, ''
    
    signature_str = signature_str.strip()
    
    # Agar FALSE bo'lsa
    if signature_str.startswith('FALSE'):
        # Matnni olish
        text_start = signature_str.find('"')
        text_end = signature_str.rfind('"')
        if text_start != -1 and text_end != -1 and text_start < text_end:
            text = signature_str[text_start+1:text_end]
            return False, text
        return False, ''
    
    # Agar TRUE bo'lsa
    if signature_str.startswith('TRUE'):
        text_start = signature_str.find('"')
        text_end = signature_str.rfind('"')
        if text_start != -1 and text_end != -1 and text_start < text_end:
            text = signature_str[text_start+1:text_end]
            return True, text
        return True, ''
    
    return False, ''


def _build_signature_value(enabled: bool, text: str) -> str:
    """Signature qiymatini yaratadi. Format: 'TRUE|FALSE "text"'"""
    status = 'TRUE' if enabled else 'FALSE'
    if text:
        return f'{status} "{text}"'
    return status


async def get_user_auto_signature(user_id: int) -> dict:
    """Foydalanuvchining avto imzo sozlamalarini qaytaradi (post_settings jadvalidan)."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT signature FROM post_settings WHERE user_id = %s",
                (user_id,)
            )
            result = cursor.fetchone()
            if result and result[0]:
                enabled, text = _parse_signature_value(result[0])
                return {
                    'enabled': enabled,
                    'text': text,
                    'position': 'bottom',
                    'newline': True
                }
            return {
                'enabled': False,
                'text': '',
                'position': 'bottom',
                'newline': True
            }
        except Exception as e:
            logger.error(f"get_user_auto_signature xatolik: {e}")
            return {
                'enabled': False,
                'text': '',
                'position': 'bottom',
                'newline': True
            }
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)


async def toggle_auto_signature(user_id: int) -> bool:
    """Avto imzoni yoqish/o'chirish. Yangi holatni qaytaradi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Avval hozirgi qiymatni olish
            cursor.execute(
                "SELECT signature FROM post_settings WHERE user_id = %s",
                (user_id,)
            )
            result = cursor.fetchone()
            
            if result and result[0]:
                enabled, text = _parse_signature_value(result[0])
                new_state = not enabled
                new_value = _build_signature_value(new_state, text)
            else:
                # Yangi yozuv - yoqilgan holatda
                new_state = True
                new_value = 'TRUE'
            
            cursor.execute("""
                INSERT INTO post_settings (user_id, signature)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    signature = EXCLUDED.signature,
                    updated_at = (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tashkent');
            """, (user_id, new_value))
            conn.commit()
            return new_state
        except Exception as e:
            logger.error(f"toggle_auto_signature xatolik: {e}")
            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)


async def update_auto_signature_text(user_id: int, text: str) -> bool:
    """Avto imzo matnini yangilash."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Avval hozirgi holatni olish
            cursor.execute(
                "SELECT signature FROM post_settings WHERE user_id = %s",
                (user_id,)
            )
            result = cursor.fetchone()
            
            if result and result[0]:
                enabled, _ = _parse_signature_value(result[0])
            else:
                enabled = False
            
            new_value = _build_signature_value(True, text)  # Always enable when saving new text
            
            cursor.execute("""
                INSERT INTO post_settings (user_id, signature)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    signature = EXCLUDED.signature,
                    updated_at = (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tashkent');
            """, (user_id, new_value))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"update_auto_signature_text xatolik: {e}")
            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)


# ============ POST STATISTIKASI FUNKSIYALARI ============

async def get_all_user_posts_for_stat(user_id: int) -> List[Dict]:
    """Foydalanuvchining barcha postlarini statistika uchun oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            admin_ids_placeholders = ','.join(['%s'] * len(config.ADMIN_IDS))
            cursor.execute(f"""
                SELECT p.post_code, p.post_name, p.message_id, p.error_message, u.user_id, u.nickname
                FROM post_info p
                INNER JOIN users u ON p.user_id = u.user_id
                WHERE u.user_id NOT IN ({admin_ids_placeholders})
            """, list(config.ADMIN_IDS))
            rows = cursor.fetchall()
            return [
                {
                    'post_code': row[0],
                    'post_name': row[1],
                    'message_id': row[2],
                    'error_message': row[3],
                    'user_id': row[4],
                    'nickname': row[5]
                }
                for row in rows
            ]
        except Exception:
            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)


async def get_all_posts_from_channel(channel_id: int) -> list:
    """Kanalning barcha postlarini oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT post_code, sent_at
                FROM send_posts 
                WHERE channel_id = %s
                ORDER BY sent_at DESC
            """, (channel_id,))
            
            rows = cursor.fetchall()
            return [
                {
                    'post_code': row[0],
                    'sent_at': row[1]
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"get_all_posts_from_channel xatolik: {e}")
            return []
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)

async def update_post_statistics(post_code: str, views: int = None, forwards: int = None, button_clicks: int = None) -> bool:
    """Post statistikasini yangilaydi (views, forwards, button_clicks)."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Faqat berilgan qiymatlarni yangilaymiz
            updates = []
            params = []
            
            if views is not None:
                updates.append("views = %s")
                params.append(views)
            
            if forwards is not None:
                updates.append("forward_count = %s")
                params.append(forwards)
            
            if button_clicks is not None:
                updates.append("button_clicks = %s")
                params.append(button_clicks)
            
            if updates:
                params.append(post_code)
                query = f"UPDATE send_posts SET {', '.join(updates)} WHERE post_code = %s"
                cursor.execute(query, params)
                conn.commit()
            
            return True
        except Exception as e:
            logger.error(f"update_post_statistics xatolik: {e}")
            return False
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)


async def get_post_statistics(post_code: str) -> Dict | None:
    """Post statistikasini oladi."""
    def _sync():
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT views, forward_count, button_clicks 
                FROM send_posts WHERE post_code = %s
            """, (post_code,))
            result = cursor.fetchone()
            if result:
                return {
                    'views': result[0] or 0,
                    'forward_count': result[1] or 0,
                    'button_clicks': result[2] or 0
                }
            return None
        except Exception:
            return None
        finally:
            if conn: release_connection(conn)
    return await asyncio.to_thread(_sync)