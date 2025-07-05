import os
import asyncio
import nest_asyncio
import logging
import datetime
import random
import pandas as pd
from flask import Flask
from telegram import Bot
from telegram.constants import ParseMode
from dotenv import load_dotenv
from firebase_admin import credentials, firestore, initialize_app

# === INIT ===
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
bot = Bot(token=TOKEN)

# Firebase init
cred = credentials.Certificate("/etc/secrets/firebase_key.json")
initialize_app(cred)
db = firestore.client()

# Flask app for external triggering
nest_asyncio.apply()
loop = asyncio.get_event_loop()
app = Flask(__name__)

# === FILES ===
SMOOTHIE_FILE = "smned.xlsx"
RECIPE_FILE = "recaur.xlsx"

# === HELPERS ===
def read_file(filename):
    df = pd.read_excel(filename)
    docs = []
    for _, row in df.iterrows():
        text = f"{row.iloc[0]}\n{row.iloc[1]}"
        docs.append(text.strip())
    return docs

def get_history_key(file):
    return "smoothie" if file == SMOOTHIE_FILE else "recipe"

def get_next_content(file):
    docs = read_file(file)
    key = get_history_key(file)
    history_ref = db.collection("history").document(key)
    history_doc = history_ref.get()

    if history_doc.exists:
        history = history_doc.to_dict().get("items", [])
    else:
        history = []

    remaining = [x for x in docs if x not in history]

    if not remaining:
        history = []
        remaining = docs

    selected = random.choice(remaining)
    history.append(selected)
    history_ref.set({"items": history})
    return selected

def split_post(text):
    if "\n" not in text:
        return text, None
    title, body = text.split("\n", 1)
    return f"<b>{title.strip()}</b>", body.strip()

async def send_to_telegram(content):
    title, body = split_post(content)
    await bot.send_message(chat_id=CHAT_ID, text=title, parse_mode=ParseMode.HTML)
    if body:
        await bot.send_message(chat_id=CHAT_ID, text=body)

@app.route("/trigger")
def trigger():
    try:
        now = datetime.datetime.now()
        minute = now.minute

        if minute % 2 == 0:
            file = RECIPE_FILE
        else:
            file = SMOOTHIE_FILE

        content = get_next_content(file)
        loop.run_until_complete(send_to_telegram(content))
        return "Triggered", 200

    except Exception as e:
        import traceback
        logging.exception("🔥 Ошибка в /trigger")
        return f"<pre>{traceback.format_exc()}</pre>", 500

# === MAIN ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=10000)
