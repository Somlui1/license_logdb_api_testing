import base64
import requests


TENANTS = {
    "ah": {
        "Credential": "583db905e5af13cd_r_id:it@minAPI1WGant!",
        "APIKey": "FfSghSoNzPlloALCK9LN5E46rzGnAYqxJ+mgirtf",
        "Account": "WGC-3-981e96282dcc4ad0856c"
    },
    "as": {
        "Credential": "8f6543f42f463fc6_r_id:5QG+M=H+)3iL)Fw",
        "APIKey": "yujbaVOGmOi5rzxU2wBwcCJMLrkKyxU7Fbw8rQgj",
        "Account": "WGC-3-50b8aa46e31d448698c7"
    },
    "ar": {
        "Credential": "7be27fa3e7cc352a_r_id:^^K7Uc~7PYruSek",
        "APIKey": "66eMRiegSh7EhWQh6C9S5hAnQ75OScy6T9kx+VKo",
        "Account": "WGC-3-048294f7f1ed497981c8"
    }
}

def fetch_devices(tenant_name):
    t = TENANTS[tenant_name]
    try:
        cred_b64 = base64.b64encode(t["Credential"].encode()).decode()
        token_resp = requests.post(
            "https://api.jpn.cloud.watchguard.com/oauth/token",
            headers={
                "accept": "application/json",
                "Authorization": f"Basic {cred_b64}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={"grant_type": "client_credentials", "scope": "api-access"}
        )
        token_resp.raise_for_status()
        token = token_resp.json().get("access_token")
        if not token:
            raise Exception("Token is null")

        url = (
            f"https://api.jpn.cloud.watchguard.com/rest/endpoint-security/"
            f"management/api/v1/accounts/{t['Account']}/devices"
        )
        dev_resp = requests.get(
            url,
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
                "WatchGuard-API-Key": t["APIKey"],
                "Authorization": f"Bearer {token}"
            },
            timeout=120
        )
        dev_resp.raise_for_status()
        return dev_resp.json().get("data", []), None

    except Exception as e:
        return [], str(e)