import csv

from leakproof.approve import draft_messages, fix_list_csv, inert


def test_formula_prefixes_are_neutralized():
    for bad in ["=HYPERLINK(\"http://evil.example\",\"x\")", "+1+1", "-2+3", "@SUM(A1)", "\tx"]:
        assert inert(bad).startswith("'")
    assert inert("<script>alert(1)</script>") == "<script>alert(1)</script>"  # text in a CSV; the UI renders it inert
    assert inert("in_ABC") == "in_ABC" and inert("12.50") == "12.50"


def test_exported_csv_is_inert(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text('invoice,email,note\nin_1,a@example.com,"=HYPERLINK(""http://evil.example"",""click"")"\n')
    rows = list(csv.reader(fix_list_csv(p).splitlines()))
    assert rows[1][2].startswith("'=HYPERLINK")


def test_drafts_only_for_rows_with_email(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text("invoice,customer_email,amount_due\nin_1,a@example.com,2900\nin_2,,100\n")
    d = draft_messages(p, "q")
    assert d["count"] == 1 and d["of"] == 2 and "To: a@example.com" in d["text"]
