import os
import json
import uuid
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, Response, send_file
import config
from quote_generator import generate_quote
from image_generator import generate_quote_image
from image_processor import strip_metadata
from linkedin_poster import post_to_linkedin
from quote_tracker import load_history, load_used_quotes, save_used_quote, is_quote_used, remove_quote_by_index

app = Flask(__name__)

# Temp image store: {image_id: {path, created, quote_data}}
temp_store = {}

# Scheduler state
sched = {
    "enabled": False,
    "post_time": config.POST_TIME,
    "next_post": None,
    "thread": None,
}


# ── Helpers ────────────────────────────────────────────────────────────────

def _calc_next_post(post_time: str) -> datetime:
    h, m = map(int, post_time.split(":"))
    now = datetime.now()
    nxt = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if nxt <= now:
        nxt += timedelta(days=1)
    return nxt


def _scheduler_loop():
    while sched["enabled"]:
        if sched["next_post"] and datetime.now() >= sched["next_post"]:
            try:
                _run_post()
            except Exception as e:
                print(f"[scheduler] Error: {e}")
            sched["next_post"] = _calc_next_post(sched["post_time"])
        time.sleep(30)


def _start_scheduler():
    sched["enabled"] = True
    sched["next_post"] = _calc_next_post(sched["post_time"])
    t = threading.Thread(target=_scheduler_loop, daemon=True)
    t.start()
    sched["thread"] = t


def _stop_scheduler():
    sched["enabled"] = False
    sched["next_post"] = None


def _run_post(image_id=None, quote=None, author=None, description=None):
    """Core post logic used by both manual and scheduled posts."""
    if image_id and image_id in temp_store:
        entry = temp_store.pop(image_id)
        img_path = entry["path"]
        qd = entry["quote_data"]
        quote = quote or qd["quote"]
        author = author or qd["author"]
        description = description or qd["description"]
    else:
        attempts = 0
        used = load_used_quotes()
        qd = None
        while attempts < 5:
            d = generate_quote()
            if d["quote"] not in used:
                qd = d
                break
            attempts += 1
        if not qd:
            raise RuntimeError("Could not generate a unique quote after 5 attempts.")
        img_path = generate_quote_image(qd["quote"], qd["author"], qd.get("scene", ""))
        strip_metadata(img_path)
        quote, author, description = qd["quote"], qd["author"], qd["description"]

    post_urn = post_to_linkedin(img_path, quote, author, description)
    save_used_quote(quote, author)
    try:
        os.remove(img_path)
    except OSError:
        pass
    return post_urn, quote, author


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def api_stats():
    history = load_history()
    last = history[-1] if history else None
    return jsonify({
        "total_posts": len(history),
        "last_post": last,
        "scheduler_enabled": sched["enabled"],
        "post_time": sched["post_time"],
        "next_post": sched["next_post"].isoformat() if sched["next_post"] else None,
    })


@app.route("/api/generate/stream")
def api_generate_stream():
    def stream():
        try:
            msg1 = json.dumps({"step": "quote", "msg": "Generating quote with Claude AI\u2026"})
            yield f"data: {msg1}\n\n"
            used = load_used_quotes()
            qd = None
            for _ in range(5):
                d = generate_quote()
                if d["quote"] not in used:
                    qd = d
                    break
            if not qd:
                msg_err = json.dumps({"step": "error", "msg": "Could not generate a unique quote. Try again."})
                yield f"data: {msg_err}\n\n"
                return
            preview_text = "Quote ready \u2014 \"" + qd["quote"][:60] + "\u2026\""
            yield f"data: {json.dumps({'step': 'quote_done', 'msg': preview_text})}\n\n"

            msg2 = json.dumps({"step": "image", "msg": "Generating matched image with DALL-E 3 HD\u2026 (~20 s)"})
            yield f"data: {msg2}\n\n"
            img_path = generate_quote_image(qd["quote"], qd["author"], qd.get("scene", ""))

            msg3 = json.dumps({"step": "meta", "msg": "Stripping image metadata\u2026"})
            yield f"data: {msg3}\n\n"
            strip_metadata(img_path)

            image_id = str(uuid.uuid4())
            temp_store[image_id] = {"path": img_path, "created": datetime.now(), "quote_data": qd}

            msg_done = json.dumps({"step": "done", "image_id": image_id, "quote": qd["quote"], "author": qd["author"], "description": qd["description"]})
            yield f"data: {msg_done}\n\n"
        except Exception as e:
            msg_exc = json.dumps({"step": "error", "msg": str(e)})
            yield f"data: {msg_exc}\n\n"

    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/preview/<image_id>")
