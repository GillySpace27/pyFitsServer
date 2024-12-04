import subprocess
import pytest
import time

@pytest.fixture(scope="session", autouse=True)
def start_server():
    """Start the pyfitsserver and ensure it's ready before tests."""
    server = subprocess.Popen(["pyfitsserver"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(5)  # Wait for the server to initialize (adjust as needed)

    yield  # Tests run after this

    # Shutdown server after tests
    server.terminate()
    server.wait()