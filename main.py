import os
import json
import random
import logging
import pandas as pd
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio

# === НАСТРОЙКИ ===
BOT_TOKEN = "7967951425:AAGraODHxLUvfWR-kcVmTC4ExygjuO2tIQ0"
CHAT_ID = 924655176  # Твой личный chat_id

bot = Bot(BOT_TOKEN)
logging.basicConfig(level=logging.INFO)

# === Загрузка файлов ===
smoothies = pd.read_excel("smned.xlsx")
recipes = pd.read_excel("recaur.xlsx")

# === Хранилище ===
history = {"smoothies": [], "recipes": [], "image_index": 0}

# === Отправка смузи ===
def send_smoothie():
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
    bot.send_photo(chat_id=CHAT_ID, photo=open(image_path, "rb"), caption=text, parse_mode="HTML")

# === Отправка рецепта ===
def send_recipe():
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
        bot.send_photo(chat_id=CHAT_ID, photo=open(os.path.join("recipe_images", photo_file), "rb"), caption=text[:1024], parse_mode="HTML")
    else:
        bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")

# === Планировщик ===
scheduler = BackgroundScheduler()
scheduler.add_job(send_smoothie, 'date', run_date=pd.Timestamp.now() + pd.Timedelta(minutes=1))
scheduler.add_job(send_recipe, 'date', run_date=pd.Timestamp.now() + pd.Timedelta(minutes=2))
scheduler.start()

# === Обработчик команды ===
async def test_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    send_smoothie()
    await asyncio.sleep(1)
    send_recipe()

# === Запуск приложения ===
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("test", test_handler))
    logging.info("Тест-бот запущен.")
    app.run_polling()
