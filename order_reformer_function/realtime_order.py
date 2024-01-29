import json
import os
import boto3
import botocore
import requests
from extractors.clover_order_extractor import CloverOrderExtractor
from transformers.clover_transformer import CloverOrderTransformer
from extractors.sqaure_order_extractor import SquareOrderExtractor
from transformers.square_order_transformer import SquareOrderTransformer
from logger import Logger
from constants import environment_urls
from constants import environment_clover_urls
from constants import DEFAULT_ORDER_STATUS
from util import Util

VERIFICATION_CODE = "verificationCode"
MERCHANTS = "merchants"
CREATE = "CREATE"
UPDATE = "UPDATE"
DELETE = "DELETE"
LOG = Logger(__name__)

stage = os.getenv("STAGE_NAME")
environment_url = environment_urls[stage]
s3_bucket_name = os.getenv("S3_BUCKET")
def lambda_handler(event, context):
    headers = event.get('headers', {})
    is_square_webhook = headers.get('User-Agent') == 'Square Connect v2' if 'User-Agent' in headers else False
    if is_square_webhook:
        return webhook_square2Uknomi(json.loads(event['body']))
    else: #TODO: Refactor the code to handle request from multiple connectors
        return webhook_clover2Uknomi(json.loads(event['body']))


def deduplicate_entries(entries: list) -> list:
    key_entry_map = {}
    for entry in entries:
        key_entry_map[entry["objectId"]] = entry
    
    return list(key_entry_map.values())

def get_merchant_api_token(merchant_id: str) -> str:
    s3 = boto3.resource('s3')
    s3_object_name = f"{merchant_id}_api_auth_code.json"
    try:
        obj = s3.Object(s3_bucket_name, s3_object_name)
        data = obj.get()['Body'].read().decode('utf-8')
        json_data = json.loads(data)
        return json_data["api_code"]
    except botocore.exceptions.ClientError as e:
        LOG.debug(f"Error occurred fetching API token: {e}")
        return None
    
def post_orders_to_uknomi(orders_to_send: list, merchant_id: str, type: str):

    LOG.debug(f"Attempting to {type} {len(orders_to_send)} order(s)")

    auth_token = Util.get_uknomi_auth_token(stage=stage)
    headers = {
        "Authorization": f"Bearer {auth_token}",
    }
    
    status_code = -1
    for order in orders_to_send:
        url = f"https://{environment_url}/pos_order/{merchant_id}?skip_matching=false"
        payload = json.dumps(order)
        x = None
        method = ""
        if type == CREATE:
            LOG.debug(f"Posting to: {url}")
            x = requests.post(url, headers=headers, data=payload)
            method = "post"
        if type == UPDATE:
            order_number = order["order_number"]
            url = f"{url}/{order_number}"
            LOG.debug(f"Putting to: {url}")
            x = requests.put(url, headers=headers, data=payload)
            method = "put"
        status_code = x.status_code
        LOG.debug(f"{status_code}: {payload}")
        LOG.debug(x)
        expected_code = 201 if type == CREATE else 200
        LOG.debug(f"Expected response code: {expected_code}")
        if status_code != expected_code:
            LOG.debug(f"Error {method}ing order to {environment_url}. Status code: {status_code}")
            if method == "put" and status_code == 404:
                LOG.debug(f"404 received. Attempting POST instead")
                url = f"{url}/pos_order/{merchant_id}"
                x = requests.post(url, headers=headers, data=payload)
                if x.status_code != 201:
                    LOG.debug(f"Error posting order to {environment_url}. Status code: {status_code}")


def webhook_square2Uknomi(payload:dict)-> dict:
    # payload = json.loads(event['body'])
    square_merchant_id = payload["merchant_id"]
    square_config = {
        "merchant_id": square_merchant_id,
        "access_token": Util.get_square_merchant_api_token(square_merchant_id),
    }
    LOG.info(f"square_config: {square_config}")
    square_client = SquareOrderExtractor(square_config)
    if payload["type"] == "order.created" or payload["type"] == "order.updated":
        order = square_client.get_order(payload["data"]["id"])
        transformer = SquareOrderTransformer()
        if payload["type"] == "order.created":
            order_to_create = transformer.get_transform_order(order["order"], square_client)
            LOG.debug(f"Transformed order to Create: {order_to_create}")
            orders = []
            orders.append(order_to_create)
            print(orders)
            post_orders_to_uknomi(orders, merchant_id=square_merchant_id, type=CREATE)
        if payload["type"] == "order.updated":
            order_to_update = transformer.get_transform_order(order["order"], square_client, order_type="ORDER_UPDATED")
            LOG.debug(f"Transformed order to Update: {order_to_update}")
            orders = []
            orders.append(order_to_update)
            post_orders_to_uknomi(orders, merchant_id=square_merchant_id, type=UPDATE)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
    }

def webhook_clover2Uknomi(payload:dict)->dict:
    # body = event["body"]
    # payload = json.loads(body)
    LOG.debug(f"Payload received from Clover: {payload}")
    if MERCHANTS in payload:
        merchants = payload[MERCHANTS]
        merchantIds = merchants.keys()

        for merchant_id in merchantIds:
            order_operation_map = {
                CREATE: [],
                UPDATE: [],
            }

            merchant_config = {
                "merchant_id": merchant_id,
                "url": environment_clover_urls[stage],
                "uknomi_url": environment_urls[stage],
                "http_method": "GET",
                "auth_mode": "Bearer",
            }
            auth_token = get_merchant_api_token(merchant_id=merchant_id)
            merchant_config["auth_token"] = auth_token
            merchant_entries = deduplicate_entries(merchants[merchant_id])
            for entry in merchant_entries:
                LOG.debug(f"entry: {entry}")
                entry_type = entry["type"]
                if entry_type == DELETE:
                    continue
                # Fetch client order based on client order number
                order_id = entry["objectId"].replace('O:', '')
                extractor = CloverOrderExtractor(merchant_config)
                order = extractor.get_order(order_id)
                pos_system_type = "Clover"
                LOG.debug(
                    f"Order extracted from pos_system_type/pos_account_id:order_id: {pos_system_type}/{merchant_id}:{order}")

                if (order != None):
                    list = order_operation_map[entry_type]
                    list.append(order)

            orders_to_create = []
            orders_to_update = []
            transformer_config = {
                "order_status": DEFAULT_ORDER_STATUS,
                "merchant_id": merchant_id,
                "auth_token": auth_token
            }

            transformer = CloverOrderTransformer(**transformer_config)
            if len(order_operation_map[CREATE]) != 0:
                orders_to_create = transformer.get_transformed_orders(orders=order_operation_map[CREATE])
                LOG.debug(f"Transformed orders to Create: {orders_to_create}")
                post_orders_to_uknomi(orders_to_send=orders_to_create, merchant_id=merchant_id, type=CREATE)

            if len(order_operation_map[UPDATE]) != 0:
                orders_to_update = transformer.get_transformed_orders(orders=order_operation_map[UPDATE])
                LOG.debug(f"Transformed orders to Update: {orders_to_update}")
                post_orders_to_uknomi(orders_to_update, merchant_id=merchant_id, type=UPDATE)

    if MERCHANTS not in payload:
        print(payload)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
        }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
    }
