import os
import time
import threading
import requests
from flask import Flask, redirect, abort
import yt_dlp

app = Flask(__name__)

# সরাসরি লাইভ ভিডিওর লিঙ্ক (আইডি: zbyQb-sQ9_M)
YOUTUBE_URL = "https://www.youtube.com/watch?v=zbyQb-sQ9_M"
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

def keep_alive():
    time.sleep(120)
    while True:
        try:
            if RENDER_EXTERNAL_URL:
                ping_url = f"{RENDER_EXTERNAL_URL}/ping"
                requests.get(ping_url, timeout=10)
                print(f"[Keep-Alive] Pinged {ping_url} successfully.")
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

@app.route("/live.m3u8")
def get_live_m3u8():
    cookie_file = 'cookies.txt' if os.path.exists('cookies.txt') else None
    
    ydl_opts = {
        'cookiefile': cookie_file,
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        # অ্যান্ড্রয়েড ও টিভি ক্লায়েন্ট দিলে ডেটাসেন্টার আইপি হলেও ইউটিউব কোনো ফরম্যাট ব্লক করে না
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'tv'],
                'player_skip': ['webpage', 'configs']
            }
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(YOUTUBE_URL, download=False)
            
            # সরাসরি ম্যানিফেস্ট অথবা ফরম্যাট লিস্ট থেকে m3u8 খুঁজে নেওয়া
            stream_url = info.get('manifest_url') or info.get('url')
            
            if not stream_url:
                for f in reversed(info.get('formats', [])):
                    f_url = f.get('url', '')
                    if '.m3u8' in f_url or 'manifest' in f_url:
                        stream_url = f_url
                        break

            if stream_url:
                return redirect(stream_url, code=302)
            else:
                return abort(404, "Stream URL not found in formats")
                
    except Exception as e:
        return abort(500, f"Error resolving stream: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
