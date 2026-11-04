# lablab.ai submission: field by field

Source of every number: README.md ("Measured") and docs/evidence/. Rebuild slides and cover with
`uv run --no-project --with python-pptx python3 docs/submission/build_slides.py`.

## Project title

LeakProof

## Short description (255 characters max)

Finds revenue leaks in billing exports without letting the data leak: model-written pandas runs in a throwaway gVisor sandbox on Vultr (no network, no secrets, hard limits), a second model checks every sentence, and each answer has a re-runnable receipt.

## Long description

In one week of October 2026 we reconciled the billing of our own agency and products, payment gateways against our billing systems, with an AI agent reading the exports. We found four kinds of revenue leak (open invoices for canceled subscriptions, a billing period never invoiced, services suspended with nothing to pay, dead receivables) and one false alarm: the agent's first read was wrong. That false alarm is why LeakProof exists. A model that describes a reconciliation will sooner or later invent a number; a model that writes code produces numbers you can check, but then model-written code runs next to your customers' financial data.

LeakProof takes the second road and contains it. A finance person uploads the gateway and billing exports and asks in plain words. glm-5.3 on Vultr Serverless Inference plans the checks and writes pandas; the code runs in a throwaway Docker container under gVisor (runsc) on a Vultr Cloud Compute VM, with no network, no secrets, read-only inputs and CPU, memory, process and time caps, destroyed after every run. deepseek-v4.1-flash-1017, a different model family, checks every sentence of the answer against the run's output, and a deterministic gate cuts any number that is not in it. Each answer ships with a receipt (SHA-256 of inputs, code, image digest, limits and outputs) that re-runs to the same hashes. Exporting the fix list or drafting customer messages needs a person to approve; nothing touches a gateway.

The containment moment: a customer note in the demo export carries a prompt injection asking the agent to upload the file to an outside URL. If the model obeys, the call dies in a sandbox with no network and the answer is marked Contained. A red-team panel runs five hostile scripts on demand against the live deployment (network exfiltration, secret hunting, fork bomb, memory balloon, infinite loop) and shows the limit that stopped each.

Measured on the VM on 3 November 2026: red-team suite 21 of 21, twice, each control with a paired "control off" test; the five checks match the seeded answer key (27, 1, 4, 4 and 2 findings, 0 of 3 decoys); 5 of 5 receipts re-run to identical hashes; a planted "$987,654.32 across 412 invoices" sentence is cut by both verifier gates. Demo data is synthetic, generated from a seed with an answer key. Solo entry by Design Master Solutions LLC; built with AI coding agents, disclosed here.

## Technologies / tags

Vultr, Vultr Cloud Compute, Vultr Serverless Inference, GLM, DeepSeek, gVisor, Docker, Python, Flask, pandas, Caddy, AI agents, sandboxing, fintech

## Links and files

- Public GitHub repository: https://github.com/DesignMaster-Solutions/leakproof
- Demo application URL: https://leakproof.designmastersolutions.com
- Video presentation: https://youtu.be/Gg3qlGzH1pU (same mp4 uploaded to the lablab form)
- Slide presentation: docs/submission/slides.pdf (11 pages, 16:9)
- Cover image: docs/submission/cover.png (1920x1080, page 1 of the deck)
- Challenge: 01 · Blast Radius Zero, Pattern A (sandboxed code execution)
