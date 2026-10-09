// UI logic: every action is one call to the Python sidecar through the shell.
const rpc = (method, params = {}) => window.__TAURI__.core.invoke("rpc", { method, params });
const $ = (id) => document.getElementById(id);

function setStatus(text, isError = false) {
  $("status").textContent = text;
  $("status").className = isError ? "error" : "";
}

async function act(label, fn) {
  setStatus(`${label}...`);
  try {
    const out = await fn();
    setStatus(`${label}: done`);
    return out;
  } catch (err) {
    setStatus(`${label} failed: ${err}`, true);
  }
}

function el(tag, text) {
  const node = document.createElement(tag);
  node.textContent = text;
  return node;
}

async function loadWorkspaces() {
  const workspaces = await rpc("list_workspaces");
  const select = $("workspace");
  select.replaceChildren(...workspaces.map((w) => {
    const opt = el("option", w.displayName);
    opt.value = w.id;
    return opt;
  }));
  await loadLakehouses();
}

async function loadLakehouses() {
  const workspaceId = $("workspace").value;
  if (!workspaceId) return;
  const lakehouses = await rpc("list_lakehouses", { workspace_id: workspaceId });
  $("lakehouses").replaceChildren(...lakehouses.map((lh) => {
    const li = el("li", `${lh.displayName}  `);
    const btn = el("button", "Tables");
    btn.onclick = () => act("Listing tables", () => showTables(workspaceId, lh.id));
    li.append(btn);
    return li;
  }));
}

async function showTables(workspaceId, lakehouseId) {
  const bySchema = await rpc("list_tables", { workspace_id: workspaceId, lakehouse_id: lakehouseId });
  $("tables").replaceChildren(...Object.entries(bySchema).map(([schema, tables]) =>
    el("p", `${schema}: ${tables.length ? tables.join(", ") : "(no tables)"}`)));
}

async function loadHistory() {
  const runs = await rpc("history");
  $("history").tBodies[0].replaceChildren(...runs.map((r) => {
    const tr = document.createElement("tr");
    [r.finished_at, r.job, r.rows, r.delta_version, r.seconds].forEach((v) => tr.append(el("td", v)));
    return tr;
  }));
}

$("sign-in").onclick = () => act("Signing in", async () => {
  const { user } = await rpc("sign_in");
  $("user").textContent = user || "Signed in";
  await loadWorkspaces();
});

$("workspace").onchange = () => act("Loading lakehouses", loadLakehouses);

$("create-lakehouse").onclick = () => act("Creating lakehouse", async () => {
  await rpc("create_lakehouse", { workspace_id: $("workspace").value, name: $("new-lakehouse").value });
  await loadLakehouses();
});

$("preview").onclick = () => act("Running locally", async () => {
  const p = await rpc("preview_job", { path: $("job-path").value, limit: 20 });
  const table = document.createElement("table");
  const head = document.createElement("tr");
  p.columns.forEach((c) => head.append(el("th", c)));
  table.append(head);
  p.sample.forEach((row) => {
    const tr = document.createElement("tr");
    p.columns.forEach((c) => tr.append(el("td", row[c])));
    table.append(tr);
  });
  $("result").replaceChildren(el("p", `${p.rows} rows`), table);
});

$("run").onclick = () => act("Running and publishing", async () => {
  const r = await rpc("run_job", { path: $("job-path").value });
  $("result").replaceChildren(el("p", `Published ${r.rows} rows to ${r.table_uri} (Delta version ${r.delta_version}).`));
  await loadHistory();
});

act("Loading history", loadHistory);
