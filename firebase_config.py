import firebase_admin
from firebase_admin import credentials, db
import os

cred = credentials.Certificate("firebase_key.json")  # Переименуй твой JSON-файл так
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://receptorfirebase-default-rtdb.firebaseio.com/'
})
