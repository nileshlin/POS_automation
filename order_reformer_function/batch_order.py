import json
import time
import os
import boto3
import botocore
import requests
import uuid
from boto3 import client as boto3_client
from extractors.clover_order_extractor import CloverOrderExtractor
from extractors.quBeyond_order_extractor import QuBeyondOrderExtractor
from transformers.clover_transformer import CloverOrderTransformer
from transformers.quBeyond_order_transformer import QuBeyondOrderTransformer
from datetime import datetime
from logger import Logger
from constants import environment_urls, OperationMode, DEFAULT_ORDER_STATUS, VERSION_CONST
from util import Util

s3_bucket_name = os.getenv("S3_BUCKET")
stage = os.getenv("STAGE_NAME")
region = os.getenv("REGION")
environment = environment_urls[stage]
LOG = Logger(__name__)
sqs_resource = boto3.resource("sqs")
sqs_client = boto3.client("sqs", region_name=region)

operation_mode = os.getenv("operation_mode")
if operation_mode is None:
    operation_mode = OperationMode.LIVE.value
LOG.info(f"Operation mode: {operation_mode}")

def fetch_last_execution_time(extractor_config: dict, pos_cahnnel = None) -> int:
    s3 = boto3.resource('s3')
    if pos_cahnnel == "QuBeyond":
        merchant = extractor_config["user_name"]
        merchant_id = extractor_config["company_id"]
        location_id = extractor_config["location_id"]
        last_run_time = 0
        s3_object_name = f"{merchant_id}_{location_id}_last_runtime.json"
    else:
        #TODO: Refector the function to handle different pos_channel
        merchant = extractor_config["merchant_name"]
        merchant_id = extractor_config["merchant_id"]
        last_run_time = 0
        s3_object_name = f"{merchant_id}_last_runtime.json"
    try:
        obj = s3.Object(s3_bucket_name, s3_object_name)
        data = obj.get()['Body'].read().decode('utf-8')
        json_data = json.loads(data)
        last_run_time = json_data["last_execution_timestamp"]
    except botocore.exceptions.ClientError as e:
        if e.response['ResponseMetadata']['HTTPStatusCode'] == 404:
            LOG.info(f"Last execution time file not found for {merchant_id} ({merchant}). Creating...")
            # The object does not exist.
            now = time.time()
            last_run_time = int(now) - 86400 #Yesterday
            run_time_dict = {"last_execution_timestamp": last_run_time}
            s3.Object(s3_bucket_name, s3_object_name).put(Body=json.dumps(run_time_dict))
        else:
            LOG.error(f"S3 object access exception attempting to access: {s3_object_name} - {e.response['ResponseMetadata']['HTTPStatusCode']}")

    last_run_time_string = datetime.utcfromtimestamp(last_run_time).strftime('%Y-%m-%d %H:%M:%S')
    LOG.info(f"Last execution time for {merchant}: {last_run_time_string}")
    return last_run_time


def update_last_execution_time(extractor_config: dict, the_time: int,pos_channel = None):
    s3 = boto3.resource('s3')
    s3_object_name = None
    if pos_channel == "QuBeyond":
        merchant = extractor_config["user_name"]
        merchant_id = extractor_config["company_id"]
        location_id = extractor_config["location_id"]
        s3_object_name = f"{merchant_id}_{location_id}_last_runtime.json"
    else:
        #TODO: Refector the function to handle different pos_channel
        merchant = extractor_config["merchant_name"]
        merchant_id = extractor_config["merchant_id"]
        s3_object_name = f"{merchant_id}_last_runtime.json"

    run_time_dict = {"last_execution_timestamp": the_time}
    try:
        s3.Object(s3_bucket_name, s3_object_name).put(Body=json.dumps(run_time_dict))
    except Exception as e:
        LOG.error(f"Error updating last execution time for {merchant_id} ({merchant}): {e}")


def get_order_extraction_config(event: dict) -> list:

    if "Clover" not in event.keys():
        event["Clover"] = []

    if "QuBeyond" not in event.keys():
        event["QuBeyond"] = []

    clover_configs = event["Clover"]
    configs = {
        "Clover": [],
        "QuBeyond": []
    }

    for merchant_config in clover_configs:
        merchant_config["order_status"] =  DEFAULT_ORDER_STATUS
        last_execution_time = fetch_last_execution_time(merchant_config)
        LOG.debug(f"Last execution epoch: {last_execution_time}")
        merchant_config["last_queried_epoch"] = last_execution_time
        merchant_id = merchant_config["merchant_id"]
        auth_token = Util.get_clover_merchant_api_token(merchant_id=merchant_id, s3_bucket_name=s3_bucket_name)
        merchant_config["auth_token"]=auth_token
        merchant_config["batch_id"] = str(uuid.uuid4())
        configs["Clover"].append(merchant_config)

    qb_company_location_tz_cache = {}

    qb_configs = event["QuBeyond"]
    for company_config in qb_configs:
        auth_header = Util.get_qubeyond_auth_header(company_config)
        company_config["auth_header"] = auth_header

        company_id = company_config["company_id"]
        company_id_int = int(company_id)
        location_cache = None
        if company_id_int in qb_company_location_tz_cache.keys():
            location_cache = qb_company_location_tz_cache[company_id_int]
        else:
            location_cache = get_qb_location_tz_cache(company_config=company_config)
            qb_company_location_tz_cache[company_id_int] = location_cache
        
        LOG.debug(location_cache)

        ## get tz
        tz = "GMT"
        location_id_int = int(company_config["location_id"])
        if location_cache[location_id_int]:
            tz = location_cache[location_id_int]

        company_config["time_zone"] = tz
        company_config["batch_id"] = str(uuid.uuid4())
        company_config["order_status"] =  DEFAULT_ORDER_STATUS
        configs["QuBeyond"].append(company_config)
        if "start_time" in company_config.keys() and "end_time" in company_config.keys():
            last_execution_time = company_config["start_time"]
        else:
            last_execution_time = fetch_last_execution_time(company_config, pos_cahnnel = "QuBeyond")
        LOG.debug(f"Last execution epoch: {last_execution_time}")
        company_config["last_queried_epoch"] = last_execution_time
    return configs


