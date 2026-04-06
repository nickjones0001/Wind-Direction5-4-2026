import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials

# 1. SETUP GOOGLE SHEETS
# Replace 'your-google-sheet-id' with your actual Sheet ID
# Ensure credentials.json is in the same directory
SHEET_ID = 'your-google-sheet-id'
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def update_google_sheet(data):
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    # Appends a new row with the scraped data
    sheet.append_row(data)

# 2. SCRAPE FRANKSTON BEACH DATA
def scrape_frankston_data():
    # Example URL for coastal observations (Substitute with specific maritime source if required)
    url = "https://www.bom.gov.au/vic/observations/melbourne.shtml" 
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Target: Frankston (Note: Searching specifically for the Frankston row in the table)
    # This logic looks for the specific station name in the table
    try:
        station_row = soup.find('th', string='Frankston Beach') or soup.find('a', string='Frankston')
        parent_row = station_row.find_parent('tr')
        cells = parent_row.find_all('td')
        
        # Data mapping based on BOM table structure
        temp = cells[1].text
        wind_dir = cells[3].text
        wind_speed = cells[4].text
        
        data_to_log = ["Frankston Beach", temp, wind_dir, wind_speed]
        return data_to_log
    except Exception as e:
        print(f"Error finding Frankston data: {e}")
        return None

# 3. EXECUTION
if __name__ == "__main__":
    extracted_data = scrape_frankston_data()
    if extracted_data:
        update_google_sheet(extracted_data)
        print("Data successfully synced to Google Sheets.")