def api_preview(image_id):
    entry = temp_store.get(image_id)
    if not entry or not os.path.exists(entry["path"]):
        return jsonify({"error": "Not found"}), 404
    return send_file(entry["path"], mimetype="image/png")


@app.route("/api/post", methods=["POST"])
def api_post():
    body = request.json or {}
    try:
        post_urn, quote, author = _run_post(
            image_id=body.get("image_id"),
            quote=body.get("quote"),
            author=body.get("author"),
            description=body.get("description"),
        )
        return jsonify({"success": True, "post_urn": post_urn, "quote": quote, "author": author})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/history")
def api_history():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    search = request.args.get("search", "").lower()

    history = load_history()
    # Attach original indices before reversing
    indexed = [{"_idx": i, **item} for i, item in enumerate(history)]
    indexed.reverse()

    if search:
        indexed = [h for h in indexed if search in h.get("quote", "").lower() or search in h.get("author", "").lower()]

    total = len(indexed)
    start = (page - 1) * per_page
    items = indexed[start:start + per_page]

    return jsonify({
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    })


@app.route("/api/history/<int:original_idx>", methods=["DELETE"])
def api_delete_history(original_idx):
    try:
        remove_quote_by_index(original_idx)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    return jsonify({
        "post_time": sched["post_time"],
        "has_anthropic_key": bool(config.ANTHROPIC_API_KEY),
        "has_openai_key": bool(config.OPENAI_API_KEY),
        "has_linkedin_token": bool(config.LINKEDIN_ACCESS_TOKEN),
        "linkedin_urn": config.LINKEDIN_PERSON_URN or "",
        "scheduler_enabled": sched["enabled"],
    })


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    data = request.json or {}
    env_path = ".env"
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

    mapping = {
        "anthropic_key": "ANTHROPIC_API_KEY",
        "openai_key": "OPENAI_API_KEY",
        "linkedin_token": "LINKEDIN_ACCESS_TOKEN",
        "linkedin_urn": "LINKEDIN_PERSON_URN",
        "post_time": "POST_TIME",
    }
    updates = {mapping[k]: v for k, v in data.items() if k in mapping and v}

    updated = set()
    new_lines = []
    for line in lines:
        key = line.split("=")[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
            updated.add(key)
        else:
            new_lines.append(line)
    for key, val in updates.items():
        if key not in updated:
            new_lines.append(f"{key}={val}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)

    from dotenv import load_dotenv
    load_dotenv(override=True)
    config.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    config.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    config.LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
    config.LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN")

    if "post_time" in data:
        config.POST_TIME = data["post_time"]
        sched["post_time"] = data["post_time"]
        if sched["enabled"]:
            sched["next_post"] = _calc_next_post(data["post_time"])

    want_sched = data.get("scheduler_enabled")
    if want_sched is True and not sched["enabled"]:
        _start_scheduler()
    elif want_sched is False and sched["enabled"]:
        _stop_scheduler()

    return jsonify({"success": True})


@app.route("/api/logs")
def api_logs():
    log_file = "scheduler.log"
    lines = []
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    lines = [l.rstrip() for l in lines[-200:]]
    lines.reverse()
    return jsonify({"lines": lines})


if __name__ == "__main__":
    import socket
    from waitress import serve

    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "127.0.0.1"

    print("=" * 55)
    print("  LinkedIn Quote Poster  —  Production Mode")
    print("=" * 55)
    print(f"  Local:    http://localhost:5000")
    print(f"  Network:  http://{local_ip}:5000")
    print("=" * 55)
    print("  Tip: allow port 5000 in Windows Firewall so")
    print("  other devices on your network can connect.")
    print("=" * 55)

    serve(app, host="0.0.0.0", port=5000, threads=4)
