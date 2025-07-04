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
    if history is None:
        history = {"smoothies": [], "recipes": [], "image_index": 0}
        ref.set(history)
    return history

def save_history(history):
    ref = db.reference("history")
    ref.set(history)
