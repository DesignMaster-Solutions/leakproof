# Records network attempts for the receipt. This is a recorder, not the control:
# the control is --network none under gVisor. Audit hooks cannot be removed from Python.
import json
import sys


def _hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto", "socket.gethostbyname"):
        try:
            target = args[1] if event in ("socket.connect", "socket.sendto") else args[0]
            sys.__stderr__.write("LEAKPROOF_BLOCKED " + json.dumps({"event": event, "target": repr(target)[:200]}) + "\n")
        except Exception:
            pass


sys.addaudithook(_hook)
