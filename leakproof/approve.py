"""Human-approved actions. Both stay local: a file to download, nothing sent anywhere."""
import csv
import io

DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


def inert(cell):
    """Spreadsheet formula injection: prefix a quote so Excel/Sheets treat the cell as text."""
    s = str(cell)
    return "'" + s if s.startswith(DANGEROUS) else s


def fix_list_csv(result_csv):
    with open(result_csv, newline="", errors="replace") as f:
        rows = list(csv.reader(f))
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    for r in rows:
        w.writerow([inert(c) for c in r])
    return out.getvalue()


def draft_messages(result_csv, question, limit=50):
    """Plain-text drafts, one per finding with an email. A person sends them, or not."""
    with open(result_csv, newline="", errors="replace") as f:
        rows = list(csv.DictReader(f))
    drafts = []
    for r in rows[:limit]:
        email = next((v for k, v in r.items() if "email" in k.lower() and "@" in str(v)), None)
        if not email:
            continue
        ref = ", ".join(f"{k}: {v}" for k, v in r.items() if any(t in k.lower() for t in ("invoice", "service", "charge", "due", "amount", "total")))
        drafts.append(f"To: {email}\nSubject: A note about your account\n\nHello,\n\nWhile reconciling our billing we found "
                      f"an item on your account that needs a correction on our side ({ref}). We will follow up with the "
                      f"details. No action is needed from you right now.\n\nThank you,\nBilling team\n")
    return {"count": len(drafts), "of": len(rows), "text": "\n-----\n\n".join(drafts)}
