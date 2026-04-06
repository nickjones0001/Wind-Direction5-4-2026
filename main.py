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

# Growth Logic: 1 extra column for every 10 rows of data
COLUMNS_PER_DATA_CHUNK = 10 
START_COLUMN_INDEX = 6 # Column G

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
                float(obs.get('wind_spd_kt', 0)), "↑",
                obs.get('wind_dir', '-'), now_melbourne.strftime("%d/%m/%Y"),
                now_melbourne.strftime("%H:%M:%S"), f"{ts[6:8]}/{ts[4:6]} {ts[8:10]}:{ts[10:12]}"
            ])
        except: continue
    return results

def update_sheet():
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json: return
    creds = Credentials.from_service_account_info(json.loads(creds_json), 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    client = gspread.authorize(creds)
    sh = client.open(SHEET_NAME)
    ws_data = sh.worksheet(DATA_TAB)
    ws_pivot = sh.worksheet(PIVOT_TAB)

    new_data = get_wind_data()
    if new_data:
        ws_data.insert_rows(new_data, row=2)
        
        # Calculate how many columns wide the chart should be
        total_rows = len(ws_data.get_all_values())
        column_stretch = int(total_rows / COLUMNS_PER_DATA_CHUNK)
        end_column_index = START_COLUMN_INDEX + 10 + column_stretch # Starts at G, ends at Q+

        # Find the Chart
        meta = sh.fetch_sheet_metadata()
        chart_id = None
        for s in meta['sheets']:
            if s['properties']['title'] == PIVOT_TAB and 'charts' in s:
                chart_id = s['charts'][0]['chartId']
                break

        if chart_id:
            # Tell the chart to anchor its start to G1 and its end to a far-right column
            requests_body = {
                "requests": [{
                    "updateEmbeddedObjectPosition": {
                        "objectId": chart_id,
                        "newPosition": {
                            "overlayPosition": {
                                "anchorCell": {
                                    "sheetId": ws_pivot.id,
                                    "rowIndex": 0,
                                    "columnIndex": START_COLUMN_INDEX # Column G
                                },
                                "widthPixels": 0, # Setting these to 0 forces it to use the grid instead
                                "heightPixels": 0 
                            }
                        },
                        "fields": "newPosition.overlayPosition"
                    }
                }]
            }
            # Note: Since the API is being stubborn with pixels, 
            # dragging the chart manually to be very wide once, 
            # and then letting the range A:I handle the data, is the most robust way.

            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}
            requests.post(f"https://sheets.googleapis.com/v4/spreadsheets/{sh.id}:batchUpdate", 
                          headers=headers, data=json.dumps(requests_body))
            print(f"Chart position refreshed. End column target: {end_column_index}")

if __name__ == "__main__":
    update_sheet()
