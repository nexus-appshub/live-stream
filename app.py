import os
import time
import threading
import requests
from flask import Flask, redirect, abort
import yt_dlp

app = Flask(__name__)

# আপনার ইউটিউব লাইভ লিঙ্ক
YOUTUBE_URL = "https://www.youtube.com/@XUBILASWEBDEVCORP/live"
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
        'extract_flat': False,
        'live_from_start': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(YOUTUBE_URL, download=False)
            
            # সরাসরি ম্যানিফেস্ট লিংক চেক করা
            stream_url = None
            if 'manifest_url' in info:
                stream_url = info['manifest_url']
            elif 'url' in info:
                stream_url = info['url']
            else:
                # ম্যানিফেস্ট ফরম্যাট থেকে m3u8 খুঁজে নেওয়া
                formats = info.get('formats', [])
                for f in reversed(formats):
                    if f.get('protocol') in ['m3u8', 'm3u8_native'] or '.m3u8' in f.get('url', ''):
                        stream_url = f.get('url')
                        break
            
            if stream_url:
                return redirect(stream_url, code=302)
            else:
                return abort(404, "No live HLS stream manifest found. Make sure the channel is actively streaming.")
                
    except Exception as e:
        return abort(500, f"Error resolving stream: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
