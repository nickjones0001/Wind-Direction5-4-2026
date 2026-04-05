import gspread
from google.oauth2.service_account import Credentials
import requests
from bs4 import BeautifulSoup
import datetime
import pytz
import os
import json

# Configuration
SHEET_NAME = "Wind+WaveScrapeLLM 28-3-2026"
TAB_NAME = "Wind+Dir"
TIMEZONE = pytz.timezone('Australia/Melbourne')

# Specified Geographical Locations
STATIONS = {
    "Frankston Beach": "http://www.bom.gov.au/fwo/IDV60901/IDV60901.94870.json",
    "Fawkner Beacon": "http://www.bom.gov.au/fwo/IDV60901/IDV60901.94864.json",
    "South Channel Island": "http://www.bom.gov.au/fwo/IDV60901/IDV60901.94857.json"
}

def get_wind_data():
    results = []
    now_melbourne = datetime.datetime.now(TIMEZONE)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for name, url in STATIONS.items():
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            # Get the most recent observation from the JSON list
            latest_obs = data['observations']['data'][0]
            
            # Mapping BOM data to your headers
            obs_date = latest_obs['local_date_time_full'][:8]
            formatted_date = f"{obs_date[6:8]}/{obs_date[4:6]}/{obs_date[0:4]}"
            obs_time = latest_obs['local_date_time_full'][8:12]
            formatted_time = f"{obs_time[0:2]}:{obs_time[2:4]}"
            
            row = [
                formatted_date,                    # Observation_Date
                formatted_time,                    # Observation_Time
                name,                              # Geographic_Node
                latest_obs.get('wind_spd_kt', 0),  # Wind_Speed_knots
                latest_obs.get('wind_dir', '-'),   # Wind_Visual (Placeholder for Dir)
                latest_obs.get('wind_dir', '-'),   # Wind_Direction
                now_melbourne.strftime("%d/%m/%Y"),# Extracted_Date
                now_melbourne.strftime("%H:%M:%S") # Extracted_Time
            ]
            results.append(row)
        except Exception as e:
            print(f"Error fetching data for {name}: {e}")
            
    return results

def update_sheet():
    # Authenticate using GitHub Secret
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ['GOOGLE_CREDENTIALS'])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Open the specific Sheet and Tab
    sh = client.open(SHEET_NAME)
    try:
        worksheet = sh.worksheet(TAB_NAME)
    except gspread.exceptions.WorksheetNotFound:
        # Create tab if missing
        worksheet = sh.add_worksheet(title=TAB_NAME, rows="1000", cols="8")
        headers = ["Observation_Date", "Observation_Time", "Geographic_Node", "Wind_Speed_knots", "Wind_Visual", "Wind_Direction", "Extracted_Date", "Extracted_Time"]
        worksheet.append_row(headers)

    new_data = get_wind_data()
    
    # Insert from bottom up (Newest at Top)
    # We insert at row 2 to keep the header at row 1
    if new_data:
        worksheet.insert_rows(new_data, row=2)

if __name__ == "__main__":
    update_sheet()
