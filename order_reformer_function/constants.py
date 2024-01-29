from enum import Enum
import os

environment_urls = {
    "dev": "dev.uknomi.com",
    "qa": "qa.uknomi.com",
    "prod": "api.uknomi.com",
}

environment_clover_urls = {
    "dev": "https://sandbox.dev.clover.com/v3/merchants",
    "qa": "https://sandbox.dev.clover.com/v3/merchants",
    "prod": "https://www.clover.com/v3/merchants",
}

square_headers = {
    "Square-Version": os.getenv("Square-Version"),
    "Content-Type": "application/json",
}

environment_square_urls = {
    "prod": "https://connect.squareup.com/oauth2/token",
    "dev": "https://connect.squareupsandbox.com/oauth2/token",
}

environment_square_app_urls = {
    "prod": "https://connect.squareup.com/v2",
    "dev": "https://connect.squareupsandbox.com/v2",
}

environment_square_app_ids = {
    "dev": "sandbox-sq0idb-Pq-5QRpU141Aw4Kx5JCq7w",
    "prod": "sq0idp-hlsXF4smg8EAV1qnqjM7xA"
}

environment_square_app_secrets = {
    "dev": "sandbox-sq0csb--g5-fH_naIGbr-AS_T7LOZzjpwC7V8TCni99Nezl7V0",
    "prod": "sq0csp-dUoQQ1dk48cX9gcdeXAraSmsAkmrsYfG8UlbeO2GBKM"
}


class OperationMode(Enum):
    LIVE = "live"
    SIMULATION = "simulation"

DEFAULT_ORDER_STATUS = "ordered"
VERSION_CONST = "$version$"