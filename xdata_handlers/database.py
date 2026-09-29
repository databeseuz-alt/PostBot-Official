import os
import json
import secrets
import string
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from dotenv import dotenv_values
from supabase import create_client, Client

from xdata_handlers import config

logger = logging.getLogger(__name__)

import time

TASHKENT_TZ = timezone(timedelta(hours=5))

_supabase_client: Optional[Client] = None

# ==================== TEZKOR KESHLASH (IN-MEMORY CACHE) ====================
_user_lang_cache: Dict[int, str] = {}
_blocked_users_cache: Optional[set] = None
_blocked_cache_time: float = 0
_user_activity_cache: Dict[int, float] = {}
_user_channels_cache: Dict[int, tuple[float, List[Dict]]] = {}
_req_channels_cache: Optional[tuple[float, List[Dict]]] = None
_user_signature_cache: Dict[int, tuple[float, dict]] = {}
_posts_cache: Dict[str, tuple[float, dict]] = {}

def get_now() -> datetime:
    """Hozirgi vaqtni har doim Toshkent vaqti bilan qaytaradi."""
    return datetime.now(TASHKENT_TZ)

def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
            if os.path.exists(dotenv_path):
                values = dotenv_values(dotenv_path, interpolate=False)
                url = url or values.get("SUPABASE_URL")
                key = key or values.get("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL yoki SUPABASE_KEY topilmadi! .env faylini tekshiring.")
        _supabase_client = create_client(url, key)
    return _supabase_client

# Dummy compatibility functions for psycopg2 connection
def _get_database_url() -> str | None:
    return None

def _get_connection_pool():
    return None

def get_connection():
    return None

def release_connection(conn):
    pass

def _normalize_language(language: str | None) -> str:
    """Til kodini normalize qiladi."""
    if not language:
        return 'uzl'
    language = language.lower().strip()
    if language == 'uz':
        return 'uzl'
    return language

# ==================== FOYDALANUVCHILAR ====================

async def set_user_language(user_id: int, nickname: str = None, username: str = None, language: str = 'uzl') -> bool:
    """Foydalanuvchi tilini o'rnatadi."""
    language = _normalize_language(language)
    _user_lang_cache[user_id] = language
    def _sync():
        try:
            sp = get_supabase()
            data = {
                'user_id': user_id,
                'language': language,
                'last_activity': get_now().isoformat()
            }
            if nickname is not None:
                data['nickname'] = nickname
            if username is not None:
                data['username'] = username
            sp.table('users').upsert(data, on_conflict='user_id').execute()
            return True
        except Exception as e:
            logger.error(f"set_user_language error: {e}")
            return False
    return await asyncio.to_thread(_sync)

async def get_user_language(user_id: int) -> str:
    """Foydalanuvchi tilini oladi (kesh orqali bir lahzada qaytadi)."""
    if user_id in _user_lang_cache:
        return _user_lang_cache[user_id]

    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('users').select('language').eq('user_id', user_id).execute()
            if res.data and res.data[0].get('language'):
                return _normalize_language(res.data[0]['language'])
            return 'uzl'
        except Exception as e:
            logger.error(f"get_user_language error: {e}")
            return 'uzl'

    lang = await asyncio.to_thread(_sync)
    _user_lang_cache[user_id] = lang
    return lang

async def add_or_update_user(user_id: int, nickname: str = None, username: str = None, language: str = None):
    """Foydalanuvchini bazaga qo'shadi yoki ma'lumotlarini yangilaydi (kesh va throttle bilan)."""
    if config.ADMIN_IDS and user_id in config.ADMIN_IDS:
        return
    now = time.time()
    last_updated = _user_activity_cache.get(user_id, 0)
    # Agar foydalanuvchi so'nggi 5 daqiqa (300 soniya) ichida yangilangan bo'lsa va til berilmagan bo'lsa, qayta yozmaymiz
    if language is None and (now - last_updated < 300):
        return

    _user_activity_cache[user_id] = now
    if language:
        _user_lang_cache[user_id] = _normalize_language(language)

    return await _add_or_update_user_impl(user_id=user_id, nickname=nickname, username=username, language=language)

async def _add_or_update_user_impl(user_id: int, nickname: str = None, username: str = None, language: str = None):
    def _sync():
        try:
            sp = get_supabase()
            now_iso = get_now().isoformat()
            # Foydalanuvchi borligini tekshirish
            res = sp.table('users').select('user_id, language').eq('user_id', user_id).execute()
            is_new = len(res.data) == 0
            
            payload = {
                'user_id': user_id,
                'last_activity': now_iso
            }
            if nickname: payload['nickname'] = nickname
            if username: payload['username'] = username
            if language: 
                payload['language'] = _normalize_language(language)
            elif is_new:
                payload['language'] = 'uzl'
                
            if is_new:
                payload['join_date'] = now_iso
                payload['is_blocked'] = 0
                
            sp.table('users').upsert(payload, on_conflict='user_id').execute()
            return is_new
        except Exception as e:
            logger.error(f"add_or_update_user error: {e}")
            return False
    return await asyncio.to_thread(_sync)

async def get_all_active_users(admin_ids: List[int] = None) -> List[int]:
    """Barcha bloklanmagan faol foydalanuvchilar IDlari."""
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('users').select('user_id').eq('is_blocked', 0).execute()
            excluded = set(admin_ids or [])
            return [row['user_id'] for row in res.data if row.get('user_id') not in excluded]
        except Exception as e:
            logger.error(f"get_all_active_users error: {e}")
            return []
    return await asyncio.to_thread(_sync)

async def get_blocked_users_with_info(admin_ids: List[int] = None) -> List[Dict]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('users').select('user_id, nickname, username').eq('is_blocked', 1).execute()
            excluded = set(admin_ids or [])
            return [
                {
                    'user_id': row['user_id'],
                    'nickname': row.get('nickname') or '',
                    'username': row.get('username') or ''
                }
                for row in res.data if row.get('user_id') not in excluded
            ]
        except Exception as e:
            logger.error(f"get_blocked_users_with_info error: {e}")
            return []
    return await asyncio.to_thread(_sync)

async def _refresh_blocked_cache_if_needed():
    global _blocked_users_cache, _blocked_cache_time
    now = time.time()
    if _blocked_users_cache is None or (now - _blocked_cache_time > 60):
        def _sync():
            try:
                sp = get_supabase()
                res = sp.table('users').select('user_id').eq('is_blocked', 1).execute()
                return {row['user_id'] for row in res.data} if res.data else set()
            except Exception as e:
                logger.error(f"refresh_blocked_cache error: {e}")
                return set()
        _blocked_users_cache = await asyncio.to_thread(_sync)
        _blocked_cache_time = now

async def is_user_blocked(user_id: int) -> bool:
    global _blocked_users_cache
    if _blocked_users_cache is None:
        await _refresh_blocked_cache_if_needed()
    return user_id in _blocked_users_cache if _blocked_users_cache is not None else False

async def block_user(user_id: int) -> bool:
    global _blocked_users_cache
    if _blocked_users_cache is not None:
        _blocked_users_cache.add(user_id)
    def _sync():
        try:
            sp = get_supabase()
            sp.table('users').update({'is_blocked': 1}).eq('user_id', user_id).execute()
            return True
        except Exception as e:
            logger.error(f"block_user error: {e}")
            return False
    return await asyncio.to_thread(_sync)

async def unblock_user(user_id: int) -> bool:
    global _blocked_users_cache
    if _blocked_users_cache is not None:
        _blocked_users_cache.discard(user_id)
    def _sync():
        try:
            sp = get_supabase()
            sp.table('users').update({'is_blocked': 0}).eq('user_id', user_id).execute()
            return True
        except Exception as e:
            logger.error(f"unblock_user error: {e}")
            return False
    return await asyncio.to_thread(_sync)

async def get_user_info_from_db(user_id: int) -> Optional[Dict]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('users').select('*').eq('user_id', user_id).execute()
            if res.data:
                row = res.data[0]
                return {
                    'user_id': row['user_id'],
                    'nickname': row.get('nickname') or '',
                    'username': row.get('username'),
                    'language': row.get('language') or 'uzl',
                    'is_blocked': bool(row.get('is_blocked')),
                    'join_date': row.get('join_date'),
                    'last_activity': row.get('last_activity')
                }
            return None
        except Exception as e:
            logger.error(f"get_user_info_from_db error: {e}")
            return None
    return await asyncio.to_thread(_sync)

async def find_user_by_id_or_username(query: str):
    def _sync():
        try:
            sp = get_supabase()
            q = query.strip().lstrip('@')
            if q.isdigit():
                res = sp.table('users').select('*').eq('user_id', int(q)).execute()
                if res.data: return res.data[0]
            res = sp.table('users').select('*').ilike('username', f"%{q}%").limit(1).execute()
            if res.data: return res.data[0]
            return None
        except Exception:
            return None
    return await asyncio.to_thread(_sync)

async def get_user_block_info(user_id: int):
    info = await get_user_info_from_db(user_id)
    if info:
        return {
            'is_blocked': info.get('is_blocked', False),
            'join_date': info.get('join_date'),
            'last_activity': info.get('last_activity')
        }
    return None

# ==================== KANALLAR ====================

async def add_user_channel(user_id: int, channel_id: int, channel_name: str, send_posts: bool = False) -> bool:
    _user_channels_cache.pop(user_id, None)
    def _sync():
        try:
            sp = get_supabase()
            sp.table('channels').upsert({
                'user_id': user_id,
                'channel_id': channel_id,
                'channel_name': channel_name,
                'send_posts': send_posts,
                'recorded_at': get_now().isoformat()
            }, on_conflict='user_id,channel_id').execute()
            return True
        except Exception as e:
            logger.error(f"add_user_channel error: {e}")
            return False
    return await asyncio.to_thread(_sync)

async def get_user_channels(user_id: int) -> List[Dict]:
    now = time.time()
    if user_id in _user_channels_cache:
        cached_time, data = _user_channels_cache[user_id]
        if now - cached_time < 30: # 30 soniyalik tezkor kesh
            return data

    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('channels').select('channel_id, channel_name, send_posts, recorded_at').eq('user_id', user_id).execute()
            return [
                {
                    'channel_id': row['channel_id'],
                    'channel_name': row.get('channel_name') or 'Nomsiz kanal',
                    'send_posts': row.get('send_posts', False),
                    'recorded_at': row.get('recorded_at')
                }
                for row in res.data
            ]
        except Exception as e:
            logger.error(f"get_user_channels error: {e}")
            return []

    channels = await asyncio.to_thread(_sync)
    _user_channels_cache[user_id] = (now, channels)
    return channels

async def get_channel_name(user_id: int, channel_id: int) -> Optional[str]:
    # Avval keshdan qidirish
    if user_id in _user_channels_cache:
        _, ch_list = _user_channels_cache[user_id]
        for ch in ch_list:
            if ch['channel_id'] == channel_id:
                return ch.get('channel_name')

    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('channels').select('channel_name').eq('user_id', user_id).eq('channel_id', channel_id).execute()
            if res.data:
                return res.data[0].get('channel_name')
            return None
        except Exception:
            return None
    return await asyncio.to_thread(_sync)

async def remove_user_channel(user_id: int, channel_id: int) -> bool:
    _user_channels_cache.pop(user_id, None)
    def _sync():
        try:
            sp = get_supabase()
            sp.table('channels').delete().eq('user_id', user_id).eq('channel_id', channel_id).execute()
            return True
        except Exception as e:
            logger.error(f"remove_user_channel error: {e}")
            return False
    return await asyncio.to_thread(_sync)

