import firebase_admin
from firebase_admin import credentials, db
import os
import json

# Получаем JSON из переменной окружения
cred_dict = json.loads(os.environ["FIREBASE_KEY_JSON"])

# Инициализируем Firebase
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred, {
     'databaseURL': 'https://receptorfirebase-default-rtdb.europe-west1.firebasedatabase.app/'

})

# === Функции ===


def load_history():
    ref = db.reference("history")
    history = ref.get()
    if not isinstance(history, dict):
        history = {}

    # Гарантируем наличие нужных ключей
    if "smoothies" not in history:
        history["smoothies"] = []
    if "recipes" not in history:
        history["recipes"] = []
    if "image_index" not in history:
        history["image_index"] = 0

    ref.set(history)  # сохраняем исправленную структуру
    return history


def save_history(history):
    ref = db.reference("history")
    ref.set(history)
