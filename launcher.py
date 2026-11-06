"""Single-window launcher: starts the local API service and then the desktop UI."""
import socket
import threading
import time
import uvicorn
from backend import app
from desktop import main as desktop_main

HOST = "127.0.0.1"
PORT = 8000


def wait_for_api(timeout=25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, PORT), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def main():
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="error", access_log=False, log_config=None)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="MachaFinanceAPI", daemon=True)
    thread.start()
    if not wait_for_api():
        raise RuntimeError("The local finance service could not start on port 8000. Close any other copy and try again.")
    desktop_main()
    server.should_exit = True


if __name__ == "__main__":
    main()
