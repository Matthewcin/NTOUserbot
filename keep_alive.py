from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "✅ Userbot Online & Vigilando."

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def start_server():
    t = Thread(target=run)
    t.start()
