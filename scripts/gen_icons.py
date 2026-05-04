"""Genera iconos PWA: gradiente rosa→dorado con nota musical."""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = os.path.join(os.path.dirname(__file__), '..', 'app', 'static', 'icons')
os.makedirs(OUT, exist_ok=True)

ROSE = (244, 63, 94)
GOLD = (245, 158, 11)


def gradient(size):
    img = Image.new('RGB', (size, size), ROSE)
    px = img.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size)
            r = int(ROSE[0] + (GOLD[0] - ROSE[0]) * t)
            g = int(ROSE[1] + (GOLD[1] - ROSE[1]) * t)
            b = int(ROSE[2] + (GOLD[2] - ROSE[2]) * t)
            px[x, y] = (r, g, b)
    return img


def draw_note(img, scale=1.0, padding_ratio=0.0):
    size = img.size[0]
    d = ImageDraw.Draw(img)
    inner = int(size * (1 - padding_ratio))
    offset = (size - inner) // 2
    font_size = int(inner * 0.7 * scale)
    font = None
    for name in ['seguisym.ttf', 'arial.ttf', 'segoeui.ttf', 'DejaVuSans.ttf']:
        try:
            font = ImageFont.truetype(name, font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    text = '♪'  # nota musical
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) // 2 - bbox[0]
    y = (size - th) // 2 - bbox[1]
    d.text((x, y), text, fill=(255, 255, 255), font=font)
    return img


def rounded(img, radius_ratio=0.22):
    size = img.size[0]
    radius = int(size * radius_ratio)
    mask = Image.new('L', (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, size, size), radius=radius, fill=255)
    rgba = img.convert('RGBA')
    rgba.putalpha(mask)
    return rgba


for s in (192, 512):
    g = gradient(s)
    draw_note(g)
    out = rounded(g)
    out.save(os.path.join(OUT, f'icon-{s}.png'), 'PNG')
    print(f'wrote icon-{s}.png')

mask = gradient(512)
draw_note(mask, scale=0.6, padding_ratio=0.2)
mask.save(os.path.join(OUT, 'icon-maskable-512.png'), 'PNG')
print('wrote icon-maskable-512.png')
