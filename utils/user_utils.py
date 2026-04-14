import random
import string
import qrcode
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime

class UserUtils:
    @staticmethod
    def generate_phone():
        # 전화번호: 4자리 숫자+기호 조합 자동 발급 (예: 3#7*) — 중복 없이 생성
        chars = string.digits + "#*"
        return ''.join(random.choices(chars, k=4))

    @staticmethod
    def generate_resident_id(name, school_info):
        # 주민번호 형식: KR-[학교명]-[학년반]-[이름]
        from utils.csv_manager import CSVManager
        prefix = CSVManager.get_config('country_id_prefix') or 'KR'

        parts = school_info.split()
        school = parts[0] if len(parts) > 0 else "미정"
        grade_class = parts[1] if len(parts) > 1 else "0-0"
        return f"{prefix}-{school}-{grade_class}-{name}"

    @staticmethod
    def create_id_card(user):
        # user: dict containing name, birth, resident_id, school_info, phone, grade
        card_width = 1000
        card_height = 600
        background_color = (173, 216, 230) # Light blue theme
        card = Image.new('RGB', (card_width, card_height), background_color)
        draw = ImageDraw.Draw(card)

        # Draw border
        draw.rectangle([10, 10, card_width-10, card_height-10], outline=(0, 0, 128), width=5)

        try:
            # Attempt to find a Korean font.
            paths = [
                "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
            ]
            font_path = next((p for p in paths if os.path.exists(p)), None)

            if font_path:
                title_font = ImageFont.truetype(font_path, 70)
                text_font = ImageFont.truetype(font_path, 40)
            else:
                title_font = ImageFont.load_default()
                text_font = ImageFont.load_default()
        except:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()

        # Draw Title
        draw.text((400, 40), "주민등록증", fill=(0, 0, 0), font=title_font)

        # Draw User Info
        info_x = 420
        draw.text((info_x, 140), f"성명: {user['name']}", fill=(0, 0, 0), font=text_font)
        draw.text((info_x, 200), f"생년월일: {user['birth']}", fill=(0, 0, 0), font=text_font)
        draw.text((info_x, 260), f"주민번호: {user['resident_id']}", fill=(0, 0, 0), font=text_font)
        draw.text((info_x, 320), f"학적: {user['school_info']}", fill=(0, 0, 0), font=text_font)
        draw.text((info_x, 380), f"전화: {user['phone']}", fill=(0, 0, 0), font=text_font)
        draw.text((info_x, 440), f"등급: {user['grade']}", fill=(0, 0, 0), font=text_font)

        # Generate QR Code (encoded resident ID + unique ID)
        qr_data = f"RES_ID:{user['resident_id']}|ID:{user.get('login_id', 'unknown')}"
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.resize((300, 300))

        # Paste QR Code
        card.paste(qr_img, (50, 150))

        save_path = f"static/uploads/id_cards/{user['name']}_id.png"
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        card.save(save_path)
        return save_path
