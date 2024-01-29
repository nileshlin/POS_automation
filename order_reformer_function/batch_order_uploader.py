import requests
import os
import json
from constants import environment_urls, OperationMode
from logger import Logger

stage = os.getenv("STAGE_NAME")
environment = environment_urls[stage]
LOG = Logger(__name__)
operation_mode = os.getenv("operation_mode")
if operation_mode is None:
    operation_mode = OperationMode.LIVE.value
LOG.info(f"Operation mode: {operation_mode}")

def lambda_handler(event, context):
    
    records = event['Records']
    for record in records:
        payload = json.loads(record['body'])

        order = json.loads(payload["order"])
        auth_header = payload["auth_header"]
        url = payload["url"]
        LOG.debug(f"Posting to: {url}")
        LOG.debug(order)
        if operation_mode == OperationMode.LIVE.value:
            x = requests.post(f"{url}?skip_matching=true", headers=auth_header, data=json.dumps(order))
            status_code = x.status_code
            LOG.debug(f"Order is type: {type(order)}")
            order_number = order["order_number"]
            batch_id = payload["batch_id"]
            LOG.info(f"{batch_id} - {status_code}: {order_number}")
            if status_code != 201:
                LOG.error(x)
                LOG.error(f"Error posting order to {environment}. Status code: {status_code}")
