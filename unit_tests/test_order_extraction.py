from ..order_reformer_function import app

def test_order_extraction():
    event = {
        "httpMethod":"POST",
        "body":'{"order_ids_list":["ok"]}'
    }
    assert batch_order.lambda_handler(event, None) == {'statusCode': 201}

