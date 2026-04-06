import os
import json
import sys
from dotenv import load_dotenv

# 🔍 ค้นหาไฟล์ .env ในโฟลเดอร์ app/ (ตำแหน่งปัจจุบันที่ไฟล์นี้ตั้งอยู่)
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

# 🛠️ Fix Mapping: ในไฟล์ .env ของคุณมีขีดล่างนำหน้า (_AD_USER) 
# แต่ใน ad_server.py เรียกหา AD_USER (ไม่มีขีดล่าง)
if os.getenv("_AD_USER") and not os.getenv("AD_USER"):
    os.environ["AD_USER"] = os.getenv("_AD_USER")
if os.getenv("_AD_PASSWORD") and not os.getenv("AD_PASSWORD"):
    os.environ["AD_PASSWORD"] = os.getenv("_AD_PASSWORD")
if os.getenv("_AD_BASE_DN") and not os.getenv("AD_BASE_DN"):
    os.environ["AD_BASE_DN"] = os.getenv("_AD_BASE_DN")

# นำเข้าเครื่องมือจาก ad_server โดยตรง
# ใช้ sys.path เพื่อให้สามารถรันจาก root ของโปรเจกต์ได้
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from app.mcp_tools.ad_server import (
        list_ou_structure,
        count_objects,
        get_users,
        get_computers,
        get_groups,
        get_ous
    )
except ImportError as e:
    print(f"❌ Error importing ad_server: {e}")
    sys.exit(1)

def run_test():
    print("="*60)
    print("   AD MCP Server — Test Diagnostics (Fixed ENV)")
    print("="*60)
    
    # ตรวจสอบ Environment Variables เบื้องต้น (เพื่อให้มั่นใจว่าดึงมาได้จริง)
    print(f"🔍 AD_HOSTS: {os.getenv('AD_HOSTS')}")
    print(f"🔍 AD_USER:  {os.getenv('AD_USER')}")
    print(f"🔍 AD_BASE_DN: {os.getenv('AD_BASE_DN')}")
    print("-" * 60)

    try:
        # 1. ทดสอบดึงโครงสร้าง OU
        print("\n[1] Testing Tool: list_ou_structure()")
        ous_json = list_ou_structure()
        ous = json.loads(ous_json)
        print(f"✅ Success! Found {len(ous)} pre-defined OU keys.")
        print(f"   Sample keys: {list(ous.keys())[:5]}")

        # 2. ทดสอบนับจำนวน User
        print("\n[2] Testing Tool: count_objects(object_type='user')")
        u_count = count_objects(object_type="user", ou_key="all")
        print(f"✅ User Count (Total): {u_count}")

        # 3. ทดสอบดึงข้อมูล User (แบบ Identity preset)
        print("\n[3] Testing Tool: get_users(columns='identity', limit=3)")
        users_result = get_users(ou_key="all", columns="identity", limit=3)
        
        # คดีพิเศษ: ถ้า ad_server คืนค่ามาเป็น error message (string) ที่ไม่ใช่ json
        try:
            users = json.loads(users_result)
            print(f"✅ Retrieved {len(users)} users.")
            for idx, u in enumerate(users):
                print(f"   {idx+1}. {u.get('username')} | {u.get('display_name')} | {u.get('email')}")
        except json.JSONDecodeError:
            print(f"⚠️ Tool returned a raw message instead of JSON: {users_result}")

        # 4. ทดสอบ Filter (ดึงข้อมูล Computer)
        print("\n[4] Testing Tool: get_computers with where string (OS contains 'Windows')")
        comp_where = "operating_system_contains=Windows"
        comps_result = get_computers(ou_key="all", where=comp_where, limit=3)
        try:
            comps = json.loads(comps_result)
            print(f"✅ Found {len(comps)} matches for filter.")
            for idx, c in enumerate(comps):
                print(f"   - {c.get('name')} ({c.get('operating_system')})")
        except json.JSONDecodeError:
            print(f"⚠️ Tool returned a raw message: {comps_result}")

    except Exception as e:
        print(f"\n❌ Test Failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("   Test Finished")
    print("="*60)

if __name__ == "__main__":
    run_test()
