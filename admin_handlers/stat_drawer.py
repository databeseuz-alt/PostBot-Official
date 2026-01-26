#--- START OF FILE admin_handlers/stat_drawer.py ---
import io
import math
from PIL import Image, ImageDraw, ImageFont

class StatDrawer:
    def __init__(self):
        # Ranglar palitrasi (TGStat uslubi)
        self.BG_COLOR = "#F0F2F5"       # Fon rangi (och kulrang)
        self.CARD_COLOR = "#FFFFFF"     # Kartochka foni (oq)
        self.TEXT_COLOR = "#000000"     # Asosiy matn
        self.SUBTEXT_COLOR = "#8C96A0"  # Yordamchi matn
        self.ACCENT_COLOR = "#E8B837"   # Asosiy grafik rangi (Sariq/Oltin)
        self.ACCENT_SEC = "#2AABEE"     # Ikkinchi rang (Telegram ko'ki)
        self.GRID_COLOR = "#E6E6E6"     # Setka rangi
        
        # Fontlarni yuklashga harakat qilamiz
        # Agar tizimda font bo'lmasa, default font ishlatiladi (kichikroq bo'lishi mumkin)
        self.font = ImageFont.load_default()
        try:
            # Linux serverlar uchun keng tarqalgan font yo'li
            self.title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
            self.header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
            self.main_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            self.small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            # Windows yoki font topilmagan holat uchun
            self.title_font = ImageFont.load_default()
            self.header_font = ImageFont.load_default()
            self.main_font = ImageFont.load_default()
            self.small_font = ImageFont.load_default()

    def _draw_header(self, draw, width, title, subtitle=None):
        """Rasmning yuqori qismini chizish"""
        draw.rectangle([(0, 0), (width, 80)], fill=self.CARD_COLOR)
        
        # Sarlavha
        draw.text((20, 20), title, font=self.title_font, fill=self.TEXT_COLOR)
        
        # Taglavha (agar bo'lsa)
        if subtitle:
            # Sarlavha balandligini hisobga olib pastroqqa yozamiz
            # Default fontda getbbox ishlamasligi mumkin, shuning uchun taxminiy joy
            draw.text((20, 55), subtitle, font=self.small_font, fill=self.SUBTEXT_COLOR)
        
        # Ajratuvchi chiziq
        draw.line([(0, 80), (width, 80)], fill="#E0E0E0", width=1)

    def _draw_card(self, draw, x, y, w, h, title, value, sub_value=None, is_highlighted=False):
        """Statistika kartochkasini chizish"""
        # Soya effekti
        shadow_offset = 3
        draw.rectangle([(x+shadow_offset, y+shadow_offset), (x+w+shadow_offset, y+h+shadow_offset)], fill="#D1D5DA")
        
        # Asosiy karta
        bg_color = self.CARD_COLOR if not is_highlighted else "#FFF9E6" # Sariqroq fon
        draw.rectangle([(x, y), (x+w, y+h)], fill=bg_color)
        draw.rectangle([(x, y), (x+w, y+h)], outline="#E0E0E0", width=1)
        
        # Matnlar
        draw.text((x+15, y+15), title, font=self.small_font, fill=self.SUBTEXT_COLOR)
        draw.text((x+15, y+40), str(value), font=self.header_font, fill=self.TEXT_COLOR)
        
        if sub_value:
            color = self.ACCENT_SEC if "+" in str(sub_value) else self.SUBTEXT_COLOR
            draw.text((x+15, y+70), str(sub_value), font=self.small_font, fill=color)

    def draw_dashboard(self, stats: dict) -> io.BytesIO:
        """Asosiy Dashboard chizish"""
        width, height = 800, 600
        img = Image.new('RGB', (width, height), self.BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        self._draw_header(draw, width, "📊 Dashboard", "Botning umumiy holati")
        
        # Kartochkalar (2x2 grid)
        margin = 20
        card_w = (width - 3 * margin) // 2
        card_h = 110
        start_y = 100
        
        # 1. Jami obunachilar
        self._draw_card(draw, margin, start_y, card_w, card_h, 
                       "Jami obunachilar", 
                       f"{stats.get('total_users', 0):,}", 
                       f"+{stats.get('today_users', 0)} bugun")
                       
        # 2. Faol foydalanuvchilar
        self._draw_card(draw, margin*2 + card_w, start_y, card_w, card_h, 
                       "Faol (bloklamagan)", 
                       f"{stats.get('active_users', 0):,}")
        
        # 3. Jami postlar
        self._draw_card(draw, margin, start_y + card_h + margin, card_w, card_h, 
                       "Jami postlar", 
                       f"{stats.get('total_posts', 0):,}",
                       f"+{stats.get('today_posts', 0)} bugun")
                       
        # 4. Top til
        self._draw_card(draw, margin*2 + card_w, start_y + card_h + margin, card_w, card_h, 
                       "Asosiy til", 
                       str(stats.get('top_lang', 'N/A')).upper())

        # Mini grafik (So'nggi 7 kun)
        graph_y = start_y + 2*card_h + 2*margin
        graph_h = height - graph_y - margin
        
        draw.rectangle([(margin, graph_y), (width-margin, height-margin)], fill=self.CARD_COLOR)
        draw.text((margin+15, graph_y+15), "So'nggi 7 kunlik o'sish dinamikasi", font=self.main_font, fill=self.TEXT_COLOR)
        
        # Grafik ma'lumotlari
        data = stats.get('last_7_days', [])
        if data and max(data) > 0:
            self._draw_simple_line_chart(draw, margin+20, graph_y+50, width-2*margin-40, graph_h-70, data)
        else:
            draw.text((width//2-50, graph_y + graph_h//2), "Ma'lumot yo'q", font=self.main_font, fill=self.SUBTEXT_COLOR)

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf

    def draw_line_chart(self, title: str, dates: list, values: list) -> io.BytesIO:
        """Chiziqli grafik chizish (30 kunlik o'sish va postlar uchun)"""
        width, height = 900, 500
        img = Image.new('RGB', (width, height), self.BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        self._draw_header(draw, width, title)
        
        # Grafik maydoni
        margin = 30
        chart_x = margin + 40 # Y o'qi yozuvlari uchun joy
        chart_y = 120
        chart_w = width - chart_x - margin
        chart_h = height - chart_y - 50 # X o'qi yozuvlari uchun joy
        
        # Oq fon
        draw.rectangle([(margin, 100), (width-margin, height-margin)], fill=self.CARD_COLOR)
        
        if not values or max(values) == 0:
            draw.text((width//2 - 50, height//2), "Ma'lumot yetarli emas", font=self.main_font, fill=self.TEXT_COLOR)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return buf

        self._draw_simple_line_chart(draw, chart_x, chart_y, chart_w, chart_h, values, dates)
        
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf

    def _draw_simple_line_chart(self, draw, x, y, w, h, values, labels=None):
        """Ichki yordamchi funksiya: Chiziqlarni chizish"""
        max_val = max(values)
        min_val = min(values)
        
        # Agar hamma qiymatlar bir xil bo'lsa (masalan 0), masshtabni to'g'irlash
        if max_val == min_val:
            max_val += 1
            min_val -= 1
            if min_val < 0: min_val = 0

        val_range = max_val - min_val
        
        # Koordinatalarni hisoblash
        points = []
        step_x = w / (len(values) - 1) if len(values) > 1 else w
        
        for i, val in enumerate(values):
            px = x + i * step_x
            # Y o'qi teskari (yuqoriga qarab o'sadi)
            py = y + h - ((val - min_val) / val_range * h)
            points.append((px, py))
            
            # X o'qi yozuvlari (faqat ba'zilarini ko'rsatish)
            if labels and i < len(labels):
                # Har 5-sana yoki agar joy yetarli bo'lsa
                if len(values) <= 10 or i % 5 == 0 or i == len(values)-1:
                    draw.text((px - 15, y + h + 10), labels[i], font=self.small_font, fill=self.SUBTEXT_COLOR)

        # Orqa fon chiziqlari (Grid)
        for i in range(5):
            line_y = y + (i * h / 4)
            draw.line([(x, line_y), (x+w, line_y)], fill=self.GRID_COLOR, width=1)
            # Qiymatlar (Y o'qi)
            val_text = f"{int(max_val - (i * val_range / 4))}"
            draw.text((x - 35, line_y - 6), val_text, font=self.small_font, fill=self.SUBTEXT_COLOR)

        # Asosiy grafik chizig'i
        if len(points) > 1:
            draw.line(points, fill=self.ACCENT_COLOR, width=3, joint='curve')
            
            # Nuqtalarni chizish
            for p in points:
                draw.ellipse((p[0]-3, p[1]-3, p[0]+3, p[1]+3), fill="#FFFFFF", outline=self.ACCENT_COLOR, width=2)

    def draw_bar_chart(self, title: str, labels: list, values: list) -> io.BytesIO:
        """Ustunli diagramma chizish (Haftalik faollik va h.k.)"""
        width, height = 800, 500
        img = Image.new('RGB', (width, height), self.BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        self._draw_header(draw, width, title)
        
        margin = 30
        chart_x = margin + 30
        chart_y = 120
        chart_w = width - chart_x - margin
        chart_h = height - chart_y - 40
        
        draw.rectangle([(margin, 100), (width-margin, height-margin)], fill=self.CARD_COLOR)
        
        if not values or max(values) == 0:
            draw.text((width//2 - 50, height//2), "Ma'lumot yo'q", font=self.main_font, fill=self.TEXT_COLOR)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return buf

        max_val = max(values)
        bar_width = (chart_w / len(values)) * 0.6
        spacing = (chart_w / len(values)) * 0.4
        
        for i, (label, val) in enumerate(zip(labels, values)):
            bar_h = (val / max_val) * chart_h
            x0 = chart_x + i * (bar_width + spacing) + spacing/2
            y0 = chart_y + chart_h - bar_h
            x1 = x0 + bar_width
            y1 = chart_y + chart_h
            
            # Ustunni chizish
            draw.rectangle([x0, y0, x1, y1], fill=self.ACCENT_SEC)
            
            # Qiymatni ustiga yozish
            val_text = str(val)
            text_w = draw.textlength(val_text, font=self.small_font)
            draw.text((x0 + (bar_width-text_w)/2, y0 - 15), val_text, font=self.small_font, fill=self.TEXT_COLOR)
            
            # Labelni pastga yozish
            draw.text((x0 + (bar_width-draw.textlength(str(label), font=self.small_font))/2, y1 + 5), str(label), font=self.small_font, fill=self.SUBTEXT_COLOR)

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf

    def draw_pie_chart(self, title: str, data: dict) -> io.BytesIO:
        """Doiraviy diagramma (Pie Chart) chizish"""
        width, height = 800, 500
        img = Image.new('RGB', (width, height), self.BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        self._draw_header(draw, width, title)
        draw.rectangle([(20, 100), (width-20, height-20)], fill=self.CARD_COLOR)
        
        if not data or sum(data.values()) == 0:
            draw.text((width//2 - 50, height//2), "Ma'lumot yo'q", font=self.main_font, fill=self.TEXT_COLOR)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return buf

        # Ranglar palitrasi
        colors = ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF", "#FF9F40", "#C9CBCF"]
        
        total = sum(data.values())
        start_angle = -90
        
        # Doira markazi va radiusi
        cx, cy = 250, 300
        radius = 150
        
        legend_x = 500
        legend_y = 150
        
        for i, (label, value) in enumerate(data.items()):
            if value == 0: continue
            
            angle = (value / total) * 360
            end_angle = start_angle + angle
            
            color = colors[i % len(colors)]
            
            # Sektorni chizish
            draw.pieslice([(cx-radius, cy-radius), (cx+radius, cy+radius)], 
                         start=start_angle, end=end_angle, fill=color, outline="white")
            
            # Legendani chizish
            percentage = (value / total) * 100
            legend_text = f"{label}: {value} ({percentage:.1f}%)"
            
            draw.rectangle([(legend_x, legend_y + i*30), (legend_x+15, legend_y + i*30 + 15)], fill=color)
            draw.text((legend_x + 25, legend_y + i*30), legend_text, font=self.main_font, fill=self.TEXT_COLOR)
            
            start_angle = end_angle

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf
#--- END OF FILE admin_handlers/stat_drawer.py ---
