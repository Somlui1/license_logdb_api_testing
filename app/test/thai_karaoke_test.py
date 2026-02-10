import requests
import json

# URL ของ API (ปรับ port ตามที่ run actual server)
base_url = "http://localhost:8000/transliterate/thai-to-karaoke/"

def test_transliterate(text, engine="royin"):
    payload = {
        "text": text,
        "engine": engine
    }
    
    try:
        print(f"กำลังส่งข้อมูล: {text} (Engine: {engine}) ...")
        response = requests.post(base_url, json=payload)
        
        if response.status_code == 200:
            print("✅ สำเร็จ! ผลลัพธ์:")
            print(json.dumps(response.json(), indent=4, ensure_ascii=False))
        else:
            print(f"❌ เกิดข้อผิดพลาด (Status {response.status_code}):")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ ไม่สามารถเชื่อต่อกับ Server ได้ (ตรวจสอบว่า FastAPI run อยู่หรือไม่)")
    except Exception as e:
        print(f"❌ Error: {e}")
    print("-" * 30)

if __name__ == "__main__":
    # Test Case 1: Paiboon Engine
    test_transliterate("สวัสดีครับ", "paiboon")

    # Test Case 2: Royin Engine (Official)
    test_transliterate("มหาวิทยาลัย", "royin")