async def update_channel_post_code(user_id: int, channel_id: int, post_code: str = None) -> bool:
    _user_channels_cache.pop(user_id, None)
    def _sync():
        try:
            sp = get_supabase()
            sp.table('channels').update({'send_posts': True}).eq('user_id', user_id).eq('channel_id', channel_id).execute()
            return True
        except Exception:
            return False
    return await asyncio.to_thread(_sync)

async def get_user_channel_statistics(user_id: int, channel_id: int = None) -> Dict:
    def _sync():
        try:
            sp = get_supabase()
            query = sp.table('send_posts').select('*', count='exact').eq('user_id', user_id)
            if channel_id:
                query = query.eq('channel_id', channel_id)
            res = query.execute()
            total = res.count or len(res.data)
            return {'total_posts': total}
        except Exception:
            return {'total_posts': 0}
    return await asyncio.to_thread(_sync)

# ==================== MAJBURIY OBUNA KANALLARI (REQ_CHANNELS) ====================

async def get_all_required_channels() -> List[Dict]:
    global _req_channels_cache
    now = time.time()
    if _req_channels_cache is not None:
        cached_time, data = _req_channels_cache
        if now - cached_time < 60: # 60 soniya kesh
            return data

    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('req_channels').select('*').execute()
            return [
                {
                    'id': row['channel_id'],
                    'channel_id': row['channel_id'],
                    'title': row.get('channel_name') or 'Kanal',
                    'name': row.get('channel_name') or 'Kanal',
                    'username': row.get('username')
                }
                for row in res.data
            ]
        except Exception as e:
            logger.error(f"get_all_required_channels error: {e}")
            return []

    channels = await asyncio.to_thread(_sync)
    _req_channels_cache = (now, channels)
    return channels

async def get_required_channels() -> List[Dict]:
    return await get_all_required_channels()

async def add_required_channel(channel_id: int, channel_name: str, username: str = None) -> bool:
    global _req_channels_cache
    _req_channels_cache = None
    def _sync():
        try:
            sp = get_supabase()
            sp.table('req_channels').upsert({
                'channel_id': channel_id,
                'channel_name': channel_name,
                'username': username
            }, on_conflict='channel_id').execute()
            return True
        except Exception as e:
            logger.error(f"add_required_channel error: {e}")
            return False
    return await asyncio.to_thread(_sync)

async def remove_required_channel(channel_id: int) -> bool:
    global _req_channels_cache
    _req_channels_cache = None
    def _sync():
        try:
            sp = get_supabase()
            sp.table('req_channels').delete().eq('channel_id', channel_id).execute()
            return True
        except Exception as e:
            logger.error(f"remove_required_channel error: {e}")
            return False
    return await asyncio.to_thread(_sync)

# ==================== POST MANAGEMENT (POST_INFO) ====================

def generate_post_code(length: int = 6) -> str:
    """Unikal post kodi generatsiya qiladi."""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))

async def add_post_to_db(user_id: int, post_data: dict, buttons_matrix: list = None, post_name: str = None, admin_ids: List[int] = None) -> str | None:
    def _sync():
        try:
            sp = get_supabase()
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
                
            sp.table('post_info').insert({
                'post_code': post_code,
                'user_id': user_id,
                'full_post_data': full_post_data,
                'post_name': post_name,
                'created_at': get_now().isoformat()
            }).execute()
            
            return post_code, full_post_data
        except Exception as e:
            logger.error(f"add_post_to_db error: {e}")
            return None, None

    res = await asyncio.to_thread(_sync)
    if res and res[0]:
        post_code, full_post_data = res
        _posts_cache[post_code] = (time.time(), full_post_data)
        return post_code
    return None

async def get_post_from_db(post_code: str) -> dict | None:
    now = time.time()
    if post_code in _posts_cache:
        cached_time, post_data = _posts_cache[post_code]
        if now - cached_time < 300: # 5 daqiqa kesh
            return post_data

    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('post_info').select('full_post_data').eq('post_code', post_code).execute()
            if res.data:
                data = res.data[0]['full_post_data']
                if isinstance(data, str):
                    return json.loads(data)
                return data
            return None
        except Exception as e:
            logger.error(f"get_post_from_db error: {e}")
            return None

    data = await asyncio.to_thread(_sync)
    if data:
        _posts_cache[post_code] = (now, data)
    return data

async def check_post_owner(post_code: str, user_id: int) -> bool:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('post_info').select('user_id').eq('post_code', post_code).execute()
            if res.data:
                return res.data[0]['user_id'] == user_id
            return False
        except Exception:
            return False
    return await asyncio.to_thread(_sync)

async def get_post_name(post_code: str) -> str | None:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('post_info').select('post_name').eq('post_code', post_code).execute()
            if res.data:
                return res.data[0].get('post_name')
            return None
        except Exception:
            return None
    return await asyncio.to_thread(_sync)

async def save_post_name(post_code: str, post_name: str) -> bool:
    def _sync():
        try:
            sp = get_supabase()
            sp.table('post_info').update({'post_name': post_name}).eq('post_code', post_code).execute()
            return True
        except Exception:
            return False
    return await asyncio.to_thread(_sync)

async def unsave_post_name(post_code: str, user_id: int = None) -> bool:
    def _sync():
        try:
            sp = get_supabase()
            q = sp.table('post_info').update({'post_name': None}).eq('post_code', post_code)
            if user_id:
                q = q.eq('user_id', user_id)
            q.execute()
            return True
        except Exception:
            return False
    return await asyncio.to_thread(_sync)

