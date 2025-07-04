import os
import random
import logging
import pandas as pd
import nest_asyncio
import asyncio
import threading
from flask import Flask

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

from firebase_config import save_history, load_history, db

# === НАСТРОЙКИ ===
BOT_TOKEN = "7967951425:AAGraODHxLUvfWR-kcVmTC4ExygjuO2tIQ0"
CHAT_ID = 924655176

logging.basicConfig(level=logging.INFO)

# === Загрузка файлов ===
smoothies = pd.read_excel("smned.xlsx")
recipes = pd.read_excel("recaur.xlsx")

# === История через Firebase ===
logging.info("🔥 Проверка Firebase — загружаю историю...")
history = load_history()

# === Отправка смузи ===
async def send_smoothie(context: ContextTypes.DEFAULT_TYPE):
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

    heading = "🥤 <b>Смузи недели</b>\n🍃 Из коллекции школы йоги ISVARA 🍃\n\n"
    title = f"<b>{smoothie['Название']}</b>"
    body = smoothie['Приготовление']
    full_text = f"{heading}{title}\n\n{body}"

    try:
        with open(image_path, "rb") as photo:
            if len(full_text) <= 1024:
                await context.bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=full_text, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=f"{heading}{title}", parse_mode="HTML")
                await context.bot.send_message(chat_id=CHAT_ID, text=body[:4096], parse_mode="HTML")
    except Exception as e:
        logging.warning(f"❗ Ошибка при отправке смузи {image_path}: {e}")
        await context.bot.send_message(chat_id=CHAT_ID, text=full_text[:4096], parse_mode="HTML")

# === Отправка рецепта ===
async def send_recipe(context: ContextTypes.DEFAULT_TYPE):
    unused = [row for _, row in recipes.iterrows() if str(row["Unnamed: 0"]) not in history["recipes"]]
    if not unused:
        history["recipes"] = []
        unused = [row for _, row in recipes.iterrows()]
    recipe = random.choice(unused)
    history["recipes"].append(str(recipe["Unnamed: 0"]))
    save_history(history)

    heading = "<b>ВЕГЕТАРИАНСКИЙ РЕЦЕПТ НА ВЫХОДНЫЕ</b>\n🍃 Из коллекции школы йоги ISVARA 🍃\n\n"
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
                    await context.bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=full_text, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=f"{heading}{title}", parse_mode="HTML")
                    await context.bot.send_message(chat_id=CHAT_ID, text=body[:4096], parse_mode="HTML")
        else:
            await context.bot.send_message(chat_id=CHAT_ID, text=full_text[:4096], parse_mode="HTML")
    except Exception as e:
        logging.warning(f"❗ Ошибка при отправке рецепта {photo_file}: {e}")
        await context.bot.send_message(chat_id=CHAT_ID, text=f"{heading}\n\n{body[:4096]}", parse_mode="HTML")

# === Тестовая команда ===
async def test_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=CHAT_ID, text="🛠 Тестовая команда активирована")
    await send_smoothie(context)
    await asyncio.sleep(1)
    await send_recipe(context)

# === Планировщик ===
scheduler = BackgroundScheduler()
scheduler.add_job(send_smoothie, "interval", minutes=60, args=[ContextTypes.DEFAULT_TYPE])
scheduler.add_job(send_recipe, "interval", minutes=90, args=[ContextTypes.DEFAULT_TYPE])

# === Flask-сервер для Render ===
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is alive"

# === Запуск ===
if __name__ == "__main__":
    nest_asyncio.apply()

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("test", test_handler))

    scheduler.start()

    threading.Thread(target=lambda: app_flask.run(host="0.0.0.0", port=10000)).start()

    logging.info("Бот запущен.")
    application.run_polling()
