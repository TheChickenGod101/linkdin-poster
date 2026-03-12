import os
import random
import requests
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from config import OPENAI_API_KEY, IMAGES_DIR, IMAGE_STYLES

# Windows system fonts, tried in order until one loads
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    # Windows fallbacks (for local dev)
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size=size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _wrap_by_pixels(text: str, font: ImageFont.FreeTypeFont, max_px: int) -> list[str]:
    """Wrap text so each line fits within max_px pixels wide."""
    # Use a tiny dummy image just for measuring text width
    dummy = Image.new("RGB", (1, 1))
    d = ImageDraw.Draw(dummy)

    words = text.split()
    lines = []
    current: list[str] = []

    for word in words:
        test = " ".join(current + [word])
        w = d.textbbox((0, 0), test, font=font)[2]
        if w <= max_px or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]

    if current:
        lines.append(" ".join(current))
    return lines


def _add_text_overlay(image_path: str, quote: str, author: str) -> None:
    """Overlay the quote text on the image using Pillow for clean, reliable rendering."""
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size

    # Horizontal padding: 7% each side so text never touches the edge
    padding = int(width * 0.07)
    max_text_px = width - padding * 2

    # Font sizes — slightly smaller so long quotes still fit nicely
    quote_size = int(width * 0.048)   # ~49px on 1024px
    author_size = int(width * 0.034)  # ~35px

    quote_font = _load_font(quote_size)
    author_font = _load_font(author_size)

    # Pixel-accurate wrapping
    lines = _wrap_by_pixels(f'"{quote}"', quote_font, max_text_px)

    line_h = int(quote_size * 1.38)
    author_h = int(author_size * 1.38)
    total_text_h = len(lines) * line_h + 14 + author_h

    # Dark gradient covers text area + breathing room above and below
    overlay_h = total_text_h + int(height * 0.14)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for y in range(overlay_h):
        progress = y / overlay_h
        alpha = int(200 * (1 - progress ** 0.65))
        draw.rectangle([(0, y), (width, y + 1)], fill=(0, 0, 0, alpha))

    cx = width // 2
    start_y = int(height * 0.07)

    def shadowed(pos, text, font, fill, s=3):
        draw.text((pos[0] + s, pos[1] + s), text, font=font,
                  fill=(0, 0, 0, 210), anchor="mt", align="center")
        draw.text(pos, text, font=font, fill=fill, anchor="mt", align="center")

    for i, line in enumerate(lines):
        shadowed((cx, start_y + i * line_h), line, quote_font,
                 fill=(255, 250, 235, 255))

    author_y = start_y + len(lines) * line_h + 14
    shadowed((cx, author_y), f"— {author}", author_font,
             fill=(255, 215, 80, 255), s=2)

    result = Image.alpha_composite(img, overlay).convert("RGB")
    result.save(image_path, format="PNG", optimize=True)


def generate_quote_image(quote: str, author: str, scene: str = "") -> str:
    """
    1. Generates a background scene with DALL-E 3 HD matched to the quote's mood.
    2. Overlays the quote and author using Pillow for pixel-perfect text.
    Returns the local file path.
    """
    from datetime import datetime
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Use the quote-matched scene if provided, otherwise fall back to a random style
    background = scene if scene else random.choice(IMAGE_STYLES)

    prompt = (
        f"{background}. "
        f"No text, no words, no letters, no watermarks, no logos, no people, no faces. "
        f"Clean open composition with uncluttered space in the upper portion. "
        f"LinkedIn-worthy, professional quality, visually stunning."
    )

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="hd",
        n=1,
    )

    os.makedirs(IMAGES_DIR, exist_ok=True)
    safe_author = "".join(c for c in author if c.isalnum() or c in " _-").strip().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    file_path = os.path.join(IMAGES_DIR, f"quote_{safe_author}_{timestamp}.png")

    img_data = requests.get(response.data[0].url, timeout=30).content
    with open(file_path, "wb") as f:
        f.write(img_data)

    _add_text_overlay(file_path, quote, author)

    print(f"[image_generator] Image saved: {file_path}")
    return file_path