async def update_post_in_db(post_code: str, post_data: dict, buttons_matrix: list = None, post_name: str = None) -> bool:
    def _sync():
        try:
            sp = get_supabase()
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
            update_dict = {'full_post_data': full_post_data}
            if post_name is not None:
                update_dict['post_name'] = post_name
            sp.table('post_info').update(update_dict).eq('post_code', post_code).execute()
            return True
        except Exception as e:
            logger.error(f"update_post_in_db error: {e}")
            return False
    return await asyncio.to_thread(_sync)

async def update_post_message_id(post_code: str, message_id: int) -> bool:
    def _sync():
        try:
            sp = get_supabase()
            sp.table('post_info').update({'message_id': message_id}).eq('post_code', post_code).execute()
            return True
        except Exception:
            return False
    return await asyncio.to_thread(_sync)

async def update_post_error(post_code: str, error_message: str) -> bool:
    def _sync():
        try:
            sp = get_supabase()
            sp.table('post_info').update({'error_message': error_message}).eq('post_code', post_code).execute()
            return True
        except Exception:
            return False
    return await asyncio.to_thread(_sync)

async def update_post_print_settings(post_code: str, print_settings: dict) -> bool:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('post_info').select('full_post_data').eq('post_code', post_code).execute()
            if not res.data:
                return False
            data = res.data[0]['full_post_data'] or {}
            if isinstance(data, str):
                data = json.loads(data)
            if 'print_settings' not in data:
                data['print_settings'] = {}
            data['print_settings'].update(print_settings)
            sp.table('post_info').update({'full_post_data': data}).eq('post_code', post_code).execute()
            return True
        except Exception as e:
            logger.error(f"update_post_print_settings error: {e}")
            return False
    return await asyncio.to_thread(_sync)

async def get_posts_by_user(user_id: int) -> list:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('post_info').select('post_code, post_name').eq('user_id', user_id).order('created_at', desc=True).execute()
            return [{"code": r['post_code'], "name": r.get('post_name') or "Nomsiz post"} for r in res.data]
        except Exception as e:
            logger.error(f"get_posts_by_user error: {e}")
            return []
    return await asyncio.to_thread(_sync)

async def get_user_posts(user_id: int) -> list:
    return await get_posts_by_user(user_id)

# ==================== AUTO SIGNATURE & SETTINGS (POST_SETTINGS) ====================

def _parse_signature_value(signature_str: str) -> tuple[bool, str]:
    if not signature_str:
        return False, ''
    if signature_str.startswith('TRUE'):
        text_start = signature_str.find('"')
        text_end = signature_str.rfind('"')
        if text_start != -1 and text_end != -1 and text_start < text_end:
            return True, signature_str[text_start+1:text_end]
        return True, ''
    return False, ''

def _build_signature_value(enabled: bool, text: str) -> str:
    status = 'TRUE' if enabled else 'FALSE'
    if text:
        return f'{status} "{text}"'
    return status

async def get_user_auto_signature(user_id: int) -> dict:
    now = time.time()
    if user_id in _user_signature_cache:
        cached_time, sig = _user_signature_cache[user_id]
        if now - cached_time < 60: # 60 soniya kesh
            return sig

    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('post_settings').select('signature').eq('user_id', user_id).execute()
            if res.data and res.data[0].get('signature'):
                enabled, text = _parse_signature_value(res.data[0]['signature'])
                return {'enabled': enabled, 'text': text, 'position': 'bottom', 'newline': True}
            return {'enabled': False, 'text': '', 'position': 'bottom', 'newline': True}
        except Exception as e:
            logger.error(f"get_user_auto_signature error: {e}")
            return {'enabled': False, 'text': '', 'position': 'bottom', 'newline': True}

    sig = await asyncio.to_thread(_sync)
    _user_signature_cache[user_id] = (now, sig)
    return sig

async def toggle_auto_signature(user_id: int) -> bool:
    _user_signature_cache.pop(user_id, None)
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('post_settings').select('signature').eq('user_id', user_id).execute()
            if res.data and res.data[0].get('signature'):
                enabled, text = _parse_signature_value(res.data[0]['signature'])
                new_state = not enabled
                new_val = _build_signature_value(new_state, text)
            else:
                new_state = True
                new_val = 'TRUE'
            sp.table('post_settings').upsert({
                'user_id': user_id,
                'signature': new_val,
                'updated_at': get_now().isoformat()
            }, on_conflict='user_id').execute()
            return new_state
        except Exception as e:
            logger.error(f"toggle_auto_signature error: {e}")
            return False
    return await asyncio.to_thread(_sync)

async def update_auto_signature_text(user_id: int, text: str) -> bool:
    _user_signature_cache.pop(user_id, None)
    def _sync():
        try:
            sp = get_supabase()
            new_val = _build_signature_value(True, text)
            sp.table('post_settings').upsert({
                'user_id': user_id,
                'signature': new_val,
                'updated_at': get_now().isoformat()
            }, on_conflict='user_id').execute()
            return True
        except Exception as e:
            logger.error(f"update_auto_signature_text error: {e}")
            return False
    return await asyncio.to_thread(_sync)

async def get_user_post_settings(user_id: int) -> Dict:
    sig = await get_user_auto_signature(user_id)
    return {'auto_signature': sig}

async def update_user_post_settings(user_id: int, settings: dict) -> bool:
    return True

# ==================== BOT SETTINGS (BOT_SETTINGS) ====================

async def get_user_bot_settings(user_id: int) -> Dict:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('bot_settings').select('*').eq('user_id', user_id).execute()
            if res.data:
                row = res.data[0]
                return {
                    'ai_assistant_enabled': bool(row.get('ai_assistant_enabled', False)),
                    'interface_settings': row.get('interface_settings') or {},
                    'timezone': row.get('timezone') or 'Asia/Tashkent'
                }
            return {'ai_assistant_enabled': False, 'interface_settings': {}, 'timezone': 'Asia/Tashkent'}
        except Exception:
            return {'ai_assistant_enabled': False, 'interface_settings': {}, 'timezone': 'Asia/Tashkent'}
    return await asyncio.to_thread(_sync)

