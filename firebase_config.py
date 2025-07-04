import firebase_admin
from firebase_admin import credentials, db
import os
import json

cred_dict = json.loads(os.environ["FIREBASE_KEY_JSON"])
cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://receptorfirebase-default-rtdb.firebaseio.com/'
})
