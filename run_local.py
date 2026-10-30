"""Local multi-user mode: one command starts the server and several phone windows.

    python run_local.py              # server + 2 clients side by side
    python run_local.py --clients 3
"""
import argparse
import logging
import os
import subprocess
import sys

from common import protocol
from server.server import ChatServer

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    parser = argparse.ArgumentParser(description="ChatGo local multi-user mode")
    parser.add_argument("--clients", type=int, default=2,
                    help="number of client windows to open")
    parser.add_argument("--db", default=os.path.join(HERE, "chatgo.db"))
    args = parser.parse_args()
    count = max(1, args.clients)

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    server = ChatServer("127.0.0.1", protocol.DEFAULT_PORT, args.db)
    started = False
    try:
        server.start_in_background()
        started = True
        print(f"Server started on 127.0.0.1:{protocol.DEFAULT_PORT}")
    except OSError:
        print("A server is already running on that port - using it.")

    clients = [subprocess.Popen([sys.executable, os.path.join(HERE, "run_client.py"),
                                 "--slot", str(i)], cwd=HERE) for i in range(count)]
    print(f"Opened {count} client window(s). Close them all to stop.")
    try:
        for proc in clients:
            proc.wait()
    except KeyboardInterrupt:
        for proc in clients:
            proc.terminate()
    finally:
        if started:
            server.stop()


if __name__ == "__main__":
    main()
