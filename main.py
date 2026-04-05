import gspread
from google.oauth2.service_account import Credentials
import requests
from bs4 import BeautifulSoup
import datetime
import pytz
import os
import json

# Configuration
SHEET_NAME = "Wind+Dir"
TIMEZONE = pytz.timezone('Australia/Melbourne')
# Specific Geographic Nodes
STATIONS = {
    "Frankston Beach": "https://www.bom.gov.au/vic/observations/melbourne.shtml", # Representative link; scrapers usually target specific ID/Table rows
    "Fawkner Beacon": "https://www.bom.gov.au/vic/observations/melbourne.shtml",
    "South Channel Island": "https://www.bom.gov.au/vic/observations/melbourne.shtml"
}

def get_wind_data():
    # In a production environment, this would parse the specific table rows for each node
    # Here we define the extraction logic for the specified headers
    results = []
    now = datetime.datetime.now(TIMEZONE)
    
    # Placeholder for scraping logic targeting specific BOM/Maritime rows
    for station_name in STATIONS.keys():
        # Scrape logic here... 
        # Example data structure based on your headers:
        row = [
            now.strftime("%d/%m/%Y"),      # Observation_Date
            now.strftime("%H:%M"),         # Observation_Time
            station_name,                  # Geographic_Node
            "15",                          # Wind_Speed_knots (Extracted)
            "↗",                           # Wind_Visual (Directional Arrow)
            "SW",                          # Wind_Direction
            now.strftime("%d/%m/%Y"),      # Extracted_Date
            now.strftime("%H:%M")          # Extracted_Time
        ]
        results.append(row)
    return results

def update_sheet():
    # Authenticate
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ['GOOGLE_CREDENTIALS'])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Open Sheet
    try:
        sh = client.open("Maritime_Wind_Data") # Ensure your Google Sheet is named this
        worksheet = sh.worksheet(SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        # Create sheet if it doesn't exist with headers
        sh = client.open("Maritime_Wind_Data")
        worksheet = sh.add_worksheet(title=SHEET_NAME, rows="1000", cols="8")
        headers = ["Observation_Date", "Observation_Time", "Geographic_Node", "Wind_Speed_knots", "Wind_Visual", "Wind_Direction", "Extracted_Date", "Extracted_Time"]
        worksheet.append_row(headers)

    data = get_wind_data()
    
    # Insert at row 2 (below headers) to keep most recent at the top
    for row in data:
        worksheet.insert_row(row, 2)

if __name__ == "__main__":
    update_sheet()
