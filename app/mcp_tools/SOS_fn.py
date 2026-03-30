import requests

def update_sos_job_status(
    req_no="77209",
    email="Viroj.s@aapico.com",
    it_emp_no="10002898",
    status="Closed",
    problem_type="19",
    problem_sub_item="82",
    cause="Request to add drive",
    solution="add drive"
):
    url = "http://intranet.aapico.com/SOS2014/save_update_status_job.php"
    
    # ตั้งค่า Headers
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9,th;q=0.8",
        "upgrade-insecure-requests": "1",
        "cookie": "PHPSESSID=5aqj7rrqaia0cksjookt7n6tf4",
        "Referer": f"http://intranet.aapico.com/SOS2014/edit_job.php?reqNo={req_no}"
    }

    # ตั้งค่า Body (ส่งแบบ data จะเป็น application/x-www-form-urlencoded อัตโนมัติ)
    payload = {
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
        # ยิง POST Request
        response = requests.post(url, headers=headers, data=payload)
        
        # ตรวจสอบว่า HTTP status code คือ 200 หรือไม่
        response.raise_for_status()
        
        print(f"\033[92mSuccessfully updated Job No: {req_no}\033[0m")
        return response.text
        
    except requests.exceptions.RequestException as e:
        print(f"\033[91mFailed to update job. Error: {e}\033[0m")
        return None

# --- วิธีใช้งาน ---
if __name__ == "__main__":
    # เรียกใช้แบบ Default
    update_sos_job_status()