async def update_user_bot_settings(user_id: int, settings: dict = None) -> bool:
    def _sync():
        try:
            sp = get_supabase()
            data = {'user_id': user_id}
            if settings:
                if 'ai_assistant_enabled' in settings:
                    data['ai_assistant_enabled'] = settings['ai_assistant_enabled']
                if 'interface_settings' in settings:
                    data['interface_settings'] = settings['interface_settings']
                if 'timezone' in settings:
                    data['timezone'] = settings['timezone']
            sp.table('bot_settings').upsert(data, on_conflict='user_id').execute()
            return True
        except Exception:
            return False
    return await asyncio.to_thread(_sync)

async def set_user_timezone(user_id: int, timezone_str: str) -> bool:
    def _sync():
        try:
            sp = get_supabase()
            sp.table('bot_settings').upsert({
                'user_id': user_id,
                'timezone': timezone_str
            }, on_conflict='user_id').execute()
            return True
        except Exception:
            return False
    return await asyncio.to_thread(_sync)

# ==================== KANALLAR TO'PLAMI (CHANNEL BUNDLES) ====================

async def get_user_channel_bundles(user_id: int) -> List[Dict]:
    """Foydalanuvchining barcha kanallar to'plamini qaytaradi."""
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('bot_settings').select('interface_settings').eq('user_id', user_id).execute()
            if not res.data:
                return []
            interface_settings = res.data[0].get('interface_settings') or {}
            return interface_settings.get('channel_bundles') or []
        except Exception as e:
            logger.error(f"get_user_channel_bundles error: {e}")
            return []
    return await asyncio.to_thread(_sync)

async def get_user_channel_bundle_by_id(user_id: int, bundle_id: str) -> Optional[Dict]:
    """ID bo'yicha bitta to'plamni qaytaradi."""
    bundles = await get_user_channel_bundles(user_id)
    for b in bundles:
        if b.get('id') == bundle_id:
            return b
    return None

async def save_user_channel_bundle(user_id: int, bundle_name: str, channel_ids: List[int], bundle_id: str = None) -> Optional[Dict]:
    """To'plamni yaratadi yoki yangilaydi."""
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('bot_settings').select('interface_settings').eq('user_id', user_id).execute()
            interface_settings = {}
            if res.data:
                interface_settings = res.data[0].get('interface_settings') or {}
            bundles = interface_settings.get('channel_bundles') or []

            nonlocal bundle_id
            if not bundle_id:
                bundle_id = f"bnd_{secrets.token_hex(4)}"
                new_bundle = {
                    'id': bundle_id,
                    'name': bundle_name.strip(),
                    'channel_ids': channel_ids,
                    'created_at': datetime.now().isoformat()
                }
                bundles.append(new_bundle)
            else:
                updated = False
                for b in bundles:
                    if b.get('id') == bundle_id:
                        b['name'] = bundle_name.strip()
                        b['channel_ids'] = channel_ids
                        updated = True
                        break
                if not updated:
                    new_bundle = {
                        'id': bundle_id,
                        'name': bundle_name.strip(),
                        'channel_ids': channel_ids,
                        'created_at': datetime.now().isoformat()
                    }
                    bundles.append(new_bundle)

            interface_settings['channel_bundles'] = bundles
            sp.table('bot_settings').upsert({
                'user_id': user_id,
                'interface_settings': interface_settings
            }, on_conflict='user_id').execute()

            return next((b for b in bundles if b.get('id') == bundle_id), None)
        except Exception as e:
            logger.error(f"save_user_channel_bundle error: {e}")
            return None
    return await asyncio.to_thread(_sync)

async def delete_user_channel_bundle(user_id: int, bundle_id: str) -> bool:
    """To'plamni o'chiradi."""
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('bot_settings').select('interface_settings').eq('user_id', user_id).execute()
            if not res.data:
                return False
            interface_settings = res.data[0].get('interface_settings') or {}
            bundles = interface_settings.get('channel_bundles') or []
            new_bundles = [b for b in bundles if b.get('id') != bundle_id]
            interface_settings['channel_bundles'] = new_bundles
            sp.table('bot_settings').upsert({
                'user_id': user_id,
                'interface_settings': interface_settings
            }, on_conflict='user_id').execute()
            return True
        except Exception as e:
            logger.error(f"delete_user_channel_bundle error: {e}")
            return False
    return await asyncio.to_thread(_sync)

async def remove_channel_from_bundle(user_id: int, bundle_id: str, channel_id: int) -> bool:
    """To'plamdan bitta kanalni chiqarib tashlaydi."""
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('bot_settings').select('interface_settings').eq('user_id', user_id).execute()
            if not res.data:
                return False
            interface_settings = res.data[0].get('interface_settings') or {}
            bundles = interface_settings.get('channel_bundles') or []
            updated = False
            for b in bundles:
                if b.get('id') == bundle_id:
                    ch_ids = list(b.get('channel_ids', []))
                    if channel_id in ch_ids:
                        ch_ids.remove(channel_id)
                        b['channel_ids'] = ch_ids
                        updated = True
                    break
            if updated:
                interface_settings['channel_bundles'] = bundles
                sp.table('bot_settings').upsert({
                    'user_id': user_id,
                    'interface_settings': interface_settings
                }, on_conflict='user_id').execute()
                return True
            return False
        except Exception as e:
            logger.error(f"remove_channel_from_bundle error: {e}")
            return False
    return await asyncio.to_thread(_sync)

