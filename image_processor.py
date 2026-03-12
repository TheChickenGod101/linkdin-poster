from PIL import Image
import os


def strip_metadata(image_path: str) -> str:
    """
    Strips all EXIF/metadata from the image and saves a clean copy.
    Returns the path to the clean image (overwrites original).
    """
    with Image.open(image_path) as img:
        # Convert to RGB to ensure no palette/alpha issues on LinkedIn
        clean = img.convert("RGB")

        # Re-save without any metadata — Pillow does not copy EXIF by default
        # when you don't pass exif= kwarg, so this is a clean save
        clean.save(image_path, format="PNG", optimize=True)

    print(f"[image_processor] Metadata stripped: {image_path}")
    return image_path


def verify_no_metadata(image_path: str) -> None:
    """Prints a confirmation that no EXIF data is present (for debugging)."""
    with Image.open(image_path) as img:
        exif = img.getexif()
        if exif:
            print(f"[image_processor] WARNING: {len(exif)} EXIF tags still present.")
        else:
            print("[image_processor] Confirmed: no EXIF metadata in image.")
