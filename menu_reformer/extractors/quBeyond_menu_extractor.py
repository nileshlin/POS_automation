import json
import requests
import jwt
from logger import Logger
from constants import VERSION_CONST

LOG = Logger(__name__)

class QuBeyondMenuExtractor:
    def __init__(self, config: dict, **entries):
        self.__dict__.update(config)

    def qu_api_url(self):
        '''Returns the quBeyond api url and auth headers to get the data from different apis for a location'''
        base_version = self.__dict__["base_version"]
        base_url = self.__dict__["base_url"].replace(VERSION_CONST, base_version)
        company_id = self.__dict__["company_id"]
        location_id = self.__dict__["location_id"]
        auth_header = self.__dict__["auth_header"]
        return f"{base_url}/{company_id}/{location_id}",auth_header

    def get_items(self, delta_from_date = None, delta_from_time = None) -> list:
        api_url,auth_header = self.qu_api_url()
        url = f"{api_url}?data_type=config&sub_data_type=item"
        items: list = (requests.request("GET", url, headers=auth_header).json())["data"]["item"]
        return items

    def get_item_groups(self,delta_from_date = None, delta_from_time = None) -> list:
        api_url, auth_header = self.qu_api_url()
        url = f"{api_url}?data_type=config&sub_data_type=item_group"
        response = requests.request("GET", url, headers=auth_header)
        response_json = response.json()
        item_group: list = response_json["data"]["item_group"]
        return item_group

    def get_portions(self) -> list:
        api_url, auth_header = self.qu_api_url()
        url = f"{api_url}?data_type=config&sub_data_type=portion"
        response = requests.request("GET", url, headers=auth_header)
        response_json = response.json()
        portions: list = response_json["data"]["portion"]
        return portions
