"""Independent pandas solution of the five checks, read only from the CSVs.

Used as a test oracle: it must reproduce answer_key.json exactly. Never shown to the model.
"""
from pathlib import Path

import pandas as pd

MONTHS = {"Monthly": 1, "Quarterly": 3, "Annually": 12}


def load(d):
    d = Path(d)
    return {n: pd.read_csv(d / f"{n}.csv", dtype=str, keep_default_na=False) for n in
            ["gateway_invoices", "gateway_charges", "gateway_subscriptions", "billing_invoices", "billing_services"]}


def check1(t):
    gi, gs = t["gateway_invoices"], t["gateway_subscriptions"]
    canceled = set(gs.loc[gs.status == "canceled", "id"])
    return sorted(gi.loc[(gi.status == "open") & gi.subscription.isin(canceled), "id"])


def check2(t, as_of):
    bi, bs = t["billing_invoices"].copy(), t["billing_services"]
    bi["due"] = pd.to_datetime(bi.duedate, format="%d/%m/%Y")
    out = []
    for s in bs.itertuples():
        inv = bi[bi.serviceid == s.serviceid]
        if inv.empty:
            continue
        covered = set(inv.loc[inv.status != "Cancelled", "due"])
        d, nxt, step = inv.due.min(), pd.Timestamp(s.nextduedate), MONTHS[s.billingcycle]
        while d < nxt:
            if d not in covered:
                out.append((int(s.serviceid), d.date().isoformat()))
            d = d + pd.DateOffset(months=step)
    return sorted(out)


def check3(t):
    bi, bs = t["billing_invoices"], t["billing_services"]
    owing = set(bi.loc[bi.status == "Unpaid", "serviceid"])
    return sorted(int(x) for x in bs.loc[(bs.status == "Suspended") & ~bs.serviceid.isin(owing), "serviceid"])


def check4(t, as_of):
    bi, bs = t["billing_invoices"], t["billing_services"]
    live = set(bs.loc[bs.status != "Terminated", "serviceid"])
    due = pd.to_datetime(bi.duedate, format="%d/%m/%Y")
    m = (bi.status == "Unpaid") & (due < pd.Timestamp(as_of)) & ~bi.serviceid.isin(live)
    return sorted(int(x) for x in bi.loc[m, "invoiceid"])


def check5(t):
    c = t["gateway_charges"]
    ok = c[(c.status == "succeeded") & (c.refunded == "false")]
    n = ok.groupby("invoice").size()
    return sorted(n[n >= 2].index)
