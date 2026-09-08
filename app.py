import os
import time
import threading
import urllib.parse
import requests
from flask import Flask, Response, request, abort

app = Flask(__name__)

# আপনার ইউটিউব লাইভ ভিডিও আইডি
VIDEO_ID = "zbyQb-sQ9_M"
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

manifest_cache = {"url": None, "timestamp": 0}

def keep_alive():
    """Render সার্ভার যাতে ঘুমিয়ে না যায়"""
    time.sleep(120)
    while True:
        try:
            if RENDER_EXTERNAL_URL:
                ping_url = f"{RENDER_EXTERNAL_URL}/ping"
                requests.get(ping_url, timeout=10)
                print(f"[Keep-Alive] Pinged: {ping_url}")
        except Exception as e:
            print(f"[Keep-Alive] Error: {e}")
        time.sleep(600)

threading.Thread(target=keep_alive, daemon=True).start()

@app.route("/")
def home():
    return "Stream Relay Server Active! Stream link: /live.m3u8"

@app.route("/ping")
def ping():
    return "pong", 200

def get_hls_url():
    """পাবলিক API ব্যবহার করে আসল HLS Manifest URL বের করা"""
    now = time.time()
    if manifest_cache["url"] and (now - manifest_cache["timestamp"] < 300):
        return manifest_cache["url"]

    # পাবলিক API নোড যা ইউটিউবের বট ব্লকিং সম্পূর্ণ এড়িয়ে যায়
    instances = [
        f"https://inv.nadeko.net/api/v1/videos/{VIDEO_ID}",
        f"https://invidious.nerdvpn.de/api/v1/videos/{VIDEO_ID}",
        f"https://invidious.private.coffee/api/v1/videos/{VIDEO_ID}"
    ]

    for api_url in instances:
        try:
            res = requests.get(api_url, timeout=8)
            if res.status_code == 200:
                data = res.json()
                hls_url = data.get("hlsUrl")
                if hls_url:
                    manifest_cache["url"] = hls_url
                    manifest_cache["timestamp"] = now
                    return hls_url
        except Exception:
            continue

    return None

@app.route("/live.m3u8")
def live_manifest():
    m_url = get_hls_url()
    if not m_url:
        return abort(503, "Could not fetch YouTube Live Manifest. Please ensure OBS is actively streaming.")

    try:
        r = requests.get(m_url, timeout=10)
        base_proxy = f"{request.host_url.rstrip('/')}/proxy?url="
        
        rewritten = []
        for line in r.text.splitlines():
            line_clean = line.strip()
            if line_clean.startswith("http://") or line_clean.startswith("https://"):
                rewritten.append(base_proxy + urllib.parse.quote(line_clean, safe=''))
            else:
                rewritten.append(line)

        return Response(
            "\n".join(rewritten),
            mimetype="application/vnd.apple.mpegurl",
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except Exception as e:
        return abort(500, f"Manifest fetch error: {str(e)}")

@app.route("/proxy")
def proxy():
    target_url = request.args.get("url")
    if not target_url:
        return abort(400, "Missing target url")

    try:
        r = requests.get(target_url, stream=True, timeout=15)
        content_type = r.headers.get("Content-Type", "")

        if "mpegurl" in content_type or "#EXTM3U" in r.text[:20]:
            base_proxy = f"{request.host_url.rstrip('/')}/proxy?url="
            rewritten = []
            for line in r.text.splitlines():
                line_clean = line.strip()
                if line_clean.startswith("http://") or line_clean.startswith("https://"):
                    rewritten.append(base_proxy + urllib.parse.quote(line_clean, safe=''))
                else:
                    rewritten.append(line)
            return Response(
                "\n".join(rewritten),
                mimetype="application/vnd.apple.mpegurl",
                headers={"Access-Control-Allow-Origin": "*"}
            )

        def generate():
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    yield chunk

        return Response(
            generate(),
            content_type=content_type or "video/mp2t",
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except Exception as e:
        return abort(500, f"Proxy chunk error: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
