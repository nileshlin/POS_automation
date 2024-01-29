import json
import requests
import os
from logger import Logger

s3_bucket_name = os.getenv("S3_BUCKET")
LOG = Logger(__name__)
CLOVER_ORDER_EXPAND_ITEMS = [
    'lineItems',
    'lineItems.modifications',
    'payments',
    'discounts'
]

def get_expand_items():
    return ",".join(CLOVER_ORDER_EXPAND_ITEMS)

class CloverOrderExtractor:
    def __init__(self, config: dict):
        self.__dict__.update(config)

    def get_latest_orders(self) -> list:
        timestamp = self.__dict__["last_queried_epoch"]
        end_timestamp = None
        if "end_time" in self.__dict__.keys():
            end_timestamp = self.__dict__["end_time"]
        start_timestamp = None
        if "start_time" in self.__dict__.keys():
            start_timestamp = self.__dict__["start_time"]
        has_more = True
        offset = 0
        orders = []
        limit = 1000
        base_url = self.__dict__["url"]
        merchant_id = self.__dict__["merchant_id"]
        http_method = self.__dict__["http_method"]
        auth_token = self.__dict__["auth_token"]
        headers = {
            "Authorization": f"Bearer {auth_token}"
        }
        expand_items = get_expand_items()
        while has_more:
            url = ""
            if end_timestamp is not None and start_timestamp is not None:
                url = f"{base_url}/{merchant_id}/orders?filter=createdTime>={start_timestamp * 1000}&filter=createdTime<{end_timestamp * 1000}&expand={expand_items}&limit={limit}&offset={offset}&orderBy=createdTime ASC"
            else:
                url = f"{base_url}/{merchant_id}/orders?filter=createdTime>={timestamp * 1000}&expand={expand_items}&limit={limit}&offset={offset}&orderBy=createdTime ASC"
            LOG.debug(f"{http_method}:{url}")
            new_orders = requests.request(http_method, url, headers=headers)
            orders_dict = json.loads(new_orders.text)
            LOG.debug(f"Orders payload response: {orders_dict}")
            orders_list = orders_dict["elements"]
            LOG.debug(f"Number of orders retrieved: {len(orders_list)}")
            LOG.debug(f"Orders: {orders_list}")
            if (len(orders_list) < 1000):
                has_more = False
            orders.extend(orders_list)
            offset = offset + 1000

        return orders
    

    def get_order(self, order_id: str) -> json:
        expand_items = get_expand_items()
        base_url = self.__dict__["url"]
        merchant_id = self.__dict__["merchant_id"]
        url = f"{base_url}/{merchant_id}/orders/{order_id}?expand={expand_items}"
        auth_token = self.__dict__["auth_token"]
        headers = {
            "Authorization": f"Bearer {auth_token}"
        }
        order_response = requests.request(method="GET", url=url, headers=headers)
        order_json = json.loads(order_response.text)
        return order_json
