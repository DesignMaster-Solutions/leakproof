"""LeakProof web app: upload exports, ask, watch the contained run, read the verified answer and receipt."""
import csv
import json
import re
import shutil
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file, send_from_directory

from leakproof import agent, checks, datagen, llm, sandbox, verify

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(sandbox.RUNS_DIR).parent
DATASETS = STATE / "datasets"
JOBS = STATE / "jobs"
MAX_FILE = 10 * 1024 * 1024
SAFE_NAME = re.compile(r"^[a-z0-9_]{1,40}\.csv$")
SLOTS = threading.Semaphore(2)  # two runs at a time on a 2 vCPU VM
RATE = {}  # ip -> [timestamps]; shortcut: in-memory, resets on restart; fine for one demo instance

app = Flask(__name__, static_folder=str(ROOT / "web"), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 6 * MAX_FILE


def demo_dir():
    d = DATASETS / "demo"
    if not (d / "answer_key.json").exists():
        datagen.generate(d)
    return d


def save_job(job):
    JOBS.mkdir(parents=True, exist_ok=True)
    tmp = JOBS / f"{job['id']}.tmp"
    tmp.write_text(json.dumps(job))
    tmp.replace(JOBS / f"{job['id']}.json")


def rate_ok(ip, limit=20, window=3600):
    now = time.time()
    RATE[ip] = [t for t in RATE.get(ip, []) if now - t < window] + [now]
    return len(RATE[ip]) <= limit


def preview(path, limit=200):
    with open(path, newline="", errors="replace") as f:
        rows = list(csv.reader(f))
    return {"header": rows[0] if rows else [], "rows": rows[1:limit + 1], "total": max(len(rows) - 1, 0)}


def work(job, data_dir, plant):
    def step(kind, label, **extra):
        job["steps"].append({"kind": kind, "label": label, "t": time.time()})
        job.update({k: v for k, v in extra.items()})
        save_job(job)

    try:
        with SLOTS:
            step("queue", "Got a sandbox slot")
            res = agent.ask(job["question"], data_dir, on_step=step)
            job.update(run_id=res["final_run"], attempts=res["attempts"], receipt=res["receipt"], ok=res["ok"],
                       stdout=res["stdout"])
            run_dir = sandbox.RUNS_DIR / res["final_run"]
            if res["ok"]:
                step("verify", "Verifying every sentence against the output")
                job["verification"] = verify.explain(job["question"], run_dir, plant=plant)
                job["table"] = preview(run_dir / "out" / "result.csv")
                if data_dir.name == "demo" and job.get("check"):
                    job["score"] = checks.score(job["check"], run_dir / "out" / "result.csv", data_dir / "answer_key.json")
            job["contained"] = any(a["blocked"] for a in res["attempts"])
            job["status"] = "done"
    except Exception as e:  # the UI shows the failure; nothing is retried silently
        job.update(status="error", error=f"{type(e).__name__}: {e}"[:500])
    save_job(job)


@app.get("/")
def index():
    return send_from_directory(ROOT / "web", "index.html")


@app.get("/api/config")
def config():
    d = demo_dir()
    return jsonify(questions=checks.QUESTIONS, models={k: llm.CONFIG[k] for k in ("planner", "coder", "verifier")},
                   limits=sandbox.LIMITS, demo_files=sorted(p.name for p in d.glob("*.csv")),
                   image_digest=sandbox.image_digest())


@app.post("/api/upload")
def upload():
    files = request.files.getlist("files")
    if not 1 <= len(files) <= 6:
        abort(400, "send 1 to 6 CSV files")
    ds = uuid.uuid4().hex[:12]
    d = DATASETS / ds
    d.mkdir(parents=True)
    names = []
    for f in files:
        name = Path(f.filename or "").name.lower().replace("-", "_").replace(" ", "_")
        if not SAFE_NAME.match(name):
            shutil.rmtree(d)
            abort(400, f"bad file name: {name!r} (letters, digits, _ and .csv)")
        f.save(d / name)
        if (d / name).stat().st_size > MAX_FILE:
            shutil.rmtree(d)
            abort(400, f"{name} is over 10 MB")
        names.append(name)
    return jsonify(dataset=ds, files=sorted(names))


@app.post("/api/ask")
def ask():
    body = request.get_json(force=True)
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
    if not rate_ok(ip):
        abort(429, "demo limit: 20 questions per hour")
    question = (body.get("question") or "").strip()[:1000]
    check = body.get("check") if body.get("check") in checks.QUESTIONS else None
    if check:
        question = checks.QUESTIONS[check]
    if not question:
        abort(400, "ask a question")
    ds = body.get("dataset") or "demo"
    if not re.fullmatch(r"demo|[0-9a-f]{12}", ds):
        abort(400, "bad dataset")
    data_dir = demo_dir() if ds == "demo" else DATASETS / ds
    if not data_dir.is_dir():
        abort(404, "dataset not found")
    job = {"id": uuid.uuid4().hex[:12], "question": question, "check": check, "dataset": ds,
           "status": "running", "steps": [], "created": time.time()}
    save_job(job)
    plant = "The total amount at risk is $987,654.32 across 412 invoices." if body.get("plant_wrong_total") else None
    threading.Thread(target=work, args=(job, data_dir, plant), daemon=True).start()
    return jsonify(job=job["id"])


@app.get("/api/jobs/<jid>")
def job(jid):
    if not re.fullmatch(r"[0-9a-f]{12}", jid) or not (JOBS / f"{jid}.json").exists():
        abort(404)
    return send_file(JOBS / f"{jid}.json", mimetype="application/json", max_age=0)


@app.get("/api/runs/<run_id>/<path:name>")
def run_file(run_id, name):
    if not re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{8}", run_id) or name not in (
            "receipt.json", "main.py", "stdout.txt", "out/result.csv", "out/summary.json"):
        abort(404)
    p = sandbox.RUNS_DIR / run_id / name
    if not p.exists():
        abort(404)
    # Served as plain text / attachment, never as HTML.
    return send_file(p, mimetype="text/plain; charset=utf-8", as_attachment=name.endswith(".csv"),
                     download_name=f"{run_id}-{Path(name).name}")


@app.after_request
def headers(resp):
    resp.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp
