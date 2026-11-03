# Vultr resources and spend

Everything runs on the hackathon credit (US$ 200 gift code `VULTRAGENTRUSH26`, applied 3 Nov 2026 16:38 UTC). No card on the account.

| Resource | Id / name | Spec | Price (list) | Created (UTC) |
|---|---|---|---|---|
| Cloud Compute VM | `leakproof`, 173.199.127.232 | `vc2-2c-4gb` (2 vCPU, 4 GB), Ubuntu 24.04 LTS, New Jersey (`ewr`) | US$ 0.027/h, US$ 20/mo | 2026-11-03 16:43 |
| Firewall group | `leakproof` | inbound TCP 22, 80, 443 only (plus `ufw` on the VM with the same ports) | free | 2026-11-03 16:43 |
| Serverless Inference | subscription `leakproof` | `glm-5.3`, `deepseek-v4.1-flash-1017` | per token | 2026-11-03 |

The VM is provisioned by `infra/cloud-init.yaml` (Docker CE, gVisor `runsc` from the gVisor apt repo, `runsc install`, ufw).

## Balance log (GET /v2/account)

| When (UTC) | balance | pending_charges |
|---|---|---|
| 2026-11-03 16:40 | -200.00 (credit) | 0.00 |
| 2026-11-03 16:58 | -200.00 (credit) | 0.03 |
| 2026-11-03 17:11 | -200 0.03 (credit) |  |
| 2026-11-03 17:38 | -200 (credit) | 0.03 |
