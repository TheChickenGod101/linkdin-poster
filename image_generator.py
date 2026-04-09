import base64
import os
import random
from datetime import datetime
from openai import OpenAI
from config import OPENAI_API_KEY, IMAGES_DIR, IMAGE_STYLES


def generate_quote_image(quote: str, author: str, scene: str = "") -> str:
    """
    Generates an image with gpt-image-1 HD where the AI renders the quote
    and author attribution directly onto the image.
    Returns the local file path.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    background = scene if scene else random.choice(IMAGE_STYLES)

    prompt = (
        f"{background}. "
        f"Overlay this quote directly on the image as beautifully rendered typography: "
        f'"{quote}" — {author}. '
        f"Choose a typography style, font pairing, layout, and color treatment that feels premium and editorial — "
        f"something you would see on a high-end LinkedIn post or magazine spread. "
        f"The design should feel intentional and cohesive with the background: if the scene is dark and moody, "
        f"use light elegant text; if bright and airy, use deep rich lettering. "
        f"The quote and attribution should be clearly legible, well-spaced, and visually balanced. "
        f"No watermarks, no logos, no extra text, no people, no faces. "
        f"Professional quality, scroll-stopping visual."
    )

    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024",
        quality="high",
        n=1,
    )

    os.makedirs(IMAGES_DIR, exist_ok=True)
    safe_author = "".join(c for c in author if c.isalnum() or c in " _-").strip().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    file_path = os.path.join(IMAGES_DIR, f"quote_{safe_author}_{timestamp}.png")

    img_data = base64.b64decode(response.data[0].b64_json)
    with open(file_path, "wb") as f:
        f.write(img_data)

    print(f"[image_generator] Image saved: {file_path}")
    return file_path
