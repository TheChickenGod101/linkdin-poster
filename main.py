"""
main.py — Run once to generate and post one quote immediately.
For daily automation use scheduler.py instead.
"""

import os
import sys
from quote_generator import generate_quote
from image_generator import generate_quote_image
from image_processor import strip_metadata, verify_no_metadata
from linkedin_poster import post_to_linkedin
from quote_tracker import save_used_quote, is_quote_used
import config


def check_config() -> bool:
    missing = []
    if not config.ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not config.OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if not config.LINKEDIN_ACCESS_TOKEN:
        missing.append("LINKEDIN_ACCESS_TOKEN")
    if not config.LINKEDIN_PERSON_URN:
        missing.append("LINKEDIN_PERSON_URN")

    if missing:
        print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your keys.")
        return False
    return True


def run_daily_post() -> None:
    print("=" * 60)
    print("LinkedIn Quote Poster — Starting daily post")
    print("=" * 60)

    if not check_config():
        sys.exit(1)

    # 1. Generate a fresh quote
    print("\n[1/5] Generating quote...")
    attempts = 0
    quote_data = None
    while attempts < 5:
        data = generate_quote()
        if not is_quote_used(data["quote"]):
            quote_data = data
            break
        print(f"  Quote already used, retrying... ({attempts + 1}/5)")
        attempts += 1

    if quote_data is None:
        print("[ERROR] Could not generate a unique quote after 5 attempts.")
        sys.exit(1)

    quote = quote_data["quote"]
    author = quote_data["author"]
    description = quote_data["description"]
    scene = quote_data.get("scene", "")

    print(f'  Quote: "{quote}" — {author}')
    if scene:
        print(f'  Scene: {scene[:80]}...')

    # 2. Generate image
    print("\n[2/5] Generating image with gpt-image-1 HD (mood-matched)...")
    image_path = generate_quote_image(quote, author, scene)

    # 3. Strip metadata
    print("\n[3/5] Stripping image metadata...")
    strip_metadata(image_path)
    verify_no_metadata(image_path)

    # 4. Post to LinkedIn
    print("\n[4/5] Posting to LinkedIn...")
    post_urn = post_to_linkedin(image_path, quote, author, description)
    print(f"  Post URN: {post_urn}")

    # 5. Save the quote as used
    print("\n[5/5] Recording used quote...")
    save_used_quote(quote, author)

    # Clean up the image file
    os.remove(image_path)
    print(f"  Cleaned up local image: {image_path}")

    print("\n✓ Done! Post published successfully.")


if __name__ == "__main__":
    run_daily_post()