async def rename_user_channel_bundle(user_id: int, bundle_id: str, new_name: str) -> bool:
    """To'plam nomini o'zgartiradi."""
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('bot_settings').select('interface_settings').eq('user_id', user_id).execute()
            if not res.data:
                return False
            interface_settings = res.data[0].get('interface_settings') or {}
            bundles = interface_settings.get('channel_bundles') or []
            updated = False
            for b in bundles:
                if b.get('id') == bundle_id:
                    b['name'] = new_name.strip()
                    updated = True
                    break
            if updated:
                interface_settings['channel_bundles'] = bundles
                sp.table('bot_settings').upsert({
                    'user_id': user_id,
                    'interface_settings': interface_settings
                }, on_conflict='user_id').execute()
                return True
            return False
        except Exception as e:
            logger.error(f"rename_user_channel_bundle error: {e}")
            return False
    return await asyncio.to_thread(_sync)

async def clone_shared_bundle_to_user(user_id: int, owner_id: int, bundle_id: str) -> Optional[Dict]:
    """Boshqa foydalanuvchi ulashgan to'plamni o'z profiliga nusxalaydi."""
    source_bundle = await get_user_channel_bundle_by_id(owner_id, bundle_id)
    if not source_bundle:
        return None
    new_name = source_bundle.get('name', "Ulashilgan to'plam")
    channel_ids = list(source_bundle.get('channel_ids', []))
    return await save_user_channel_bundle(user_id, new_name, channel_ids)


# ==================== SCHEDULED & SENT POSTS (SEND_POSTS) ====================

async def add_scheduled_post(user_id: int, post_code: str, scheduled_time: datetime, channel_id: int, channel_name: str, repeat_interval: str = None) -> Optional[int]:
    def _sync():
        try:
            sp = get_supabase()
            time_iso = scheduled_time.isoformat() if isinstance(scheduled_time, datetime) else str(scheduled_time)
            res = sp.table('send_posts').insert({
                'user_id': user_id,
                'post_code': post_code,
                'channel_id': channel_id,
                'channel_name': channel_name,
                'schedule_time': time_iso,
                'status': 'pending',
                'created_at': get_now().isoformat()
            }).execute()
            if res.data:
                return res.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"add_scheduled_post error: {e}")
            return None
    return await asyncio.to_thread(_sync)

async def save_sent_post(post_code: str, user_id: int, channel_id: int, channel_name: str, message_id: int = None) -> bool:
    def _sync():
        try:
            sp = get_supabase()
            now_iso = get_now().isoformat()
            sp.table('send_posts').insert({
                'user_id': user_id,
                'post_code': post_code,
                'channel_id': channel_id,
                'channel_name': channel_name,
                'message_id': message_id,
                'status': 'sent',
                'sent_at': now_iso,
                'created_at': now_iso
            }).execute()
            return True
        except Exception as e:
            logger.error(f"save_sent_post error: {e}")
            return False
    return await asyncio.to_thread(_sync)

async def get_scheduled_posts() -> List[Dict]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('send_posts').select('*').eq('status', 'pending').execute()
            return res.data or []
        except Exception:
            return []
    return await asyncio.to_thread(_sync)

async def get_all_pending_scheduled_posts() -> List[Dict]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('send_posts').select('*').eq('status', 'pending').order('schedule_time', desc=False).execute()
            return res.data or []
        except Exception:
            return []
    return await asyncio.to_thread(_sync)

async def get_user_scheduled_posts(user_id: int) -> List[Dict]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('send_posts').select('*').eq('user_id', user_id).eq('status', 'pending').order('schedule_time', desc=False).execute()
            return res.data or []
        except Exception:
            return []
    return await asyncio.to_thread(_sync)

async def get_scheduled_post_by_id(post_id: int, user_id: int) -> Optional[Dict]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('send_posts').select('*').eq('id', post_id).eq('user_id', user_id).execute()
            return res.data[0] if res.data else None
        except Exception:
            return None
    return await asyncio.to_thread(_sync)

async def cancel_scheduled_post(post_id: int, user_id: int) -> bool:
    def _sync():
        try:
            sp = get_supabase()
            sp.table('send_posts').delete().eq('id', post_id).eq('user_id', user_id).execute()
            return True
        except Exception:
            return False
    return await asyncio.to_thread(_sync)

async def reschedule_scheduled_post(post_id: int, user_id: int, new_time: datetime) -> bool:
    def _sync():
        try:
            sp = get_supabase()
            time_iso = new_time.isoformat() if isinstance(new_time, datetime) else str(new_time)
            sp.table('send_posts').update({'schedule_time': time_iso}).eq('id', post_id).eq('user_id', user_id).execute()
            return True
        except Exception:
            return False
    return await asyncio.to_thread(_sync)

async def mark_scheduled_post_as_sent(post_id: int) -> bool:
    def _sync():
        try:
            sp = get_supabase()
            sp.table('send_posts').update({
                'status': 'sent',
                'sent_at': get_now().isoformat()
            }).eq('id', post_id).execute()
            return True
        except Exception:
            return False
    return await asyncio.to_thread(_sync)

async def get_user_sent_posts(user_id: int) -> List[Dict]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('send_posts').select('*').eq('user_id', user_id).eq('status', 'sent').order('sent_at', desc=True).execute()
            return res.data or []
        except Exception:
            return []
    return await asyncio.to_thread(_sync)

async def get_pending_scheduled_posts() -> List[Dict]:
    return await get_all_pending_scheduled_posts()

async def set_post_repeat_interval(post_id: int, user_id: int, repeat_interval: str) -> bool:
    return True

async def add_next_recurring_post(post_code: str, user_id: int, channel_id: int, channel_name: str, next_time: datetime, repeat_interval: str):
    return await add_scheduled_post(user_id, post_code, next_time, channel_id, channel_name, repeat_interval)

# ==================== REAKSIONLAR (REACTIONS) ====================

async def add_reaction(button_index: int, reaction_emoji: str, user_id: int, chat_id: int, message_id: int) -> bool:
    return await add_or_update_reaction(button_index, reaction_emoji, user_id, chat_id, message_id)

