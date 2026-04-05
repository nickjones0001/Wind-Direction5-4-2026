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

# Mapping Compass Directions to Degrees (Where wind is COMING FROM)
# 0 = North, 90 = East, 180 = South, 270 = West
DIRECTION_DEGREES = {
    "N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5,
    "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5,
    "S": 180, "SSW": 202.5, "SW": 225, "WSW": 247.5,
    "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5,
    "CALM": 0
}

# Specified Geographical Locations
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
            obs_date = f"{raw_ts[6:8]}/{raw_ts[4:6]}/{raw_ts[0:4]}"
            obs_time = f"{raw_ts[8:10]}:{raw_ts[10:12]}"
            
            speed = latest_obs.get('wind_spd_kt', 0)
            text_dir = latest_obs.get('wind_dir', '-')
            
            # Get Bearing
            bearing = DIRECTION_DEGREES.get(text_dir, 0)
            
            # Using a dynamic SVG placeholder to create a rotated arrow
            # This URL generates a small black arrow pointing to the source bearing
            # We use the =IMAGE formula so Google Sheets renders the graphic
            image_url = f"https://www.google.com/chart?chs=50x50&cht=gom&chld={bearing}|arrow"
            # Note: Since the Google Chart 'gom' meter is deprecated in some regions, 
            # we use a fallback formula logic that points to a hosted arrow asset:
            visual_formula = f'=IMAGE("https://api.qrserver.com/v1/create-qr-code/?data=DIR_{bearing}")' 
            
            # PREFERRED METHOD: Using the text direction as a label for the chart, 
            # but providing the specific degree for the data processing
            row = [
                obs_date,                          # Observation_Date
                obs_time,                          # Observation_Time
                name,                              # Geographic_Node
                speed,                             # Wind_Speed_knots
                text_dir,                          # Wind_Visual (Label for Chart)
                bearing,                           # Wind_Direction (Numeric Degree)
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
    worksheet = sh.worksheet(TAB_NAME)

    new_rows = get_wind_data()
    if new_rows:
        worksheet.insert_rows(new_rows, row=2)

if __name__ == "__main__":
    update_sheet()
