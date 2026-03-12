import requests
import config

# LinkedIn API version — required by the new Posts API
_LI_VERSION = "202503"


def _get_headers(content_type: str = "application/json") -> dict:
    return {
        "Authorization": f"Bearer {config.LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": content_type,
        "LinkedIn-Version": _LI_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }


def _initialize_image_upload() -> tuple[str, str]:
    """
    Initializes an image upload with the new LinkedIn Images API.
    Returns (upload_url, image_urn).
    """
    url = "https://api.linkedin.com/v2/images?action=initializeUpload"
    payload = {
        "initializeUploadRequest": {
            "owner": config.LINKEDIN_PERSON_URN,
        }
    }

    resp = requests.post(url, json=payload, headers=_get_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()

    upload_url = data["value"]["uploadUrl"]
    image_urn = data["value"]["image"]

    print(f"[linkedin] Upload initialized. Image URN: {image_urn}")
    return upload_url, image_urn


def _upload_image(upload_url: str, image_path: str) -> None:
    """Uploads the binary image to LinkedIn's upload URL."""
    with open(image_path, "rb") as f:
        image_data = f.read()

    upload_headers = {
        "Authorization": f"Bearer {config.LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/octet-stream",
    }

    resp = requests.put(upload_url, data=image_data, headers=upload_headers, timeout=60)
    resp.raise_for_status()
    print("[linkedin] Image uploaded successfully.")


def _create_post(image_urn: str, text: str) -> str:
    """
    Creates a LinkedIn post using the new Posts API (/rest/posts).
    Returns the post URN from the response header.
    """
    url = "https://api.linkedin.com/rest/posts"
    payload = {
        "author": config.LINKEDIN_PERSON_URN,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {
            "media": {
                "title": "Quote of the Day",
                "id": image_urn,
            }
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    resp = requests.post(url, json=payload, headers=_get_headers(), timeout=30)
    resp.raise_for_status()

    # New Posts API returns the post URN in the x-restli-id response header
    post_urn = resp.headers.get("x-restli-id", "unknown")
    print(f"[linkedin] Post created: {post_urn}")
    return post_urn


def post_to_linkedin(image_path: str, quote: str, author: str, description: str) -> str:
    """
    Full LinkedIn posting flow: initialize upload → upload image → create post.
    Returns the post URN.
    """
    post_text = (
        f'"{quote}"\n'
        f"— {author}\n\n"
        f"{description}\n\n"
        f"#Inspiration #Motivation #QuoteOfTheDay #Leadership #Mindset"
    )

    upload_url, image_urn = _initialize_image_upload()
    _upload_image(upload_url, image_path)
    post_urn = _create_post(image_urn, post_text)
    return post_urn
