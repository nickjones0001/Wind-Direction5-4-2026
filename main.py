def update_sheet():
    # ... (Standard Creds/Client setup as before) ...
    sh = client.open(SHEET_NAME)
    ws_pivot = sh.worksheet(PIVOT_TAB)

    # STRESS TEST: Resize Columns G through R to be massive
    # This forces the underlying "ground" of the chart to expand
    requests_body = {
        "requests": [
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": ws_pivot.id,
                        "dimension": "COLUMNS",
                        "startIndex": 6, # Column G
                        "endIndex": 18   # Column R
                    },
                    "properties": {
                        "pixelSize": 400 # Make each column 400px wide
                    },
                    "fields": "pixelSize"
                }
            }
        ]
    }

    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}
    
    # Send the "Grid Expansion" command
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sh.id}:batchUpdate"
    response = requests.post(url, headers=headers, data=json.dumps(requests_body))
    
    if response.status_code == 200:
        print("STRESS TEST SUCCESS: The grid has expanded. Check the Pivot tab!")
    else:
        print(f"FAILED: {response.text}")
