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
    items = []

    if "Название" in df.columns and "Приготовление" in df.columns:
        # Смузи
        for _, row in df.iterrows():
            title = str(row["Название"]).strip()
            prep = str(row["Приготовление"]).strip()
            number = str(row["Номер"]).strip()

            heading = "🥤 <b>Смузи недели</b>\n🍃 Из коллекции школы йоги ISVARA 🍃"
            title_tag = f"<b>{title}</b>"
            content = f"{heading}\n\n{title_tag}\n\n{prep}".strip()

            # Привязываем номер для картинки, но не показываем его
            full = f"__id__{number}\n{content}"
            items.append(full)

    elif "Название рецепта" in df.columns:
        # Рецепты
        for _, row in df.iterrows():
            number = str(row["Unnamed: 0"]).strip()
            title = str(row["Название рецепта"]).strip()

            heading = "<b>🍲 ВЕГЕТАРИАНСКИЙ РЕЦЕПТ НА ВЫХОДНЫЕ</b>\n🍃 Из коллекции школы йоги ISVARA 🍃"
            title_tag = f"<b>{title}</b>"

            parts = []
            for col in ["описание-порции", "Ингредиенты", "Приготовление (шаги)", "Финальный абзац (польза/советы)"]:
                if col in row and isinstance(row[col], str) and row[col].strip():
                    parts.append(row[col].strip())

            body = "\n\n".join(parts)
            content = f"{heading}\n\n{title_tag}\n\n{body}".strip()

            # Привязываем номер для поиска изображения
            full = f"__id__{number}\n{content}"
            items.append(full)

    else:
        logging.warning("Неизвестная структура Excel-файла.")

    return items

    

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

async def send_to_telegram(content, filetype):
    # Вырежем служебный ID (для номера рецепта/смузи)
    internal_id = None
    if content.startswith("__id__"):
        internal_id, content = content.split("\n", 1)
        internal_id = internal_id.replace("__id__", "").strip()

    
    title, body = split_post(content)

    # === Найдём фото ===
    image_path = None
    if filetype == "smoothie":
        image_files = sorted(os.listdir("smoothie_images"))
        index_key = "smoothie_image_index"
    else:
        number = internal_id
        image_files = [f for f in os.listdir("recipe_images") if number and f.startswith(number)]
        index_key = "recipe_image_index"

    # === Получим/обновим индекс из Firestore ===
    index_doc_ref = db.collection("history").document("image_index")
    index_doc = index_doc_ref.get()
    if index_doc.exists:
        index_data = index_doc.to_dict()
        index = index_data.get(index_key, 0)
    else:
        index = 0

    # === Назначим путь к фото (если есть) ===
    if filetype == "smoothie" and image_files:
        image_path = os.path.join("smoothie_images", image_files[index % len(image_files)])
        index += 1
        index_doc_ref.set({index_key: index}, merge=True)
    elif filetype == "recipe" and image_files:
        image_path = os.path.join("recipe_images", image_files[0])

    try:
        if image_path:
            with open(image_path, "rb") as photo:
                if len(content) <= 1024:
                    await bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=content, parse_mode=ParseMode.HTML,message_thread_id=3)
                else:
                    await bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=title, parse_mode=ParseMode.HTML,message_thread_id=3)
                    await bot.send_message(chat_id=CHAT_ID, text=body[:4096], parse_mode=ParseMode.HTML,message_thread_id=3)
        else:
            await bot.send_message(chat_id=CHAT_ID, text=content[:4096], parse_mode=ParseMode.HTML,message_thread_id=3)
    except Exception as e:
        logging.warning(f"❗ Ошибка при отправке с фото: {e}")
        await bot.send_message(chat_id=CHAT_ID, text=content[:4096], parse_mode=ParseMode.HTML,message_thread_id=3)

@app.route("/trigger")
def trigger():
    try:
        now = datetime.datetime.now()
        weekday = now.weekday()

        if weekday == 5:  # Saturday
            file = RECIPE_FILE
            filetype = "recipe"
        elif weekday == 1:  # Tuesday
            file = SMOOTHIE_FILE
            filetype = "smoothie"
        else:
            return "⏳ Not scheduled today", 200

        content = get_next_content(file)
        loop.run_until_complete(send_to_telegram(content, filetype))
        return "Triggered", 200

    except Exception as e:
        import traceback
        logging.exception("🔥 Ошибка в /trigger")
        return f"<pre>{traceback.format_exc()}</pre>", 500


# === MAIN ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=10000)

    # 👉 Временно отправим смузи
    content = get_next_content(SMOOTHIE_FILE)
    loop.run_until_complete(send_to_telegram(content, "smoothie"))

    # Или рецепт:
    # content = get_next_content(RECIPE_FILE)
    # loop.run_until_complete(send_to_telegram(content, "recipe"))
