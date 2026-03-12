import io
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import logging
import qrcode

logger = logging.getLogger(__name__)

from aiogram import Router, types, Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from xdata_handlers.translator import get_text
from xdata_handlers.database import (
    get_user_channels, get_user_language,
    get_user_channel_statistics
)
from post_handlers.xreply_keyboard import get_main_menu
from post_handlers.localize_filter import LocalizedText

statistic_router = Router()


class AddChannelFromStatsCallback(CallbackData, prefix="add_channel_from_stats"):
    action: str


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
        current_date = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
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


async def generate_channel_statistics_image(user_id: int, lang: str = 'uzl', bot_username: str = "PostBot_Bot") -> io.BytesIO:
    """Foydalanuvchining kanal statistikasi rasmini yaratadi."""
    # Statistikani olish
    stats = await get_user_channel_statistics(user_id)
    channels = await get_user_channels(user_id)

    # Kanal nomini olish
    if channels:
        if len(channels) == 1:
            channel_name = channels[0].get('channel_name', 'Kanal')
        else:
            channel_name = f"{len(channels)} ta kanal statistikasi"
    else:
        channel_name = "Kanal statistikasi"

    # Rasmni chizish
    return channel_stat_drawer.draw_channel_stats(channel_name, stats, bot_username)


@statistic_router.message(LocalizedText('statistic_btn'))
async def handle_generate_statistics(message: types.Message, state: FSMContext, bot: Bot):
    """Statistika tugmasi bosilganda statistikani yaratadi (faqat kanal ulaganlar uchun)"""
    user_id = message.from_user.id
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
        builder.adjust(1)
        await message.answer(
            get_text('statistics_no_channel_msg', lang),
            reply_markup=builder.as_markup()
        )
        return

    # Yuklanayotgan xabar
    loading_msg = await message.answer(get_text('generating_statistics_msg', lang))

    try:
        # Bot username ni olish
        bot_info = await bot.get_me()
        bot_username = bot_info.username or "PostBot_Bot"

        # Statistika rasmini yaratish
        img_buffer = await generate_channel_statistics_image(user_id, lang, bot_username)

        # Yuklanish xabarini o'chirish
        await loading_msg.delete()

        # Rasmni yuborish
        img_buffer.seek(0)
        input_file = BufferedInputFile(
            file=img_buffer.read(),
            filename='channel_statistics.png'
        )

        await message.answer_photo(
            photo=input_file,
            caption=get_text('statistics_image_caption', lang),
            reply_markup=await get_main_menu(lang, user_id)
        )

    except Exception as e:
        logger.error(f"Statistika rasmini yaratishda xatolik: {e}")
        # Yuklanish xabarini o'chirish
        try:
            await loading_msg.delete()
        except Exception:
            pass
        await message.answer(
            f"Statistikani yaratishda xatolik yuz berdi: {str(e)}",
            reply_markup=await get_main_menu(lang, user_id)
        )

@statistic_router.callback_query(AddChannelFromStatsCallback.filter(F.action == "add"))
async def handle_add_channel_from_stats(callback: types.CallbackQuery, state: FSMContext):
    """Statistika bo'limidan kanal qo'shish tugmasi bosilganda."""
    await callback.message.delete()
    from post_handlers.send_handler import cmd_add_channel
    await cmd_add_channel(callback.message, state)
    await callback.answer()
