// All model and data output is inserted with textContent, never innerHTML.
const $ = (id) => document.getElementById(id);
const el = (tag, text, cls) => { const e = document.createElement(tag); if (text != null) e.textContent = text; if (cls) e.className = cls; return e; };
let dataset = "demo", cfg = null, poll = null, currentJob = null;

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error((await r.text()).replace(/<[^>]+>/g, " ").trim().slice(0, 300) || r.statusText);
  return r.json();
}

function showFiles(list) {
  const ul = $("files"); ul.replaceChildren();
  list.forEach((f) => { const li = el("li"); li.append(el("span", f.name || f), el("span", f.note || "")); ul.append(li); });
}

async function init() {
  cfg = await api("/api/config");
  showFiles(cfg.demo_files.map((n) => ({ name: n, note: "read-only" })));
  $("mPlanner").textContent = cfg.models.planner;
  $("mVerifier").textContent = cfg.models.verifier;
  const L = cfg.limits;
  $("lims").textContent = `${L.memory_mb} MB, ${L.cpus} CPU, ${L.pids} processes, ${L.wall_s} s`;
  const qs = $("qs");
  Object.entries(cfg.questions).forEach(([k, q]) => {
    const b = el("button", null, "q"); b.type = "button"; b.dataset.check = k;
    b.append(el("b", k), el("span", q));
    b.onclick = () => ask({ check: k });
    qs.append(b);
  });
}

document.querySelectorAll(".seg-b").forEach((b) => b.onclick = () => {
  document.querySelectorAll(".seg-b").forEach((x) => x.classList.toggle("on", x === b));
  const up = b.dataset.ds === "upload";
  $("drop").hidden = !up;
  if (!up) { dataset = "demo"; showFiles(cfg.demo_files.map((n) => ({ name: n, note: "read-only" }))); }
  else showFiles([]);
});

