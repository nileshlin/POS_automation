from order_reformer_function import qu_beyond_batch_order


def test_lambda_handler():
    event = {
        "httpMethod":"POST",
        "body":'{"TO_BE_EDITED": "EVENT_PARAMS"}' #TODO: EVENT SCHEMA NEED TO BE UPDATED
    }
    assert qu_beyond_batch_order.lambda_handler(event, None) == {'body': '"ok"', 'statusCode': 200} #TODO: RETURN BODY SHOULD BE CHANGED IN PRODUCTION ENVIORNMENT

