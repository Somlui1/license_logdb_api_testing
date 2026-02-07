import requests
import random
import os

# Access the variables
user = os.getenv("SOSusername")
pw = os.getenv("SOSpassword")
class IntranetService:
    def __init__(self):
        self.login_url = "http://intranet.aapico.com/SOS2014/conIdap.php"
        self.ticket_url = "http://intranet.aapico.com/SOS2014/savenewticket.php"
        self.base_referrer = "http://intranet.aapico.com/SOS2014/index.php"

    def submit_ticket(self, username, password, sos_message, requestor_name, email, dept, tel, location, company, ips):
        """ 
        ฟังก์ชันหลักในการ Login และส่ง Ticket
        คืนค่า: Dict ผลลัพธ์ หรือ Raise Exception หากเกิดข้อผิดพลาด
        """
        session = requests.Session()
        
        # --- 1. LOGIN ---
        login_headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded",
            "x-requested-with": "XMLHttpRequest",
            "referrer": self.base_referrer
        }

        login_payload = {
            "user_name": username,
            "password": password,
            "cpn": "undefined",  # Assuming this is static or needs to be passed if dynamic
            "rand": str(random.random())
        }

        try:
            login_resp = session.post(self.login_url, headers=login_headers, data=login_payload)
            if login_resp.status_code != 200:
                raise Exception(f"Login failed (HTTP {login_resp.status_code})")
            
            # Check for failed login indicators in response text if known, e.g.:
            # if "Invalid username or password" in login_resp.text:
            #     raise Exception("Authentication failed")
            
        except Exception as e:
            raise Exception(f"Connection Error during Login: {str(e)}")

        # --- 2. SUBMIT TICKET ---
        ticket_headers = {
            "referrer": "http://intranet.aapico.com/SOS2014/main.php?p=request&lang=th",
            "upgrade-insecure-requests": "1"
        }

        # Format payload for multipart/form-data
        # Key: (filename, value) - filename is None for form fields
        ticket_payload = {
            "requestor": (None, requestor_name),
            "company": (None, company),
            "dept": (None, dept),
            "u_email": (None, email),
            "numrow2": (None, ""),
            "ips": (None, ips),
            "tel2request": (None, tel),
            "r_location": (None, location),
            "inform": (None, "1. IT Support"),  # Defaulting, or make parameter
            "g_itSupport": (None, "1. IT Support"),
            "iradio": (None, "Low"), # Defaulting
            "p_des": (None, sos_message)
        }

        try:
            ticket_resp = session.post(self.ticket_url, headers=ticket_headers, files=ticket_payload)
            
            if ticket_resp.status_code == 200:
                return {
                    "status": "success",
                    "message": "Ticket recorded successfully",
                    "intranet_response": ticket_resp.text[:100]
                }
            else:
                raise Exception(f"Failed to submit ticket (HTTP {ticket_resp.status_code})")
                
        except Exception as e:
            raise Exception(f"Error submitting ticket: {str(e)}")