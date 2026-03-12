import anthropic
from quote_tracker import load_used_quotes
from config import ANTHROPIC_API_KEY


def generate_quote() -> dict:
    """
    Returns a dict with:
        - quote: str   (the quote text)
        - author: str  (the author name)
        - description: str  (short LinkedIn post description)
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    used = load_used_quotes()
    used_section = ""
    if used:
        used_lines = "\n".join(f"- {q}" for q in used[-50:])  # last 50 to keep prompt short
        used_section = f"""
IMPORTANT — Do NOT use any of these already-posted quotes:
{used_lines}
"""

    prompt = f"""You are a curator of famous inspirational quotes. Generate ONE real, famous inspirational quote that has never been faked or misattributed.

Rules:
- The quote must be from a real, well-known person (historical figures, leaders, athletes, scientists, philosophers, authors, etc.)
- The quote must be authentic and verifiable
- Keep the quote concise (under 25 words ideally)
- Write a short LinkedIn post description (2-4 sentences) giving context about the quote or author and why it matters today. Make it engaging and professional.
- Write a "scene": a vivid, specific background scene for an AI image that MATCHES the emotional mood and theme of the quote. Describe lighting, landscape, atmosphere. No people, no text, no logos. Cinematic quality. Example: "A lone mountain summit at golden dawn, dramatic clouds parting to reveal a vast sunlit valley below, rays of light breaking through, photorealistic, epic landscape photography."
{used_section}

Respond in this exact JSON format (no extra text):
{{
  "quote": "The actual quote text here",
  "author": "Full Name",
  "description": "Your LinkedIn post description here.",
  "scene": "Your vivid background scene description here."
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw.strip())
    return data
