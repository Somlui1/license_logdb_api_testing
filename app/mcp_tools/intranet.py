import requests
import random
from .router_core import MCPRouter

router = MCPRouter("Intranet SOS")

@router.tool()
def update_sos_job_status(
    req_no: str = "77209",
    email: str = "Viroj.s@aapico.com",
    it_emp_no: str = "10002898",
    status: str = "Closed",
    problem_type: str = "19",
    problem_sub_item: str = "82",
    cause: str = "Request to add drive",
    solution: str = "add drive"
) -> str:
    """Update SOS job status via the Intranet system."""
    # 1. สร้าง Session เพื่อเก็บ Cookie อัตโนมัติ
    session = requests.Session()

    # ==================================================================================
    # 2. Login เพื่อเอา Cookie (PHPSESSID)
    # ==================================================================================
    login_url = "http://intranet.aapico.com/SOS2014/conIdap.php"
    login_payload = {
        "user_name": "wajeepradit.p", # ใช้ user ของคุณ
        "password": "A@123456",      # ใช้ password ของคุณ
        "cpn": "undefined",
        "rand": str(random.random())
    }
    login_headers = {
        "x-requested-with": "XMLHttpRequest",
        "referrer": "http://intranet.aapico.com/SOS2014/index.php"
    }

    try:
        login_res = session.post(login_url, data=login_payload, headers=login_headers)
        if login_res.status_code != 200:
            return "Login Failed"
        
        # ตอนนี้ session จะมี Cookie PHPSESSID เรียบร้อยแล้ว
        print("Login success, cookie obtained.")

    except Exception as e:
        return f"Login Error: {e}"

    # ==================================================================================
    # 3. Update Job Status โดยใช้ Session เดิม
    # ==================================================================================
    update_url = "http://intranet.aapico.com/SOS2014/save_update_status_job.php"
    
    update_headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9,th;q=0.8",
        "upgrade-insecure-requests": "1",
        "Referer": f"http://intranet.aapico.com/SOS2014/edit_job.php?reqNo={req_no}"
        # ไม่ต้องใส่ cookie เองแล้ว เพราะ session.post จะส่งไปให้ให้อัตโนมัติ
    }

    update_payload = {
        "REQ_NO": req_no,
        "REQ_EMAIL": email,
        "old_it": it_emp_no,
        "new_it": it_emp_no,
        "SET_STATUS": status,
        "SET_TIME": "2",
        "Function_Type": "0",
        "stc": "",
        "PROBLEM_TYPE": problem_type,
        "PROBLEM_SUB_ITEM": problem_sub_item,
        "p_cause": cause,
        "p_solution": solution,
        "I_level": "1",
        "button": "Update Job Status"
    }

    try:
        # ใช้ session.post แทน requests.post
        response = session.post(update_url, headers=update_headers, data=update_payload)
        response.raise_for_status()
        
        print(f"\033[92mSuccessfully updated Job No: {req_no}\033[0m")
        return f"Update Success: {response.status_code}"
        
    except Exception as e:
        print(f"\033[91mUpdate Failed: {e}\033[0m")
        return None

# ทดสอบใช้งาน
if __name__ == "__main__":
    update_sos_job_status(req_no="77209", status="Closed", solution="Fixed via script")