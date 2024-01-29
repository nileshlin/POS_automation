from order_reformer_function import batch_order


def test_lambda_handler():
    event = {
        "httpMethod":"POST",
        "QuBeyond": [],
        "Clover": [
        ],
        "body":'{"TO_BE_EDITED": "EVENT_PARAMS"}' #TODO: EVENT SCHEMA NEED TO BE UPDATED
    }
    assert batch_order.lambda_handler(event, None) == {'body': '"ok"', 'statusCode': 200} #TODO: RETURN BODY SHOULD BE CHANGED IN PRODUCTION ENVIORNMENT

