import requests
import json
import jwt
import boto3
import botocore
from constants import environment_urls, square_headers, environment_square_urls, environment_square_app_ids, environment_square_app_secrets, VERSION_CONST
from logger import Logger
import os
from datetime import datetime

LOG = Logger(__name__)
stage = os.getenv("STAGE_NAME")

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

    def get_clover_merchant_api_token(merchant_id: str, s3_bucket_name: str) -> str:
        s3 = boto3.resource('s3')
        s3_object_name = f"{merchant_id}_api_auth_code.json"
        try:
            obj = s3.Object(s3_bucket_name, s3_object_name)
            data = obj.get()['Body'].read().decode('utf-8')
            json_data = json.loads(data)
            return json_data["api_code"]
        except botocore.exceptions.ClientError as e:
            LOG.error(e)
            return None
        

    def get_square_merchant_api_token(merchant_id: str) -> str:
        s3 = boto3.resource('s3')
        s3_object_name = f"square_{merchant_id}_api_token.json"
        LOG.info(f"s3_object_name: {s3_object_name}")
        try:
            obj = s3.Object(os.getenv("S3_BUCKET"), s3_object_name)
            data = obj.get()['Body'].read().decode('utf-8')
            LOG.info(data)
            json_data = json.loads(data)
            LOG.info(json_data)
            current_datetime = datetime.utcnow().isoformat() + "Z"
            LOG.info(current_datetime)
            expires_at = json_data["expires_at"]
            if current_datetime < expires_at:
                return json_data["access_token"]
            return Util.get_refreshed_square_token(json_data["refresh_token"])
        except botocore.exceptions.ClientError as e:
            LOG.error(e)
            return None


    def get_and_store_square_oauth_token(auth_code: str):
        data = {
            "client_id": environment_square_app_ids[stage],
            "client_secret": environment_square_app_secrets[stage],
            "code": auth_code,
            "grant_type": "authorization_code",
            "short_lived": True,
        }
        response = requests.post(environment_square_urls[stage], headers=square_headers, data=json.dumps(data))
        LOG.debug(f"Oauth response: {response}")
        LOG.debug(f"Status code: {response.status_code}")
        if response.status_code == 200:
            response_json = response.json()
            LOG.debug(f"Response json: {response_json}")
            merchant_id = response_json["merchant_id"]
            LOG.debug(f"merchant_id: {merchant_id}")
            s3_object_name = f"square_{merchant_id}_api_token.json"
            LOG.debug(f"S3 object name: {s3_object_name}")
            json_bytes = json.dumps(response_json).encode('utf-8')
            LOG.debug(f"json_bytes: {json_bytes}")
            Util.put_object_in_s3(s3_object_name, json_bytes)
        else:
            LOG.error(f"Error in generating square token: {response.status_code} {response.text}")


    @staticmethod
    def put_object_in_s3(key:str, body):
        s3 = boto3.resource('s3')
        LOG.debug(f"S3 resource: {s3}")
        try:
            s3.Object(os.getenv("S3_BUCKET"), key).put(Body=body)
        except Exception as e:
            LOG.error(f"Error saving square auth code: {e}")


    @staticmethod
    def get_refreshed_square_token(refresh_token):
        # Make a request to refresh the access token using the provided credentials
        data = {
            "client_id": environment_square_app_ids[stage],
            "grant_type": "refresh_token",
            "client_secret": environment_square_app_secrets[stage],
            "refresh_token": refresh_token,
            "short_lived": True,
        }
        response = requests.post(environment_square_urls[stage], headers=square_headers, json=data)
        if response.status_code == 200:
            r = response.json()
            new_access_token = r.get("access_token")
            merchant_id = r["merchant_id"]
            s3_object_name = f"square_{merchant_id}_api_token.json"
            json_bytes = json.dumps(response.json()).encode('utf-8')
            Util.put_object_in_s3(s3_object_name,json_bytes)
            return new_access_token
        else:
            LOG.error(f"Token refresh failed with status code {response.status_code}")
            return None