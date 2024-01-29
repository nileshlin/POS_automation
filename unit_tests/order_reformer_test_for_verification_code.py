import pytest
import json
import sys
from order_reformer_function import batch_order

def test_lambda_handler():
    event = {
    "httpMethod":"POST",
    "body":"{\"verificationCode\":\"99f801e3-89ca-44e8-98c5-3ccbb74e4d82\"}"

 }
    assert batch_order.lambda_handler(event, None) == {'body': '"Thank you"', 'statusCode': 200}


