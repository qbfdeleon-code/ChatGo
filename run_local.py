"""Local multi-user mode: starts the server and several client windows on this computer.

    python run_local.py          (2 clients)
    python run_local.py 3        (3 clients)
"""
import subprocess
import sys
import time

clients_count = int(sys.argv[1]) if len(sys.argv) > 1 else 2

server = subprocess.Popen([sys.executable, "server.py"])
time.sleep(1)                                   # give the server a moment to start

clients = [subprocess.Popen([sys.executable, "main.py", "--slot", str(i)])
           for i in range(clients_count)]
try:
    for client in clients:
        client.wait()                           # wait until every window is closed
except KeyboardInterrupt:
    pass
finally:
    for process in clients + [server]:
        process.terminate()
    print("ChatGo stopped.")
