import requests
import time
import logging

# Define the server URL for health checking
health_check_url = 'http://127.0.0.1:5000/health'

# Interval between checks (in seconds)
interval = 5
start_time = time.time()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server_health.log"),  # Log to a file
        logging.StreamHandler()  # Also output to console
    ]
)
logger = logging.getLogger(__name__)

def check_server_health():
    try:
        # Send a request to the health check endpoint
        response = requests.get(health_check_url)

        # Check if the server responded successfully
        if response.status_code == 200:
            logger.info(f"Server is responding correctly.")
            logger.debug(f"Response headers: {response.headers}")
            for line in response.iter_lines():
                logger.debug(f"Response line: {line.decode('utf-8')}")
        else:
            logger.warning(f"Server responded with status code: {response.status_code}")
    except requests.ConnectionError:
        logger.error("Server is down or cannot be reached.")
    except Exception as e:
        logger.error(f"An error occurred while checking server health: {e}")

if __name__ == "__main__":
    logger.info("Starting periodic health check...")

    # Infinite loop for checking the server health periodically
    while True:
        check_server_health()

        # Wait for the specified interval before the next check
        time.sleep(interval)
        uptime = time.time() - start_time
        logger.info(f"Tester Uptime: {uptime:.2f} seconds")