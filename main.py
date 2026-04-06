import gspread
from google.oauth2.service_account import Credentials
import requests
import datetime
import pytz
import os
import json

# Configuration
SHEET_NAME = "Wind+WaveScrapeLLM 28-3-2026"
TAB_NAME = "Wind+Dir"
TIMEZONE = pytz.timezone('Australia/Melbourne')

# Mapping Compass Directions to Degrees
DIRECTION_DEGREES = {
    "N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5,
    "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5,
    "S": 180, "SSW": 202.5, "SW": 225, "WSW": 247.5,
    "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5,
    "CALM": 0
}

# 16-point Visual Arrow mapping
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
            # READABLE FORMAT: "DD/MM HH:MM"
            # Example: "06/04 10:00"
            obs_label = f"{raw_ts[6:8]}/{raw_ts[4:6]} {raw_ts[8:10]}:{raw_ts[10:12]}"
            
            speed = float(latest_obs.get('wind_spd_kt', 0))
            text_dir = latest_obs.get('wind_dir', '-')
            bearing = float(DIRECTION_DEGREES.get(text_dir, 0))
            arrow = DIRECTION_ARROWS.get(text_dir, "-")
            
            row = [
                obs_label,                         # Combined Date/Time for X-Axis
                name,                              # Geographic_Node
                speed,                             # Wind_Speed_knots
                arrow,                             # Wind_Visual (Label)
                text_dir,                          # Wind_Direction (Text)
                bearing,                           # Wind_Direction (Numeric)
                now_melbourne.strftime("%d/%m/%Y"),# Extracted_Date
                now_melbourne.strftime("%H:%M:%S") # Extracted_Time
            ]
            results.append(row)
        except Exception as e:
            print(f"Error: {e}")
            
    return results

def update_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json: return
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    sh = client.open(SHEET_NAME)
    try:
        worksheet = sh.worksheet(TAB_NAME)
    except:
        worksheet = sh.add_worksheet(title=TAB_NAME, rows="2000", cols="8")
        worksheet.append_row(["Observation_Label", "Geographic_Node", "Wind_Speed_knots", "Wind_Visual", "Wind_Direction_Text", "Wind_Direction_Deg", "Extracted_Date", "Extracted_Time"])

    new_rows = get_wind_data()
    if new_rows:
        worksheet.insert_rows(new_rows, row=2)

if __name__ == "__main__":
    update_sheet()
