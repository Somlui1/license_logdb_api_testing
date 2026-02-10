import requests

# URL ของ FastAPI ที่เราสร้างไว้
api_url = "http://localhost:8000/SOS/report-issue"

# ข้อมูลที่ต้องการส่ง (Login Intranet)
payload = {
   "sos_message": "test sos",     # รายละเอียดปัญหา
   "requestor_name": "Wajeepradit Prompan",
   "email": "[EMAIL_ADDRESS]",
   "dept": "IT",
   "tel": "0812345678",
   "location": "BKK",
   "company": "AH",
   "ips": "10.10.20.93(API_AGENT)"
}

try:
    print(f"กำลังส่งข้อมูลไปที่ {api_url} ...")
    response = requests.post(api_url, json=payload)
    
    if response.status_code == 200:
        print("✅ สำเร็จ! ข้อมูลตอบกลับ:")
        print(response.json())
    else:
        print(f"❌ เกิดข้อผิดพลาด (Status {response.status_code}):")
        print(response.text)

except Exception as e:
    print(f"Connection Error: {e}")