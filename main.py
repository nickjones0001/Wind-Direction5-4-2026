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

# Scaling Settings
BASE_WIDTH = 1000      # Starting width in pixels
PIXELS_PER_ROW = 4     # How much to grow per row added
CHART_HEIGHT = 450    

DIRECTION_ARROWS = {
    "N": "↑", "NNE": "↗", "NE": "↗", "ENE": "→",
    "E": "→", "ESE": "↘", "SE": "↘", "SSE": "↓",
    "S": "↓", "SSW": "↙", "SW": "↙", "WSW": "←",
    "W": "←", "WNW": "↖", "NW": "↖", "NNW": "↑",
    "CALM": "○", "-": "-"
}

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
            results.append([
                f"{ts[6:8]}/{ts[4:6]}/{ts[0:4]}", f"{ts[8:10]}:{ts[10:12]}", name,
                float(obs.get('wind_spd_kt', 0)), DIRECTION_ARROWS.get(obs.get('wind_dir', '-'), "-"),
                obs.get('wind_dir', '-'), now_melbourne.strftime("%d/%m/%Y"),
                now_melbourne.strftime("%H:%M:%S"), f"{ts[6:8]}/{ts[4:6]} {ts[8:10]}:{ts[10:12]}"
            ])
        except: continue
    return results

def update_sheet():
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json: 
        print("Credentials not found.")
        return
        
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    
    client = gspread.authorize(creds)
    sh = client.open(SHEET_NAME)
    ws_data = sh.worksheet(DATA_TAB)
    ws_pivot = sh.worksheet(PIVOT_TAB)

    new_data = get_wind_data()
    if new_data:
        ws_data.insert_rows(new_data, row=2)
        
        # Calculate new width based on the current row count
        # This will grow the chart physically as your history increases
        current_rows = len(ws_data.get_all_values())
        calculated_width = int(BASE_WIDTH + (current_rows * PIXELS_PER_ROW))

        # Identify the existing chart on the Pivot tab
        meta = sh.fetch_sheet_metadata()
        chart_id = None
        for sheet in meta['sheets']:
            if sheet['properties']['title'] == PIVOT_TAB and 'charts' in sheet:
                chart_id = sheet['charts'][0]['chartId']
                break

        if chart_id:
            # SURGICAL STRETCH REQUEST
            requests_body = {
                "requests": [{
                    "updateEmbeddedObjectPosition": {
                        "objectId": chart_id,
                        "newPosition": {
                            "overlayPosition": {
                                "anchorCell": {
                                    "sheetId": ws_pivot.id, 
                                    "rowIndex": 0,    # Row 1
                                    "columnIndex": 6  # Column G
                                },
                                "widthPixels": calculated_width,
                                "heightPixels": CHART_HEIGHT
                            }
                        },
                        "fields": "newPosition.overlayPosition.widthPixels"
                    }
                }]
            }

            # Authenticate and send raw POST request
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}
            
            response = requests.post(
                f"https://sheets.googleapis.com/v4/spreadsheets/{sh.id}:batchUpdate", 
                headers=headers, 
                data=json.dumps(requests_body)
            )
            
            if response.status_code == 200:
                print(f"SUCCESS: Data added. Chart physically stretched to {calculated_width}px.")
            else:
                print(f"STRETCH FAILED: {response.text}")
        else:
            print("No chart found to stretch. Ensure a chart exists on the Pivot tab.")

if __name__ == "__main__":
    update_sheet()
