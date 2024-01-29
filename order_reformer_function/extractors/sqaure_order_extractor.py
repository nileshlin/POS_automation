from square.client import Client
from logger import Logger
import os

stage = os.getenv("STAGE_NAME")

LOG = Logger(__name__)
class SquareOrderExtractor:
    def __init__(self, config:dict):
        self.__dict__.update(config)
        square_env = ""
        if stage == "dev":
            square_env = "sandbox"
        elif stage == "prod":
            square_env = "production"
        self.client = Client(
            access_token=config["access_token"],
            environment=square_env
        )


    def get_order(self, order_id: str) -> dict:
        result = self.client.orders.retrieve_order(
            order_id=order_id
        )
        if result.is_success():
            return result.body
        elif result.is_error():
            LOG.error(f"Error in getting order from square: {result.errors}")


    def get_store_operator(self, location_id:str):
        result = self.client.employees.list_employees(
            location_id=location_id
        )
        if result.is_success():
            return result.body
        elif result.is_error():
            LOG.error(f"Error in getting operator from square: {result.errors}")
