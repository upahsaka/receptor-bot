import os
import random
import logging
import pandas as pd
import nest_asyncio
import asyncio
import threading
import signal
from flask import Flask
from telegram import Update
from telegram.ext import Application
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone

from firebase_config import save_history, load_history

# === НАСТРОЙКИ ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7967951425:AAF7cvpngiLcUeKzLWtCWQO9JzFI5xMzY98")
CHAT_ID = -1002132227893  # Рабочий чат

logging.basicConfig(level=logging.INFO)

# === Загрузка данных ===
smoothies = pd.read_excel("smned.xlsx")
recipes = pd.read_excel("recaur.xlsx")

# === История из Firebase ===
logging.info("🔥 Загрузка истории из Firebase...")
history = load_history() or {"smoothies": [], "recipes": [], "image_index": 0}

# === Отправка смузи ===
async def send_smoothie():
    unused = [row for _, row in smoothies.iterrows() if str(row["Номер"]) not in history["smoothies"]]
    if not unused:
        history["smoothies"] = []
        unused = [row for _, row in smoothies.iterrows()]
    smoothie = random.choice(unused)
    history["smoothies"].append(str(smoothie["Номер"]))
    save_history(history)

    image_files = sorted(os.listdir("smoothie_images"))
    image_path = os.path.join("smoothie_images", image_files[history["image_index"] % len(image_files)])
    history["image_index"] += 1
    save_history(history)

    heading = "\U0001F964 <b>Смузи недели</b>\n\U0001F343 Из коллекции школы йоги ISVARA \U0001F343\n\n"
    title = f"<b>{smoothie['Название']}</b>"
    body = smoothie['Приготовление']
    full_text = f"{heading}{title}\n\n{body}"

    try:
        with open(image_path, "rb") as photo:
            if len(full_text) <= 1024:
                await bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=full_text, parse_mode="HTML")
            else:
                await bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=f"{heading}{title}", parse_mode="HTML")
                await bot.send_message(chat_id=CHAT_ID, text=body[:4096], parse_mode="HTML")
    except Exception as e:
        logging.warning(f"❗ Ошибка при отправке смузи {image_path}: {e}")
        await bot.send_message(chat_id=CHAT_ID, text=full_text[:4096], parse_mode="HTML")

# === Отправка рецепта ===
async def send_recipe():
    unused = [row for _, row in recipes.iterrows() if str(row["Unnamed: 0"]) not in history["recipes"]]
    if not unused:
        history["recipes"] = []
        unused = [row for _, row in recipes.iterrows()]
    recipe = random.choice(unused)
    history["recipes"].append(str(recipe["Unnamed: 0"]))
    save_history(history)

    heading = "<b>ВЕГЕТАРИАНСКИЙ РЕЦЕПТ НА ВЫХОДНЫЕ</b>\n\U0001F343 Из коллекции школы йоги ISVARA \U0001F343\n\n"
    title = f"<b>{recipe['Название рецепта']}</b>"
    body_parts = []
    for col in ["описание-порции", "Ингредиенты", "Приготовление (шаги)", "Финальный абзац (польза/советы)"]:
        val = recipe.get(col)
        if isinstance(val, str) and val.strip():
            body_parts.append(val.strip())
    body = "\n\n".join(body_parts)
    full_text = f"{heading}{title}\n\n{body}".strip()

    number = str(recipe["Unnamed: 0"])
    photo_file = next((f for f in os.listdir("recipe_images") if f.startswith(number)), None)

    try:
        if photo_file:
            with open(os.path.join("recipe_images", photo_file), "rb") as photo:
                if len(full_text) <= 1024:
                    await bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=full_text, parse_mode="HTML")
                else:
                    await bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=f"{heading}{title}", parse_mode="HTML")
                    await bot.send_message(chat_id=CHAT_ID, text=body[:4096], parse_mode="HTML")
        else:
            await bot.send_message(chat_id=CHAT_ID, text=full_text[:4096], parse_mode="HTML")
    except Exception as e:
        logging.warning(f"❗ Ошибка при отправке рецепта {photo_file}: {e}")
        await bot.send_message(chat_id=CHAT_ID, text=f"{heading}\n\n{body[:4096]}", parse_mode="HTML")

# === Flask-сервер для Render ===
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is alive"

# === Инициализация бота и планировщика ===
application = Application.builder().token(BOT_TOKEN).build()
bot = application.bot
scheduler = BackgroundScheduler(timezone=timezone("Europe/Moscow"))
scheduler.add_job(lambda: asyncio.run(send_smoothie()), "interval", minutes=1)
scheduler.add_job(lambda: asyncio.run(send_recipe()), "interval", minutes=1)

# === Завершение ===
def shutdown(*_):
    logging.info("\u274C Завершение...")
    scheduler.shutdown()
    asyncio.run(application.stop())
    os._exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# === Запуск ===
if __name__ == "__main__":
    nest_asyncio.apply()
    scheduler.start()
    threading.Thread(target=lambda: app_flask.run(host="0.0.0.0", port=10000)).start()
    logging.info("\u2705 Бот и планировщик запущены")
    application.run_async()
