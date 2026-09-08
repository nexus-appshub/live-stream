import os
import re
import html
import time
import threading
import urllib.parse
import http.cookiejar
import requests
from flask import Flask, Response, request, abort
import yt_dlp

app = Flask(__name__)

# আপনার ইউটিউব চ্যানেল বা লাইভ ভিডিও লিঙ্ক
YOUTUBE_URL = "https://www.youtube.com/@XUBILASWEBDEVCORP/live"
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

# ক্যাশ মেমরি (যাতে প্রতি সেকেন্ডে ইউটিউবে রিকোয়েস্ট না যায়)
manifest_cache = {"url": None, "timestamp": 0}

def keep_alive():
    """Render সার্ভার যাতে sleep মোডে না যায়"""
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
    return "HLS Proxy is running! Stream URL: /live.m3u8"

@app.route("/ping")
def ping():
    return "pong", 200

def get_hls_url():
    """ইউটিউব থেকে আসল hlsManifestUrl বের করা"""
    now = time.time()
    if manifest_cache["url"] and (now - manifest_cache["timestamp"] < 300):
        return manifest_cache["url"]

    # পদ্ধতি ১: রেজেক্স দিয়ে দ্রুত সোর্স থেকে রিড করা
    try:
        session = requests.Session()
        if os.path.exists("cookies.txt"):
            cj = http.cookiejar.MozillaCookieJar("cookies.txt")
            cj.load(ignore_discard=True, ignore_expires=True)
            session.cookies = cj
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
        res = session.get(YOUTUBE_URL, headers=headers, timeout=10)
        match = re.search(r'["\']hlsManifestUrl["\']:\s*["\'](https:[^"\']+)["\']', res.text)
        if match:
            clean_url = html.unescape(match.group(1).replace(r'\/', '/').replace('\\u0026', '&'))
            manifest_cache["url"] = clean_url
            manifest_cache["timestamp"] = now
            return clean_url
    except Exception as e:
        print(f"[Direct Regex Error] {e}")

    # পদ্ধতি ২: yt-dlp ফলব্যাক
    try:
        ydl_opts = {
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(YOUTUBE_URL, download=False)
            url = info.get('manifest_url') or info.get('url')
            if url:
                manifest_cache["url"] = url
                manifest_cache["timestamp"] = now
                return url
    except Exception as e:
        print(f"[yt-dlp Error] {e}")

    return manifest_cache.get("url")

@app.route("/live.m3u8")
def live_manifest():
    """মাস্টার প্লেলিস্ট রি-রাইট করে নিজস্ব প্রক্সি রুটে পাঠানো"""
    m_url = get_hls_url()
    if not m_url:
        return abort(503, "Could not fetch YouTube Live Manifest. Stream might be offline.")

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
    """প্লেলিস্টের সাব-ম্যানিফেস্ট এবং ভিডিও সেগমেন্ট (.ts) প্রক্সি করা"""
    target_url = request.args.get("url")
    if not target_url:
        return abort(400, "Missing target url")

    try:
        r = requests.get(target_url, stream=True, timeout=15)
        content_type = r.headers.get("Content-Type", "")

        # যদি এটি সাব-প্লেলিস্ট (.m3u8) হয়, ভেতরের লিঙ্কগুলোও রি-রাইট করবে
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

        # ভিডিও সেগমেন্ট (.ts বাইটস) ক্লায়েন্টকে পাঠানো
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
