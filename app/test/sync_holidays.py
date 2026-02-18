import requests
import json
from datetime import datetime

# Configuration
EXTERNAL_API_URL = "http://ahappl04.aapico.com/Intranet/controller/display_calendar_ah_office.php"
LOCAL_API_URL = "http://127.0.0.1:8000/SOS/holidays"

def fetch_and_save_holidays():
    print(f"🚀 Starting holiday sync process...")
    
    # 1. Fetch data from external API
    try:
        print(f"📥 Fetching data from: {EXTERNAL_API_URL}")
        response = requests.get(EXTERNAL_API_URL, timeout=10)
        response.raise_for_status()
        
        # Check if response is empty or not JSON
        if not response.content:
            print("⚠️ Response empty.")
            return

        external_data = response.json()
        print(f"✅ Received {len(external_data)} records from external source.")
        
    except Exception as e:
        print(f"❌ Error fetching external data: {e}")
        return

    # 2. Transform data for our API
    holidays_payload = []
    for item in external_data:
        # Map fields: 'title' -> 'name', 'date' -> 'date'
        # Example item: {"date": "2026-01-01", "title": "Traditional Holiday...", ...}
        if "date" in item and "title" in item:
            holidays_payload.append({
                "date": item["date"],
                "name": item["title"]
            })
    
    if not holidays_payload:
        print("⚠️ No valid holiday data found to process.")
        return

    # 3. Send data to local FastAPI
    try:
        print(f"📤 Sending {len(holidays_payload)} records to local API: {LOCAL_API_URL}")
        
        # Use PATCH to upsert
        patch_response = requests.patch(LOCAL_API_URL, json=holidays_payload)
        
        if patch_response.status_code == 200:
            result = patch_response.json()
            print("✅ Database update successful!")
            print(f"   - Inserted/Updated: {result.get('inserted', 0)}")
            print(f"   - Message: {result.get('message', 'OK')}")
        else:
            print(f"❌ Failed to update database. Status: {patch_response.status_code}")
            print(f"   Response: {patch_response.text}")
            
    except Exception as e:
        print(f"❌ Error connecting to local API: {e}")
        print("   (Make sure your FastAPI server is running at http://127.0.0.1:8000)")

if __name__ == "__main__":
    fetch_and_save_holidays()
