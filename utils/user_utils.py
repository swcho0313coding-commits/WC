import random
import string
import qrcode
from PIL import Image, ImageDraw, ImageFont
import os

class UserUtils:
    @staticmethod
    def generate_phone():
        # 4자리 숫자+기호 조합 (예: 3#7*)
        chars = string.digits + "#*"
        return ''.join(random.choices(chars, k=4))

    @staticmethod
    def generate_resident_id(name, school_info):
        # KR-[학교명]-[학년반]-[이름]
        # school_info is expected to be "학교명 학년반" or just "학년반"
        return f"KR-{school_info}-{name}"

    @staticmethod
    def create_id_card(user):
        # user: dict containing name, birth, resident_id, school_info, phone, grade
        card_width = 1000
        card_height = 600
        background_color = (240, 240, 240)
        card = Image.new('RGB', (card_width, card_height), background_color)
        draw = ImageDraw.Draw(card)

        # Load fonts (fallback to default if necessary)
        try:
            # You might need a specific Korean font for correct rendering
            font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
            if not os.path.exists(font_path):
                font_path = "arial.ttf" # Fallback

            title_font = ImageFont.truetype(font_path, 60)
            text_font = ImageFont.truetype(font_path, 40)
        except:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()

        # Draw Title
        draw.text((400, 50), "주민등록증", fill=(0, 0, 0), font=title_font)

        # Draw User Info
        info_x = 450
        draw.text((info_x, 150), f"성명: {user['name']}", fill=(0, 0, 0), font=text_font)
        draw.text((info_x, 220), f"생년월일: {user['birth']}", fill=(0, 0, 0), font=text_font)
        draw.text((info_x, 290), f"주민번호: {user['resident_id']}", fill=(0, 0, 0), font=text_font)
        draw.text((info_x, 360), f"학적: {user['school_info']}", fill=(0, 0, 0), font=text_font)
        draw.text((info_x, 430), f"전화: {user['phone']}", fill=(0, 0, 0), font=text_font)
        draw.text((info_x, 500), f"등급: {user['grade']}", fill=(0, 0, 0), font=text_font)

        # Generate QR Code
        qr_data = f"ID:{user['resident_id']}|NAME:{user['name']}"
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.resize((300, 300))

        # Paste QR Code as "Photo"
        card.paste(qr_img, (50, 150))

        save_path = f"static/uploads/id_cards/{user['name']}_id.png"
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        card.save(save_path)
        return save_path
