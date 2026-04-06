import gspread
from google.oauth2.service_account import Credentials
import google.auth.transport.requests
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

# --- TEST VALUES (Force Wide) ---
BASE_WIDTH = 2500      
PIXELS_PER_ROW = 5    
CHART_HEIGHT = 500    

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
    
    data_ws = sh.worksheet(DATA_TAB)
    pivot_ws = sh.worksheet(PIVOT_TAB)

    new_rows = get_wind_data()
    if new_rows:
        data_ws.insert_rows(new_rows, row=2)
        
        all_data = data_ws.get_all_values()
        total_rows = len(all_data)
        calc_width = int(BASE_WIDTH + (total_rows * PIXELS_PER_ROW))

        # 1. Find and Delete Existing Charts
        metadata = sh.fetch_sheet_metadata()
        delete_requests = []
        for sheet in metadata['sheets']:
            if sheet['properties']['title'] == PIVOT_TAB:
                if 'charts' in sheet:
                    for chart in sheet['charts']:
                        delete_requests.append({"deleteEmbeddedObject": {"objectId": chart['chartId']}})

        # 2. Prepare the NEW Chart Request
        add_chart_request = {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Wind Speed Profile (Dynamic)",
                        "basicChart": {
                            "chartType": "LINE",
                            "legendPosition": "BOTTOM_LEGEND",
                            "domains": [{"domain": {"sourceRange": {"sources": [{"sheetId": data_ws.id, "startRowIndex": 0, "endRowIndex": total_rows, "startColumnIndex": 8, "endColumnIndex": 9}]}}}],
                            "series": [{"series": {"sourceRange": {"sources": [{"sheetId": data_ws.id, "startRowIndex": 0, "endRowIndex": total_rows, "startColumnIndex": 3, "endColumnIndex": 4}]}}, "targetAxis": "LEFT_AXIS"}]
                        }
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {"sheetId": pivot_ws.id, "rowIndex": 0, "columnIndex": 6},
                            "widthPixels": calc_width,
                            "heightPixels": int(CHART_HEIGHT)
                        }
                    }
                }
            }
        }

        # Combine: Delete old, add new
        full_requests = delete_requests + [add_chart_request]
        
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sh.id}:batchUpdate"
        
        response = requests.post(url, headers=headers, data=json.dumps({"requests": full_requests}))
        
        if response.status_code == 200:
            print(f"RECREATED CHART: Width {calc_width}px starting at Column G.")
        else:
            print(f"FAILURE: {response.text}")

if __name__ == "__main__":
    update_sheet()
