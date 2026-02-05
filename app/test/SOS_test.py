import requests

# URL ของ FastAPI ที่เราสร้างไว้
api_url = "http://localhost:8000/SOS/report-issue"

# ข้อมูลที่ต้องการส่ง (เปลี่ยน User/Pass ได้ตรงนี้)
payload = {
    "username": "wajeepradit.p",
    "password": "YOUR_REAL_PASSWORD",
    "sos_message": "ขอแจ้งซ่อม Printer ที่ชั้น 2 หมึกหมดและกระดาษติด (Reported via API)",
    
    # Optional fields (ถ้าไม่ใส่ ระบบจะใช้ Default ใน code)
    "requestor_name": "Wajeepradit Prompan",
    "tel": "9999"
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