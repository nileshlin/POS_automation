from menu_reformer import batch_menu

def test_lambda_handler():
    event = {
        "httpMethod":"POST",
        "body":'{"TO_BE_EDITED": "EVENT_PARAMS"}' #TODO: EVENT SCHEMA NEED TO BE UPDATED
    }
    assert batch_menu.lambda_handler(event, None) == {'body': '"ok"', 'statusCode': 200} #TODO: RETURN BODY SHOULD BE CHANGED IN PRODUCTION ENVIORNMENT
