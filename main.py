import os
import json
import random
import datetime
import logging
import pandas as pd
from telegram import Bot
from apscheduler.schedulers.blocking import BlockingScheduler

# === НАСТРОЙКИ ===
BOT_TOKEN = "7967951425:AAGraODHxLUvfWR-kcVmTC4ExygjuO2tIQ0"
CHAT_ID = -1001966409362  # ← ЗАМЕНИ НА СВОЙ! (временная заглушка)
TIMEZONE_SHIFT = 3  # Москва = UTC+3

bot = Bot(BOT_TOKEN)
scheduler = BlockingScheduler()
logging.basicConfig(level=logging.INFO)

# === Загрузка истории ===
HISTORY_FILE = "sent_history.json"
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        history = json.load(f)
else:
    history = {"smoothies": [], "recipes": [], "image_index": 0}

def save_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# === Загрузка данных ===
smoothies = pd.read_excel("smned.xlsx")
recipes = pd.read_excel("recaur.xlsx")

def send_smoothie():
    unused = [row for idx, row in smoothies.iterrows() if str(row["Номер"]) not in history["smoothies"]]
    if not unused:
        history["smoothies"] = []
        unused = [row for idx, row in smoothies.iterrows()]
    smoothie = random.choice(unused)
    history["smoothies"].append(str(smoothie["Номер"]))

    # Фото — по кругу
    image_files = sorted(os.listdir("smoothie_images"))
    image_path = os.path.join("smoothie_images", image_files[history["image_index"] % len(image_files)])
    history["image_index"] += 1

    text = f"🥤 <b>Смузи недели:</b>\n\n<b>{smoothie['Название']}</b>\n\n{smoothie['Приготовление']}"
    bot.send_photo(chat_id=CHAT_ID, photo=open(image_path, "rb"), caption=text, parse_mode="HTML")
    save_history()

def send_recipe():
    unused = [row for idx, row in recipes.iterrows() if str(row["Unnamed: 0"]) not in history["recipes"]]
    if not unused:
        history["recipes"] = []
        unused = [row for idx, row in recipes.iterrows()]
    recipe = random.choice(unused)
    history["recipes"].append(str(recipe["Unnamed: 0"]))

    text_parts = [f"🍲 <b>{recipe['Название рецепта']}</b>"]
    for col in ["описание-порции", "Ингредиенты", "Приготовление (шаги)", "Финальный абзац (польза/советы)"]:
        val = recipe.get(col)
        if isinstance(val, str) and val.strip():
            text_parts.append(val.strip())

    text = "\n\n".join(text_parts)
    number = str(recipe["Unnamed: 0"])
    photo_file = next((f for f in os.listdir("recipe_images") if f.startswith(number)), None)

    if photo_file:
        path = os.path.join("recipe_images", photo_file)
        bot.send_photo(chat_id=CHAT_ID, photo=open(path, "rb"), caption=text[:1024], parse_mode="HTML")
    else:
        bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")

    save_history()

# === Планировщик ===
@scheduler.scheduled_job("cron", day_of_week="tue", hour=12, minute=0)  # 15:00 мск
def scheduled_smoothie():
    send_smoothie()

@scheduler.scheduled_job("cron", day_of_week="fri", hour=13, minute=0)  # 16:00 мск
def scheduled_recipe():
    send_recipe()

# === Запуск ===
if __name__ == "__main__":
    logging.info("Бот запущен.")
    scheduler.start()
