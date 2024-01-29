import json
import requests
from logger import Logger
from jsonpath_ng import jsonpath, parse

CREATE = "CREATE"
UPDATE = "UPDATE"
MERCHANTS = "merchants"

LOG = Logger(__name__)

class MenuItemExtractor:
    modifier_cache = {}
    transformer_config = None

    def __init__(self, **entries):
        self.__dict__.update(entries)
        LOG.debug(self.__dict__)

    def get_quantity(self):
        isUnitPrice = "unitQty" in self.__dict__.keys()
        quantity = int(self.unitQty / 1000) if isUnitPrice is True else 1
        return quantity

    def get_modifier_details(self, modifications):
        modifier_details = []
        modifiers = modifications["elements"]
        
        modifier_detail = None

        for item in modifiers:
            modID = item["modifier"]["id"]
            modAmount = item["amount"]
            mod_line_item_id = item["id"]
            
            if modID not in self.modifier_cache.keys():
                base_url = self.__dict__["transformer_config"]["url"]
                LOG.debug(f"Menu Item Extractor dictionary: {self.__dict__}")
                merchant_id = self.__dict__["transformer_config"]["merchant_id"]
                auth_token = self.__dict__["transformer_config"]["auth_token"]
                url = f"{base_url}/{merchant_id}/modifiers?filter=id%3D{modID}"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {auth_token}"
                }
                response = requests.request("GET", url, headers=headers)
                response_json = json.loads(response.text)
                if response.status_code != 200:
                    LOG.error(f"Error getting modifier details: {response.text}")
                    break
                modifier_detail = response_json["elements"][0]
                self.modifier_cache[modID] = modifier_detail
            else:
                modifier_detail = self.modifier_cache[modID]

            modPrice = modifier_detail["price"]
            try:
                mod_quantity = int(modAmount / modPrice)
            except ZeroDivisionError as e:
                mod_quantity = 1

            quantity = mod_quantity if mod_quantity != 0 else 1
            nesting_dict = {"client_order_line_id": mod_line_item_id, "client_menu_item_id": modID,
                        "quantity": quantity, "subtract": False}
            modifier_details.append(nesting_dict)

        return modifier_details

class CloverOrderTransformer:
    tender_cache = {}

    def __init__(self, config: dict):
        self.__dict__.update(config)
        LOG.debug(self.__dict__)

    def payment_type(self, tender_id):
        if tender_id not in self.tender_cache.keys():
            base_url = self.__dict__["url"]
            LOG.debug(f"Menu Item Extractor dictionary: {self.__dict__}")
            merchant_id = self.__dict__["merchant_id"]
            auth_token = self.__dict__["auth_token"]
            url = f"{base_url}/{merchant_id}/tenders/{tender_id}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }
            response = requests.request("GET", url, headers=headers)
            response_json = json.loads(response.text)
            if response.status_code != 200:
                LOG.error(f"Error getting tender details: {response}")
                return None

            tender_detail = response_json
            self.tender_cache[tender_id] = tender_detail
        else:
            tender_detail = self.tender_cache[tender_id]
        return tender_detail


    def _payment(self,payments:list) -> list:
        payment_list = []
        for payment in payments:
            tender_id = payment["tender"]["id"]
            payment_type_dict = self.payment_type(tender_id=tender_id)
            if payment_type_dict is None:
                continue

            payment_type = payment_type_dict["label"]
            temp_dict = {
                "payment_type": payment_type,
                "amount": payment["amount"] / 100,
                "payment_date_time": payment["createdTime"],
                "closed_date_time": payment["clientCreatedTime"]
            }
            payment_list.append(temp_dict)
        return payment_list

    def get_discounts(self, order) -> list:
        discount_list = []
        discounts_expression = parse('discounts[elements][*]')
        _discount_list = [match.value for match in discounts_expression.find(order)]
        LOG.info(f"Looking for discounts in order: {json.dumps(order)}")
        LOG.info(f"Discounts: {_discount_list}")
        for _discount in _discount_list:
            '''
            Discount should look like:
            {
                "discount_type": "uKnomi - $1",
                "amount": -100,  // if amount
                "percentage": 50,  // if percentage
                "reference": asdf123  // discount id
            }
            '''
            discount = {
                "discount_name": _discount["name"],
                "reference": _discount["id"]
            }
            if "amount" in _discount:
                discount["amount"] = _discount["amount"]
            if "percentage" in _discount:
                discount["percentage"] = _discount["percentage"]
            discount_list.append(discount)

        return discount_list

    def get_transformed_orders(self, orders: list) -> list:
        orders_to_send = []
        for order in orders:
            
            posted_date_time = None
            if "modifiedTime" in order:
                posted_date_time = int(order["modifiedTime"]/1000)
            elif "createdTime" in order:
                posted_date_time = int(order["createdTime"]/1000)

            order_id = order["id"]
            last_modified_date_time = int(order["modifiedTime"]/1000)
            if "device" not in order:
                continue
            device_id = order["device"]["id"]
            total = order["total"]/100
            currency = order["currency"]
            operator = order["employee"]["id"]
            payments = None
            if "payments" in order:
                payments = self._payment(order["payments"]["elements"])

            discounts = self.get_discounts(order)

            data_to_send = {
                "currency": currency,
                "status": self.__dict__["order_status"],
                "total": total,
                "order_number": order_id,
                "third_party_order_type": "Drive-Thru",
                "third_party_order_channel": "In Store",
                "posted_date_time": posted_date_time,
                "last_modified_date_time": last_modified_date_time,
                "device_id": device_id,
                "client_order_id": order_id,
                "created_by": operator,
                "discounts": discounts
            }

            if payments is not None:
                data_to_send["payment"] = payments

            if "lineItems" not in order:
                orders_to_send.append(data_to_send)
                continue

            order_lines = order["lineItems"]["elements"]
            order_item_list = []
            order_line_dict = {"order_lines": order_item_list}

            for order_line in order_lines:
                order_line_id = order_line["id"]
                try:
                    menu_item_id = order_line["item"]["id"]
                except KeyError:
                    LOG.debug(f"No item.id on Order/Order Line {order_id}/{order_line_id}")
                menu_item_extractor = MenuItemExtractor(**order_line)
                menu_item_extractor.transformer_config = {
                    "auth_token": self.__dict__["auth_token"],
                    "merchant_id": self.__dict__["merchant_id"],
                    "url": self.__dict__["url"],
                }
                quantity = menu_item_extractor.get_quantity()
                menu_dict = {"client_order_line_id": order_line_id, "client_menu_item_id": menu_item_id,
                    "quantity": quantity, "subtract": False}
                order_line_has_modifications = "modifications" in order_line.keys()
                if order_line_has_modifications is True:
                    modifications = order_line["modifications"]
                    modifier_details = menu_item_extractor.get_modifier_details(modifications)
                    modifier_dict = {"order_lines": modifier_details}
                    menu_dict.update(modifier_dict)

                order_item_list.append(menu_dict)

            data_to_send.update(order_line_dict)

            orders_to_send.append(data_to_send)
            
        return orders_to_send