import requests
import json
import jwt
from constants import environment_urls
from constants import VERSION_CONST
from logger import Logger

LOG = Logger(__name__)

class Util:

    def get_uknomi_auth_token(stage: str) -> str:
        auth_payload = {
            "username": "plewis@uknomi.com",
            "password": "uKn0m!.2022",
        }
        environment = environment_urls[stage]
        auth_response = requests.post(f"https://{environment}/user/signin", data=json.dumps(auth_payload))
        auth_json = json.loads(auth_response.text)
        token = auth_json["AuthenticationResult"]["IdToken"]
        return token

    def fetch_last_execution_time(config: str, type: str): #type ('order', 'batch')
        return None
    
    def get_qubeyond_auth_header(config):
        auth_version = config["auth_version"]
        url = config["auth_url"].replace(VERSION_CONST, auth_version)
        user_name = config["user_name"]
        password = config["password"]
        company_id = config["company_id"]

        payload = json.dumps({
            "userName": user_name,
            "password": password,
            "companyId": company_id
        })

        headers = {
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code != 200:
            LOG.error(f"QuBeyond authentication failed with status code: {response.status_code}")
            return None
        
        try:
            access_token = json.loads(response.text)["token"]
            decoded = jwt.decode(access_token, options={"verify_signature": False})
            integration_header = decoded["qu.uid"]
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Integration": integration_header
            }
            return headers
        except Exception as e:
            LOG.error(f"Error constructing QuBeyond Auth Header for companyId: {company_id}: {e}")
            return None