function upload(files) {
  const csvs = [...files].filter((f) => f.name.toLowerCase().endsWith(".csv"));
  if (!csvs.length) return;
  showFiles(csvs.map((f) => ({ name: f.name, note: `${(f.size / 1024).toFixed(1)} KB` })));
  const fd = new FormData(); csvs.forEach((f) => fd.append("files", f));
  const x = new XMLHttpRequest(); const bar = $("upProg"); bar.hidden = false;
  x.upload.onprogress = (e) => { if (e.lengthComputable) bar.firstElementChild.style.width = `${(100 * e.loaded / e.total).toFixed(0)}%`; };
  x.onload = () => {
    if (x.status !== 200) { alert(x.responseText.replace(/<[^>]+>/g, " ").trim().slice(0, 200)); return; }
    const r = JSON.parse(x.responseText); dataset = r.dataset;
    showFiles(csvs.map((f) => ({ name: f.name, note: `${(f.size / 1024).toFixed(1)} KB · uploaded` })));
  };
  x.open("POST", "/api/upload"); x.send(fd);
}
$("pick").onclick = () => $("fileIn").click();
$("fileIn").onchange = (e) => upload(e.target.files);
const drop = $("drop");
["dragenter", "dragover"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", (e) => upload(e.dataTransfer.files));

$("free").onsubmit = (e) => { e.preventDefault(); const q = $("freeQ").value.trim(); if (q) ask({ question: q }); };

function lock(on) { document.querySelectorAll(".q, #free .btn, #rtGo").forEach((b) => b.disabled = on); }

async function ask(body) {
  clearInterval(poll); lock(true);
  ["ansP", "tableP", "codeP", "rcpt", "err", "stamp", "apprP", "drafts"].forEach((id) => $(id).hidden = true);
  $("empty").hidden = true; $("rt").hidden = true; $("job").hidden = false; $("reviewed").checked = false; setAppr(false);
  $("job").scrollIntoView({ behavior: "smooth", block: "start" }); $("steps").replaceChildren();
  $("jq").textContent = body.check ? cfg.questions[body.check] : body.question;
  try {
    const { job } = await api("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body, dataset, plant_wrong_total: $("plant").checked }) });
    history.replaceState(null, "", `#job=${job}`);
    watch(job);
  } catch (e) { fail(e.message); }
}

function fail(msg) { $("err").textContent = msg; $("err").hidden = false; lock(false); }

function watch(id) {
  const tick = async () => {
    let j; try { j = await api(`/api/jobs/${id}`); } catch (e) { return; }
    render(j);
    if (j.status !== "running") { clearInterval(poll); lock(false); }
  };
  tick(); poll = setInterval(tick, 1500);
}

function render(j) {
  $("jq").textContent = j.question;
  const ol = $("steps"); ol.replaceChildren();
  const t0 = j.created;
  j.steps.forEach((s, i) => {
    const last = i === j.steps.length - 1 && j.status === "running";
    const li = el("li", null, last ? "live" : "done");
    li.append(el("span", s.label), el("span", `${(s.t - t0).toFixed(1)} s`, "t"));
    ol.append(li);
  });
  if (j.status === "error") fail(j.error);
  if (j.code) { $("code").textContent = j.code; $("codeP").hidden = false; }
  if (j.contained) $("stamp").hidden = false;
  if (j.status !== "done") return;
  const done = el("li", null, "done"); done.append(el("span", j.ok ? "Done" : "Stopped after 3 attempts"));
  ol.append(done);
  if (j.verification) renderAnswer(j);
  if (j.table) { renderTable(j); currentJob = j.id; $("apprN").textContent = j.table.total; $("apprP").hidden = false; }
  if (j.receipt) renderReceipt(j);
}

function renderAnswer(j) {
  const v = j.verification;
  $("answer").textContent = v.answer || "Nothing in the draft was backed by the output.";
  const ul = $("cuts"); ul.replaceChildren();
  const cut = v.sentences.filter((s) => !s.kept).length;
  $("cutN").textContent = `${v.sentences.length - cut} kept, ${cut} cut`;
  v.sentences.forEach((s) => {
    const li = el("li", null, s.kept ? "kept" : "cut");
    li.append(el("span", s.kept ? "KEPT" : "CUT", "tagk"), el("span", s.sentence, "s"));
    const why = s.numbers_not_in_output.length ? `numbers not in the output: ${s.numbers_not_in_output.join(", ")}. ` : "";
    li.append(el("span", `${v.model}: ${s.model_backed ? "backed" : "not backed"}. ${why}${s.evidence}`, "why"));
    ul.append(li);
  });
  $("cutD").open = cut > 0;
  const sc = $("score");
  if (j.score) {
    sc.hidden = false; sc.classList.toggle("bad", !j.score.pass);
    let t = `Answer key: ${j.score.found.length} of ${j.score.expected} found, ${j.score.extra.length} extra`;
    if (j.score.decoys_reported) t += `, ${j.score.decoys_reported.length} decoys reported`;
    sc.textContent = `${t} · ${j.score.pass ? "PASS" : "FAIL"}`;
  } else sc.hidden = true;
  $("ansP").hidden = false;
}

function renderTable(j) {
  const t = $("tbl"); t.replaceChildren();
  const hr = el("tr"); j.table.header.forEach((h) => hr.append(el("th", h)));
  const thead = el("thead"); thead.append(hr); t.append(thead);
  const tb = el("tbody");
  j.table.rows.forEach((r) => { const tr = el("tr"); r.forEach((c) => tr.append(el("td", c))); tb.append(tr); });
  t.append(tb);
  $("tcount").textContent = `${j.table.total} rows${j.table.total > j.table.rows.length ? `, first ${j.table.rows.length} shown` : ""}`;
  $("dlCsv").href = `/api/runs/${j.run_id}/out/result.csv`;
  $("tableP").hidden = false;
}

function renderReceipt(j) {
  const r = j.receipt, dl = $("rcptBody"); dl.replaceChildren();
  const row = (k, v) => { dl.append(el("dt", k), el("dd", v)); };
  row("run", r.run_id);
  r.inputs.forEach((i) => row(i.name, `sha256:${i.sha256.slice(0, 16)}…`));
  row("code", `sha256:${r.code_sha256.slice(0, 16)}…`);
  row("image", r.image_digest.slice(0, 23) + "…");
  row("runtime", r.runtime);
  row("network", r.limits.network);
  row("limits", `${r.limits.memory_mb} MB · ${r.limits.cpus} CPU · ${r.limits.pids} pids · ${r.limits.wall_s} s`);
  row("exit", `${r.exit_code}${r.killed_by ? ` · killed_by ${r.killed_by}` : ""}`);
  row("blocked", r.blocked.length ? r.blocked.map((b) => `${b.event} ${b.target}`).join("; ") : "none");
  row("attempts", String(j.attempts.length));
  row("duration", `${r.duration_ms} ms`);
  r.outputs.forEach((o) => row(o.name, `sha256:${o.sha256.slice(0, 16)}…`));
  $("dlRcpt").href = `/api/runs/${j.run_id}/receipt.json`;
  $("dlCode").href = `/api/runs/${j.run_id}/main.py`;
  $("rcpt").hidden = false;
}

init().then(() => {
  const m = location.hash.match(/job=([0-9a-f]{12})/); if (m) { $("empty").hidden = true; $("job").hidden = false; watch(m[1]); }
  const r = location.hash.match(/rt=([0-9a-f]{12})/); if (r) { $("empty").hidden = true; $("rt").hidden = false; watchRt(r[1]); }
});

// --- human approval: both actions stay local -------------------------------
function setAppr(on) { $("aExport").disabled = !on; $("aDrafts").disabled = !on; }
$("reviewed").onchange = (e) => setAppr(e.target.checked);
async function approve(action) {
  const r = await fetch(`/api/jobs/${currentJob}/approve`, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, confirmed: $("reviewed").checked }) });
  if (!r.ok) { alert("Approval failed"); return; }
  if (action === "export") {
    const url = URL.createObjectURL(await r.blob()); const a = document.createElement("a");
    a.href = url; a.download = `fix-list-${currentJob}.csv`; a.click(); URL.revokeObjectURL(url);
  } else {
    const d = await r.json(); const t = $("drafts");
    t.value = d.count ? d.text : `No findings with an email address (${d.of} rows).`; t.hidden = false;
  }
}
$("aExport").onclick = () => approve("export");
$("aDrafts").onclick = () => approve("drafts");

