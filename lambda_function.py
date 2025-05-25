import sys
import os

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
        # Import and execute test.py
        import test  # This will execute the print('hello') statement

        return {'statusCode': 200, 'body': 'Hello Dave. Test function executed successfully - test.py has been imported and run'}
    except Exception as e:
        return {'statusCode': 500, 'body': f'Error executing test function: {str(e)}'}


# For local testing
if __name__ == "__main__":
    result = lambda_handler({}, {})
    print(f"Result: {result}")
