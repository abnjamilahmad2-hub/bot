from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

def create_card(username, subtitle, avatar_url, output_path):
    width = 1100
    height = 350

    img = Image.new("RGB", (width, height), (32, 32, 32))
    draw = ImageDraw.Draw(img)

    # Red side line
    draw.rectangle((0, 0, 18, height), fill=(180, 20, 20))

    # Gray panels
    draw.rounded_rectangle((40, 30, width - 40, height - 30), radius=24, fill=(45, 45, 45))

    # Avatar
    response = requests.get(avatar_url)
    avatar = Image.open(BytesIO(response.content)).convert("RGB")
    avatar = avatar.resize((180, 180))

    img.paste(avatar, (850, 80))

    try:
        font_big = ImageFont.truetype("arial.ttf", 42)
        font_small = ImageFont.truetype("arial.ttf", 26)
    except:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    draw.text((80, 110), username, fill=(255,255,255), font=font_big)
    draw.text((80, 180), subtitle, fill=(200,200,200), font=font_small)

    img.save(output_path)
