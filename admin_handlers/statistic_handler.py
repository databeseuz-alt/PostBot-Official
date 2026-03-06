import io
import math
from PIL import Image, ImageDraw, ImageFont

from aiogram import F, Router, types
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramBadRequest

from admin_handlers.admin_handler import IsAdmin
from xdata_handlers import config
from xdata_handlers.database import (
    get_detailed_user_stats, get_new_users_stats_extended,
    get_posts_stats, get_language_distribution, get_daily_stats_for_graph,
    get_active_users_by_period, get_total_errors_count, get_activity_heatmap_for_last_24h,
    get_weekly_activity, get_daily_hours_activity, get_post_formats, get_button_stats,
    get_now, get_database_table_stats
)
from admin_handlers.xinline_keyboard import (
    get_stats_menu_keyboard, get_graphics_menu_keyboard, 
    get_users_stats_keyboard, get_posts_stats_keyboard, 
    get_back_navigation_keyboard
)

statistic_router = Router()

class StatDrawer:
    def __init__(self):
        self.BG_COLOR = "#FFFFFF"           # Toza oq fon
        self.CARD_BG = "#F8FAFC"            # Kartochka foni (juda och kulrang)
        self.CARD_BORDER = "#E2E8F0"        # Kartochka chegarasi
        self.TEXT_PRIMARY = "#1E293B"       # Asosiy matn (qora)
        self.TEXT_SECONDARY = "#64748B"     # Ikkinchi darajali matn
        self.TEXT_MUTED = "#94A3B8"         # Xira matn

        self.GRADIENT_START = "#38BDF8"     # Och ko'k (gradient boshi)
        self.GRADIENT_END = "#0EA5E9"       # To'q ko'k (gradient oxiri)
        self.ACCENT_BLUE = "#3B82F6"        # Asosiy ko'k
        self.ACCENT_GREEN = "#22C55E"       # Yashil (ijobiy)
        self.ACCENT_YELLOW = "#F59E0B"      # Sariq (ogohlantirish)
        self.ACCENT_RED = "#EF4444"         # Qizil (salbiy)

        self.PIE_COLORS = [
            "#3B82F6", "#22C55E", "#F59E0B", "#EF4444", 
            "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16"
        ]

        self._load_fonts()

    def _load_fonts(self):
        """Fontlarni yuklash"""
        self.font = ImageFont.load_default()
        try:
            self.font_bold_xl = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            self.font_bold_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
            self.font_bold_md = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            self.font_regular_md = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
            self.font_regular_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            self.font_regular_xs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            try:
                self.font_bold_xl = ImageFont.truetype("arial.ttf", 48)
                self.font_bold_lg = ImageFont.truetype("arial.ttf", 32)
                self.font_bold_md = ImageFont.truetype("arial.ttf", 24)
                self.font_regular_md = ImageFont.truetype("arial.ttf", 18)
                self.font_regular_sm = ImageFont.truetype("arial.ttf", 14)
                self.font_regular_xs = ImageFont.truetype("arial.ttf", 12)
            except:
                self.font_bold_xl = ImageFont.load_default()
                self.font_bold_lg = ImageFont.load_default()
                self.font_bold_md = ImageFont.load_default()
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

    def _draw_gradient_area(self, img, coords, values, color_start, color_end, alpha=80):
        """Gradient to'ldiruvchi maydon chizish (grafik ostida)"""
        from PIL import Image as PILImage
        x, y, w, h = coords
        max_val = max(values) if values and max(values) > 0 else 1
        min_val = min(values) if values else 0
        val_range = max_val - min_val if max_val != min_val else 1

        overlay = PILImage.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        points = []
        step_x = w / (len(values) - 1) if len(values) > 1 else w

        for i, val in enumerate(values):
            px = x + i * step_x
            py = y + h - ((val - min_val) / val_range * h)
            points.append((px, py))

        if points:
            polygon_points = points + [(x + w, y + h), (x, y + h)]

            r, g, b = 59, 130, 246  # #3B82F6
            overlay_draw.polygon(polygon_points, fill=(r, g, b, alpha))

            img.paste(PILImage.alpha_composite(img.convert('RGBA'), overlay).convert('RGB'))

        return points

    def _draw_stat_card(self, draw, x, y, w, h, value, label, sub_label=None, trend=None, show_graph=False, graph_data=None):
        """TGStat uslubidagi statistika kartochkasi"""
        self._draw_rounded_rect(draw, (x, y, x+w, y+h), 12, self.CARD_BG, self.CARD_BORDER)

        draw.text((x + 20, y + 20), str(value), font=self.font_bold_lg, fill=self.TEXT_PRIMARY)

        label_bbox = draw.textbbox((0, 0), label, font=self.font_regular_sm)
        label_w = label_bbox[2] - label_bbox[0]
        draw.text((x + w - label_w - 20, y + 15), label, font=self.font_regular_sm, fill=self.TEXT_SECONDARY)

        if sub_label:
            draw.text((x + 20, y + 60), sub_label, font=self.font_regular_sm, fill=self.TEXT_MUTED)

        if trend:
            trend_color = self.ACCENT_GREEN if trend.startswith("+") else self.ACCENT_RED if trend.startswith("-") else self.TEXT_MUTED
            draw.text((x + 20, y + h - 30), trend, font=self.font_regular_sm, fill=trend_color)

    def draw_dashboard(self, stats: dict) -> io.BytesIO:
        """Zamonaviy Dashboard chizish"""
        width, height = 900, 650
        img = Image.new('RGB', (width, height), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        draw.text((30, 25), "📊 Bot Dashboard", font=self.font_bold_md, fill=self.TEXT_PRIMARY)
        draw.text((30, 55), "Umumiy ko'rsatkichlar", font=self.font_regular_sm, fill=self.TEXT_SECONDARY)

        margin = 25
        card_w = (width - 3 * margin) // 2
        card_h = 120
        start_y = 100

        self._draw_stat_card(draw, margin, start_y, card_w, card_h,
                            f"{stats.get('total_users', 0):,}",
                            "OBUNACHILAR",
                            f"{stats.get('today_users', 0)} bugun",
                            f"+{stats.get('today_users', 0)} bugun" if stats.get('today_users', 0) > 0 else None)

        self._draw_stat_card(draw, margin*2 + card_w, start_y, card_w, card_h,
                            f"{stats.get('active_users', 0):,}",
                            "FAOL A'ZOLAR",
                            "Bloklamaganlar")

        self._draw_stat_card(draw, margin, start_y + card_h + margin, card_w, card_h,
                            f"{stats.get('total_posts', 0):,}",
                            "POSTLAR",
                            f"{stats.get('today_posts', 0)} bugun",
                            f"+{stats.get('today_posts', 0)} bugun" if stats.get('today_posts', 0) > 0 else None)

        self._draw_stat_card(draw, margin*2 + card_w, start_y + card_h + margin, card_w, card_h,
                            str(stats.get('top_lang', 'UZ')).upper(),
                            "ASOSIY TIL")

        graph_y = start_y + 2*(card_h + margin)
        graph_h = height - graph_y - margin

        self._draw_rounded_rect(draw, (margin, graph_y, width - margin, height - margin), 12, self.CARD_BG, self.CARD_BORDER)
        draw.text((margin + 20, graph_y + 15), "So'nggi 7 kunlik o'sish", font=self.font_regular_md, fill=self.TEXT_PRIMARY)

        data = stats.get('last_7_days', [])
        if data and max(data) > 0:
            chart_x = margin + 30
            chart_y = graph_y + 50
            chart_w = width - 2*margin - 60
            chart_h = graph_h - 80

            points = self._draw_area_chart(img, draw, chart_x, chart_y, chart_w, chart_h, data)
        else:
            draw.text((width//2 - 50, graph_y + graph_h//2), "Ma'lumot yo'q", font=self.font_regular_md, fill=self.TEXT_MUTED)

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf

    def _draw_area_chart(self, img, draw, x, y, w, h, values, labels=None):
        """Maydonli grafik (gradient bilan)"""
        if not values:
            return []

        max_val = max(values) if max(values) > 0 else 1
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

        for i in range(5):
            line_y = y + (i * h / 4)
            draw.line([(x, line_y), (x + w, line_y)], fill="#E5E7EB", width=1)

        if len(points) > 1:
            polygon_points = list(points) + [(x + w, y + h), (x, y + h)]
            draw.polygon(polygon_points, fill="#DBEAFE")

        if len(points) > 1:
            draw.line(points, fill=self.ACCENT_BLUE, width=3)

        for p in points:
            draw.ellipse((p[0]-4, p[1]-4, p[0]+4, p[1]+4), fill=self.BG_COLOR, outline=self.ACCENT_BLUE, width=2)

        return points

    def draw_line_chart(self, title: str, dates: list, values: list) -> io.BytesIO:
        """Zamonaviy chiziqli grafik"""
        width, height = 950, 550
        img = Image.new('RGB', (width, height), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        draw.text((30, 20), title, font=self.font_bold_md, fill=self.TEXT_PRIMARY)

        margin = 30
        self._draw_rounded_rect(draw, (margin, 70, width - margin, height - margin), 12, self.CARD_BG, self.CARD_BORDER)

        if not values or max(values) == 0:
            draw.text((width//2 - 80, height//2), "Ma'lumot yetarli emas", font=self.font_regular_md, fill=self.TEXT_MUTED)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return buf

        chart_x = margin + 60
        chart_y = 100
        chart_w = width - chart_x - margin - 20
        chart_h = height - chart_y - 80

        max_val = max(values)
        min_val = min(values)
        if max_val == min_val:
            max_val += 1
        val_range = max_val - min_val

        for i in range(5):
            line_y = chart_y + (i * chart_h / 4)
            draw.line([(chart_x, line_y), (chart_x + chart_w, line_y)], fill="#E5E7EB", width=1)
            val_text = f"{int(max_val - (i * val_range / 4))}"
            draw.text((chart_x - 45, line_y - 8), val_text, font=self.font_regular_xs, fill=self.TEXT_MUTED)

        points = []
        step_x = chart_w / (len(values) - 1) if len(values) > 1 else chart_w

        for i, val in enumerate(values):
            px = chart_x + i * step_x
            py = chart_y + chart_h - ((val - min_val) / val_range * chart_h)
            points.append((px, py))

            if dates and i < len(dates):
                if len(values) <= 15 or i % 5 == 0 or i == len(values) - 1:
                    draw.text((px - 15, chart_y + chart_h + 15), dates[i], font=self.font_regular_xs, fill=self.TEXT_MUTED)

        if len(points) > 1:
            polygon_points = list(points) + [(chart_x + chart_w, chart_y + chart_h), (chart_x, chart_y + chart_h)]
            draw.polygon(polygon_points, fill="#DBEAFE")

        if len(points) > 1:
            draw.line(points, fill=self.ACCENT_BLUE, width=3)

        for p in points:
            draw.ellipse((p[0]-5, p[1]-5, p[0]+5, p[1]+5), fill=self.BG_COLOR, outline=self.ACCENT_BLUE, width=2)

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf

    def draw_bar_chart(self, title: str, labels: list, values: list) -> io.BytesIO:
        """Zamonaviy ustunli diagramma"""
        width, height = 900, 550
        img = Image.new('RGB', (width, height), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        draw.text((30, 20), title, font=self.font_bold_md, fill=self.TEXT_PRIMARY)

        margin = 30
        self._draw_rounded_rect(draw, (margin, 70, width - margin, height - margin), 12, self.CARD_BG, self.CARD_BORDER)

        if not values or max(values) == 0:
            draw.text((width//2 - 50, height//2), "Ma'lumot yo'q", font=self.font_regular_md, fill=self.TEXT_MUTED)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return buf

        chart_x = margin + 50
        chart_y = 100
        chart_w = width - chart_x - margin - 30
        chart_h = height - chart_y - 80

        max_val = max(values)
        bar_width = (chart_w / len(values)) * 0.6
        spacing = (chart_w / len(values)) * 0.4

        for i in range(5):
            line_y = chart_y + (i * chart_h / 4)
            draw.line([(chart_x, line_y), (chart_x + chart_w, line_y)], fill="#E5E7EB", width=1)

        for i, (label, val) in enumerate(zip(labels, values)):
            bar_h = (val / max_val) * chart_h if max_val > 0 else 0
            x0 = chart_x + i * (bar_width + spacing) + spacing / 2
            y0 = chart_y + chart_h - bar_h
            x1 = x0 + bar_width
            y1 = chart_y + chart_h

            if bar_h > 10:
                self._draw_rounded_rect(draw, (x0, y0, x1, y1), 6, self.ACCENT_BLUE)
            else:
                draw.rectangle([x0, y0, x1, y1], fill=self.ACCENT_BLUE)

            val_text = str(val)
            text_bbox = draw.textbbox((0, 0), val_text, font=self.font_regular_sm)
            text_w = text_bbox[2] - text_bbox[0]
            draw.text((x0 + (bar_width - text_w) / 2, y0 - 20), val_text, font=self.font_regular_sm, fill=self.TEXT_PRIMARY)

            label_bbox = draw.textbbox((0, 0), str(label), font=self.font_regular_xs)
            label_w = label_bbox[2] - label_bbox[0]
            draw.text((x0 + (bar_width - label_w) / 2, y1 + 10), str(label), font=self.font_regular_xs, fill=self.TEXT_MUTED)

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf

    def draw_pie_chart(self, title: str, data: dict) -> io.BytesIO:
        """Zamonaviy doiraviy diagramma"""
        width, height = 900, 550
        img = Image.new('RGB', (width, height), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        draw.text((30, 20), title, font=self.font_bold_md, fill=self.TEXT_PRIMARY)

        margin = 30
        self._draw_rounded_rect(draw, (margin, 70, width - margin, height - margin), 12, self.CARD_BG, self.CARD_BORDER)

        if not data or sum(data.values()) == 0:
            draw.text((width//2 - 50, height//2), "Ma'lumot yo'q", font=self.font_regular_md, fill=self.TEXT_MUTED)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return buf

        total = sum(data.values())
        start_angle = -90

        cx, cy = 280, 310
        radius = 140
        inner_radius = 70  # Donut effekti uchun

        legend_x = 500
        legend_y = 130

        for i, (label, value) in enumerate(data.items()):
            if value == 0:
                continue

            angle = (value / total) * 360
            end_angle = start_angle + angle

            color = self.PIE_COLORS[i % len(self.PIE_COLORS)]

            draw.pieslice([(cx - radius, cy - radius), (cx + radius, cy + radius)],
                         start=start_angle, end=end_angle, fill=color, outline=self.BG_COLOR, width=2)

            percentage = (value / total) * 100
            legend_text = f"{label}: {value} ({percentage:.1f}%)"

            self._draw_rounded_rect(draw, (legend_x, legend_y + i * 40, legend_x + 20, legend_y + i * 40 + 20), 4, color)
            draw.text((legend_x + 30, legend_y + i * 40), legend_text, font=self.font_regular_md, fill=self.TEXT_PRIMARY)

            start_angle = end_angle

        draw.ellipse([(cx - inner_radius, cy - inner_radius), (cx + inner_radius, cy + inner_radius)], fill=self.CARD_BG)

        total_text = f"{total}"
        total_bbox = draw.textbbox((0, 0), total_text, font=self.font_bold_lg)
        total_w = total_bbox[2] - total_bbox[0]
        draw.text((cx - total_w // 2, cy - 15), total_text, font=self.font_bold_lg, fill=self.TEXT_PRIMARY)
        draw.text((cx - 15, cy + 20), "Jami", font=self.font_regular_xs, fill=self.TEXT_MUTED)

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf

drawer = StatDrawer()

@statistic_router.callback_query(F.data == "admin:stats_menu", IsAdmin())
async def admin_stats_menu_handler(callback: types.CallbackQuery):
    """Statistika bo'limining asosiy menyusini (2-1) ko'rsatadi."""
    text = "📊 <b>Statistika bo'limi</b>\n\nKerakli bo'limni tanlang:"
    keyboard = get_stats_menu_keyboard()

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)

    await callback.answer()

async def _format_stats_text(
    detailed_stats: dict,
    new_user_stats: dict,
    posts_stats: dict,
    lang_dist: dict,
    active_users: dict,
    total_errors: int,
    current_time
) -> str:
    """Statistika ma'lumotlaridan formatlangan matn yaratadi."""
    time_str = current_time.strftime('%d.%m.%Y %H:%M')
    status_line = f" <b>( {time_str} )</b>"

    lang_block_parts = ["<b>🏴 Tillar boʻyicha taqsimot:</b>"]
    lang_map = {
        'uzl': 'UZ 🇺🇿', 'uzk': 'ЎЗ 🇺🇿', 'ru': 'RU 🇷🇺', 'en': 'EN 🇬🇧',
        'kz': 'KZ 🇰🇿', 'az': 'AZ 🇦🇿', 'tr': 'TR 🇹🇷', 'kg': 'KG 🇰🇬',
        'tj': 'TJ 🇹🇯', 'tk': 'TK 🇹🇲',
        None: "Noma'lum"
    }

    total_lang_users = sum(lang_dist.values())

    if lang_dist:
        for lang_code, count in lang_dist.items():
            lang_name = lang_map.get(lang_code, lang_code)
            percentage = int((count / total_lang_users) * 100) if total_lang_users > 0 else 0
            lang_block_parts.append(f"  - {lang_name} : {count} ta ({percentage}%)")
    else:
        lang_block_parts.append("Tillar bo'yicha ma'lumot yo'q.")

    lang_text = "\n".join(lang_block_parts)

    return (
        f"<b>📊 Bot Statistikasi</b>\n\n"
        f"<b>👥 Jami foydalanuvchilar:</b> {detailed_stats.get('total_users', 0)} ta{status_line}\n\n"
        f"<b>📈 Yangi a'zolar:</b>\n"
        f"  - Bugun: {new_user_stats.get('daily', 0)} ta\n"
        f"  - Shu hafta: {new_user_stats.get('weekly', 0)} ta\n"
        f"  - Shu oy: {new_user_stats.get('monthly', 0)} ta\n\n"
        f"<b>🏃‍♂️ Faol a'zolar:</b>\n"
        f"  - Bugun: {active_users.get('daily', 0)} ta\n"
        f"  - Shu hafta: {active_users.get('weekly', 0)} ta\n"
        f"  - Shu oy: {active_users.get('monthly', 0)} ta\n\n"
        f"{lang_text}\n\n"
        f"<b>✍️ Yaratilgan postlar:</b>\n"
        f"  - Jami: {posts_stats.get('total', 0)} ta\n"
        f"  - Bugun: {posts_stats.get('daily', 0)} ta\n"
        f"  - Shu hafta: {posts_stats.get('weekly', 0)} ta\n"
        f"  - Shu oy: {posts_stats.get('monthly', 0)} ta\n\n"
        f"<b>⚙️ Tizim holati:</b>\n"
        f"  - Qayd etilgan xatolar: {total_errors} ta"
    )

@statistic_router.callback_query(F.data == "admin:stats:general_text", IsAdmin())
async def show_general_text_stats(callback: types.CallbackQuery):
    await callback.answer("⏳ Ma'lumotlar yuklanmoqda...")

    detailed_stats = await get_detailed_user_stats(config.ADMIN_IDS)
    new_user_stats = await get_new_users_stats_extended(config.ADMIN_IDS)
    posts_stats = await get_posts_stats(config.ADMIN_IDS)
    lang_dist = await get_language_distribution(config.ADMIN_IDS)
    active_users = await get_active_users_by_period(config.ADMIN_IDS)
    total_errors = await get_total_errors_count()

    current_time = get_now()

    text = await _format_stats_text(
        detailed_stats, new_user_stats, posts_stats, lang_dist,
        active_users, total_errors, current_time
    )

    keyboard = get_back_navigation_keyboard("admin:stats_menu")

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)

@statistic_router.callback_query(F.data == "admin:stats:graphics_menu", IsAdmin())
async def show_graphics_menu(callback: types.CallbackQuery):
    text = "📈 <b>Grafika bo'limi</b>\n\nQanday turdagi grafikani ko'rmoqchisiz?"
    keyboard = get_graphics_menu_keyboard()

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

@statistic_router.callback_query(F.data == "admin:stats:dashboard", IsAdmin())
async def show_dashboard_handler(callback: types.CallbackQuery):
    await callback.answer("📊 Dashboard yuklanmoqda...")
    stats = await get_detailed_user_stats(config.ADMIN_IDS)
    image_buffer = drawer.draw_dashboard(stats)
    photo_file = BufferedInputFile(image_buffer.read(), filename="dashboard.png")

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_file,
        caption="📊 <b>Asosiy Dashboard</b>",
        reply_markup=get_back_navigation_keyboard("admin:stats:graphics_menu")
    )

@statistic_router.callback_query(F.data == "admin:stats:users_menu", IsAdmin())
async def show_users_menu(callback: types.CallbackQuery):
    text = "👥 <b>A'zolar statistikasi</b>\n\nQaysi davr yoki turni ko'rmoqchisiz?"
    keyboard = get_users_stats_keyboard()
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

@statistic_router.callback_query(F.data == "admin:stats:users:monthly", IsAdmin())
async def show_users_monthly(callback: types.CallbackQuery):
    await callback.answer("Grafik chizilmoqda...")
    dates, users, _ = await get_daily_stats_for_graph(30)
    image_buffer = drawer.draw_line_chart("👥 Yangi a'zolar (30 kun)", dates, users)
    photo_file = BufferedInputFile(image_buffer.read(), filename="users_monthly.png")

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_file,
        caption="📈 <b>30 kunlik a'zolar o'sishi</b>",
        reply_markup=get_back_navigation_keyboard("admin:stats:users_menu")
    )

@statistic_router.callback_query(F.data == "admin:stats:users:weekly", IsAdmin())
async def show_users_weekly(callback: types.CallbackQuery):
    await callback.answer("Grafik chizilmoqda...")
    labels, values = await get_weekly_activity(config.ADMIN_IDS)
    image_buffer = drawer.draw_bar_chart("📅 Haftalik faollik", labels, values)
    photo_file = BufferedInputFile(image_buffer.read(), filename="users_weekly.png")

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_file,
        caption="📅 <b>Hafta kunlari bo'yicha faollik</b>",
        reply_markup=get_back_navigation_keyboard("admin:stats:users_menu")
    )

@statistic_router.callback_query(F.data == "admin:stats:users:hourly", IsAdmin())
async def show_users_hourly(callback: types.CallbackQuery):
    await callback.answer("Grafik chizilmoqda...")
    labels, values = await get_daily_hours_activity(config.ADMIN_IDS)
    image_buffer = drawer.draw_bar_chart("🕒 Kunlik faollik soatlari", labels, values)
    photo_file = BufferedInputFile(image_buffer.read(), filename="users_hourly.png")

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_file,
        caption="🕒 <b>Soatlar bo'yicha faollik</b>",
        reply_markup=get_back_navigation_keyboard("admin:stats:users_menu")
    )

@statistic_router.callback_query(F.data == "admin:stats:langs_menu", IsAdmin())
async def show_langs_stats(callback: types.CallbackQuery):
    await callback.answer("Grafik chizilmoqda...")
    data = await get_language_distribution(config.ADMIN_IDS)
    image_buffer = drawer.draw_pie_chart("🌍 Tillar taqsimoti", data)
    photo_file = BufferedInputFile(image_buffer.read(), filename="langs_pie.png")

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_file,
        caption="🌍 <b>Foydalanuvchilar tili</b>",
        reply_markup=get_back_navigation_keyboard("admin:stats:graphics_menu")
    )

@statistic_router.callback_query(F.data == "admin:stats:posts_menu", IsAdmin())
async def show_posts_menu(callback: types.CallbackQuery):
    text = "📝 <b>Postlar statistikasi</b>\n\nQaysi ma'lumotni ko'rmoqchisiz?"
    keyboard = get_posts_stats_keyboard()
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

@statistic_router.callback_query(F.data == "admin:stats:posts:monthly", IsAdmin())
async def show_posts_monthly(callback: types.CallbackQuery):
    await callback.answer("Grafik chizilmoqda...")
    dates, _, posts = await get_daily_stats_for_graph(30)
    image_buffer = drawer.draw_line_chart("📝 Yaratilgan postlar (30 kun)", dates, posts)
    photo_file = BufferedInputFile(image_buffer.read(), filename="posts_monthly.png")

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_file,
        caption="📈 <b>30 kunlik postlar statistikasi</b>",
        reply_markup=get_back_navigation_keyboard("admin:stats:posts_menu")
    )

@statistic_router.callback_query(F.data == "admin:stats:posts:formats", IsAdmin())
async def show_posts_formats(callback: types.CallbackQuery):
    await callback.answer("Grafik chizilmoqda...")
    data = await get_post_formats(config.ADMIN_IDS)
    image_buffer = drawer.draw_pie_chart("📄 Post formatlari", data)
    photo_file = BufferedInputFile(image_buffer.read(), filename="posts_formats.png")

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_file,
        caption="📄 <b>Post turlari</b>",
        reply_markup=get_back_navigation_keyboard("admin:stats:posts_menu")
    )

@statistic_router.callback_query(F.data == "admin:stats:posts:buttons", IsAdmin())
async def show_posts_buttons(callback: types.CallbackQuery):
    await callback.answer("Grafik chizilmoqda...")
    data = await get_button_stats(config.ADMIN_IDS)
    image_buffer = drawer.draw_bar_chart("🔘 Tugmalar ishlatilishi", list(data.keys()), list(data.values()))
    photo_file = BufferedInputFile(image_buffer.read(), filename="posts_buttons.png")

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo_file,
        caption="🔘 <b>Postlarda tugmalar soni</b>",
        reply_markup=get_back_navigation_keyboard("admin:stats:posts_menu")
    )


@statistic_router.callback_query(F.data == "admin:stats:db_tables", IsAdmin())
async def show_db_tables_stats(callback: types.CallbackQuery):
    """Barcha jadval va ularning qatorlar sonini ko'rsatadi."""
    await callback.answer("📊 Ma'lumotlar bazasi statistikasi...")
    
    table_stats = await get_database_table_stats()
    
    text = "<b>📊 Ma'lumotlar bazasi jadvallari</b>\n\n"
    
    total_rows = 0
    for table_name, count in table_stats.items():
        text += f"  • {table_name}: <code>{count}</code>\n"
        total_rows += count
    
    text += f"\n<b>Jami qatorlar:</b> {total_rows}"
    
    keyboard = get_back_navigation_keyboard("admin:stats_menu")
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()
