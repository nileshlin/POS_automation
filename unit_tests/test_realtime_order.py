from order_reformer_function.realtime_order import lambda_handler
from order_reformer_function.client_app_redirect import lambda_handler_function

def test_lambda_handler_square_webhook():
    event = {
        "httpMethod":"POST",
        'headers': {"User-Agent": "Square Connect v2"},
        "body":'''{
  "merchant_id": "MLZVCA443P4WK",
  "type": "order.created",
  "event_id": "335b326d-1a2c-33ad-ae83-b401d0baf6ea",
  "created_at": "2024-01-08T06:35:40Z",
  "data": {
    "type": "order_created",
    "id": "XWoy3fu5wdWrJwG4LfQrPUSjk7KZY",
    "object": {
      "order_created": {
        "created_at": "2024-01-08T06:35:38.850Z",
        "location_id": "LC7AFKRKEVPKN",
        "order_id": "XWoy3fu5wdWrJwG4LfQrPUSjk7KZY",
        "state": "OPEN",
        "version": 1
      }
    }
  }
}''' #TODO: EVENT SCHEMA NEED TO BE UPDATED
    }
    assert lambda_handler(event, None) == {'headers': {'Content-Type': 'application/json'}, 'statusCode': 200} #TODO: RETURN BODY SHOULD BE CHANGED IN PRODUCTION ENVIORNMENT


def test_lambda_handler_get_square_token():
    '''Get the code to generate sample access token in your s3 by replacing client_id using below url,
    Create developer account on square and setup redirect url to get the code
    example url:
    https://connect.squareup.com/oauth2/authorize?client_id=sq0idp-hlsXF4smg8EAV1qnqjM7xA&scope=ITEMS_READ+ITEMS_WRITE+ORDERS_READ+ORDERS_WRITE+EMPLOYEES_READ
&session=false'''
    event = {
        "httpMethod":"GET",
        'headers': {"User-Agent": "Square Connect v2",
                    "referer": "https://squareup.com/"},
        'queryStringParameters': {'code': 'sq0cgp-mMeITkwcur3opLcP-QCyDQ'}
        #TODO: EVENT SCHEMA NEED TO BE UPDATED
    }
    assert lambda_handler_function(event, None) == {'message': 'Square code generated', 'statusCode': 200} #TODO: RETURN BODY SHOULD BE CHANGED IN PRODUCTION ENVIORNMENT

