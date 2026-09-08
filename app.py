import os
import time
import threading
import requests
from flask import Flask, redirect, abort
import yt_dlp

app = Flask(__name__)

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
    ydl_opts = {
        'format': 'best[protocol^=m3u8]/best',
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android']
            }
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(YOUTUBE_URL, download=False)
            stream_url = info.get('url')
            if stream_url:
                return redirect(stream_url, code=302)
            else:
                return abort(404, "Stream URL not found")
    except Exception as e:
        return abort(500, f"Error resolving stream: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
