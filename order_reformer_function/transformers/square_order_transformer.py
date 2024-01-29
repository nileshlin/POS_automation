from logger import Logger
from datetime import datetime
from extractors.sqaure_order_extractor import SquareOrderExtractor

LOG = Logger(__name__)

timestamp_format = "%Y-%m-%dT%H:%M:%S.%fZ"
class SquareOrderTransformer:

    def get_modifier_details(self, modifiers: list) -> list:
        modifier_details = []
        for modifier in modifiers:
            modifier_dict = {"client_order_line_id": modifier["uid"], "client_menu_item_id": modifier["catalog_object_id"],
                             "quantity": modifier["quantity"], "subtract": False}
            modifier_details.append(modifier_dict)
        return modifier_details


    def get_applied_discounts(self,discounts:list)-> list:
        '''

                   Discount should look like:
                   {
                       "discount_type": "uKnomi - $1",
                       "amount": -100,  // if amount
                       "percentage": 50,  // if percentage
                       "reference": asdf123  // discount id
                   }
                   '''
        applied_discounts = []
        for discount in discounts:
            Adiscount = {}
            if discount["type"] == "FIXED_PERCENTAGE":
                Adiscount["discount_type"] = discount["type"] #TODO: check type mapping
                Adiscount["percentage"] = discount["percentage"]
                Adiscount["amount"] = discount["applied_money"]["amount"]
                Adiscount["reference"] = discount["uid"]
            elif discount["type"] == "FIXED_AMOUNT":
                Adiscount["discount_type"] = discount["type"] #TODO: check type mapping
                Adiscount["amount"] = discount["applied_money"]["amount"]
                Adiscount["reference"] = discount["uid"]
            applied_discounts.append(Adiscount)
        return applied_discounts
    

    def get_transform_order(self, order:dict, square_client: SquareOrderExtractor, order_type="ORDER_CREATED") -> dict:
        '''Takes order schema from square pos channel and returns the transform order according to uknomi order schema
        fn Args:
            order: req (an order dict from square pos channel'''
        posted_date_time = None
        if "created_at" in order:
            posted_date_time = int(datetime.strptime(order["created_at"],timestamp_format).timestamp())
        order_id = order["id"]
        last_modified_date_time = int(datetime.strptime(order["updated_at"],timestamp_format).timestamp())
        device_id = None #TODO: Device id will be implemented later as there is no direct way found to access it
        total = order["total_money"]["amount"] / 100
        currency = order["total_money"]["currency"]
        operator = square_client.get_store_operator(order["location_id"])["employees"][0]["id"]
        discounts = self.get_applied_discounts(order["discounts"]) if order.get("discounts") else []
        payments = None
        data_to_send = {
            "currency": currency,
            "status": order_type,
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
        #Extract line items from the order
        # if "line_items" not in order:
        #     pass
        # else:
        #     order_lines = order["line_items"]
        #     order_item_list = []
        #     order_line_dict = {"order_lines": order_item_list}
        #     for order_line in order_lines:
        #         order_line_id = order_line["uid"]
        #         menu_item_id = ""
        #         try:
        #             menu_item_id = order_line["catalog_object_id"]
        #         except KeyError:
        #             LOG.debug(f"No item.id on Order/Order Line {order_id}/{order_line_id}")
        #         quantity = order_line["quantity"]
        #         menu_dict = {"client_order_line_id": order_line_id, "client_menu_item_id": menu_item_id,
        #                      "quantity": quantity, "subtract": False}
        #         order_line_has_modifications = "modifiers" in order_line.keys()
        #         if order_line_has_modifications is True:
        #             modifications = order_line["modifiers"]
        #             modifier_details = self.get_modifier_details(modifications)
        #             modifier_dict = {"order_lines": modifier_details}
        #             menu_dict.update(modifier_dict)
        #         order_item_list.append(menu_dict)
        #     data_to_send.update(order_line_dict)
        return data_to_send

