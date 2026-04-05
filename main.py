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

# Mapping Compass Directions to Visual Arrows
DIRECTION_ARROWS = {
    "N": "↓", "NNE": "↓", "NE": "↙", "ENE": "←",
    "E": "←", "ESE": "←", "SE": "↖", "SSE": "↑",
    "S": "↑", "SSW": "↑", "SW": "↗", "WSW": "→",
    "W": "→", "WNW": "→", "NW": "↘", "NNW": "↓",
    "CALM": "○", "-": "-"
}

# Specified Geographical Locations (BOM JSON feeds)
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
            
            # Format Time/Date from BOM string (YYYYMMDDHHMMSS)
            raw_ts = latest_obs['local_date_time_full']
            obs_date = f"{raw_ts[6:8]}/{raw_ts[4:6]}/{raw_ts[0:4]}"
            obs_time = f"{raw_ts[8:10]}:{raw_ts[10:12]}"
            
            # Wind Speed & Direction
            speed = latest_obs.get('wind_spd_kt', 0)
            text_dir = latest_obs.get('wind_dir', '-')
            
            # Get the visual arrow symbol
            visual_arrow = DIRECTION_ARROWS.get(text_dir, text_dir)
            
            row = [
                obs_date,                          # Observation_Date
                obs_time,                          # Observation_Time
                name,                              # Geographic_Node
                speed,                             # Wind_Speed_knots
                visual_arrow,                      # Wind_Visual (Now with Arrows)
                text_dir,                          # Wind_Direction (Text)
                now_melbourne.strftime("%d/%m/%Y"),# Extracted_Date
                now_melbourne.strftime("%H:%M:%S") # Extracted_Time
            ]
            results.append(row)
        except Exception as e:
            print(f"Error fetching data for {name}: {e}")
            
    return results

def update_sheet():
    # Auth
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json:
        print("Error: GOOGLE_CREDENTIALS secret not found.")
        return

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Access Spreadsheet
    sh = client.open(SHEET_NAME)
    try:
        worksheet = sh.worksheet(TAB_NAME)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=TAB_NAME, rows="1000", cols="8")
        headers = ["Observation_Date", "Observation_Time", "Geographic_Node", "Wind_Speed_knots", "Wind_Visual", "Wind_Direction", "Extracted_Date", "Extracted_Time"]
        worksheet.append_row(headers)

    new_rows = get_wind_data()
    
    if new_rows:
        # Insert at row 2 to keep newest data at the top
        worksheet.insert_rows(new_rows, row=2)
        print(f"Successfully added {len(new_rows)} rows with arrows.")

if __name__ == "__main__":
    update_sheet()
