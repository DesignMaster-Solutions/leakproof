"""Run untrusted Python in a throwaway gVisor container and return a receipt.

Every limit from docs/containment.md is set here, in one place (LIMITS). The container
is removed in a finally block, including on timeout.
"""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path

IMAGE = os.environ.get("LEAKPROOF_IMAGE", "leakproof-sandbox")
LIMITS = {"runtime": "runsc", "network": "none", "memory_mb": 512, "cpus": 1, "pids": 128, "wall_s": 30,
          "tmpfs_mb": 64, "out_mb": 32, "stdout_kb": 256}
RUNS_DIR = Path(os.environ.get("LEAKPROOF_RUNS", "/var/lib/leakproof/runs"))


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    return sha256_bytes(Path(p).read_bytes())


def _docker(*args, timeout=30, check=False):
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout, check=check)


def _read_capped(stream, cap, sink):
    """Keep the first `cap` bytes, drain and drop the rest so the child never blocks."""
    kept, dropped = bytearray(), 0
    for chunk in iter(lambda: stream.read(65536), b""):
        room = cap - len(kept)
        kept += chunk[:max(room, 0)]
        dropped += max(len(chunk) - max(room, 0), 0)
    sink["data"], sink["dropped"] = bytes(kept), dropped


def _watch_cgroup(cid, watch):
    """Poll the container's host cgroup; it disappears when the container exits."""
    path = Path(f"/sys/fs/cgroup/system.slice/docker-{cid}.scope/pids.events")
    while not watch["stop"]:
        try:
            for line in path.read_text().splitlines():
                k, v = line.split()
                if k == "max":
                    watch["pids_max"] = max(watch["pids_max"], int(v))
        except OSError:
            pass
        time.sleep(0.05)


def image_digest(image=IMAGE):
    return _docker("image", "inspect", image, "--format", "{{.Id}}", check=True).stdout.strip()


def run(code, inputs, limits=None, image=IMAGE):
    """inputs: {name: path}. Returns the receipt dict; outputs are copied under RUNS_DIR/<run_id>/out."""
    lim = {**LIMITS, **(limits or {})}
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
    name = f"lp-{run_id}"
    work = Path(tempfile.mkdtemp(prefix="lp-"))
    (work / "in").mkdir()
    (work / "out").mkdir()
    code_b = code.encode()
    (work / "main.py").write_bytes(code_b)
    receipt_inputs = []
    for n, p in sorted(inputs.items()):
        shutil.copyfile(p, work / "in" / n)
        receipt_inputs.append({"name": n, "sha256": sha256_file(work / "in" / n)})
    # Output dir is a size-capped tmpfs on the host, so a run cannot fill the disk.
    mounted = subprocess.run(["mount", "-t", "tmpfs", "-o", f"size={lim['out_mb']}m,mode=0777", "tmpfs",
                              str(work / "out")], capture_output=True).returncode == 0
    os.chmod(work / "out", 0o777)
    for f in [work, work / "in", work / "main.py", *(work / "in").iterdir()]:
        os.chmod(f, 0o755 if f.is_dir() else 0o644)
    cmd = ["create", "--name", name, "--label", "leakproof=run",
           "--runtime", lim["runtime"], "--network", lim["network"],
           "--memory", f"{lim['memory_mb']}m", "--memory-swap", f"{lim['memory_mb']}m",
           "--cpus", str(lim["cpus"]), "--pids-limit", str(lim["pids"]),
           "--read-only", "--tmpfs", f"/tmp:size={lim['tmpfs_mb']}m",
           "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
           "--log-driver", "none", "--env", "HOME=/tmp",
           "-v", f"{work / 'in'}:/data:ro", "-v", f"{work / 'main.py'}:/code/main.py:ro",
           "-v", f"{work / 'out'}:/out", image, "python", "/code/main.py"]
    cid = _docker(*cmd, check=True).stdout.strip()
    watch = {"pids_max": 0, "stop": False}
    watcher = threading.Thread(target=_watch_cgroup, args=(cid, watch), daemon=True)
    watcher.start()
    t0 = time.monotonic()
    proc = subprocess.Popen(["docker", "start", "-a", name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cap = lim["stdout_kb"] * 1024
    out, err = {}, {}
    threads = [threading.Thread(target=_read_capped, args=(proc.stdout, cap, out)),
               threading.Thread(target=_read_capped, args=(proc.stderr, cap, err))]
    for t in threads:
        t.start()
    killed_by, state = None, {}
    try:
        try:
            proc.wait(timeout=lim["wall_s"])
        except subprocess.TimeoutExpired:
            killed_by = "timeout"
            _docker("kill", name)
            proc.wait(timeout=30)
        for t in threads:
            t.join(timeout=10)
        duration_ms = int((time.monotonic() - t0) * 1000)
        watch["stop"] = True
        watcher.join(timeout=2)
        info = _docker("inspect", name, "--format", "{{json .State}}|{{.HostConfig.Runtime}}")
        if info.returncode == 0:
            s, runtime = info.stdout.strip().split("|")
            state = json.loads(s)
        else:
            runtime = None
    finally:
        _docker("rm", "-f", name)
    stdout, stderr = out.get("data", b"").decode(errors="replace"), err.get("data", b"").decode(errors="replace")
    exit_code = state.get("ExitCode", proc.returncode)
    if killed_by is None:
        if state.get("OOMKilled") or "MemoryError" in stderr:
            killed_by = "oom"
        elif watch["pids_max"] > 0:  # the host cgroup refused a new task: the pids limit stopped it
            killed_by = "pids"
    blocked = []
    for line in stderr.splitlines():
        if line.startswith("LEAKPROOF_BLOCKED "):
            try:
                blocked.append(json.loads(line[len("LEAKPROOF_BLOCKED "):]))
            except ValueError:
                pass
    # Keep outputs, capped by the tmpfs size, then release the mount.
    dest = RUNS_DIR / run_id
    dest.mkdir(parents=True, exist_ok=True)
    outputs = []
    for f in sorted((work / "out").rglob("*")):
        if f.is_file() and not f.is_symlink():
            rel = f.relative_to(work / "out")
            (dest / "out" / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, dest / "out" / rel)
            outputs.append({"name": str(rel), "sha256": sha256_file(f), "bytes": f.stat().st_size})
    if mounted:
        subprocess.run(["umount", str(work / "out")], capture_output=True)
    shutil.rmtree(work, ignore_errors=True)
    (dest / "main.py").write_bytes(code_b)
    (dest / "stdout.txt").write_text(stdout)
    (dest / "stderr.txt").write_text(stderr)
    receipt = {
        "run_id": run_id, "inputs": receipt_inputs, "code_sha256": sha256_bytes(code_b),
        "image": image, "image_digest": image_digest(image), "runtime": runtime,
        "limits": {k: lim[k] for k in ("network", "memory_mb", "cpus", "pids", "wall_s")},
        "pids_limit_hits": watch["pids_max"],
        "exit_code": exit_code, "killed_by": killed_by, "blocked": blocked,
        "duration_ms": duration_ms, "stdout_sha256": sha256_bytes(stdout.encode()),
        "stdout_truncated_bytes": out.get("dropped", 0), "outputs": outputs,
    }
    (dest / "receipt.json").write_text(json.dumps(receipt, indent=2))
    receipt["stdout"], receipt["stderr"] = stdout, stderr
    return receipt
