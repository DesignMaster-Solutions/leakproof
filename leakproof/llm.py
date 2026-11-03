"""Vultr Serverless Inference (OpenAI-compatible). The key lives only in this process."""
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

CONFIG = json.loads((Path(__file__).resolve().parents[1] / "config" / "models.json").read_text())


def _key():
    k = os.environ.get("VULTR_INFERENCE_KEY")
    if not k:  # dev machine: read from the Clauditor vault
        k = subprocess.run(["cld", "vault", "get", "vultr-inference:leakproof"], capture_output=True, text=True).stdout.strip()
    if not k:
        raise RuntimeError("VULTR_INFERENCE_KEY is not set")
    return k


def chat(model, messages, max_tokens=4000, effort="low", retries=2):
    body = json.dumps({"model": model, "messages": messages, "max_tokens": max_tokens,
                       "reasoning_effort": effort, "temperature": 0}).encode()
    for attempt in range(retries + 1):
        req = urllib.request.Request(CONFIG["base_url"] + "/chat/completions", data=body, method="POST",
                                     headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"})
        try:
            t0 = time.monotonic()
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.load(r)
            msg = d["choices"][0]["message"]
            return {"content": msg.get("content") or "", "usage": d.get("usage", {}), "model": d.get("model", model),
                    "finish_reason": d["choices"][0].get("finish_reason"), "ms": int((time.monotonic() - t0) * 1000)}
        except (urllib.error.URLError, TimeoutError, KeyError) as e:
            if attempt == retries:
                raise RuntimeError(f"inference failed: {e}") from e
            time.sleep(2 * (attempt + 1))
