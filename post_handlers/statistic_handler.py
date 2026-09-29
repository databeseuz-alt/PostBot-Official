import io
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import logging
import qrcode
import asyncio

logger = logging.getLogger(__name__)

from aiogram import Router, types, Bot, F, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, ChatPermissions
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from xdata_handlers.translator import get_text
from xdata_handlers.database import (
    get_user_channels, get_user_language,
    get_user_channel_statistics,
    get_all_posts_from_channel,
    track_button_click,
    get_user_sent_posts, get_post_detailed_stats, get_best_posting_hours
)
from post_handlers.xreply_keyboard import get_main_menu
from post_handlers.localize_filter import LocalizedText

import html as _html

statistic_router = Router()


class AddChannelFromStatsCallback(CallbackData, prefix="add_channel_from_stats"):
    action: str

class StatChannelSelectCallback(CallbackData, prefix="stat_ch_sel"):
    channel_id: str


def get_stats_actions_keyboard(lang: str = 'uzl') -> types.InlineKeyboardMarkup:
    """Statistika rasmi ostidagi tugmalar."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('back_btn', lang), callback_data="cancel_action")
    builder.adjust(1)
    return builder.as_markup()


def _fmt_num(n) -> str:
    """Raqamni o'qishga qulay ko'rinishda formatlaydi."""
    try:
        n = int(n or 0)
    except (TypeError, ValueError):
        n = 0
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1000:
        return f"{n / 1000:.1f}K"
    return str(n)


@statistic_router.callback_query(F.data == "stats_posts_report")
async def handle_stats_posts_report(callback: types.CallbackQuery, callback_data=None, bot: Bot = None):
    """Foydalanuvchining yuborilgan postlari ro'yxati — batafsil hisobot uchun."""
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    try:
        sent_posts = await get_user_sent_posts(user_id)
    except Exception as e:
        logger.error(f"stats_posts_report xatolik: {e}")
        sent_posts = []

    if not sent_posts:
        builder = InlineKeyboardBuilder()
        builder.button(text=get_text('back_btn', lang), callback_data="stats_report_close")
        builder.adjust(1)
        await callback.message.answer(
            get_text('stats_no_posts_msg', lang),
            reply_markup=builder.as_markup()
        )
        await callback.answer()
        return

    seen_codes = set()
    builder = InlineKeyboardBuilder()
    shown = 0
    for post in sent_posts:
        code = post.get('post_code')
        if not code or code in seen_codes:
            continue
        seen_codes.add(code)

        channel_name = post.get('channel_name') or 'Kanal'
        sent_at = post.get('sent_at')
        date_str = sent_at.strftime("%d.%m") if sent_at else ""

        builder.button(
            text=f"📋 #{code} · {_html.escape(str(channel_name)[:20])} {date_str}",
            callback_data=f"stats_post_detail:{code}"
        )
        shown += 1
        if shown >= 10:
            break

    builder.button(text=get_text('back_btn', lang), callback_data="stats_report_close")
    builder.adjust(1)

    await callback.message.answer(
        get_text('stats_posts_report_title', lang).format(count=len(seen_codes)),
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@statistic_router.callback_query(F.data.startswith("stats_post_detail:"))
async def handle_stats_post_detail(callback: types.CallbackQuery, bot: Bot = None):
    """Bitta post bo'yicha batafsil hisobot."""
    post_code = callback.data.split(":")[1]
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    try:
        stats = await get_post_detailed_stats(post_code)
    except Exception as e:
        logger.error(f"stats_post_detail xatolik: {e}")
        stats = {'views': 0, 'shares': 0, 'clicks': 0, 'channels_count': 0, 'reactions': [], 'published_channels': []}

    lines = [
        f"📊 <b>#{_html.escape(post_code)}</b> — {get_text('stats_post_detail_title', lang)}",
        "",
        f"👁 {get_text('stats_views_label', lang)}: <b>{_fmt_num(stats['views'])}</b>",
        f"🔗 {get_text('stats_clicks_label', lang)}: <b>{_fmt_num(stats['clicks'])}</b>",
        f"📤 {get_text('stats_shares_label', lang)}: <b>{_fmt_num(stats['shares'])}</b>",
    ]

    if stats.get('reactions'):
        reaction_parts = [f"{r['emoji']} {r['count']}" for r in stats['reactions'][:8]]
        lines.append("")
        lines.append(f"❤️ {get_text('stats_reactions_label', lang)}: {' · '.join(reaction_parts)}")

    if stats.get('published_channels'):
        lines.append("")
        lines.append(f"📍 {get_text('stats_published_label', lang)}:")
        for ch in stats['published_channels'][:6]:
            sent_at = ch.get('sent_at')
            when = sent_at.strftime("%d.%m.%Y %H:%M") if sent_at else "—"
            lines.append(f"  • {_html.escape(str(ch.get('name') or 'Kanal')[:28])} — {when}")

    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('back_btn', lang), callback_data="stats_posts_report")
    builder.adjust(1)

    await callback.message.answer(
        "\n".join(lines),
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@statistic_router.callback_query(F.data == "stats_best_time")
async def handle_stats_best_time(callback: types.CallbackQuery, bot: Bot = None):
    """Postlarning eng yaxshi joylashash vaqtlari tahlili."""
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    try:
        hours = await get_best_posting_hours(user_id)
    except Exception as e:
        logger.error(f"stats_best_time xatolik: {e}")
        hours = []

    if not hours:
        builder = InlineKeyboardBuilder()
        builder.button(text=get_text('back_btn', lang), callback_data="stats_report_close")
        builder.adjust(1)
        await callback.message.answer(
            get_text('stats_best_time_empty', lang),
            reply_markup=builder.as_markup()
        )
        await callback.answer()
        return

    lines = [
        f"⏰ <b>{get_text('stats_best_time_title', lang)}</b>",
        "",
        get_text('stats_best_time_intro', lang),
        "",
    ]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for i, (hour, avg_views, posts_count) in enumerate(hours[:5]):
        lines.append(
            f"{medals[i]} <b>{hour:02d}:00</b> — "
            f"{get_text('stats_avg_views_label', lang)}: <b>{_fmt_num(avg_views)}</b> "
            f"({posts_count} {get_text('stats_posts_word', lang)})"
        )

    best_hour = hours[0][0]
    lines.append("")
    lines.append(get_text('stats_best_time_advice', lang).format(hour=f"{best_hour:02d}:00"))

    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('back_btn', lang), callback_data="stats_report_close")
    builder.adjust(1)

    await callback.message.answer(
        "\n".join(lines),
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@statistic_router.callback_query(F.data == "stats_report_close")
async def handle_stats_report_close(callback: types.CallbackQuery, bot: Bot = None):
    """Hisobot menyuni yopish."""
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()


class ChannelStatDrawer:
    """TGStat uslubidagi kanal statistikasi rasmi."""

    def __init__(self):
        self.BG_COLOR = "#FFFFFF"
        self.CARD_BG = "#F8FAFC"
        self.CARD_BORDER = "#E2E8F0"
        self.TEXT_PRIMARY = "#1E293B"
        self.TEXT_SECONDARY = "#64748B"
        self.TEXT_MUTED = "#94A3B8"
        self.ACCENT_BLUE = "#0EA5E9"
        self.ACCENT_LIGHT_BLUE = "#E0F2FE"
        self.HEADER_BG = "#F0F9FF"
        self.DIVIDER = "#E2E8F0"

        self._load_fonts()

    def _load_fonts(self):
        """Fontlarni yuklash"""
        try:
            self.font_bold_xl = ImageFont.truetype("arial.ttf", 42)
            self.font_bold_lg = ImageFont.truetype("arial.ttf", 28)
            self.font_bold_md = ImageFont.truetype("arial.ttf", 20)
            self.font_bold_sm = ImageFont.truetype("arial.ttf", 16)
            self.font_regular_md = ImageFont.truetype("arial.ttf", 18)
            self.font_regular_sm = ImageFont.truetype("arial.ttf", 14)
            self.font_regular_xs = ImageFont.truetype("arial.ttf", 12)
        except Exception:
            try:
                self.font_bold_xl = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
                self.font_bold_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
                self.font_bold_md = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
                self.font_bold_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
                self.font_regular_md = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
                self.font_regular_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
                self.font_regular_xs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            except Exception:
                self.font_bold_xl = ImageFont.load_default()
                self.font_bold_lg = ImageFont.load_default()
                self.font_bold_md = ImageFont.load_default()
                self.font_bold_sm = ImageFont.load_default()
                self.font_regular_md = ImageFont.load_default()
                self.font_regular_sm = ImageFont.load_default()
                self.font_regular_xs = ImageFont.load_default()

    def _draw_rounded_rect(self, draw, coords, radius, fill, outline=None, width=1):
        """Yumaloq burchakli to'rtburchak chizish"""
        x1, y1, x2, y2 = coords

        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)

        draw.pieslice([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=fill)
        draw.pieslice([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=fill)
        draw.pieslice([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=fill)
        draw.pieslice([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=fill)

        if outline:
            draw.arc([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=outline, width=width)
            draw.arc([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=outline, width=width)
            draw.arc([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=outline, width=width)
            draw.arc([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=outline, width=width)
            draw.line([x1 + radius, y1, x2 - radius, y1], fill=outline, width=width)
            draw.line([x1 + radius, y2, x2 - radius, y2], fill=outline, width=width)
            draw.line([x1, y1 + radius, x1, y2 - radius], fill=outline, width=width)
            draw.line([x2, y1 + radius, x2, y2 - radius], fill=outline, width=width)

    def _draw_stat_card(self, draw, x, y, w, h, value, label, sub_label=None, info_icon=False):
        """TGStat uslubidagi statistika kartochkasi"""
        self._draw_rounded_rect(draw, (x, y, x + w, y + h), 10, self.CARD_BG, self.CARD_BORDER)

        # Katta raqam - chap tarafda
        draw.text((x + 20, y + 18), str(value), font=self.font_bold_xl, fill=self.TEXT_PRIMARY)

        # Label - yuqori o'ng burchakda
        label_bbox = draw.textbbox((0, 0), label, font=self.font_regular_sm)
        label_w = label_bbox[2] - label_bbox[0]
        draw.text((x + w - label_w - 20, y + 15), label, font=self.font_regular_sm, fill=self.TEXT_SECONDARY)

        # Sub label - pastda
        if sub_label:
            draw.text((x + 20, y + 70), sub_label, font=self.font_regular_sm, fill=self.TEXT_MUTED)

        # Info icon
        if info_icon:
            icon_text = "(i)"
            icon_bbox = draw.textbbox((0, 0), icon_text, font=self.font_regular_xs)
            icon_w = icon_bbox[2] - icon_bbox[0]
            draw.text((x + w - icon_w - 20, y + 38), icon_text, font=self.font_regular_xs, fill=self.TEXT_MUTED)

    def _draw_mini_graph(self, draw, x, y, w, h, values):
        """Kichik gradient graph chizish (obunachilar kartochkasida)"""
        if not values or max(values) == 0:
            return

        max_val = max(values)
        min_val = min(values)
        if max_val == min_val:
            max_val += 1
        val_range = max_val - min_val

        points = []
        step_x = w / (len(values) - 1) if len(values) > 1 else w

        for i, val in enumerate(values):
            px = x + i * step_x
            py = y + h - ((val - min_val) / val_range * h)
            points.append((px, py))

        # Gradient area
        if len(points) > 1:
            polygon_points = list(points) + [(x + w, y + h), (x, y + h)]
            draw.polygon(polygon_points, fill=self.ACCENT_LIGHT_BLUE)
            draw.line(points, fill=self.ACCENT_BLUE, width=2)

    def _draw_qr_code(self, draw, img, x, y, size, bot_username):
        """Haqiqiy QR-kod chizadi (bot linki bilan)"""
        qr_url = f"https://t.me/{bot_username}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=0,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color=self.TEXT_PRIMARY, back_color="#FFFFFF").convert('RGB')
        qr_img = qr_img.resize((size, size), Image.Resampling.LANCZOS)
        
        # QR kod uchun ramka
        draw.rectangle([x-2, y-2, x + size+2, y + size+2], outline=self.CARD_BORDER, width=1)
        img.paste(qr_img, (x, y))

    def draw_channel_stats(self, channel_name: str, stats: dict, bot_username: str = "PostBot_Bot") -> io.BytesIO:
        """TGStat uslubida kanal statistikasi rasmini chizadi."""
        total_posts = stats.get('total_posts', 0)
        total_views = stats.get('total_views', 0)
        total_reactions = stats.get('total_reactions', 0)
        total_shares = stats.get('total_shares', 0)
        total_button_clicks = stats.get('total_button_clicks', 0)

        # Faqat 4 ta kartochka + header + footer
        width = 900
        height = 450  # Biroz balandlik qo'shamiz

        img = Image.new('RGB', (width, height), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        margin = 25
        card_gap = 20

        # ===== HEADER =====
        header_h = 80
        self._draw_rounded_rect(draw, (margin, margin, width - margin, margin + header_h), 12, self.HEADER_BG, self.CARD_BORDER)

        # Kanal nomi - chap
        ch_display = channel_name if len(channel_name) <= 35 else channel_name[:32] + "..."
        draw.text((margin + 20, margin + 15), ch_display, font=self.font_bold_lg, fill=self.TEXT_PRIMARY)

        # "Telegram" yozuvi pastda
        draw.text((margin + 20, margin + 50), "Telegram", font=self.font_regular_sm, fill=self.ACCENT_BLUE)

        # O'ngda - Postlar soni
        info_text = f"Postlar    {total_posts}"
        info_bbox = draw.textbbox((0, 0), info_text, font=self.font_regular_sm)
        info_w = info_bbox[2] - info_bbox[0]
        draw.text((width - margin - info_w - 20, margin + 22), info_text, font=self.font_regular_sm, fill=self.TEXT_SECONDARY)

        # ===== 4 TA STAT KARTOCHKALAR (2x2) =====
        card_w = (width - 3 * margin) // 2
        card_h = 105
        row1_y = margin + header_h + card_gap

        # 1. KO'RISHLAR
        self._draw_stat_card(
            draw, margin, row1_y, card_w, card_h,
            f"{total_views:,}",
            "KO'RISHLAR",
            f"Jami ko'rishlar soni",
        )

        # Mini graf - agar ko'rishlar bor bo'lsa
        if total_views > 0:
            graph_values = [0, total_views // 3, total_views // 2, total_views]
            self._draw_mini_graph(
                draw,
                margin + card_w // 2, row1_y + 35,
                card_w // 2 - 30, 55,
                graph_values
            )

        # 2. ULASHISHLAR (Endi yuqori o'ngda)
        self._draw_stat_card(
            draw, margin * 2 + card_w, row1_y, card_w, card_h,
            f"{total_shares:,}",
            "ULASHISHLAR",
            "Forward va ulashishlar"
        )

        row2_y = row1_y + card_h + card_gap

        # 3. REAKSIYALAR (Endi pastki chapda)
        self._draw_stat_card(
            draw, margin, row2_y, card_w, card_h,
            f"{total_reactions:,}",
            "REAKSIYALAR",
            "Jami reaksiyalar",
            info_icon=True
        )

        # Top reactions detail
        top_reacts = stats.get('top_reactions', [])
        if top_reacts:
            react_text = "   ".join([f"{item['emoji']} {item['count']}" for item in top_reacts])
            draw.text((margin + 20, row2_y + 73), react_text, font=self.font_regular_sm, fill=self.TEXT_MUTED)

        # 4. TUGMA BOSILGANLAR SONI
        self._draw_stat_card(
            draw, margin * 2 + card_w, row2_y, card_w, card_h,
            f"{total_button_clicks:,}",
            "TUGMA BOSILGAN",
            info_icon=True
        )

        if total_posts > 0:
            avg_clicks = total_button_clicks / total_posts
            click_sub = f"O'rtacha {avg_clicks:.1f} ta/post"
        else:
            click_sub = "Ma'lumot yetarli emas"
        draw.text((margin * 2 + card_w + 20, row2_y + 70), click_sub, font=self.font_regular_sm, fill=self.TEXT_MUTED)

        # ===== FOOTER (Bot nomi + sana + QR kod o'ngda) =====
        footer_y = height - 65
        qr_size = 55

        # 2. Bot nomi va tavsifi - Chapda (Kattaroq shriftda)
        draw.text((margin, footer_y - 2), "PostBot", font=self.font_bold_md, fill=self.ACCENT_BLUE)
        draw.text((margin, footer_y + 26), "Telegram post boshqaruv boti", font=self.font_regular_md, fill=self.TEXT_MUTED)

        # 3. Sana/vaqt va @bot_username - O'ngda (Kattaroq shriftda)
        from datetime import timezone, timedelta
        tashkent_now = datetime.now(timezone(timedelta(hours=5)))
        current_date = tashkent_now.strftime('%d-%m-%Y %H:%M')
        bot_handle = f"@{bot_username}"
        
        # O'ngda QR kod bor, uning oldiga joylaymiz
        qr_left_boundary = width - margin - qr_size - 18
        
        date_bbox = draw.textbbox((0, 0), current_date, font=self.font_regular_sm)
        date_w = date_bbox[2] - date_bbox[0]
        draw.text((qr_left_boundary - date_w, footer_y + 4), current_date, font=self.font_regular_sm, fill=self.TEXT_SECONDARY)
        
        handle_bbox = draw.textbbox((0, 0), bot_handle, font=self.font_bold_sm)
        handle_w = handle_bbox[2] - handle_bbox[0]
        draw.text((qr_left_boundary - handle_w, footer_y + 26), bot_handle, font=self.font_bold_sm, fill=self.ACCENT_BLUE)

        # 4. QR kod - Eng o'ngda
        qr_x = width - margin - qr_size
        self._draw_qr_code(draw, img, qr_x, footer_y, qr_size, bot_username)

        # Saqlash
        buf = io.BytesIO()
        img.save(buf, format='PNG', quality=95)
        buf.seek(0)
        return buf


channel_stat_drawer = ChannelStatDrawer()


async def get_live_channel_statistics(bot: Bot, channel_id: int) -> dict:
    """Telegramdan to'g'ridan-to'g'ri kanal statistikasini oladi."""
    try:
        # Kanal chat ma'lumotlarini olish
        chat = await bot.get_chat(channel_id)
        
        # Kanal a'zolar soni
        member_count = chat.member_count or 0
        
        # Oxirgi postlarni olish va statistika yig'ish
        total_views = 0
        total_forwards = 0
        total_reactions = 0
        
        # Oxirgi 10 ta postni olish
        try:
            # Telegram API orqali message history olish
            # Bu uchun bot kanal admini bo'lishi kerak
            async for message in bot.get_chat_history(channel_id, limit=10):
                # Ko'rishlar
                if hasattr(message, 'views') and message.views:
                    total_views += message.views
                
                # Forwardlar
                if hasattr(message, 'forward_count') and message.forward_count:
                    total_forwards += message.forward_count
                
                # Reaksiyalar
                if message.reactions:
                    for reaction_group in message.reactions:
                        for reaction in reaction_group.reactions:
                            if hasattr(reaction, 'count'):
                                total_reactions += reaction.count
        except Exception as e:
            logger.error(f"Postlarni olishda xatolik: {e}")
        
        return {
            'total_posts': 10,
            'member_count': member_count,
            'total_views': total_views,
            'total_forwards': total_forwards,
            'total_reactions': total_reactions
        }
    except Exception as e:
        logger.error(f"Kanal statistikasini olishda xatolik: {e}")
        return {
            'total_posts': 0,
            'member_count': 0,
            'total_views': 0,
            'total_forwards': 0,
            'total_reactions': 0
        }


async def generate_channel_statistics_image(user_id: int, lang: str = 'uzl', bot_username: str = "PostBot_Bot", bot: Bot = None, channel_id: int = None) -> io.BytesIO:
    """Foydalanuvchining kanal statistikasi rasmini yaratadi."""
    channels = await get_user_channels(user_id)
    
    # Faqat foydalanuvchi yaratgan va bot orqali yuborilgan postlar stats-i
    stats = await get_user_channel_statistics(user_id, channel_id)
    
    # Kanal nomini olish
    if channels:
        if channel_id:
            channel_name = next((c.get('channel_name', 'Kanal') for c in channels if str(c.get('channel_id')) == str(channel_id)), "Kanal statistikasi")
        else:
            if len(channels) == 1:
                channel_name = channels[0].get('channel_name', 'Kanal')
            else:
                channel_name = f"{len(channels)} ta kanal statistikasi"
    else:
        channel_name = "Kanal statistikasi"
    
    # Rasmni chizish
    return channel_stat_drawer.draw_channel_stats(channel_name, stats, bot_username)


@statistic_router.message(LocalizedText('statistic_btn'))
@statistic_router.callback_query(F.data == "main:statistic")
async def handle_generate_statistics(event: types.Message | types.CallbackQuery, state: FSMContext, bot: Bot, user_id: int = None):
    """Statistika tugmasi bosilganda statistikani yaratadi (faqat kanal ulaganlar uchun)"""
    if user_id is None:
        user_id = event.from_user.id

    message = event.message if isinstance(event, types.CallbackQuery) else event
    lang = await get_user_language(user_id)

    # Foydalanuvchi kanal ulaganligni tekshirish
    user_channels = await get_user_channels(user_id)
    if not user_channels:
        # Kanal yo'q bo'lsa - klaviatura bilan xabar yuborish
        builder = InlineKeyboardBuilder()
        builder.button(
            text=get_text('add_channel_btn', lang),
            callback_data=AddChannelFromStatsCallback(action="add").pack()
        )
        builder.button(
            text=get_text('back_btn', lang),
            callback_data="cancel_action"
        )
        builder.adjust(1, 1)
        if isinstance(event, types.CallbackQuery):
            try:
                await event.message.edit_text(
                    get_text('statistics_no_channel_msg', lang),
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
            except Exception:
                await event.message.answer(
                    get_text('statistics_no_channel_msg', lang),
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
        else:
            await message.answer(
                get_text('statistics_no_channel_msg', lang),
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        return

    builder = InlineKeyboardBuilder()
    if len(user_channels) > 1:
        builder.button(
            text="📊 Barcha kanallar",
            callback_data=StatChannelSelectCallback(channel_id="all").pack()
        )
    for ch in user_channels:
        builder.button(
            text=ch.get('channel_name', 'Kanal'),
            callback_data=StatChannelSelectCallback(channel_id=str(ch.get('channel_id'))).pack()
        )
    builder.button(
        text=get_text('back_btn', lang),
        callback_data="cancel_action"
    )
    builder.adjust(1)
    
    choose_text = "📊 Qaysi kanal statistikasini ko'rmoqchisiz? Iltimos, kanalni tanlang:"
    if isinstance(event, types.CallbackQuery):
        try:
            await event.message.edit_text(choose_text, reply_markup=builder.as_markup())
        except Exception:
            await event.message.answer(choose_text, reply_markup=builder.as_markup())
    else:
        await message.answer(
            choose_text,
            reply_markup=builder.as_markup()
        )
    return

@statistic_router.callback_query(StatChannelSelectCallback.filter())
async def handle_stat_channel_selection(callback: types.CallbackQuery, callback_data: StatChannelSelectCallback, bot: Bot):
    """Statistika uchun kanal tanlanganda"""
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    
    selected_channel = callback_data.channel_id
    ch_id = int(selected_channel) if selected_channel != "all" else None
    
    await callback.message.delete()
    
    loading_msg = await callback.message.answer(get_text('generating_statistics_msg', lang))

    try:
        bot_info = await bot.get_me()
        bot_username = bot_info.username or "PostBot_Bot"

        img_buffer = await generate_channel_statistics_image(user_id, lang, bot_username, bot, channel_id=ch_id)

        await loading_msg.delete()

        img_buffer.seek(0)
        input_file = BufferedInputFile(
            file=img_buffer.read(),
            filename='channel_statistics.png'
        )

        await callback.message.answer_photo(
            photo=input_file,
            caption=get_text('statistics_image_caption', lang),
            reply_markup=get_stats_actions_keyboard(lang)
        )

    except Exception as e:
        logger.error(f"Statistika rasmini yaratishda xatolik: {e}")
        try:
            await loading_msg.delete()
        except Exception:
            pass
        await callback.message.answer(
            f"Statistikani yaratishda xatolik yuz berdi: {str(e)}",
            reply_markup=await get_main_menu(lang, user_id)
        )

@statistic_router.callback_query(AddChannelFromStatsCallback.filter(F.action == "add"))
async def handle_add_channel_from_stats(callback: types.CallbackQuery, state: FSMContext):
    """Statistika bo'limidan kanal qo'shish tugmasi bosilganda."""
    lang = await get_user_language(callback.from_user.id)
    from post_handlers.send_handler import PostSending
    await state.clear()
    await state.set_state(PostSending.waiting_for_channel_info)

    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('cancel_btn', lang), callback_data="cancel_action")

    add_channel_text = get_text('add_channel_msg', lang)
    try:
        await callback.message.edit_text(add_channel_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(add_channel_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


# Button click tracking is now handled in button_handler.py to support text_btn and reaction logic.

