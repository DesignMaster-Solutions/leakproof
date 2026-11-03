"""Re-run a receipt: same code, same inputs (checked by SHA-256), compare output hashes."""
import argparse
import json
import sys
from pathlib import Path

from leakproof import sandbox


def rerun(run_dir, data_dir):
    run_dir, data_dir = Path(run_dir), Path(data_dir)
    rec = json.loads((run_dir / "receipt.json").read_text())
    inputs = {}
    for i in rec["inputs"]:
        p = data_dir / i["name"]
        if sandbox.sha256_file(p) != i["sha256"]:
            raise SystemExit(f"input changed: {i['name']}")
        inputs[i["name"]] = str(p)
    new = sandbox.run((run_dir / "main.py").read_text(), inputs)
    same = {"code": new["code_sha256"] == rec["code_sha256"], "outputs": new["outputs"] == rec["outputs"],
            "stdout": new["stdout_sha256"] == rec["stdout_sha256"], "image": new["image_digest"] == rec["image_digest"]}
    return {"original": rec["run_id"], "rerun": new["run_id"], "same": same, "match": all(same.values())}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--data", default="data/demo")
    a = ap.parse_args()
    r = rerun(a.run_dir, a.data)
    print(json.dumps(r, indent=2))
    sys.exit(0 if r["match"] else 1)
