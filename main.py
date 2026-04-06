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
PIVOT_TAB = "Wind+Dir-Pivot"
TIMEZONE = pytz.timezone('Australia/Melbourne')

# Scaling Settings
BASE_WIDTH = 800      # Starting width in pixels
PIXELS_PER_ROW = 3    # Increase this to make it stretch faster
CHART_HEIGHT = 450    # Fixed height

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
            obs_date = f"{raw_ts[6:8]}/{raw_ts[4:6]}/{raw_ts[0:4]}"
            obs_time = f"{raw_ts[8:10]}:{raw_ts[10:12]}"
            speed = float(latest_obs.get('wind_spd_kt', 0))
            text_dir = latest_obs.get('wind_dir', '-')
            arrow = DIRECTION_ARROWS.get(text_dir, "-")
            obs_datetime_label = f"{raw_ts[6:8]}/{raw_ts[4:6]} {obs_time}"
            row = [obs_date, obs_time, name, speed, arrow, text_dir, 
                   now_melbourne.strftime("%d/%m/%Y"), now_melbourne.strftime("%H:%M:%S"), obs_datetime_label]
            results.append(row)
        except Exception as e:
            print(f"Error fetching data for {name}: {e}")
    return results

def update_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json: 
        print("Missing Credentials")
        return
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sh = client.open(SHEET_NAME)
    
    data_ws = sh.worksheet(DATA_TAB)
    pivot_ws = sh.worksheet(PIVOT_TAB)

    new_rows = get_wind_data()
    if new_rows:
        data_ws.insert_rows(new_rows, row=2)
        
        # Calculate row count and new width
        all_data = data_ws.get_all_values()
        total_rows = len(all_data)
        dynamic_width = BASE_WIDTH + (total_rows * PIXELS_PER_ROW)

        # CORRECT WAY TO FIND CHART ID:
        # Fetch metadata for the entire spreadsheet to find the chart on the Pivot Tab
        metadata = sh.fetch_sheet_metadata()
        chart_id = None
        
        for sheet in metadata['sheets']:
            if sheet['properties']['title'] == PIVOT_TAB:
                if 'charts' in sheet:
                    # Get the ID of the first chart found on that tab
                    chart_id = sheet['charts'][0]['chartId']
                    break

        if chart_id is not None:
            requests_body = {
                "requests": [
                    {
                        "updateChartSpec": {
                            "chartId": chart_id,
                            "spec": {
                                "sourceRange": {
                                    "sources": [
                                        {
                                            "sheetId": data_ws.id,
                                            "startRowIndex": 0,
                                            "endRowIndex": total_rows,
                                            "startColumnIndex": 0,
                                            "endColumnIndex": 5
                                        }
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "updateEmbeddedObjectPosition": {
                            "objectId": chart_id,
                            "newPosition": {
                                "overlayPosition": {
                                    "anchorCell": {
                                        "sheetId": pivot_ws.id, 
                                        "rowIndex": 0,    # Row 1
                                        "columnIndex": 6  # Column G
                                    },
                                    "widthPixels": dynamic_width,
                                    "heightPixels": CHART_HEIGHT
                                }
                            },
                            "fields": "newPosition.overlayPosition"
                        }
                    }
                ]
            }
            sh.batch_update(requests_body)
            print(f"Success: Updated row {total_rows} and widened chart to {dynamic_width}px.")
        else:
            print(f"Error: No chart found on the tab '{PIVOT_TAB}'.")

if __name__ == "__main__":
    update_sheet()
