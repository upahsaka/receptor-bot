import os
import random
import logging
import pandas as pd
import nest_asyncio
import asyncio
from flask import Flask
import threading

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# === НАСТРОЙКИ ===
BOT_TOKEN = "7967951425:AAGraODHxLUvfWR-kcVmTC4ExygjuO2tIQ0"
CHAT_ID = 924655176  # Твой личный chat_id

logging.basicConfig(level=logging.INFO)

# === Загрузка файлов ===
smoothies = pd.read_excel("smned.xlsx")
recipes = pd.read_excel("recaur.xlsx")

# === Хранилище ===
history = {"smoothies": [], "recipes": [], "image_index": 0}

# === Отправка смузи ===
async def send_smoothie(context: ContextTypes.DEFAULT_TYPE):
    unused = [row for idx, row in smoothies.iterrows() if str(row["Номер"]) not in history["smoothies"]]
    if not unused:
        history["smoothies"] = []
        unused = [row for idx, row in smoothies.iterrows()]
    smoothie = random.choice(unused)
    history["smoothies"].append(str(smoothie["Номер"]))

    image_files = sorted(os.listdir("smoothie_images"))
    image_path = os.path.join("smoothie_images", image_files[history["image_index"] % len(image_files)])
    history["image_index"] += 1

    text = f"\U0001F964 <b>Смузи недели:</b>\n\n<b>{smoothie['Название']}</b>\n\n{smoothie['Приготовление']}"
    with open(image_path, "rb") as photo:
        await context.bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=text, parse_mode="HTML")

# === Отправка рецепта ===
async def send_recipe(context: ContextTypes.DEFAULT_TYPE):
    unused = [row for idx, row in recipes.iterrows() if str(row["Unnamed: 0"]) not in history["recipes"]]
    if not unused:
        history["recipes"] = []
        unused = [row for idx, row in recipes.iterrows()]
    recipe = random.choice(unused)
    history["recipes"].append(str(recipe["Unnamed: 0"]))

    text_parts = [f"\U0001F372 <b>{recipe['Название рецепта']}</b>"]
    for col in ["описание-порции", "Ингредиенты", "Приготовление (шаги)", "Финальный абзац (польза/советы)"]:
        val = recipe.get(col)
        if isinstance(val, str) and val.strip():
            text_parts.append(val.strip())
    text = "\n\n".join(text_parts)

    number = str(recipe["Unnamed: 0"])
    photo_file = next((f for f in os.listdir("recipe_images") if f.startswith(number)), None)
    if photo_file:
        with open(os.path.join("recipe_images", photo_file), "rb") as photo:
            await context.bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=text[:1024], parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id=CHAT_ID, text=text[:4096], parse_mode="HTML")

# === Обработчик команды ===
async def test_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=CHAT_ID, text="🛠 Тестовая команда активирована")
    await send_smoothie(context)
    await asyncio.sleep(1)
    await send_recipe(context)

# === Планировщик ===
scheduler = BackgroundScheduler()
scheduler.add_job(send_smoothie, "interval", minutes=60, args=[ContextTypes.DEFAULT_TYPE])
scheduler.add_job(send_recipe, "interval", minutes=90, args=[ContextTypes.DEFAULT_TYPE])
scheduler.start()

# === Запуск приложения ===
async def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("test", test_handler))
    logging.info("Тест-бот запущен.")
    await application.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())

    # === Flask server to keep Render.com instance alive ===
    app = Flask(__name__)

    @app.route("/")
    def home():
        return "Bot is alive"

    def run_flask():
        app.run(host="0.0.0.0", port=10000)

    threading.Thread(target=run_flask).start()
