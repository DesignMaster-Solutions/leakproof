# Build plan, 3-8 November 2026

Times in UTC. Build window: 3 Nov 16:00 to 8 Nov 23:00 (lablab schedule). Each day ends with a check that a stranger could run.

| Day | Build | Done when |
|---|---|---|
| Mon 3 Nov (kickoff) | Apply the hackathon gift code on the Vultr account; create the VM (Ubuntu, Docker, gVisor); data generator with seed and `answer_key.json`; sandbox runner with all limits from [containment.md](containment.md) | Red-team tests pass on the VM: no network, no secrets, `killed_by` for fork bomb, memory balloon and loop, no leftover containers, runtime `runsc` |
| Tue 4 Nov | Planner, coder and retry loop on Vultr Serverless Inference; receipts | Checks 1-4 return the answer key on the seeded data from the command line, with receipts that re-run to the same output hashes |
| Wed 5 Nov | Check 5 with decoys; verifier model; web app (upload, ask, answer, table, receipt) | Check 5 reports 2 and none of the 3 decoys; a planted wrong total is cut by the verifier; app works over HTTPS on the public URL |
| Thu 6 Nov | Red-team panel in the app; approval buttons (export fix list, draft messages, both local only); CSV formula escaping; reset button | All four hostile scripts shown live with the limit that stopped each; exported CSV opens inert in a spreadsheet |
| Fri 7 Nov | README with real architecture and the measured numbers; slides (PDF); demo video with the containment moment | Video under 5 minutes; slides cover problem, solution, market, revenue, next steps (lablab presentation rubric, score 4-5) |
| Sat 8 Nov | Submit on lablab.ai before 23:00 UTC; optional post on Vultr Community | Submission page shows all required fields: repo, demo URL, video, slides, Vultr documentation |

## Required for the submission (event page, read 1 Nov 2026)

- Public GitHub repository with setup and documentation
- Vultr VM backend deployment
- Public demo URL
- Recorded demo video, with one containment moment shown
- Clear architecture and use-case explanation, including the Vultr services used, in this README
- Slides as PDF, cover image 16:9 (lablab defaults)

## Risks we already know

- The gift code arrives at kickoff. Until then no Vultr resources exist.
- gVisor on a small VM can be slow to start containers; if a run takes too long to start, keep gVisor and pre-warm one container per run slot, never fall back to the default runtime.
- Model ids on Serverless Inference can change; read `/v1/models` at kickoff and pin the ids in config.
