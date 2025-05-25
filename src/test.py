from datetime import datetime


def test():
    """
    Test function to demonstrate functionality
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"Test function executed successfully at {current_time}"
