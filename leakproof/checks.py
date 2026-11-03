"""The five demo questions and scoring of a result.csv against answer_key.json."""
import csv
import json
from pathlib import Path

QUESTIONS = {
    "1": "Which gateway invoices are still open (payable) for subscriptions that are already canceled in the gateway?",
    "2": "Is there a billing period nobody was invoiced for? For each billing service, every period from its first "
         "invoice due date up to (not including) its next due date, stepping by its billing cycle, should have at least "
         "one invoice that was not cancelled. List each missing period start with the service.",
    "3": "Which billing services are suspended while the customer has no unpaid invoice?",
    "4": "Which receivables are dead: unpaid billing invoices already past due whose service is terminated or missing?",
    "5": "Was any gateway invoice charged twice? Count only successful, non-refunded charges and match them by invoice id, "
         "never by amount or date.",
}

# The column of each answer-key row that identifies a finding.
KEY_FIELD = {"1": "invoice", "2": "serviceid", "3": "serviceid", "4": "invoiceid", "5": "invoice"}


def score(check, result_csv, answer_key):
    """Find the result column whose values best match the key ids. Returns found/missed/extra."""
    key = json.loads(Path(answer_key).read_text()) if not isinstance(answer_key, dict) else answer_key
    want = {str(r[KEY_FIELD[check]]) for r in key["checks"][check]}
    with open(result_csv, newline="") as f:
        rows = list(csv.DictReader(f))
    best = None
    for col in (rows[0].keys() if rows else []):
        got = {str(r[col]).strip().removesuffix(".0") for r in rows}
        hit = len(got & want)
        if best is None or hit > best[1]:
            best = (col, hit, got)
    got = best[2] if best else set()
    res = {"check": check, "column": best[0] if best else None, "expected": len(want), "rows": len(rows),
           "found": sorted(want & got), "missed": sorted(want - got), "extra": sorted(got - want)}
    if check == "2":  # the missing period must be the right one too
        dates = {v for r in rows for v in r.values()}
        res["missed"] += [r["missing_duedate"] for r in key["checks"]["2"]
                          if not any(r["missing_duedate"] in d or _ddmmyyyy(r["missing_duedate"]) in d for d in dates)]
    if check == "5":
        decoy_ids = {i for d in key["decoys"]["5"] for i in d["invoices"]}
        res["decoys_reported"] = sorted(decoy_ids & got)
    res["pass"] = not res["missed"] and not res["extra"] and not res.get("decoys_reported")
    return res


def _ddmmyyyy(iso):
    y, m, d = iso.split("-")
    return f"{d}/{m}/{y}"