async def add_or_update_reaction(button_index: int, reaction_emoji: str, user_id: int, chat_id: int, message_id: int) -> bool:
    def _sync():
        try:
            sp = get_supabase()
            sp.table('reactions').upsert({
                'button_index': button_index,
                'reaction_emoji': reaction_emoji,
                'user_id': user_id,
                'chat_id': chat_id,
                'message_id': message_id
            }).execute()
            return True
        except Exception:
            return False
    return await asyncio.to_thread(_sync)

async def add_or_update_reaction_by_chat_message(chat_id: int, message_id: int, user_id: int, reaction_emoji: str) -> bool:
    return await add_or_update_reaction(0, reaction_emoji, user_id, chat_id, message_id)

async def get_post_reactions(chat_id: int, message_id: int) -> List[Dict]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('reactions').select('*').eq('chat_id', chat_id).eq('message_id', message_id).execute()
            return res.data or []
        except Exception:
            return []
    return await asyncio.to_thread(_sync)

async def get_reaction_count(chat_id: int, message_id: int, button_index: int) -> int:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('reactions').select('user_id', count='exact').eq('chat_id', chat_id).eq('message_id', message_id).eq('button_index', button_index).execute()
            return res.count or len(res.data)
        except Exception:
            return 0
    return await asyncio.to_thread(_sync)

async def get_reaction_count_by_chat_message(chat_id: int, message_id: int, reaction_emoji: str) -> int:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('reactions').select('user_id', count='exact').eq('chat_id', chat_id).eq('message_id', message_id).eq('reaction_emoji', reaction_emoji).execute()
            return res.count or len(res.data)
        except Exception:
            return 0
    return await asyncio.to_thread(_sync)

async def get_post_code_from_chat_message(chat_id: int, message_id: int) -> tuple[Optional[str], Optional[int]]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('send_posts').select('post_code, channel_id').eq('channel_id', chat_id).eq('message_id', message_id).limit(1).execute()
            if res.data:
                return res.data[0]['post_code'], res.data[0]['channel_id']
            return None, None
        except Exception:
            return None, None
    return await asyncio.to_thread(_sync)

# ==================== TEXT BUTTONS ====================

async def create_text_button() -> Optional[int]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('text_buttons').insert({
                'button_type': 'text_btn',
                'content_sub': '',
                'content_nonsub': ''
            }).execute()
            if res.data:
                return res.data[0]['id']
            return None
        except Exception:
            return None
    return await asyncio.to_thread(_sync)

async def get_text_button_content(btn_id: int) -> Optional[Dict]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('text_buttons').select('*').eq('id', btn_id).execute()
            return res.data[0] if res.data else None
        except Exception:
            return None
    return await asyncio.to_thread(_sync)

# ==================== FEEDBACK & ERRORS ====================

async def log_user_feedback(user_id: int, feedback_text: str):
    def _sync():
        try:
            sp = get_supabase()
            sp.table('users').update({'feedback_text': feedback_text}).eq('user_id', user_id).execute()
        except Exception:
            pass
    return await asyncio.to_thread(_sync)

async def log_user_error(user_id: int, error_text: str):
    def _sync():
        try:
            sp = get_supabase()
            sp.table('users').update({'error_text': error_text}).eq('user_id', user_id).execute()
        except Exception:
            pass
    return await asyncio.to_thread(_sync)

async def get_feedbacks_by_user(user_id: int) -> list:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('users').select('feedback_text').eq('user_id', user_id).execute()
            if res.data and res.data[0].get('feedback_text'):
                return [{'feedback_text': res.data[0]['feedback_text']}]
            return []
        except Exception:
            return []
    return await asyncio.to_thread(_sync)

async def get_errors_by_user(user_id: int) -> list:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('users').select('error_text').eq('user_id', user_id).execute()
            if res.data and res.data[0].get('error_text'):
                return [{'error_text': res.data[0]['error_text']}]
            return []
        except Exception:
            return []
    return await asyncio.to_thread(_sync)

# ==================== AI PROMPTS ====================

async def save_prompt(user_id: int, prompt_text: str) -> Optional[int]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('ai_prompts').insert({
                'user_id': user_id,
                'prompt_text': prompt_text,
                'created_at': get_now().isoformat()
            }).execute()
            return res.data[0]['id'] if res.data else None
        except Exception:
            return None
    return await asyncio.to_thread(_sync)

async def get_user_prompts(user_id: int) -> List[Dict]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('ai_prompts').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
            return res.data or []
        except Exception:
            return []
    return await asyncio.to_thread(_sync)

async def delete_prompt(prompt_id: int, user_id: int) -> bool:
    def _sync():
        try:
            sp = get_supabase()
            sp.table('ai_prompts').delete().eq('id', prompt_id).eq('user_id', user_id).execute()
            return True
        except Exception:
            return False
    return await asyncio.to_thread(_sync)

async def get_prompt_by_id(prompt_id: int, user_id: int) -> Optional[Dict]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('ai_prompts').select('*').eq('id', prompt_id).eq('user_id', user_id).execute()
            return res.data[0] if res.data else None
        except Exception:
            return None
    return await asyncio.to_thread(_sync)

# ==================== STATISTIKA ====================

async def record_new_post():
    return await record_bot_stat('new_posts')

async def record_bot_stat(stat_type: str = 'new_users'):
    def _sync():
        try:
            sp = get_supabase()
            today = get_now().strftime('%Y-%m-%d')
            res = sp.table('bot_stats').select('*').eq('stat_date', today).execute()
            if res.data:
                curr = res.data[0].get(stat_type, 0) or 0
                sp.table('bot_stats').update({stat_type: curr + 1}).eq('stat_date', today).execute()
            else:
                sp.table('bot_stats').insert({
                    'stat_date': today,
                    stat_type: 1
                }).execute()
        except Exception as e:
            logger.error(f"record_bot_stat error: {e}")
    return await asyncio.to_thread(_sync)

