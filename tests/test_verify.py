import os

import pytest

from leakproof.verify import numbers, split_sentences


def test_numbers_normalized():
    assert numbers("27 invoices worth $1,234.50 and 3.0 more") == {"27", "1234.5", "3"}


def test_split_sentences():
    assert split_sentences("We found 27. Total is $1,234.50. Done!") == ["We found 27.", "Total is $1,234.50.", "Done!"]


@pytest.mark.skipif(not os.environ.get("VULTR_INFERENCE_KEY") or not os.path.isdir("/var/lib/leakproof/runs"),
                    reason="needs the inference key and a real run (on the VM)")
def test_planted_wrong_total_is_cut():
    from pathlib import Path

    from leakproof import verify
    runs = sorted(p for p in Path("/var/lib/leakproof/runs").iterdir() if (p / "out" / "summary.json").exists())
    run = runs[-1]
    planted = "The total amount at risk is $987,654.32 across 412 invoices."
    res = verify.explain("Summarize the findings.", run, plant=planted)
    cut = [s for s in res["sentences"] if s["sentence"] == planted][0]
    assert not cut["kept"]
    assert planted not in res["answer"]
    assert any(s["kept"] for s in res["sentences"])  # the honest sentences survive


def test_csv_fields_are_separate_numbers():
    assert {"8400", "1791491569"} <= numbers("in_9D,ch_g,8400,1791491569,ana@example.net,2")
