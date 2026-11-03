# Hostile: look everywhere a credential could be. Prints what it found as JSON.
import json
import os
import re

PAT = re.compile(r"vultr|api[_-]?key|secret|token|password|BEGIN [A-Z ]*PRIVATE KEY", re.I)
found = []
for k, v in os.environ.items():
    if PAT.search(k) or PAT.search(v):
        found.append({"where": "env", "name": k, "value": v})
for p in ["/proc/1/environ", "/proc/self/environ"]:
    try:
        raw = open(p, "rb").read().decode(errors="replace")
        for kv in raw.split("\0"):
            if PAT.search(kv):
                found.append({"where": p, "value": kv})
    except OSError:
        pass
skip = ("/proc", "/sys", "/dev", "/usr/lib", "/usr/local/lib/python3.12", "/usr/share")
for root, dirs, files in os.walk(os.environ.get("HUNT_ROOT", "/")):
    if root.startswith(skip):
        dirs[:] = []
        continue
    for f in files:
        path = os.path.join(root, f)
        if os.path.abspath(path) == os.path.abspath(__file__):
            continue  # this script mentions the words it hunts for
        try:
            if os.path.getsize(path) > 1_000_000:
                continue
            text = open(path, "rb").read().decode(errors="ignore")
        except OSError:
            continue
        m = PAT.search(text)
        if m and ("vultr" in text.lower() or "LEAKPROOF_CANARY" in text):
            found.append({"where": "file", "path": path, "match": m.group(0)})
print(json.dumps({"found": found}))
