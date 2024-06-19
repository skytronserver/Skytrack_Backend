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
    image = Image.new('RGB', (100, 40), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((10, 10), expression, font=font, fill=(0, 0, 0))

    # Convert image to blob
    byte_io = io.BytesIO()
    image.save(byte_io, 'PNG')
    byte_io.seek(0)

    return byte_io, result
