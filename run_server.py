"""Start the ChatWave server:  python run_server.py [--host H] [--port P] [--db FILE]"""
import argparse
import logging

from common import protocol
from server.server import ChatServer


def main() -> None:
    parser = argparse.ArgumentParser(description="ChatWave chat server")
    parser.add_argument("--host", default="0.0.0.0", help="interface to bind (default: all)")
    parser.add_argument("--port", type=int, default=protocol.DEFAULT_PORT)
    parser.add_argument("--db", default="chatwave.db", help="SQLite file for accounts/history")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    print("================================")
    print("💬 GROUP 2 CHAT SERVER")
    print("================================")
    print("Waiting for users... (Ctrl+C to stop)")

    server = ChatServer(args.host, args.port, args.db)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
