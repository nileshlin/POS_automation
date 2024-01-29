import json
import requests
from logger import Logger
from constants import VERSION_CONST

LOG = Logger(__name__)

class CloverMenuExtractor:
    def __init__(self, config: dict, **entries):
        self.__dict__.update(config)

    def clover_api_url(self):
        '''Returns the clover api url and auth headers to get the data from different apis for a merchant'''
        base_version = self.__dict__["base_version"]
        base_url = self.__dict__["url"].replace(VERSION_CONST, base_version)
        merchant_id = self.__dict__["merchant_id"]
        auth_token = self.__dict__["auth_token"]
        headers = {
            "Authorization": f"Bearer {auth_token}"
        }
        return f"{base_url}/{merchant_id}",headers

    def get_categories_and_items(self) -> list:
        api_url,headers = self.clover_api_url()
        url = f"{api_url}/categories?expand=items"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            LOG.error(f"Response: {response}")
            return []
        categories_dict = json.loads(response.text)
        LOG.debug(f"Response: {categories_dict}")
        categories_list = categories_dict["elements"]
        LOG.debug(f"Number of category retrieved: {len(categories_list)}")
        LOG.debug(f"{categories_list}")
        return categories_list
    
    def get_modifier_groups(self) -> json:
        api_url,headers = self.clover_api_url()
        url = f"{api_url}/modifier_groups?expand=modifiers,items"
        LOG.debug(f"Fetching modifiers from url: {url}")
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            LOG.error(f"Response: {response}")
            return json.loads("{}")
        response_json = json.loads(response.text)
        return response_json
    
    def get_properties(self) -> json:
        api_url,headers = self.clover_api_url()
        url = f"{api_url}/properties"
        LOG.debug(f"Fetching properties from url: {url}")
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            LOG.error(f"Response: {response}")
            return json.loads("{}")
        response_json = json.loads(response.text)
        return response_json
        