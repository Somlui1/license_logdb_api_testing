"""
Test script สำหรับ create_voucher_endpoint
รันตรงๆ ไม่ต้องผ่าน FastAPI server

Usage:
    python -m app.test.vocher_test
"""
import sys
import os

# เพิ่ม path ของ project root เพื่อให้ import ได้
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.service.vocher_wifi import create_voucher_endpoint

# ==========================================
# ตั้งค่า Test Parameters
# ==========================================
TEST_GROUP_NAME = "AH"              # ชื่อ Network Group
TEST_PROFILE_NAME = "AAPICO_Day"    # ชื่อ Profile
TEST_QUANTITY = 1                   # จำนวน Voucher

if __name__ == "__main__":
    print("=" * 50)
    print("🧪 Test: create_voucher_endpoint")
    print("=" * 50)
    print(f"  groupname    : {TEST_GROUP_NAME}")
    print(f"  profile_name : {TEST_PROFILE_NAME}")
    print(f"  quantity     : {TEST_QUANTITY}")
    print("-" * 50)

    try:
        result = create_voucher_endpoint(
            groupname=TEST_GROUP_NAME,
            profile_name=TEST_PROFILE_NAME,
            quantity=TEST_QUANTITY,
        )
        print("✅ สำเร็จ! ผลลัพธ์:")
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
