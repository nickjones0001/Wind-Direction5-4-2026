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

# CORRECTED MARITIME STATIONS
STATIONS = {
    "Fawkner Beacon": "http://www.bom.gov.au/fwo/IDV60901/IDV60901.95872.json",
    "South Channel Island": "http://www.bom.gov.au/fwo/IDV60901/IDV60901.94853.json",
    "Frankston Beach": "http://www.bom.gov.au/fwo/IDV60801/IDV60801.94871.json"
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
            
            # ISO format for Google Sheets Timeline: YYYY-MM-DD HH:MM:SS
            iso_label = f"{raw_ts[0:4]}-{raw_ts[4:6]}-{raw_ts[6:8]} {raw_ts[8:10]}:{raw_ts[10:12]}:00"
            
            row = [
                f"{raw_ts[6:8]}/{raw_ts[4:6]}/{raw_ts[0:4]}", # A: Date
                f"{raw_ts[8:10]}:{raw_ts[10:12]}",           # B: Time
                name,                                        # C: Station
                float(latest_obs.get('wind_spd_kt', 0)),     # D: Speed (Knots)
                DIRECTION_ARROWS.get(latest_obs.get('wind_dir', '-'), "-"), # E: Visual
                latest_obs.get('wind_dir', '-'),             # F: Text Dir
                now_melbourne.strftime("%Y-%m-%d"),          # G: Scraping Date
                now_melbourne.strftime("%H:%M:%S"),          # H: Scraping Time
                iso_label                                    # I: Chart Label
            ]
            results.append(row)
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            
    return results

def update_sheet():
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json: return
        
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    client = gspread.authorize(creds)
    
    try:
        sh = client.open(SHEET_NAME)
        ws = sh.worksheet(DATA_TAB)
        
        new_data = get_wind_data()
        if new_data:
            ws.insert_rows(new_data, row=2)
            print(f"Success: Updated with Maritime IDs 95872, 94853, 94871")
            
    except Exception as e:
        print(f"Sheet Update Error: {e}")

if __name__ == "__main__":
    update_sheet()
