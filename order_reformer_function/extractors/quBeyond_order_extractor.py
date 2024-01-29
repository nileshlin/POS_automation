import json
import requests
import time
import uuid
import pytz
from logger import Logger
from constants import VERSION_CONST
from datetime import datetime, timezone

LOG = Logger(__name__)

class MenuItemExtractor:
    def __init__(self, **entries):
        self.__dict__.update(entries)

    def order_line_maker(self, line_items: dict) -> dict:

        item_id = line_items["item_id"]
        quantity = line_items["quantity"]
        menu_dict = {"client_order_line_id": str(uuid.uuid4()), "client_menu_item_id": item_id,
                     "quantity": quantity, "subtract": False}
        if("child_item" in line_items.keys()):
            child_item_list = line_items["child_item"]
            order_item_list = []
            temp = {"order_lines": order_item_list}
            for item in child_item_list:
                order_item_list.append(self.order_line_maker(item))
            menu_dict.update(temp)
        return menu_dict


class QuBeyondOrderExtractor(MenuItemExtractor):
    def __init__(self, config: dict, **entries):
        self.__dict__.update(config)

    def get_transformed_orders(self, orders: list) -> list:
        checks_to_be_sent = []
        for order in orders:
            order_number = order["check_id"]
            posted_date_time = int(time.mktime(time.strptime(order["opened_at"], '%Y-%m-%dT%H:%M:%S')))
            last_modified_date_time = int(time.mktime(time.strptime(order["last_modified_at"], '%Y-%m-%dT%H:%M:%S')))
            data_to_send = {"order_number": order_number, "posted_date_time": posted_date_time,
                            "last_modified_date_time": last_modified_date_time, "currency": "USD"}
            # try:
            #     item_lists = order["item"]
            # except KeyError:
            #     item_lists = []
            # line_items = []
            # temp = {"order_lines": line_items}
            # for line_item in item_lists:
            #     line_items.append(self.order_line_maker(line_item))
            #data_to_send.update(temp)
            checks_to_be_sent.append(data_to_send)
        return checks_to_be_sent

    def get_latest_orders(self) -> list:
        base_url = self.__dict__["base_url"]
        base_version = self.__dict__["base_version"]
        url = base_url.replace(VERSION_CONST, base_version)
        company_id = self.__dict__["company_id"]
        location_id = self.__dict__["location_id"]

        tz = pytz.timezone(self.__dict__["time_zone"])
        dt = datetime.utcnow()
        offset_seconds = tz.utcoffset(dt).total_seconds()
        LOG.debug(f"Offset seconds: {offset_seconds}")

        _end_date = None
        _start_date = None
        delta_from_date = None
        delta_from_time = None

        if "end_time" in self.__dict__.keys():
            _end_date = self.__dict__["end_time"]
            _start_date = self.__dict__["start_time"]
        else:
            timestamp = self.__dict__["last_queried_epoch"]

            LOG.debug(f"Last queried timestamp: {timestamp}")
            timestamp = timestamp + offset_seconds

            LOG.debug(f"Last queried timestamp - adjusted: {timestamp}")
            last_queried = datetime.fromtimestamp(timestamp)

            LOG.debug(f"Last Queried: {last_queried}")

            delta_from_date = last_queried.strftime('%m%d%Y')
            delta_from_time = last_queried.strftime("%H%M")

            LOG.debug(f"Delta from date: {delta_from_date}")
            LOG.debug(f"Delta from time: {delta_from_time}")

        if _end_date is None:
            url = f"{url}/{company_id}/{location_id}?data_type=checks&delta_from_date={delta_from_date}&delta_from_time={delta_from_time}&include_abandoned=true"
        else:
            url = f"{url}/{company_id}/{location_id}?data_type=checks&start_date={_start_date}&end_date={_end_date}&include_abandoned=true"
        LOG.debug(f"url: {url}")
        headers = self.__dict__["auth_header"]
        response = requests.get(url, headers=headers)
        LOG.debug(f"Response: {response}")
        checks: list = json.loads(response.text)["data"]["check"]
        return checks