import requests

# ==========================================
# Test Script สำหรับ SOS SLA Calculation
# ==========================================

API_BASE = "http://localhost:8000/SOS"

def test_sla_calculate():
    """ทดสอบ SLA calculation ผ่าน FastAPI"""
    url = f"{API_BASE}/sla/calculate"
    params = {
        "id": "10002898",
        "year": 2026,
    }

    print(f"🚀 Testing SLA calculation...")
    print(f"   URL: {url}")
    print(f"   Params: {params}")
    print("-" * 50)

    try:
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ สำเร็จ!")
            print(f"   Total tickets:   {data.get('total_tickets', 0)}")
            print(f"   Calculated:      {data.get('calculated_tickets', 0)}")
            print(f"   Skipped:         {data.get('skipped_tickets', 0)}")
            print(f"   SLA Met:         {data.get('sla_met_count', 0)}")
            print(f"   SLA Missed:      {data.get('sla_missed_count', 0)}")
            print()

            # แสดงผลแต่ละ ticket
            for r in data.get("results", [])[:5]:  # แสดง 5 รายการแรก
                status = "✅" if r.get("sla_met") else "❌"
                cache = "📦 Cache" if r.get("from_cache") else "🔄 Calculated"
                print(f"   {status} Ticket #{r['ticket_id']} | "
                      f"{r.get('working_minutes', '?')} min | "
                      f"{cache} | {r.get('req_user', '')}")

            if len(data.get("results", [])) > 5:
                print(f"   ... and {len(data['results']) - 5} more")
        else:
            print(f"❌ Error (Status {response.status_code}):")
            print(f"   {response.text}")

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("   (ตรวจสอบว่า FastAPI server รันอยู่ที่ http://localhost:8000)")


def test_sla_cache():
    """ทดสอบดึงข้อมูล SLA จาก Cache"""
    url = f"{API_BASE}/sla/cache"

    print(f"\n{'=' * 50}")
    print(f"🔍 Testing SLA cache query...")
    print(f"   URL: {url}")
    print("-" * 50)

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {len(data)} cached results")
            for r in data[:5]:
                status = "✅" if r.get("sla_met") else "❌"
                print(f"   {status} Ticket #{r['ticket_id']} | "
                      f"{r.get('working_minutes', '?')} min | "
                      f"{r.get('req_user', '')}")
        else:
            print(f"❌ Error: {response.text}")

    except Exception as e:
        print(f"❌ Connection Error: {e}")


if __name__ == "__main__":
    test_sla_calculate()
    test_sla_cache()
