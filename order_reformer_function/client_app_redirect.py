import json
import boto3
import os
import requests
from util import Util
from logger import Logger


QUERY_PARAMETERS = "queryStringParameters"
MERCHANT_ID = "merchant_id"
CODE = "code"
LOG = Logger(__name__)
s3_bucket_name = os.getenv("S3_BUCKET")
stage = os.getenv("STAGE_NAME")


clover_environment_urls = {
    "dev": "https://sandbox.dev.clover.com",
    "prod": "https://www.clover.com/v3",
}

square_auth_referer = "https://squareup.com/"


def lambda_handler_function(event, context):

    LOG.debug(event)
    if "headers" not in event:
        LOG.info("No headers in event. Call is not likely from a client app. Returning")
        return
    headers = event.get("headers")
    LOG.debug(f"Headers: {headers}")
    referer = headers.get("Referer") if "Referer" in headers else ""
    LOG.debug(f"Referer: {referer}")
    # if referer == square_auth_referer:
    LOG.debug("Square client detected")
    code = event.get('queryStringParameters', {}).get('code')
    if code:
        Util.get_and_store_square_oauth_token(code)
        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps(
                {
                    "message": "Square auth token generated and stored successfully",
                    "description": "",
                }
            ),
        }
    else:
        return {
            "statusCode": 400
        }
    
    # LOG.debug("Assuming Clover client")
    # merchant_id = None
    # if MERCHANT_ID in event[QUERY_PARAMETERS] and event[QUERY_PARAMETERS][MERCHANT_ID]:
    #     merchant_id = event[QUERY_PARAMETERS][MERCHANT_ID]

    # code = None
    
    # if CODE in event[QUERY_PARAMETERS] and event[QUERY_PARAMETERS][CODE]:
    #     code = event[QUERY_PARAMETERS][CODE]

    # if not merchant_id or not code:
    #     return
    # base_url = clover_environment_urls[stage]
    # url = f"{base_url}/oauth/token?client_id=GZY9ZQ4AR258Y&client_secret=74b23b8a-5021-99d7-d9c6-3926da8153dc&code={code}"
    # headers = {
    #     "Authorization": f"Bearer 0121b373-466f-d4e5-6eac-f442607e624a"
    # }
    # response = requests.request("GET", url, headers=headers)
    # if response.status_code == 200:
    #     payload = json.loads(response.text)
    #     print(f"Auth token response: {payload}")
    #     auth_token = payload["access_token"]
    # else:
    #     return

    # error = save_merchant_code(merchant_id=merchant_id, auth_token=auth_token)
    # if error != "":
    #     return {
    #         "statusCode": 400,
    #         "headers": {"Access-Control-Allow-Origin": "*"},
    #         "body": json.dumps(
    #             {
    #                 "message": "Bad Request",
    #                 "description": error,
    #             }
    #         ),
    #     }
    
    # return {
    #     "statusCode": 200,
    # }

    
def save_merchant_code(merchant_id: str, auth_token: str) -> str:
    s3 = boto3.resource("s3")
    s3_object_name = f"{merchant_id}_api_auth_code.json"
    auth_code_dict = {"api_code": auth_token}
    try:
        s3.Object(s3_bucket_name, s3_object_name).put(Body=json.dumps(auth_code_dict))
        return ""
    except Exception as e:
        error = f"Error saving auth code for merchant_id: {merchant_id}: {e}"
        print(error)
        return error