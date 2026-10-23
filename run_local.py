"""Start the server and several clients. Example: python run_local.py 3"""
import subprocess
import sys
import time

clients_count = int(sys.argv[1]) if len(sys.argv) > 1 else 2

server = subprocess.Popen([sys.executable, "server.py"])
time.sleep(1)                                   # wait for the server

clients = [subprocess.Popen([sys.executable, "main.py", "--slot", str(i)])
           for i in range(clients_count)]
try:
    for client in clients:
        client.wait()                           # wait for the windows to close
except KeyboardInterrupt:
    pass
finally:
    for process in clients + [server]:
        process.terminate()
    print("ChatGo stopped.")
