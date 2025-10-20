# storage.py

import json
from config import ECONOMY_FILE

def load_data(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def get_user_data(user_id):
    data = load_data(ECONOMY_FILE)
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {
            'balance': 100,
            'bank': 0,
            'last_work': None,
            'last_daily': None,
            'last_crime': None,
            'job': None,
            'business_job': None,
            'level': 1,
            'experience': 0,
            'last_rob': None
        }
        save_data(ECONOMY_FILE, data)
    return data[user_id]

def update_user_data(user_id, user_data):
    data = load_data(ECONOMY_FILE)
    data[str(user_id)] = user_data
    save_data(ECONOMY_FILE, data)
