from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import asyncio

from ..human_interaction import interaction_manager, ApprovalStatus
from ..crew import PMAgentCrew
from ..config import settings

app = FastAPI(title="PM Agent Dashboard")

# CORS for frontend (e.g., Next.js on localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ModifyRequest(BaseModel):
    action: dict
    message: str | None = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/summary")
async def summary():
    return interaction_manager.get_interaction_summary()


@app.get("/api/requests")
async def list_requests():
    return {"pending": interaction_manager.list_pending()}


@app.post("/api/requests/{request_id}/approve")
async def approve(request_id: str):
    result = interaction_manager.resolve_request(request_id, ApprovalStatus.APPROVED.value)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"ok": True}


@app.post("/api/requests/{request_id}/reject")
async def reject(request_id: str):
    result = interaction_manager.resolve_request(request_id, ApprovalStatus.REJECTED.value)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"ok": True}


@app.post("/api/requests/{request_id}/modify")
async def modify(request_id: str, body: ModifyRequest):
    result = interaction_manager.resolve_request(request_id, ApprovalStatus.MODIFIED.value, body.action, body.message or "")
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"ok": True}


crew_instance: PMAgentCrew | None = None
crew_lock = asyncio.Lock()


async def get_crew() -> PMAgentCrew:
    global crew_instance
    async with crew_lock:
        if crew_instance is None:
            crew_instance = PMAgentCrew()
        return crew_instance


class PlanBody(BaseModel):
    brief: str


@app.post("/api/workflows/plan")
async def start_plan(body: PlanBody):
    crew = await get_crew()
    result = await crew.run_planning_workflow(body.brief)
    return result


@app.post("/api/workflows/standup")
async def start_standup():
    crew = await get_crew()
    result = await crew.run_daily_standup()
    return result


@app.post("/api/workflows/monitor")
async def start_monitor():
    crew = await get_crew()
    result = await crew.run_monitoring_check()
    return result


INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>PM Agent Dashboard</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif; margin: 20px; }
    h1 { margin-top: 0; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
    .row { display: flex; gap: 16px; flex-wrap: wrap; }
    .col { flex: 1 1 320px; }
    button { padding: 8px 12px; margin-right: 8px; cursor: pointer; }
    code { background: #f7f7f7; padding: 2px 4px; border-radius: 4px; }
    .pill { font-size: 12px; padding: 2px 6px; border-radius: 999px; background: #eee; }
  </style>
</head>
<body>
  <h1>PM Agent Dashboard</h1>
  <div class="row">
    <div class="col card">
      <h3>Summary</h3>
      <pre id="summary">Loading...</pre>
      <button onclick="refresh()">Refresh</button>
    </div>
    <div class="col card">
      <h3>Workflows</h3>
      <input id="brief" placeholder="Project brief" style="width:100%; padding:8px;"/>
      <div style="margin-top:8px;">
        <button onclick="plan()">Run Planning</button>
        <button onclick="standup()">Daily Standup</button>
        <button onclick="monitor()">Monitoring Check</button>
      </div>
      <pre id="workflowResult"></pre>
    </div>
  </div>

  <div class="card">
    <h3>Pending Approvals</h3>
    <div id="pending">Loading...</div>
  </div>

<script>
async function refresh() {
  const s = await fetch('/api/summary').then(r=>r.json());
  document.getElementById('summary').textContent = JSON.stringify(s, null, 2);
  const r = await fetch('/api/requests').then(r=>r.json());
  const items = (r.pending || []).map(req => `
    <div class="card">
      <div><b>${req.action_type}</b> <span class="pill">${req.risk_level}</span></div>
      <div>${req.description}</div>
      <pre>${JSON.stringify(req.proposed_action, null, 2)}</pre>
      <button onclick="approve('${req.id}')">Approve</button>
      <button onclick="reject('${req.id}')">Reject</button>
      <button onclick="modify('${req.id}')">Modify</button>
      <small>ID: <code>${req.id}</code></small>
    </div>`).join('');
  document.getElementById('pending').innerHTML = items || '<em>No pending requests</em>';
}

async function approve(id) {
  await fetch(`/api/requests/${id}/approve`, {method:'POST'});
  await refresh();
}
async function reject(id) {
  await fetch(`/api/requests/${id}/reject`, {method:'POST'});
  await refresh();
}
async function modify(id) {
  const json = prompt('Provide modified action JSON:');
  if (!json) return;
  try {
    const body = { action: JSON.parse(json), message: 'Modified from dashboard' };
    await fetch(`/api/requests/${id}/modify`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    await refresh();
  } catch(e) { alert('Invalid JSON'); }
}

async function plan() {
  const brief = document.getElementById('brief').value || 'Plan a sample feature';
  const res = await fetch('/api/workflows/plan', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({brief})}).then(r=>r.json());
  document.getElementById('workflowResult').textContent = JSON.stringify(res, null, 2);
}
async function standup() {
  const res = await fetch('/api/workflows/standup', {method:'POST'}).then(r=>r.json());
  document.getElementById('workflowResult').textContent = JSON.stringify(res, null, 2);
}
async function monitor() {
  const res = await fetch('/api/workflows/monitor', {method:'POST'}).then(r=>r.json());
  document.getElementById('workflowResult').textContent = JSON.stringify(res, null, 2);
}

refresh();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(INDEX_HTML)