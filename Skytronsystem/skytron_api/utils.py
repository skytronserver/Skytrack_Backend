import random
import io
from PIL import Image, ImageDraw, ImageFont

def generate_captcha():
    # Generate a random mathematical expression
    num1 = random.randint(1, 9)
    num2 = random.randint(1, 9)
    expression = f"{num1} + {num2}"
    result = num1 + num2

    # Create an image with the expression
    image = Image.new('RGB', (200, 80), color=(205, 205, 205))
    draw = ImageDraw.Draw(image) 
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_size = 50  # Change this value to the desired font size
    font = ImageFont.truetype(font_path, font_size)
    draw.text((25, 12), expression, font=font, fill=(0, 0, 0))

    # Convert image to blob
    byte_io = io.BytesIO()
    image.save(byte_io, 'PNG')
    byte_io.seek(0)

    return byte_io, result
