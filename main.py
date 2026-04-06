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

DIRECTION_ARROWS = {
    "N": "↑", "NNE": "↗", "NE": "↗", "ENE": "→",
    "E": "→", "ESE": "↘", "SE": "↘", "SSE": "↓",
    "S": "↓", "SSW": "↙", "SW": "↙", "WSW": "←",
    "W": "←", "WNW": "↖", "NW": "↖", "NNW": "↑",
    "CALM": "○", "-": "-"
}

STATIONS = {
    "Frankston Beach": "http://www.bom.gov.au/fwo/IDV60901/IDV60901.94870.json",
    "Fawkner Beacon": "http://www.bom.gov.au/fwo/IDV60901/IDV60901.94864.json",
    "South Channel Island": "http://www.bom.gov.au/fwo/IDV60901/IDV60901.94857.json"
}

def get_wind_data():
    results = []
    now_melbourne = datetime.datetime.now(TIMEZONE)
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for name, url in STATIONS.items():
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            latest_obs = data['observations']['data'][0]
            raw_ts = latest_obs['local_date_time_full']
            
            # Label: DD/MM HH:MM
            obs_datetime_label = f"{raw_ts[6:8]}/{raw_ts[4:6]} {raw_ts[8:10]}:{raw_ts[10:12]}"
            
            row = [
                f"{raw_ts[6:8]}/{raw_ts[4:6]}/{raw_ts[0:4]}", # A
                f"{raw_ts[8:10]}:{raw_ts[10:12]}",           # B
                name,                                        # C
                float(latest_obs.get('wind_spd_kt', 0)),     # D
                DIRECTION_ARROWS.get(latest_obs.get('wind_dir', '-'), "-"), # E
                latest_obs.get('wind_dir', '-'),             # F
                now_melbourne.strftime("%d/%m/%Y"),          # G
                now_melbourne.strftime("%H:%M:%S"),          # H
                obs_datetime_label                           # I
            ]
            results.append(row)
        except Exception as e:
            print(f"BOM Error: {e}")
    return results

def update_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json: return
        
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    try:
        sh = client.open(SHEET_NAME)
        ws = sh.worksheet(DATA_TAB)
        
        new_data = get_wind_data()
        if new_data:
            # Insert at Row 2. The Pivot Table (A:I) will pick this up automatically.
            ws.insert_rows(new_data, row=2)
            print(f"Scrape successful. Data added to row 2.")
            
    except Exception as e:
        print(f"Script Error: {e}")

if __name__ == "__main__":
    update_sheet()
