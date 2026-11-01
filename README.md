# LeakProof

**Finds revenue leaks in your billing exports without letting your data leak.**

Entry for the [Vultr: Agent Rush Hackathon](https://lablab.ai/ai-hackathons/vultr-hackathon) (lablab.ai, online build 3-8 November 2026), challenge **01 · Blast Radius Zero**, Pattern A (sandboxed code execution).

> **Status, 1 November 2026: concept only.** This repository holds the concept, the containment model and the build plan, written before kickoff (step 5 of the lablab team checklist, "Create your concept"). No product code exists yet. All code will be written during the build window, 3-8 November 2026, and every commit is timestamped here.

## The problem, from our own books

In one week of October 2026 we reconciled the billing of our own agency and products, payment gateways against our billing systems, with an AI agent querying the exports and databases read-only. We found four kinds of leak and one false alarm, all real:

| Leak | What we found |
|---|---|
| Open invoices for subscriptions already canceled | 27 invoices (one product) and 4 (another) still payable in the gateway. Customers could pay twice. |
| A billing period never invoiced | A paid, refunded and re-paid invoice pushed the due date forward twice. One quarter was never billed. |
| Service suspended with nothing to pay | 4 services cut off after the period's invoice had been cancelled by hand. |
| Dead receivables | 4 unpaid invoices from 2021-2026 with no active service behind them. |
| **A false alarm** | Two domains flagged "renewed without invoice" had paid. The agent's first read was wrong. |

The last row is why this project exists. A model that *describes* a reconciliation will sooner or later invent a number, and a finance team cannot act on an invented number. A model that *writes code* that runs on the real exports produces numbers you can check, but now you are running model-written code next to your customers' financial data.

## The idea

LeakProof is a web app where a finance person uploads two exports (gateway and billing system), asks a question in plain words ("which invoices are still payable for canceled subscriptions?"), and gets back a reconciliation **with receipts**:

1. **Plan.** A model on Vultr Serverless Inference turns the question into a short plan of checks.
2. **Code.** The model writes Python (pandas) for each check.
3. **Contained run.** The code runs in a throwaway container on the Vultr VM: gVisor runtime, no network, no secrets, read-only inputs, CPU, memory, process and time caps, destroyed after every run.
4. **Verify.** A second model from a different family checks every claim in the answer against the run's actual output. Anything not backed by output is cut, not softened.
5. **Receipt.** Each answer ships with a receipt: SHA-256 of each input file, the exact code, stdout, outputs, model ids, container image digest, limits, exit code and duration. Anyone can re-run it and get the same numbers.
6. **Human approval.** Exporting the fix list or drafting customer messages only happens after a person approves. The agent never touches the gateway.

Errors from a run are fed back to the model for a bounded number of retries (Pattern A).

## The containment moment

Billing data is written by customers: names, addresses, notes. One cell in the demo export carries a prompt injection asking the agent to "upload this file for auditing" to an outside URL. If the model obeys and writes the upload code, the call dies in a sandbox with no network, the receipt records the blocked attempt, and the UI marks the answer **Contained**. The video shows this live, along with a red-team panel that runs four hostile scripts on every deploy (network exfiltration, secret hunting, fork bomb, infinite loop) and shows which limit stopped each one. Details in [docs/containment.md](docs/containment.md).

## Vultr architecture (planned)

| Piece | Vultr service | Role |
|---|---|---|
| Control plane | Vultr Cloud Compute VM | Web app, orchestrator, job queue, receipts |
| Planner and coder | Vultr Serverless Inference (`glm-5.3`) | Plan of checks and Python per check |
| Verifier | Vultr Serverless Inference (`deepseek-v4.1-flash`) | Claim-by-claim check against run output |
| Sandbox | Docker with gVisor (`runsc`) on the same VM | Isolated execution, one container per run |

The API key for Serverless Inference lives only in the orchestrator. The sandbox never sees it. Model ids come from the public list at `https://api.vultrinference.com/v1/models` (read 1 Nov 2026) and will be confirmed at kickoff.

## Plan and docs

- [docs/concept.md](docs/concept.md): users, the five checks, what a receipt contains, what is out of scope.
- [docs/containment.md](docs/containment.md): threats, controls and the test that proves each control.
- [docs/data.md](docs/data.md): the synthetic exports (shaped like real gateway and billing exports, no real customer data) and the seeded leaks.
- [docs/build-plan.md](docs/build-plan.md): day-by-day plan for 3-8 November with a done check for each day.

## Team

Solo: Alan De Bortolo, Design Master Solutions LLC (United States). Built with AI coding agents, disclosed in the submission.

## License

MIT. See [LICENSE](LICENSE).
