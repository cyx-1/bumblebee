import sys
import os
import importlib
from io import StringIO

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
    old_stdout = sys.stdout
    try:
        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        # Import and reload test.py to ensure fresh execution
        # Use importlib to avoid "unused import" warnings
        test_module = importlib.import_module('test')

        # If the module has a main function, call it; otherwise just importing executes the code
        if hasattr(test_module, 'main'):
            test_module.main()

        # Get captured output
        output = captured_output.getvalue()

        return {'statusCode': 200, 'body': f'Hello Dave. Test function executed successfully - test.py has been imported and run. Output: {output.strip()}'}
    except Exception as e:
        return {'statusCode': 500, 'body': f'Error executing test function: {str(e)}'}
    finally:
        # Always restore stdout
        sys.stdout = old_stdout


# For local testing
if __name__ == "__main__":
    result = lambda_handler({}, {})
    print(f"Result: {result}")
