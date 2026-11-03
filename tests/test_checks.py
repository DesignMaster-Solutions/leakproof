import csv

from leakproof.checks import score

KEY = {"checks": {"5": [{"invoice": "in_A"}, {"invoice": "in_B"}]},
       "decoys": {"5": [{"invoices": ["in_C", "in_D"], "amount": 2900}]}}


def write(tmp_path, rows):
    p = tmp_path / "result.csv"
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return p


def test_one_row_per_charge_still_passes(tmp_path):
    p = write(tmp_path, [{"invoice_id": i, "charge": c} for i, c in [("in_A", 1), ("in_A", 2), ("in_B", 3), ("in_B", 4)]])
    assert score("5", p, KEY)["pass"]


def test_lowercased_ids_fail(tmp_path):
    assert not score("5", write(tmp_path, [{"invoice": "in_a"}, {"invoice": "in_b"}]), KEY)["pass"]


def test_reporting_a_decoy_fails(tmp_path):
    p = write(tmp_path, [{"invoice": i} for i in ["in_A", "in_B", "in_C"]])
    r = score("5", p, KEY)
    assert not r["pass"] and r["decoys_reported"] == ["in_C"]
