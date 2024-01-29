import json
import time
import os
import requests
from logger import Logger
from constants import environment_urls
from util import Util

stage = os.getenv("STAGE_NAME")
environment = environment_urls[stage]
LOG = Logger(__name__)


def lambda_handler(event, context):

    start_time = int(time.time()) - (60 * 60 * 25)
    end_time = int(time.time())

    auth_token = Util.get_uknomi_auth_token(stage=stage)
    auth_header = {
        "Authorization": f"Bearer {auth_token}"
    }

    body = {
        "start_time": start_time,
        "end_time": end_time
    }

    LOG.debug(f"Matching period: {body}")

    url = f"https://{environment}/match_customers_to_orders_for_date_range"

    LOG.debug(f"Posting to: {url}")
    x = requests.post(url=url, headers=auth_header, data=json.dumps(body))

    LOG.debug(x)