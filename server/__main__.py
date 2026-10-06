"""Run the server:  python -m server [--host 0.0.0.0] [--port 5555]"""
import argparse
import logging
from pathlib import Path

from common.protocol import DEFAULT_PORT
from server.chat_server import ChatServer


def main() -> None:
    parser = argparse.ArgumentParser(description="ChatWave local chat server")
    parser.add_argument("--host", default="0.0.0.0", help="interface to listen on (default: all)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="TCP port (default: 5555)")
    parser.add_argument("--data-dir", default=str(Path(__file__).parent / "data"),
                        help="where accounts and history are saved")
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug output")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
    print("================================")
    print("💬 CHATWAVE SERVER  (Group 2)")
    print("================================")
    print(f"Listening on port {args.port} - press Ctrl+C to stop.\n")

    server = ChatServer(args.host, args.port, args.data_dir)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
