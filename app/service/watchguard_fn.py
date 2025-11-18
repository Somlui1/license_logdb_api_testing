import base64
import requests
import mysql.connector
from mysql.connector import Error
from urllib.parse import urlencode



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

def fetch_devices(tenant_name: str, segment: str, retrive: str, querystring: str):

    
    
    if tenant_name.lower() == 'all':
        for key in TENANTS.keys():
            tenant = TENANTS[key]
    
    elif not TENANTS.get(tenant_name):
        return [], f"Tenant '{tenant_name}' is missing required '{tenant_name}'"
    else:
         TENANTS_KEYS = [tenant_name]
    

    for key in TENANTS_KEYS:
        tenant = TENANTS[key]
        try:
            cred_b64 = base64.b64encode(tenant["Credential"].encode()).decode()
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
                f"https://api.jpn.cloud.watchguard.com/rest/{segment}/"
                f"management/api/v1/accounts/{tenant['Account']}/{retrive}?{querystring}"
            )
            dev_resp = requests.get(
                url,
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/json",
                    "WatchGuard-API-Key": tenant["APIKey"],
                    "Authorization": f"Bearer {token}"
                },
                timeout=120
            )
            dev_resp.raise_for_status()
            return dev_resp.json(), None

        except Exception as e:
            return [], str(e)




#test = {
#        "tenant_name": "ah",
#        "segment": "endpoint-security",
#        "retrive": "devices",
#        "querystring": urlencode({
#            "$top": 1,
#            "$count": "true"
#        })
#}
#
#
#result = fetch_devices(tenant_name = test["tenant_name"],segment =test["segment"], retrive = test["retrive"],querystring = test["querystring"])
#
#print(result)