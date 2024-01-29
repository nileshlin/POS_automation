import json
from logger import Logger
from jsonpath_ng import jsonpath, parse

LOG = Logger(__name__)

class CloverMenuTransformer:

    currency = "USD"

    def __init__(self, config: dict, **entries):
        self.__dict__.update(config)

    def get_menus(self, menu_name, categories_and_items, modifier_groups, merchant_properties):

        # Make all categories
        # Make all items
        #    - Create map of item to category
        #    - add item to category's items
        # Make items from modifiers
        #    - Make map of item to modifier group
        #    - use item-modifier_group map to fetch category via item
        #    - add modifier item to category's items
        
        # Default currency will be USD
        if merchant_properties is not None and "defaultCurrency" in merchant_properties.keys():
            self.currency = merchant_properties["defaultCurrency"]

        menu_categories = []
        item_category_map = {}
        menu_category_map = {}
        item_map = {}
        menu_to_upload = {
            "name": menu_name,
            "active": True,
            "menu_categories": menu_categories,
        }
        for menu_category in categories_and_items:
            LOG.debug(f"Menu Category: {menu_category}")
            menu_items = []
            t_menu_category = {
                "name": menu_category["name"],
                "description": menu_category["name"],
                "active": True,
                "menu_items": menu_items,
            }

            categorory_items = menu_category["items"]["elements"] if "elements" in menu_category["items"] else []
            for item in categorory_items:
                menu_item = self.get_menu_item(item)
                item_map[menu_item["client_id"]] = menu_item
                menu_items.append(menu_item)
                item_category_map[menu_item["client_id"]] = menu_category["id"]

            menu_category_map[menu_category["id"]] = t_menu_category
            menu_categories.append(t_menu_category)

        # Create category for modifiers
        modifier_category = {
            "name": "Modifiers",
            "description": f"{self.__dict__['merchant_name']} - Modifiers",
            "active": True,
            "menu_items": []
        }
        modifier_menu_items = modifier_category["menu_items"]
        menu_categories.append(modifier_category)
        # Create modifiers as items

        modifier_expression = parse('elements[*][modifiers][elements][*]')
        modifiers = [match.value for match in modifier_expression.find(modifier_groups)]
        modifier_menu_items = list(map(self.get_menu_item, modifiers))
        modifier_category["menu_items"] = modifier_menu_items

        for modifier_menu_item in modifier_menu_items:
            item_map[modifier_menu_item["client_id"]] = modifier_menu_item

        modifier_group_expr = parse('elements[*]')
        all_modifier_groups = [match.value for match in modifier_group_expr.find(modifier_groups)]

        LOG.debug(f"Item Map: {item_map}")

        for modifier_group in all_modifier_groups:
            if "modifiers" not in modifier_group.keys():
                continue
            modifiers_ = modifier_group["modifiers"]
            if "elements" not in modifiers_:
                continue
            modifiers = modifiers_["elements"]
            if "items" not in modifier_group.keys():
                continue
            items_ = modifier_group["items"]
            if "elements" not in items_.keys() or len(items_["elements"]) == 0:
                continue
            items = items_["elements"]
            for item in items:
                # find matching itme in menu...  must go through all categories and menu_items in each category... sigh
                matching_item = None
                for category in menu_to_upload["menu_categories"]:
                    for menu_item in category["menu_items"]:
                        if menu_item["client_id"] == item["id"]:
                            matching_item = menu_item

                if matching_item is None:
                    continue

                option_group = {
                    "title": modifier_group["name"],
                    "number_required_to_select": modifier_group["minRequired"] if "minRequired" in modifier_group.keys() else 0,
                    "options": []
                }
                matching_item["option_group"] = option_group
                options = option_group["options"]
                for modifier in modifiers:
                    options.append({
                        "option": modifier["name"],
                        "parent_menu_item": matching_item["name"]
                    })

        return menu_to_upload

    def get_menu_item(self, item :dict) -> dict:
        item_name = item["name"]
        LOG.debug(f"Creating item: {item_name}")
        item_id = item["id"]
        base_item = {
            "client_id": f"{item_id}",
            "name": item_name,
            "description": "Not Present",
            "active": True,
            "display_on_menu": not item["hidden"] if "hidden" in item else False,
            "item_price": []
        }
        price = {
            "currency": self.currency, #TODO get currency
            "price": item["price"]/100,
            "active": True
        }
        base_item["item_price"].append(price)
        LOG.debug(f"Transformed item: {base_item}")

        return base_item  # Returns the transformed item info to append in item list for the menu


class Item:
    def __init__(self, **entries):
        self.__dict__.update(entries)