def get_qb_location_tz_cache(company_config):
    base_version = company_config["base_version"]
    base_url = company_config["base_url"].replace(VERSION_CONST, base_version)
    url = f"{base_url}/locations"
    response = requests.get(url, headers=company_config["auth_header"])
    location_tz_map = {}
    if (response.status_code == 200):
        response_payload = response.json()
        if (response_payload["data"] and response_payload["data"]["location"]):
            for location in response_payload["data"]["location"]:
                location_tz_map[location["id"]] = location["time_zone"]
            
    return location_tz_map


def lambda_handler(event, context):

    LOG.info(event)

    extraction_configs = get_order_extraction_config(event)

    auth_token = Util.get_uknomi_auth_token(stage=stage)
    auth_header = {
        "Authorization": f"Bearer {auth_token}"
    }
    for config in extraction_configs["Clover"]:
        merchant_id = config["merchant_id"]
        
        extractor = CloverOrderExtractor(config)
        dont_skip_update_last_execution = True
        if "end_time" in config.keys():
            dont_skip_update_last_execution = False

        if operation_mode == OperationMode.LIVE.value and dont_skip_update_last_execution:
            LOG.info(f"Updating last execution time for merchant id: {merchant_id}")
            update_last_execution_time(config, int(time.time()))

        orders = extractor.get_latest_orders()
        LOG.debug(f"Number of orders found: {len(orders)}") 

        transformer = CloverOrderTransformer(config)
        LOG.debug(f"Orders before transform: {orders}")

        orders_to_send = transformer.get_transformed_orders(orders=orders)
        LOG.debug(f"Orders after transform: {orders_to_send}")

        sorted_orders = sorted(orders_to_send, key=lambda d: d['posted_date_time'])
        url = f"https://{environment}/pos_order/{merchant_id}"
        batch_id = config["batch_id"]

        LOG.info(f"{len(sorted_orders)} orders to be posted with batch_id={batch_id}")

        for order in sorted_orders:
            new_event = {
                "url": url,
                "environment": environment,
                "order": json.dumps(order),
                "batch_id": batch_id,
                "auth_header": auth_header
            }

            post_order_upload_message(json.dumps(new_event), batch_id=batch_id)

    for config in extraction_configs["QuBeyond"]:
        
        merchant_id = config["location_id"]
        extractor = QuBeyondOrderExtractor(config)
        dont_skip_update_last_execution = True
        if "end_time" in config.keys():
            dont_skip_update_last_execution = False

        if operation_mode == OperationMode.LIVE.value and dont_skip_update_last_execution:
            new_time = int(time.time())
            LOG.info(f"Updating last execution time for merchant id: {merchant_id} to {new_time}")
            update_last_execution_time(config, new_time, pos_channel="QuBeyond")

        orders = extractor.get_latest_orders()
        LOG.debug(f"Number of orders found: {len(orders)}")

        transformer = QuBeyondOrderTransformer(config=config)
        LOG.debug(f"Orders before transform: {orders}")

        orders_to_send = transformer.get_transformed_orders(order_list=orders)
        LOG.debug(f"Orders after transform: {orders_to_send}")

        sorted_orders = sorted(orders_to_send, key=lambda d: d['posted_date_time'])
        url = f"https://{environment}/pos_order/{merchant_id}"
        batch_id = config["batch_id"]

        LOG.info(f"{len(sorted_orders)} orders to be posted with batch_id={batch_id}")

        for order in sorted_orders:
            LOG.debug(f"Order: {order}")
            new_event = {
                "url": url,
                "environment": environment,
                "order": json.dumps(order),
                "batch_id": batch_id,
                "auth_header": auth_header
            }

            post_order_upload_message(json.dumps(new_event), batch_id)


def post_order_upload_message(event: str, batch_id: str):
    queue = sqs_resource.get_queue_by_name(QueueName='OrderUploadQueue.fifo')
    queue.send_message(MessageBody=event, MessageGroupId=batch_id)