async def get_bot_stats(days: int = 30) -> Dict:
    def _sync():
        try:
            sp = get_supabase()
            users_res = sp.table('users').select('user_id', count='exact').execute()
            total_users = users_res.count or len(users_res.data)
            
            today = get_now().strftime('%Y-%m-%d')
            today_res = sp.table('bot_stats').select('*').eq('stat_date', today).execute()
            new_today = today_res.data[0].get('new_users', 0) if today_res.data else 0
            posts_today = today_res.data[0].get('new_posts', 0) if today_res.data else 0
            
            return {
                'total_users': total_users,
                'new_today': new_today,
                'new_week': new_today,
                'new_month': new_today,
                'posts_today': posts_today,
                'posts_week': posts_today,
                'posts_month': posts_today,
                'current_time': get_now()
            }
        except Exception as e:
            logger.error(f"get_bot_stats error: {e}")
            return {
                'total_users': 0, 'new_today': 0, 'new_week': 0, 'new_month': 0,
                'posts_today': 0, 'posts_week': 0, 'posts_month': 0, 'current_time': get_now()
            }
    return await asyncio.to_thread(_sync)

async def get_total_users_count() -> tuple[int, datetime]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('users').select('user_id', count='exact').execute()
            return res.count or len(res.data), get_now()
        except Exception:
            return 0, get_now()
    return await asyncio.to_thread(_sync)

async def get_language_stats(excluded_admin_ids: List[int] = None) -> Dict[str, int]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('users').select('language').execute()
            counts = {}
            for r in res.data:
                lang = _normalize_language(r.get('language'))
                counts[lang] = counts.get(lang, 0) + 1
            return counts
        except Exception:
            return {}
    return await asyncio.to_thread(_sync)

async def get_total_errors_count() -> int:
    return 0

async def get_post_statistics(post_code: str) -> Optional[Dict]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('post_stats').select('*').eq('post_code', post_code).execute()
            if res.data:
                row = res.data[0]
                return {
                    'views': row.get('total_views', 0),
                    'forward_count': row.get('total_shares', 0),
                    'button_clicks': row.get('total_clicks', 0)
                }
            return None
        except Exception:
            return None
    return await asyncio.to_thread(_sync)

async def update_post_statistics(post_code: str, views: int = 0, forwards: int = 0, button_clicks: int = 0) -> bool:
    def _sync():
        try:
            sp = get_supabase()
            sp.table('post_stats').upsert({
                'post_code': post_code,
                'total_views': views,
                'total_shares': forwards,
                'total_clicks': button_clicks
            }, on_conflict='post_code').execute()
            return True
        except Exception:
            return False
    return await asyncio.to_thread(_sync)

async def track_button_click(post_code: str, channel_id: int = 0) -> bool:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('post_stats').select('*').eq('post_code', post_code).execute()
            if res.data:
                curr = res.data[0].get('total_clicks', 0)
                sp.table('post_stats').update({'total_clicks': curr + 1}).eq('post_code', post_code).execute()
            else:
                sp.table('post_stats').insert({
                    'post_code': post_code,
                    'total_clicks': 1
                }).execute()
            return True
        except Exception:
            return False
    return await asyncio.to_thread(_sync)

async def get_post_detailed_stats(post_code: str):
    return await get_post_statistics(post_code)

async def get_best_posting_hours(user_id: int):
    return None

async def get_all_user_posts_for_stat(user_id: int) -> List[Dict]:
    return await get_posts_by_user(user_id)

async def get_all_posts_from_channel(channel_id: int) -> List[Dict]:
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('send_posts').select('*').eq('channel_id', channel_id).execute()
            return res.data or []
        except Exception:
            return []
    return await asyncio.to_thread(_sync)

async def get_users_for_export(admin_ids: list = None, period: str = 'all'):
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('users').select('*').execute()
            return res.data or []
        except Exception:
            return []
    return await asyncio.to_thread(_sync)

async def get_post_creators_for_export(admin_ids: list = None, period: str = 'all'):
    return []

async def get_user_settings_for_export(admin_ids: list = None, period: str = 'all'):
    return []

# ==================== INIT_DB ====================

async def init_db():
    """Supabase bazaga ulanishni tekshiradi va keshni ishga tushiradi."""
    def _sync():
        try:
            sp = get_supabase()
            res = sp.table('users').select('user_id').limit(1).execute()
            logger.info("✅ Supabase ma'lumotlar bazasiga ulanish muvaffaqiyatli!")
            
            # Bloklangan foydalanuvchilar keshini to'ldiramiz
            b_res = sp.table('users').select('user_id').eq('is_blocked', 1).execute()
            blocked_set = {row['user_id'] for row in b_res.data} if b_res.data else set()
            
            # Majburiy kanallarni keshlaymiz
            r_res = sp.table('req_channels').select('*').execute()
            req_list = [
                {
                    'id': row['channel_id'],
                    'channel_id': row['channel_id'],
                    'title': row.get('channel_name') or 'Kanal',
                    'name': row.get('channel_name') or 'Kanal',
                    'username': row.get('username')
                }
                for row in r_res.data
            ] if r_res.data else []
            
            return blocked_set, req_list
        except Exception as e:
            logger.error(f"❌ Supabase ulanishida xatolik: {e}")
            return set(), []

    global _blocked_users_cache, _blocked_cache_time, _req_channels_cache
    blocked_set, req_list = await asyncio.to_thread(_sync)
    _blocked_users_cache = blocked_set
    _blocked_cache_time = time.time()
    _req_channels_cache = (time.time(), req_list)
    logger.info(f"⚡ Kesh yuklandi: {len(blocked_set)} ta bloklangan foydalanuvchi, {len(req_list)} ta majburiy kanal.")
    return True
