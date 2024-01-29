import pytz
import uuid
from datetime import datetime
from datetime import timedelta
from logger import Logger


LOG = Logger(__name__)

CREATE = "CREATE"
UPDATE = "UPDATE"
class MenuItemExtractor:
    def __init__(self, **entries):
        self.__dict__.update(entries)

class QuBeyondOrderTransformer(MenuItemExtractor):
    def __init__(self, config: dict, **entries):
        super().__init__(**entries)
        self.__dict__.update(config)

    def get_payments(self, payments:list) -> list:
        payment_list = []
        for payment in payments:
            temp_dict = {
                "payment_type": payment["payment_type_id"],
                "amount": payment["received"],
                "payment_date_time": payment["payment_time"]
            }
            payment_list.append(temp_dict)
        return payment_list

    def get_order_line(self, order_line: dict) -> dict:

        item_id = order_line["item_id"]
        if "portion_id" in order_line.keys() and order_line["portion_id"] != -1:
            portion_id = order_line["portion_id"]
            item_id = f"{item_id}-{portion_id}"

        quantity = order_line["quantity"]
        menu_dict = {
            "client_order_line_id": str(uuid.uuid4()), 
            "client_menu_item_id": item_id,
            "quantity": quantity, 
            "subtract": False,
        }
        return menu_dict


    def get_transformed_orders(self, order_list: list) -> list:
        checks_to_be_sent = []

        tz = pytz.timezone(self.__dict__["time_zone"])
        dt = datetime.utcnow()
        offset_seconds = tz.utcoffset(dt).total_seconds()

        for order in order_list:
            order_number = order["check_id"]

            opened_at = datetime.fromisoformat(order["opened_at"]) - timedelta(seconds=offset_seconds)
            posted_date_time = int(opened_at.timestamp())

            last_modified_at = datetime.fromisoformat(order["last_modified_at"]) - timedelta(seconds=offset_seconds)
            last_modified_date_time = int(last_modified_at.timestamp())
            
            closed_at = datetime.fromisoformat(order["closed_at"]) - timedelta(seconds=offset_seconds)
            closed_date_time = int(closed_at.timestamp())

            terminal_id = None
            if "terminal_id" in order and order["terminal_id"]:
                terminal_id = order["terminal_id"]

            total = order["total"]
            order_type_id = order["order_type_id"]
            order_channel_id = order["order_channel_id"]

            data_to_send = {
                "order_number": order_number,
                "posted_date_time": posted_date_time,
                "last_modified_date_time": last_modified_date_time,
                "total": total,
                "currency": "USD",
                "device_id": terminal_id,
                "third_party_order_type": order_type_id,
                "third_party_order_channel": order_channel_id,
                "client_order_id": order_number,
                "status": self.__dict__["order_status"],
                "closed_date_time": closed_date_time
            }

            if "payment" in order:
                data_to_send["payment"] = self.get_payments(order["payment"])

            try:
                item_list = order["item"]
            except KeyError:
                item_list = []
            order_lines = []
            temp = {"order_lines": order_lines}
            for line_item in item_list:
                order_line = self.get_order_line(line_item)
                order_lines.append(order_line)
                if "child_item" in line_item.keys():
                    for child_item in line_item["child_item"]:
                        child_line = self.get_order_line(child_item)
                        order_lines.append(child_line)
                        child_line["parent_order_line_id"] = order_line["client_order_line_id"]
                
            data_to_send.update(temp)
            checks_to_be_sent.append(data_to_send)

        return checks_to_be_sent
