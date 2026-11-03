import io
import json

import pytest

from leakproof import sandbox, web

RUN = "20261103T120000Z-abcdef12"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(web, "DATASETS", tmp_path / "datasets")
    monkeypatch.setattr(web, "JOBS", tmp_path / "jobs")
    out = tmp_path / "runs" / RUN / "out"
    out.mkdir(parents=True)
    (out / "result.csv").write_text('invoice,email,note\nin_1,a@example.com,"=HYPERLINK(""http://evil.example"",""x"")"\nin_2,b@example.com,<script>alert(1)</script>\n')
    web.RATE.clear()
    return web.app.test_client()


def done_job(client, tmp_path):
    job = {"id": "0123456789ab", "status": "done", "run_id": RUN, "question": "q", "steps": [], "created": 0}
    web.save_job(job)
    return job["id"]


def test_upload_rejects_path_tricks(client):
    r = client.post("/api/upload", data={"files": (io.BytesIO(b"a,b\n1,2\n"), "../../etc/passwd.csv")},
                    content_type="multipart/form-data")
    assert r.status_code == 200  # the name is reduced to its basename...
    assert json.loads(r.data)["files"] == ["passwd.csv"]  # ...and stays inside the dataset dir
    r = client.post("/api/upload", data={"files": (io.BytesIO(b"x"), "run.sh")}, content_type="multipart/form-data")
    assert r.status_code == 400


def test_output_files_are_served_as_text_attachments(client):
    r = client.get(f"/api/runs/{RUN}/out/result.csv")
    assert r.status_code == 200 and r.mimetype == "text/plain"
    assert "attachment" in r.headers["Content-Disposition"]
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
    assert client.get(f"/api/runs/{RUN}/../../etc/passwd").status_code == 404


def test_approval_needs_confirmation(client, tmp_path):
    jid = done_job(client, tmp_path)
    assert client.post(f"/api/jobs/{jid}/approve", json={"action": "export"}).status_code == 400
    r = client.post(f"/api/jobs/{jid}/approve", json={"action": "export", "confirmed": True})
    assert r.status_code == 200 and "'=HYPERLINK" in r.data.decode()
    d = json.loads(client.post(f"/api/jobs/{jid}/approve", json={"action": "drafts", "confirmed": True}).data)
    assert d["count"] == 2
    assert [a["action"] for a in json.loads(client.get(f"/api/jobs/{jid}").data)["approvals"]] == ["export", "drafts"]


def test_rate_limit(client):
    for _ in range(20):
        web.rate_ok("1.2.3.4")
    assert client.post("/api/ask", json={"check": "1"}, headers={"X-Forwarded-For": "1.2.3.4"}).status_code == 429
