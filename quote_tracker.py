import json
import os
from datetime import datetime
from config import QUOTES_FILE


def load_history() -> list[dict]:
    """Returns list of {quote, author, posted_at} dicts, oldest first."""
    if not os.path.exists(QUOTES_FILE):
        return []
    with open(QUOTES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    result = []
    for item in data:
        if isinstance(item, str):
            result.append({"quote": item, "author": "Unknown", "posted_at": None})
        else:
            result.append(item)
    return result


def load_used_quotes() -> list[str]:
    return [item["quote"] for item in load_history()]


def save_used_quote(quote: str, author: str = "") -> None:
    history = load_history()
    history.append({
        "quote": quote,
        "author": author,
        "posted_at": datetime.now().isoformat(),
    })
    with open(QUOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def is_quote_used(quote: str) -> bool:
    return quote in load_used_quotes()


def remove_quote_by_index(original_index: int) -> None:
    history = load_history()
    if 0 <= original_index < len(history):
        history.pop(original_index)
        with open(QUOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
