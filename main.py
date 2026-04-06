import gspread
from google.oauth2.service_account import Credentials
import datetime
import pytz
import json
import os
import random

# Configuration
SHEET_NAME = "Wind+WaveScrapeLLM 28-3-2026"
DATA_TAB = "Wind+Dir"
TIMEZONE = pytz.timezone('Australia/Melbourne')

DIRECTION_ARROWS = {"N":"↓","NNE":"↙","NE":"↙","ENE":"←","E":"←","ESE":"↖","SE":"↖","SSE":"↑","S":"↑","SSW":"↗","SW":"↗","WSW":"→","W":"→","WNW":"↘","NW":"↘","NNW":"↓","CALM":"○"}
DIRS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

def generate_dummy_data():
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    client = gspread.authorize(creds)
    ws = client.open(SHEET_NAME).worksheet(DATA_TAB)

    dummy_rows = []
    # Start 14 days ago, end 3 days ago (where live backfill takes over)
    now = datetime.datetime.now(TIMEZONE)
    start_date = now - datetime.timedelta(days=14)
    
    nodes = {
        "South Channel Island": {"base": 14, "var": 6},
        "Fawkner Beacon": {"base": 10, "var": 4},
        "Frankston Beach": {"base": 7, "var": 3}
    }

    # Iterate through every 30 minutes for 11 days
    for day in range(11):
        current_day = start_date + datetime.timedelta(days=day)
        
        for hour in range(24):
            for minute in [0, 30]:
                dt = current_day.replace(hour=hour, minute=minute, second=0)
                
                # Simulate a daily sea breeze (windier in afternoon)
                time_multiplier = 1.0 + (math.sin((hour - 6) * math.pi / 12) * 0.5) 
                
                for name, stats in nodes.items():
                    speed = round((stats['base'] + random.uniform(-stats['var'], stats['var'])) * time_multiplier, 1)
                    text_dir = random.choice(DIRS)
                    
                    dummy_rows.append([
                        dt.strftime("%d/%m/%Y"),           # A: Date
                        dt.strftime("%H:%M"),              # B: Time
                        name,                               # C: Station
                        speed,                              # D: Speed
                        DIRECTION_ARROWS.get(text_dir, "-"),# E: Visual
                        text_dir,                           # F: Text Dir
                        "DUMMY", "DUMMY",                   # G, H: Metadata
                        dt.strftime("%Y-%m-%d %H:%M:%S")    # I: ISO Label
                    ])

    # Batch upload to avoid API timeouts
    ws.append_rows(dummy_rows)
    print(f"Successfully added {len(dummy_rows)} rows of dummy maritime data.")

import math
if __name__ == "__main__":
    generate_dummy_data()
