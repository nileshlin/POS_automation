import json
import requests
import os
import uuid
import boto3
import botocore
from extractors.quBeyond_menu_extractor import QuBeyondMenuExtractor
from transformers.quBeyond_menu_transformer import QuBeyondMenuTransformer
from logger import Logger
from util import Util
from constants import environment_urls, VERSION_CONST
from extractors.clover_menu_extractor import CloverMenuExtractor
from transformers.clover_menu_transformer import CloverMenuTransformer

stage = os.getenv("STAGE_NAME")
s3_bucket_name = os.getenv("S3_BUCKET")
environment = environment_urls[stage]
LOG = Logger(__name__)

def get_menu_extraction_config(event) -> list:

    if "Clover" not in event.keys():
        event["Clover"] = []

    if "QuBeyond" not in event.keys():
        event["QuBeyond"] = []

    configs = {
        "Clover": [],
        "QuBeyond": []
    }

    for company_config in event["QuBeyond"]:
        auth_header = Util.get_qubeyond_auth_header(company_config)
        company_config["auth_header"] = auth_header
        company_config["batch_id"] = str(uuid.uuid4())
        configs["QuBeyond"].append(company_config)

    for merchant_config in event["Clover"]:
        merchant_id = merchant_config["merchant_id"]
        auth_token = get_merchant_api_token(merchant_id=merchant_id)
        merchant_config["auth_token"]=auth_token
        configs["Clover"].append(merchant_config)

    return configs


def lambda_handler(event, context):
    
  LOG.debug(event)

  extraction_configs = get_menu_extraction_config(event)
  auth_token = Util.get_uknomi_auth_token(stage=stage)

  auth_header = {
      "Authorization": f"Bearer {auth_token}"
  }

  for config in extraction_configs["QuBeyond"]:
      extractor = QuBeyondMenuExtractor(config)
      transformer = QuBeyondMenuTransformer(config)
      menu = transformer.get_menus(extractor.get_items(), extractor.get_item_groups(), extractor.get_portions())
      LOG.debug(f"Menus from Qu Beyond Connector: {menu}")
      payload = json.dumps(menu)
      pos_account_id = config["location_id"]
      url = f'https://{environment}/pos_menu/{pos_account_id}'
      LOG.debug(f"Posting to URL: {url}")
      LOG.debug(payload)
      x = requests.post(url, headers=auth_header, data=payload)
      if x.status_code != 201:
          LOG.error(f"Error posting menus to {environment}. Response: {x}")
      else:
          LOG.info(f"{x.status_code}: {payload}")

  for merchant_config in extraction_configs["Clover"]:
      extractor = CloverMenuExtractor(merchant_config)
      transformer = CloverMenuTransformer(merchant_config)
      categories_and_items = extractor.get_categories_and_items()
      modifier_groups = extractor.get_modifier_groups()
      properties = extractor.get_properties()
      menu_name = merchant_config["menu_name"]
      menu = transformer.get_menus(menu_name, categories_and_items, modifier_groups, properties)
      LOG.debug(f"Menus from Clover Connector: {menu}")
      payload = json.dumps(menu)
      pos_account_id = merchant_config["merchant_id"]
      url = f'https://{environment}/pos_menu/{pos_account_id}'
      LOG.debug(f"Posting to URL: {url}")
      LOG.debug(payload)
      x = requests.post(url, headers=auth_header, data=payload)
      if x.status_code != 201:
          LOG.error(f"Error posting menus to {environment}. Response: {x}")
      else:
          LOG.info(f"{x.status_code}: {payload}") 

def get_merchant_api_token(merchant_id: str) -> str:
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