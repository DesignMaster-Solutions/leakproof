Title: LeakProof: sandboxed revenue-leak agent on Vultr (Agent Rush demo)

LeakProof finds revenue leaks in billing exports without letting the data leak. Entry for the Vultr: Agent Rush hackathon (lablab.ai), Challenge 01 · Blast Radius Zero, Pattern A.

What this video shows, recorded on the live deployment on 4 November 2026:
- Check 1 asked live: glm-5.3 (Vultr Serverless Inference) plans and writes pandas, the code runs in a throwaway gVisor container with no network, deepseek-v4.1-flash-1017 checks every sentence. 27 of 27 found against the answer key; the verifier cut a drafted sentence that claimed 13 subscriptions when the output had 12.
- The receipt: SHA-256 of inputs, code, sandbox image and outputs, runtime runsc, network none, limits.
- The containment moment: a prompt injection in a customer note asks for an upload to an outside URL; the model refused, and the red-team panel runs five hostile scripts live (exfiltration, secret hunt, fork bomb, memory balloon, infinite loop): 5 of 5 contained, each with the limit that stopped it.
- Human approval before exporting the fix list or drafting customer messages.
- Measured results from the VM (evidence files in the repo).

Limits: demo data is synthetic, generated from a seed with an answer key; no real customer data. Solo build by Design Master Solutions LLC with AI coding agents.

Live demo: https://leakproof.designmastersolutions.com
Code (MIT): https://github.com/DesignMaster-Solutions/leakproof

Chapters
0:00 The problem, from our own books
0:38 Question, plan, code, contained run, verify, receipt
0:59 Live: check 1 on the deployed app
1:31 A receipt anyone can re-run
1:54 The containment moment: an injection in the data
2:24 Live: five hostile scripts, 5 of 5 contained
3:06 Human approval
3:22 Built on Vultr
3:42 Try it
