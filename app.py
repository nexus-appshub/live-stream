import os
import time
import threading
import subprocess
import requests
from flask import Flask, Response, abort

app = Flask(__name__)

# আপনার ইউটিউব লাইভ লিঙ্ক
YOUTUBE_URL = "https://www.youtube.com/watch?v=zbyQb-sQ9_M"
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

def keep_alive():
    """Render সার্ভার যাতে স্লিপে না যায়, প্রতি ১০ মিনিট পরপর পিং পাঠাবে"""
    time.sleep(120)
    while True:
        try:
            if RENDER_EXTERNAL_URL:
                ping_url = f"{RENDER_EXTERNAL_URL}/ping"
                requests.get(ping_url, timeout=10)
                print(f"[Keep-Alive] Pinged {ping_url}")
        except Exception as e:
            print(f"[Keep-Alive] Error: {e}")
        time.sleep(600)

threading.Thread(target=keep_alive, daemon=True).start()

@app.route("/")
def home():
    return "Server is running! Use /live.ts or /live.m3u8 in your IPTV Player."

@app.route("/ping")
def ping():
    return "pong", 200

@app.route("/live.ts")
@app.route("/live.m3u8")
def live_stream():
    """ইউটিউব থেকে সরাসরি ভিডিও ফেচ করে প্লেয়ারে রিলে করা"""
    cmd = [
        "streamlink",
        "--stdout",
        "--default-stream", "best",
        "--url", YOUTUBE_URL
    ]
    
    # cookies.txt থাকলে সেটি যুক্ত করবে
    if os.path.exists("cookies.txt"):
        cmd.extend(["--cookies", "cookies.txt"])

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=1024 * 1024
        )

        def generate():
            try:
                while True:
                    data = proc.stdout.read(64 * 1024)
                    if not data:
                        break
                    yield data
            finally:
                proc.terminate()
                proc.wait()

        # সরাসরি MPEG-TS লাইভ স্ট্রিম রেসপন্স পাঠানো
        return Response(generate(), mimetype="video/mp2t")
    except Exception as e:
        return abort(500, f"Streaming error: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
