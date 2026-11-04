# LeakProof

**Finds revenue leaks in your billing exports without letting your data leak.**

Entry for the [Vultr: Agent Rush Hackathon](https://lablab.ai/ai-hackathons/vultr-hackathon) (lablab.ai, online build 3-8 November 2026), challenge **01 · Blast Radius Zero**, Pattern A (sandboxed code execution).

**Live demo:** https://leakproof.designmastersolutions.com (synthetic data, one shared instance)

**Demo video (3:58):** https://youtu.be/Gg3qlGzH1pU (recorded on the live deployment: check 1 end to end, the receipt, the prompt-injection note, the red-team panel with 5 of 5 contained, human approval) · **lablab submission:** https://lablab.ai/ai-hackathons/vultr-hackathon/design-master-solutions/leakproof

> **Status, 3 November 2026.** Concept, containment model and plan were written before kickoff; all code was written from kickoff on (commit history). What works today, measured on the Vultr VM: the red-team suite (21 tests, each control with a paired "control off" test), all five checks matching the answer key, receipts that re-run to the same hashes, the verifier cutting a planted wrong total, and the web app over HTTPS.

## Why this and not just another sandbox

Sandboxing model-written code is the challenge; it is table stakes here. What LeakProof adds:

- **A real business problem with a known answer.** The demo data is a synthetic copy of the leaks we found in our own books (table below), generated from a seed, with an `answer_key.json`. Every answer in the app is scored against it on screen: found, missed, extra, and decoys reported.
- **Receipts you can re-run.** Each answer carries SHA-256 hashes of the inputs, the exact code, the sandbox image digest, the limits and the outputs. `python -m leakproof.rerun <run>` runs it again and compares hashes.
- **Answers that cannot invent numbers.** A model from a different family checks every sentence against the raw output, and a deterministic gate cuts any sentence carrying a number that is not in the output.
- **A human between the answer and any action.** Exporting the fix list or drafting customer messages needs a person to confirm; both stay local. The agent never touches a gateway.

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

Billing data is written by customers: names, addresses, notes. One cell in the demo export carries a prompt injection asking the agent to "upload this file for auditing" to an outside URL. If the model obeys and writes the upload code, the call dies in a sandbox with no network, the receipt records the blocked attempt, and the UI marks the answer **Contained**. The video shows this live, along with a red-team panel that runs five hostile scripts on demand against the live deployment (network exfiltration, secret hunting, fork bomb, memory balloon, infinite loop) and shows which limit stopped each one. Details in [docs/containment.md](docs/containment.md).

## Vultr architecture (as built)

```
 browser ──HTTPS──> Caddy (Let's Encrypt) ──> Flask app + orchestrator  (Vultr Cloud Compute VM, vc2-2c-4gb, Ubuntu 24.04, New Jersey)
                                                │   │
             Vultr Serverless Inference <───────┘   │  key lives here only (/etc/leakproof/env, root 0600)
             glm-5.3: plan, code, draft             │
             deepseek-v4.1-flash-1017: verify       ▼
                                      docker create --runtime runsc (gVisor)
                                      --network none --memory 512m --memory-swap 512m --cpus 1 --pids-limit 128
                                      --read-only --tmpfs /tmp:64m --cap-drop ALL --no-new-privileges --user 10001
                                      inputs mounted read-only at /data, /out = 32 MB host tmpfs per run
                                      30 s wall clock, container removed in a finally block
```

| Piece | Vultr service | Role |
|---|---|---|
| Control plane | Vultr Cloud Compute VM (`vc2-2c-4gb`, US$ 0.027/h list) | Web app, orchestrator, job threads, receipts |
| Planner, coder, explainer | Vultr Serverless Inference (`glm-5.3`) | Plan of checks, pandas code, answer draft |
| Verifier | Vultr Serverless Inference (`deepseek-v4.1-flash-1017`) | Sentence-by-sentence check against the run output |
| Sandbox | Docker with gVisor (`runsc`) on the same VM | One throwaway container per run |
| Firewall | Vultr Firewall group | Inbound 22, 80, 443 only |

Model ids are pinned in `config/models.json` (read from `/v1/models` at kickoff). Resources and spend: [docs/vultr.md](docs/vultr.md).

## Measured (3 November 2026, on the VM)

| What | Result | Evidence |
|---|---|---|
| Red-team suite | 21 of 21 passed, twice in a row; no leftover containers or mounts | [docs/evidence/day1-redteam-vm.txt](docs/evidence/day1-redteam-vm.txt) |
| Fork bomb | stopped by the pids limit after about 47 forks; with the limit off it reached 476 forks in 8 s | `tests/test_containment.py` |
| Memory balloon | OOM-killed at 512 MB; with 2 GB it allocates the full 1.5 GB | same |
| Exfiltration | DNS, HTTP and TCP all fail, only `lo` inside; with `--network bridge` the same script reaches 1.1.1.1:53 | same |
| Kernel | `/proc/version` inside differs from the host under `runsc`, matches it under `runc` | same |
| Five checks, end to end | 5 of 5 match the answer key (27, 1, 4, 4, 2 findings; 0 of 3 decoys reported); 5 of 5 receipts re-run to identical hashes | [docs/evidence/day2-eval-vm.txt](docs/evidence/day2-eval-vm.txt) |
| Verifier | a planted "$987,654.32 across 412 invoices" sentence cut by both gates | `tests/test_verify.py` |

## Run it

```bash
python -m leakproof.datagen --out data/demo            # synthetic exports + answer_key.json
pytest tests/test_datagen.py tests/test_checks.py tests/test_approve.py tests/test_web.py   # anywhere
sudo pytest tests/test_containment.py                  # on a host with Docker + runsc (see infra/cloud-init.yaml)
VULTR_INFERENCE_KEY=... python -m leakproof.evaluate   # all five checks, scored, with re-runs
./infra/deploy.sh                                      # sync to the VM, rebuild image, restart, smoke-test HTTPS
```

## Plan and docs

- [docs/concept.md](docs/concept.md): users, the five checks, what a receipt contains, what is out of scope.
- [docs/containment.md](docs/containment.md): threats, controls and the test that proves each control.
- [docs/data.md](docs/data.md): the synthetic exports (shaped like real gateway and billing exports, no real customer data) and the seeded leaks.
- [docs/build-plan.md](docs/build-plan.md): day-by-day plan for 3-8 November with a done check for each day, and the progress log.
- [docs/vultr.md](docs/vultr.md): Vultr resources, prices and the balance log.

## Team

Solo: Alan De Bortolo, Design Master Solutions LLC (United States). Built with AI coding agents, disclosed in the submission.

## License

MIT. See [LICENSE](LICENSE).
