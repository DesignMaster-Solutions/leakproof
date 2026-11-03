"""Red-team tests. They run on the Vultr VM (Docker + gVisor, as root); elsewhere they skip.

Each control has a pair: the hostile script is contained with the control on, and the same
script gets through with that one control off. The second test is what proves the first can fail.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RT = ROOT / "redteam"

if shutil.which("docker") is None or shutil.which("runsc") is None or os.geteuid() != 0:
    pytest.skip("containment tests need Docker + runsc as root (run them on the VM)", allow_module_level=True)

from leakproof import sandbox  # noqa: E402

CANARY = "LEAKPROOF_CANARY_7f3a91"


@pytest.fixture(autouse=True)
def runs_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setenv("VULTR_INFERENCE_KEY", CANARY)  # the orchestrator holds a key; the sandbox must not see it


def hostile(name, **limits):
    return sandbox.run((RT / name).read_text(), {"customers.csv": str(ROOT / "tests" / "fixtures" / "tiny.csv")},
                       limits=limits or None)


def leftovers():
    return subprocess.run(["docker", "ps", "-aq", "--filter", "label=leakproof=run"],
                          capture_output=True, text=True).stdout.split()


# --- network --------------------------------------------------------------
def test_network_exfiltration_is_blocked():
    r = hostile("network_exfil.py")
    res = json.loads(r["stdout"].strip().splitlines()[-1])
    assert res["interfaces"] == ["lo"]
    assert all(v.startswith("blocked") for k, v in res.items() if k != "interfaces"), res
    events = {b["event"] for b in r["blocked"]}
    assert {"socket.gethostbyname", "socket.connect"} <= events  # the receipt lists the attempts


def test_network_exfiltration_without_control_gets_out():
    r = hostile("network_exfil.py", network="bridge")
    res = json.loads(r["stdout"].strip().splitlines()[-1])
    assert res["tcp 1.1.1.1:53"] == "sent"


# --- secrets ----------------------------------------------------------------
def test_secret_hunt_finds_nothing():
    r = hostile("secret_hunt.py")
    assert r["exit_code"] == 0, r["stderr"]
    assert json.loads(r["stdout"])["found"] == []
    assert CANARY not in r["stdout"] + r["stderr"]


def test_secret_hunt_finds_the_key_where_it_lives(tmp_path):
    (tmp_path / "inference.env").write_text(f"VULTR_INFERENCE_KEY={CANARY}\n")
    out = subprocess.run([sys.executable, str(RT / "secret_hunt.py")], capture_output=True, text=True,
                         env={**os.environ, "HUNT_ROOT": str(tmp_path)}).stdout
    assert CANARY in out  # same script, on the orchestrator's side of the wall


# --- resource limits ------------------------------------------------------------
def test_fork_bomb_stopped_by_pids_limit():
    r = hostile("fork_bomb.py")
    assert r["killed_by"] == "pids", (r["killed_by"], r["stderr"][-500:])
    assert r["duration_ms"] < sandbox.LIMITS["wall_s"] * 1000


def test_fork_bomb_without_pids_limit_runs_until_the_clock():
    r = hostile("fork_bomb.py", pids=-1, wall_s=8)
    assert r["killed_by"] == "timeout"
    forks = [int(x) for x in re.findall(r"forked (\d+)", r["stdout"])]  # last line may be cut by the kill
    assert max(forks) > sandbox.LIMITS["pids"]


def test_memory_balloon_stopped_by_oom():
    r = hostile("memory_balloon.py")
    assert r["killed_by"] == "oom"
    assert "BALLOON_DONE" not in r["stdout"]


def test_memory_balloon_without_limit_completes():
    r = hostile("memory_balloon.py", memory_mb=2048)
    assert "BALLOON_DONE" in r["stdout"]


def test_infinite_loop_stopped_by_wall_clock():
    r = hostile("infinite_loop.py")
    assert r["killed_by"] == "timeout"
    assert sandbox.LIMITS["wall_s"] * 1000 <= r["duration_ms"] < (sandbox.LIMITS["wall_s"] + 15) * 1000


def test_host_stays_healthy_after_attacks():
    hostile("fork_bomb.py")
    hostile("memory_balloon.py")
    assert subprocess.run(["docker", "info"], capture_output=True).returncode == 0
    avail_kb = int([l for l in open("/proc/meminfo") if l.startswith("MemAvailable")][0].split()[1])
    assert avail_kb > 1_000_000


# --- lifecycle --------------------------------------------------------------------
def test_no_state_carries_between_runs():
    a = sandbox.run("open('/out/marker.txt','w').write('A'); open('/tmp/marker','w').write('A'); print('ok')", {})
    assert a["stdout"].strip() == "ok" and any(o["name"] == "marker.txt" for o in a["outputs"])
    b = sandbox.run("import os; print(sorted(os.listdir('/out')), sorted(os.listdir('/tmp')))", {})
    assert "marker" not in b["stdout"], b["stdout"]


def test_no_leftover_containers_or_mounts():
    hostile("infinite_loop.py", wall_s=3)
    hostile("fork_bomb.py")
    assert leftovers() == []
    assert "lp-" not in Path("/proc/mounts").read_text()


# --- kernel isolation -------------------------------------------------------------
KERNEL = "import os; print(open('/proc/version').read().strip()); print(os.getuid())"


def test_runs_under_gvisor_not_the_host_kernel():
    r = sandbox.run(KERNEL, {})
    assert r["runtime"] == "runsc"
    host = Path("/proc/version").read_text().strip()
    assert r["stdout"].splitlines()[0] != host
    assert r["stdout"].splitlines()[1] == "10001"  # non-root inside


def test_default_runtime_would_share_the_host_kernel():
    r = sandbox.run(KERNEL, {}, limits={"runtime": "runc"})
    assert r["stdout"].splitlines()[0] == Path("/proc/version").read_text().strip()


def test_root_filesystem_and_inputs_are_read_only():
    code = """
for p in ['/etc/x', '/data/customers.csv', '/code/main.py', '/usr/local/x']:
    try:
        open(p, 'a').write('x'); print('WROTE', p)
    except OSError as e:
        print('denied', p)
import os
try:
    os.setuid(0); print('ROOT')
except OSError:
    print('no root')
"""
    r = sandbox.run(code, {"customers.csv": str(ROOT / "tests" / "fixtures" / "tiny.csv")})
    assert "WROTE" not in r["stdout"] and "ROOT" not in r["stdout"], r["stdout"]
    assert r["stdout"].count("denied") == 4


# --- receipt ------------------------------------------------------------------------
def test_receipt_is_complete_and_reproducible():
    code = "import pandas as pd; df = pd.read_csv('/data/customers.csv'); df.to_csv('/out/result.csv', index=False); print(len(df))"
    inputs = {"customers.csv": str(ROOT / "tests" / "fixtures" / "tiny.csv")}
    a, b = sandbox.run(code, inputs), sandbox.run(code, inputs)
    for k in ["run_id", "inputs", "code_sha256", "image_digest", "runtime", "limits", "exit_code", "killed_by",
              "blocked", "duration_ms", "outputs"]:
        assert k in a
    assert a["image_digest"].startswith("sha256:") and a["exit_code"] == 0
    assert a["outputs"] == b["outputs"] and a["stdout_sha256"] == b["stdout_sha256"]
    assert a["run_id"] != b["run_id"]
