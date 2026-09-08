import os
import re
import html
import time
import threading
import http.cookiejar
import requests
from flask import Flask, redirect, abort
import yt_dlp

app = Flask(__name__)

# সরাসরি লাইভ ভিডিও লিঙ্ক
YOUTUBE_URL = "https://www.youtube.com/watch?v=zbyQb-sQ9_M"
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

def keep_alive():
    """Render সার্ভারকে ঘুমিয়ে যাওয়া থেকে আটকাতে প্রতি ১০ মিনিটে পিং পাঠাবে"""
    time.sleep(120)
    while True:
        try:
            if RENDER_EXTERNAL_URL:
                ping_url = f"{RENDER_EXTERNAL_URL}/ping"
                requests.get(ping_url, timeout=10)
                print(f"[Keep-Alive] Pinged successfully: {ping_url}")
        except Exception as e:
            print(f"[Keep-Alive] Ping error: {e}")
        time.sleep(600)

threading.Thread(target=keep_alive, daemon=True).start()

@app.route("/")
def home():
    return "Server is running 24/7! Use /live.m3u8 for IPTV stream."

@app.route("/ping")
def ping():
    return "pong", 200

def extract_m3u8_direct(url):
    """কুকিজ সহ ডিরেক্ট ওয়েবপেজ থেকে hlsManifestUrl বের করার দ্রুততম পদ্ধতি"""
    session = requests.Session()
    
    # cookies.txt থাকলে সেশনে লোড করা
    if os.path.exists("cookies.txt"):
        try:
            cj = http.cookiejar.MozillaCookieJar("cookies.txt")
            cj.load(ignore_discard=True, ignore_expires=True)
            session.cookies = cj
        except Exception as e:
            print(f"[Cookies] Load warning: {e}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    resp = session.get(url, headers=headers, timeout=15)
    page_text = resp.text

    # YouTube প্লেয়ার রেসপন্সে থাকা hlsManifestUrl খোঁজা
    match = re.search(r'["\']hlsManifestUrl["\']:\s*["\'](https:[^"\']+)["\']', page_text)
    if match:
        raw_url = match.group(1)
        # JSON ও HTML ক্যারেক্টার ক্লিন করা
        clean_url = raw_url.replace(r'\/', '/').replace('\\u0026', '&')
        return html.unescape(clean_url)
    
    return None

@app.route("/live.m3u8")
def get_live_m3u8():
    # পদ্ধতি ১: সরাসরি দ্রুততম রেজেক্স এক্সট্রাকশন
    try:
        direct_url = extract_m3u8_direct(YOUTUBE_URL)
        if direct_url:
            return redirect(direct_url, code=302)
    except Exception as e:
        print(f"[Direct Extract Error] {e}")

    # পদ্ধতি ২: ব্যাকআপ হিসেবে ক্লিন yt-dlp
    cookie_file = 'cookies.txt' if os.path.exists('cookies.txt') else None
    ydl_opts = {
        'cookiefile': cookie_file,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'web']
            }
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(YOUTUBE_URL, download=False)
            stream_url = info.get('manifest_url') or info.get('url')
            
            if stream_url:
                return redirect(stream_url, code=302)
            else:
                return abort(404, "Live stream manifest not found.")
    except Exception as e:
        return abort(500, f"Error resolving stream: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
