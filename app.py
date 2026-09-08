import os
import time
import threading
import requests
from flask import Flask, redirect, abort
import yt_dlp

app = Flask(__name__)

# আপনার ইউটিউব লাইভ চ্যানেল/ভিডিও লিঙ্ক
YOUTUBE_URL = "https://www.youtube.com/@XUBILASWEBDEVCORP/live"

# Render-এর নিজের ডোমেইন (Render পরিবেশ থেকে নিজে থেকেই নিয়ে নেয়)
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

def keep_alive():
    """Render সার্ভার যাতে sleep মোডে না যায়, তাই প্রতি ১০ মিনিট পর পিং পাঠাবে"""
    # সার্ভার পুরোপুরি বুট হওয়ার জন্য ২ মিনিট অপেক্ষা করবে
    time.sleep(120)
    while True:
        try:
            if RENDER_EXTERNAL_URL:
                ping_url = f"{RENDER_EXTERNAL_URL}/ping"
                requests.get(ping_url, timeout=10)
                print(f"[Keep-Alive] Pinged {ping_url} successfully.")
            else:
                print("[Keep-Alive] Waiting for RENDER_EXTERNAL_URL to be set...")
        except Exception as e:
            print(f"[Keep-Alive] Ping error: {e}")
        # ১০ মিনিট (৬০০ সেকেন্ড) পর পর পুনরায় কল করবে
        time.sleep(600)

# ব্যাকগ্রাউন্ডে পিং থ্রেড চালু করা
threading.Thread(target=keep_alive, daemon=True).start()

@app.route("/")
def home():
    return "Server is running 24/7! Use /live.m3u8 for IPTV stream."

@app.route("/ping")
def ping():
    return "pong", 200

@app.route("/live.m3u8")
def get_live_m3u8():
    """ইউটিউব থেকে আসল ফ্রেশ m3u8 লিংক নিয়ে প্লেয়ারকে রিডাইরেক্ট (302) করবে"""
    ydl_opts = {
        'format': 'best[protocol^=m3u8]/best',
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(YOUTUBE_URL, download=False)
            stream_url = info.get('url')
            if stream_url:
                # প্লেয়ারকে সরাসরি গুগলের আসল m3u8 লিঙ্কে রিডাইরেক্ট করে
                return redirect(stream_url, code=302)
            else:
                return abort(404, "Stream URL not found")
    except Exception as e:
        return abort(500, f"Error resolving stream: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
