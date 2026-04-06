import gspread
from google.oauth2.service_account import Credentials
import requests
import datetime
import pytz
import os
import json

# Configuration
SHEET_NAME = "Wind+WaveScrapeLLM 28-3-2026"
DATA_TAB = "Wind+Dir"
TIMEZONE = pytz.timezone('Australia/Melbourne')

DIRECTION_ARROWS = {"N":"↑","NNE":"↗","NE":"↗","ENE":"→","E":"→","ESE":"↘","SE":"↘","SSE":"↓","S":"↓","SSW":"↙","SW":"↙","WSW":"←","W":"←","WNW":"↖","NW":"↖","NNW":"↑","CALM":"○"}

def get_wind_data():
    results = []
    now_melbourne = datetime.datetime.now(TIMEZONE)
    headers = {'User-Agent': 'Mozilla/5.0'}
    stations = {
        "Frankston Beach": "http://www.bom.gov.au/fwo/IDV60901/IDV60901.94870.json",
        "Fawkner Beacon": "http://www.bom.gov.au/fwo/IDV60901/IDV60901.94864.json",
        "South Channel Island": "http://www.bom.gov.au/fwo/IDV60901/IDV60901.94857.json"
    }
    for name, url in stations.items():
        try:
            res = requests.get(url, headers=headers).json()
            obs = res['observations']['data'][0]
            ts = obs['local_date_time_full']
            
            # ISO-style format: YYYY-MM-DD HH:MM:SS
            # This is the most "machine-readable" format for Google Sheets to auto-convert to Date/Time
            iso_label = f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:00"
            
            results.append([
                f"{ts[6:8]}/{ts[4:6]}/{ts[0:4]}", 
                f"{ts[8:10]}:{ts[10:12]}", 
                name,
                float(obs.get('wind_spd_kt', 0)), 
                DIRECTION_ARROWS.get(obs.get('wind_dir', '-'), "-"),
                obs.get('wind_dir', '-'), 
                now_melbourne.strftime("%Y-%m-%d"),
                now_melbourne.strftime("%H:%M:%S"), 
                iso_label # Column I
            ])
        except: continue
    return results

def update_sheet():
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json: return
    creds = Credentials.from_service_account_info(json.loads(creds_json), 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    client = gspread.authorize(creds)
    sh = client.open(SHEET_NAME)
    ws = sh.worksheet(DATA_TAB)

    new_data = get_wind_data()
    if new_data:
        ws.insert_rows(new_data, row=2)
        print("Data pushed. Ensure Column I is formatted as 'Date time' in Sheets.")

if __name__ == "__main__":
    update_sheet()
