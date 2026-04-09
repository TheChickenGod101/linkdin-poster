import base64
import os
import random
from datetime import datetime
from difflib import SequenceMatcher
from openai import OpenAI
from config import OPENAI_API_KEY, IMAGES_DIR, IMAGE_STYLES

MAX_TRIES = 5
# Accept the image if similarity to the expected quote is at least this high (0–1)
SIMILARITY_THRESHOLD = 0.85


def _similarity(a: str, b: str) -> float:
    """Case-insensitive character-level similarity ratio."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _verify_quote_in_image(client: OpenAI, image_b64: str, quote: str, author: str) -> tuple[bool, str]:
    """
    Ask gpt-4o-mini to read the quote text off the image.
    Returns (ok, reason) where ok=True means the text looks correct.
    """
    expected = f'"{quote}" — {author}'.lower()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Read the quote text and author attribution written on this image. "
                            "Reply with ONLY the exact text you can read, nothing else. "
                            "Include the quote marks and the attribution if present."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                ],
            }
        ],
        max_tokens=300,
    )

    extracted = response.choices[0].message.content.strip()
    similarity = _similarity(expected, extracted)
    ok = similarity >= SIMILARITY_THRESHOLD

    if not ok:
        reason = f"similarity {similarity:.0%} (expected: {expected!r}, got: {extracted!r})"
    else:
        reason = f"similarity {similarity:.0%} — looks good"

    return ok, reason


def generate_quote_image(quote: str, author: str, scene: str = "") -> str:
    """
    Generates an image with gpt-image-1 HD where the AI renders the quote
    and author attribution directly onto the image.
    Verifies the text with gpt-4o-mini vision and retries up to MAX_TRIES times.
    Returns the local file path.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    background = scene if scene else random.choice(IMAGE_STYLES)

    prompt = (
        f"{background}. "
        f"Overlay this exact quote — spelled letter-for-letter correctly — as beautifully rendered typography on the image: "
        f'"{quote}" — {author}. '
        f"Accuracy of the text is critical: every word, comma, and apostrophe must match exactly. "
        f"Choose a typography style, font pairing, layout, and color treatment that feels premium and editorial — "
        f"something you would see on a high-end LinkedIn post or magazine spread. "
        f"The design should feel intentional and cohesive with the background: if the scene is dark and moody, "
        f"use light elegant text; if bright and airy, use deep rich lettering. "
        f"The quote and attribution should be clearly legible, well-spaced, and visually balanced. "
        f"No watermarks, no logos, no extra text, no people, no faces. "
        f"Professional quality, scroll-stopping visual."
    )

    os.makedirs(IMAGES_DIR, exist_ok=True)
    safe_author = "".join(c for c in author if c.isalnum() or c in " _-").strip().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    file_path = os.path.join(IMAGES_DIR, f"quote_{safe_author}_{timestamp}.png")

    for attempt in range(1, MAX_TRIES + 1):
        print(f"[image_generator] Generating image (attempt {attempt}/{MAX_TRIES})…")

        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024",
            quality="high",
            n=1,
        )

        image_b64 = response.data[0].b64_json
        img_data = base64.b64decode(image_b64)

        print(f"[image_generator] Verifying quote text with vision…")
        ok, reason = _verify_quote_in_image(client, image_b64, quote, author)
        print(f"[image_generator] Verification: {reason}")

        if ok:
            with open(file_path, "wb") as f:
                f.write(img_data)
            print(f"[image_generator] Image saved: {file_path}")
            return file_path

        if attempt < MAX_TRIES:
            print(f"[image_generator] Text mismatch — retrying…")

    # All attempts failed — save the last one anyway
    print(f"[image_generator] Warning: could not verify quote after {MAX_TRIES} attempts. Saving last result.")
    with open(file_path, "wb") as f:
        f.write(img_data)
    print(f"[image_generator] Image saved: {file_path}")
    return file_path
