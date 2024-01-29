from logger import Logger

LOG = Logger(__name__)

class QuBeyondMenuTransformer:
    def __init__(self, config: dict, **entries):
        self.__dict__.update(config)

    def get_menus(self, items, item_groups, portions):
        menu_categories = []
        menus_to_upload = {
            "name": "Main Menu",
            "active": True,
            "menu_categories": menu_categories,
        }

        # iterate through items - if there are portions, generate an item per portion
        # generate menu_item_option_group for each item as well

        for menu_category in item_groups:
            LOG.debug(f"Menu Category: {menu_category}")
            menu_items = []
            t_menu_category = {
                "name": menu_category["name"],
                "description": menu_category["name"],
                "active": True,
                "menu_items": menu_items,
            }

            menu_item_ids = menu_category["items"]
            LOG.debug(f"Menu Item Ids: {menu_item_ids}")
            for menu_item_id in menu_item_ids:
                for item in items:
                    obj = Item(**item)
                    if obj.id == menu_item_id:
                        menu_items_to_add = self.get_menu_item(item, portions)
                        menu_items.extend(menu_items_to_add)
            menu_categories.append(t_menu_category)
        return menus_to_upload


    def get_menu_item(self, item :dict, portions: list) -> list:
        item_name = item["name"]
        LOG.debug(f"Creating item: {item_name}")
        base_item_price = {}
        items = []
        item_id = item["id"]
        base_item = {
            "client_id": f"{item_id}", 
            "name": item_name, 
            "description": "Not Present", 
            "active": True, 
            "display_on_menu": True, 
        }
        items.append(base_item)
        price :dict = item["price"] if "price" in item.keys() else {}
        if "portions" in item.keys():
            LOG.debug("Creating menu_item_option_groups")
            # create menu_item_option_group
            menu_item_options = []
            menu_item_option_group = {
                "title": f"{item_name} - Portions",
                "number_required_to_select": 1,
                "options": menu_item_options
            }
            base_item["option_group"] = menu_item_option_group

            for item_portion in item["portions"]:
                portion_id = item_portion["id"]
                matched_portion = None
                for portion in portions:
                    if portion["id"] == portion_id:
                        matched_portion = portion

                portion_name = matched_portion["name"]
                option_name = f"{item_name} ({portion_name})"
                option = {
                    "option": option_name,
                    "parent_menu_item": f"{item_name}",
                }
                menu_item_options.append(option)
                portion_price = {
                    "currency": "USD", 
                    "price": 0, 
                    "active": True, 
                }
                if "portions" in price.keys():
                    for item_portion in price["portions"]:
                        if portion_id == item_portion["id"]:
                            portion_price["price"] = item_portion["amount"]

                portion_item = {
                    "client_id": f"{item_id}-{portion_id}",
                    "name": option_name,
                    "description": "Not Present",
                    "active": True,
                    "display_on_menu": True,
                    "item_price": [],
                }
                portion_item["item_price"].append(portion_price)
                LOG.debug(f"Created portion item: {portion_item}")
                items.append(portion_item)

        else:
            base_item["item_price"] = []
            base_item_price = {
                "currency": "USD",
                "price": 0 if not price else price["base"],
                "active": True,
            }
            base_item["item_price"].append(base_item_price)

        LOG.debug(f"Items: {items}")

        return items  # Returns the transformed item info to append in item list for the menu


class Item:
    def __init__(self, **entries):
        self.__dict__.update(entries)