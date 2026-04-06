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
            
            obs_date = f"{raw_ts[6:8]}/{raw_ts[4:6]}/{raw_ts[0:4]}"
            obs_time = f"{raw_ts[8:10]}:{raw_ts[10:12]}"
            speed = float(latest_obs.get('wind_spd_kt', 0))
            text_dir = latest_obs.get('wind_dir', '-')
            arrow = DIRECTION_ARROWS.get(text_dir, "-")
            obs_datetime_label = f"{raw_ts[6:8]}/{raw_ts[4:6]} {obs_time}"
            
            row = [
                obs_date,                           # A
                obs_time,                           # B
                name,                               # C
                speed,                              # D
                arrow,                              # E
                text_dir,                           # F
                now_melbourne.strftime("%d/%m/%Y"), # G
                now_melbourne.strftime("%H:%M:%S"), # H
                obs_datetime_label                  # I
            ]
            results.append(row)
        except Exception as e:
            print(f"Error fetching data for {name}: {e}")
    return results

def update_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json: return
        
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    sh = client.open(SHEET_NAME)
    
    # 1. Handle Data Tab
    try:
        data_worksheet = sh.worksheet(DATA_TAB)
    except:
        data_worksheet = sh.add_worksheet(title=DATA_TAB, rows="2000", cols="9")
        headers = ["Observation_Date", "Observation_Time", "Geographic_Node", "Wind_Speed_knots", "Wind_Visual", "Wind_Direction", "Extracted_Date", "Extracted_Time", "Obs_DateTime"]
        data_worksheet.append_row(headers)

    # 2. Insert Data
    new_rows = get_wind_data()
    if new_rows:
        data_worksheet.insert_rows(new_rows, row=2)
        
        # 3. Handle Chart on Pivot Tab
        try:
            pivot_worksheet = sh.worksheet(PIVOT_TAB)
            all_data = data_worksheet.get_all_values()
            total_rows = len(all_data)
            
            charts = pivot_worksheet.get_all_charts()
            if charts:
                chart_id = charts[0].id
                
                # Update Chart Source Range
                # Note: 'endColumnIndex': 5 covers A through E
                requests_body = {
                    "requests": [
                        {
                            "updateChartSpec": {
                                "chartId": chart_id,
                                "spec": {
                                    "sourceRange": {
                                        "sources": [
                                            {
                                                "sheetId": data_worksheet.id,
                                                "startRowIndex": 0,
                                                "endRowIndex": total_rows,
                                                "startColumnIndex": 0,
                                                "endColumnIndex": 5
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    ]
                }
                sh.batch_update(requests_body)
                print(f"Pivot Chart updated to row {total_rows}")
        except Exception as e:
            print(f"Pivot Tab/Chart update failed: {e}")

if __name__ == "__main__":
    update_sheet()
