"""Draft an answer from the run output, then cut every sentence the output does not back.

Two gates, both must pass for a sentence to stay:
1. the verifier model (a different family from the coder) marks it backed, quoting evidence;
2. every number in the sentence appears in the raw output (deterministic, no model).
"""
import json
import re

from leakproof import llm

NUM = re.compile(r"(?<![\w.])\$?(\d{1,3}(?:,\d{3})+(?![\d])(?:\.\d+)?|\d+(?:\.\d+)?)")


def numbers(text):
    out = set()
    for m in NUM.findall(text):
        v = m.replace(",", "")
        out.add(v.rstrip("0").rstrip(".") if "." in v else v)
    return out


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9$])", text.strip()) if s.strip()]


def raw_output(run_dir):
    parts = []
    for name in ("summary.json", "result.csv"):
        p = run_dir / "out" / name
        if p.exists():
            parts.append(f"--- {name}\n" + p.read_text(errors="replace")[:20000])
    parts.append("--- stdout\n" + (run_dir / "stdout.txt").read_text(errors="replace")[:4000])
    return "\n".join(parts)


def draft(question, raw):
    r = llm.chat(llm.CONFIG["planner"], [
        {"role": "system", "content": "Write a short answer (2-5 sentences) for a finance person, using only facts in the run output. Give counts and totals exactly as they appear. Start with the finding itself (never a bare yes or no). No advice, no speculation."},
        {"role": "user", "content": f"Question: {question}\n\nRun output:\n{raw}"}], max_tokens=3000)
    return r["content"].strip()


def verify(sentences, raw):
    model = llm.CONFIG["verifier"]
    r = llm.chat(model, [
        {"role": "system", "content": "You check claims against raw program output. For each numbered sentence, decide if the output directly backs every fact and number in it. Reply with JSON only: [{\"n\": 1, \"backed\": true|false, \"evidence\": \"short quote from the output or why not\"}]"},
        {"role": "user", "content": "Raw output:\n" + raw + "\n\nSentences:\n" + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(sentences))}],
        max_tokens=4000)
    m = re.search(r"\[.*\]", r["content"], re.S)
    verdicts = {v["n"]: v for v in json.loads(m.group(0))} if m else {}
    raw_nums = numbers(raw)
    out = []
    for i, s in enumerate(sentences):
        v = verdicts.get(i + 1, {"backed": False, "evidence": "no verdict"})
        missing = sorted(numbers(s) - raw_nums)
        keep = bool(v.get("backed")) and not missing
        out.append({"sentence": s, "kept": keep, "model_backed": bool(v.get("backed")),
                    "numbers_not_in_output": missing, "evidence": str(v.get("evidence", ""))[:300]})
    return {"model": model, "sentences": out, "answer": " ".join(x["sentence"] for x in out if x["kept"])}


def explain(question, run_dir, plant=None):
    """plant: an extra sentence appended to the draft (used by tests and the demo to show a cut)."""
    raw = raw_output(run_dir)
    text = draft(question, raw)
    sents = split_sentences(text) + ([plant] if plant else [])
    return {"draft": text, **verify(sents, raw)}
