# Concept

Written 1 November 2026, before the build window. Nothing here is built yet.

## Who it is for

The person who closes the month at a small subscription business or service agency: usually an owner or an office manager, not an analyst. They can export CSVs from the payment gateway and from the billing system, and they already suspect the two do not agree. They do not write pandas and should not have to trust a chatbot's arithmetic.

## The five checks

Each check is a question the user can ask in plain words. The agent turns it into code; the checks below are the ones the demo must answer correctly on the seeded data (see [data.md](data.md)).

| # | Question | What the code has to find |
|---|---|---|
| 1 | Which gateway invoices are still payable for subscriptions that are already canceled? | `open` invoices whose subscription is `canceled` in the gateway or in billing |
| 2 | Is there a billing period nobody was invoiced for? | gaps between consecutive paid periods per service, after refunds and re-payments |
| 3 | Is any service suspended while the customer owes nothing? | `suspended` services with no `unpaid` invoice for the period that triggered suspension |
| 4 | Which receivables are dead? | `unpaid` invoices past due with no active service behind them |
| 5 | Was anything charged twice? | two successful charges against the same invoice id (same invoice, not "similar amount") |

Check 5 is deliberately strict: duplicates are matched by invoice or order id, never by amount and date. Matching by amount is how an agent produces false alarms, which is what happened to us (README, last row of the table).

## One question, end to end

1. User uploads `gateway_invoices.csv` and `billing_invoices.csv` and asks check 1.
2. Planner (Vultr Serverless Inference) returns a plan: load both files, normalize ids, join on subscription id, filter.
3. Coder writes the Python for the plan. The orchestrator writes it to a temp dir with the two inputs, read-only.
4. Sandbox run (see [containment.md](containment.md)). stdout, a result CSV and a JSON summary come back.
5. If the run failed, the error goes back to the coder; at most 3 attempts.
6. Explainer drafts the answer from the summary. Verifier (a model from a different family) gets the draft plus the raw output and must mark each sentence as backed or not. Unbacked sentences are removed.
7. UI shows the answer, the table, the receipt, and two buttons that need a human: "Export fix list" and "Draft customer messages". Nothing is sent anywhere by the agent.

## The receipt

```json
{
  "run_id": "...",
  "question": "...",
  "inputs": [{"name": "gateway_invoices.csv", "sha256": "..."}],
  "code_sha256": "...",
  "image_digest": "sha256:...",
  "runtime": "runsc",
  "limits": {"network": "none", "memory_mb": 512, "cpus": 1, "pids": 128, "wall_s": 30},
  "exit_code": 0,
  "killed_by": null,
  "blocked": [],
  "duration_ms": 0,
  "models": {"planner": "glm-5.3", "verifier": "deepseek-v4.1-flash"},
  "outputs": [{"name": "result.csv", "sha256": "..."}]
}
```

`blocked` lists what the sandbox stopped (for example a DNS lookup or a connection attempt). `killed_by` is `timeout`, `oom` or `pids` when a limit ended the run. The receipt plus the code plus the inputs are enough to re-run and get the same output hashes.

## Out of scope

- Writing to any gateway or billing system. The agent is read-only by design.
- Real customer data in the demo. All demo data is synthetic (see [data.md](data.md)).
- Pattern B (browser use). One pattern, done well.
- Accounts, teams, billing for LeakProof itself. One shared demo instance with a reset button.