$("reset").onclick = async () => {
  await fetch("/api/reset", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ dataset }) });
  location.href = "/";
};

// --- red team ---------------------------------------------------------------
$("rtGo").onclick = async () => {
  clearInterval(poll); lock(true);
  $("empty").hidden = true; $("job").hidden = true; $("rt").hidden = false; $("rt").scrollIntoView({ behavior: "smooth", block: "start" });
  try { const { job } = await api("/api/redteam", { method: "POST" }); history.replaceState(null, "", `#rt=${job}`); watchRt(job); }
  catch (e) { $("rtSub").textContent = e.message; lock(false); }
};

function watchRt(id) {
  const tick = async () => {
    let j; try { j = await api(`/api/jobs/${id}`); } catch (e) { return; }
    renderRt(j);
    if (j.status !== "running") { clearInterval(poll); lock(false); }
  };
  tick(); poll = setInterval(tick, 1500);
}

function renderRt(j) {
  const box = $("cards"); box.replaceChildren();
  const byName = Object.fromEntries(j.cards.map((c) => [c.script, c]));
  j.expected.forEach((e) => {
    const c = byName[e.script];
    const card = el("div", null, `card ${c ? (c.stopped ? "ok" : "fail") : "wait"}`);
    const hd = el("div", null, "hd"); hd.append(el("h3", e.script));
    if (c) hd.append(el("span", c.stopped ? "Contained" : "Escaped", "stamp"));
    card.append(hd, el("p", e.goal, "goal"));
    if (c) {
      card.append(el("div", c.verdict, "verdict"),
        el("div", `runtime ${c.runtime} · exit ${c.exit_code} · ${(c.duration_ms / 1000).toFixed(1)} s`, "meta"));
      const d = el("details"); d.append(el("summary", "script"), el("pre", c.code)); card.append(d);
    } else card.append(el("div", "", "verdict"));
    box.append(card);
  });
  const n = j.cards.filter((c) => c.stopped).length;
  $("rtSub").textContent = j.status === "done" ? `${n} of ${j.expected.length} contained · containers left behind: ${j.leftover_containers}` : "running";
}
