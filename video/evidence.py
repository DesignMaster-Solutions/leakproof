"""Condense the evidence files for the demo video: python3 evidence.py eval|redteam (reads docs/evidence, prints real lines)."""
import json, pathlib, re, sys

EV = pathlib.Path(__file__).resolve().parent.parent / "docs" / "evidence"

if sys.argv[1] == "eval":
    for line in (EV / "day2-eval-vm.txt").read_text().splitlines():
        if line.startswith("{"):
            j = json.loads(line)
            print(f"check {j['check']}: expected {j['expected']:>2}  missed {len(j['missed'])}  extra {len(j['extra'])}"
                  f"  decoys {len(j.get('decoys_reported', []))}  pass {j['pass']}  re-run same hashes {j['rerun_same_hashes']}")
else:
    for line in (EV / "day1-redteam-vm.txt").read_text().splitlines():
        if re.search(r"without|stopped|blocked|gvisor|passed in|leftovers", line):
            print(re.sub(r"tests/test_containment.py::|\s+\[\s*\d+%\]|^=+ | =+$", "", line))
