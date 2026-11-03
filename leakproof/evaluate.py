"""Ask the preset questions end to end and score each answer against answer_key.json."""
import argparse
import json

from leakproof import agent, checks, rerun, sandbox

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("checks", nargs="*", default=["1", "2", "3", "4", "5"])
    ap.add_argument("--data", default="data/demo")
    a = ap.parse_args()
    for c in a.checks:
        res = agent.ask(checks.QUESTIONS[c], a.data)
        out = sandbox.RUNS_DIR / res["final_run"] / "out" / "result.csv"
        sc = checks.score(c, out, f"{a.data}/answer_key.json") if out.exists() else {"check": c, "pass": False, "error": "no result.csv"}
        sc.update(run=res["final_run"], attempts=len(res["attempts"]))
        sc["rerun_same_hashes"] = rerun.rerun(sandbox.RUNS_DIR / res["final_run"], a.data)["match"]
        for k in ("found", "extra", "missed"):
            if isinstance(sc.get(k), list) and len(sc[k]) > 6:
                sc[k] = sc[k][:6] + [f"... {len(sc[k])} total"]
        print(json.dumps(sc), flush=True)
