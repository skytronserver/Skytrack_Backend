from functools import lru_cache
import secrets
import io
from PIL import Image, ImageDraw, ImageFont

@lru_cache(maxsize=None)
def _captcha_png(expression):
    """PNG bytes for a captcha expression. Only 81 expressions exist, so each
    is drawn once per process instead of on every captcha request."""
    image = Image.new('RGB', (200, 80), color=(205, 205, 205))
    draw = ImageDraw.Draw(image) 
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_size = 50  # Change this value to the desired font size
    font = ImageFont.truetype(font_path, font_size)
    draw.text((25, 12), expression, font=font, fill=(0, 0, 0))

    byte_io = io.BytesIO()
    image.save(byte_io, 'PNG')
    return byte_io.getvalue()


def generate_captcha(static=False):
    # Generate a random mathematical expression
    if static:
        num1 = 1
        num2 = 1
    else:
        num1 = secrets.randbelow(9) + 1
        num2 = secrets.randbelow(9) + 1
    expression = f"{num1} + {num2}"
    result = num1 + num2

    # Image blob for the expression
    byte_io = io.BytesIO(_captcha_png(expression))

    return byte_io, result
