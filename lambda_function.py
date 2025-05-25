import sys
import os
from src import test

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def lambda_handler(event, context):
    """
    AWS Lambda handler function that executes test.py
    Args:
        event: AWS Lambda event data
        context: AWS Lambda context object

    Returns:
        dict: Response with statusCode and body
    """
    try:
        result = test.test()
        return {'statusCode': 200, 'body': f'Hello Dave. Output: {result}'}
    except Exception as e:
        return {'statusCode': 500, 'body': f'Error executing test function: {str(e)}'}


# For local testing
if __name__ == "__main__":
    result = lambda_handler({}, {})
    print(f"Result: {result}")
