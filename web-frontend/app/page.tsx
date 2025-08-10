"use client"
import { useEffect, useState } from "react"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8001"

type PendingReq = { id: string; action_type: string; description: string; risk_level: string; proposed_action: any }

export default function Home() {
  const [summary, setSummary] = useState<any>({})
  const [pending, setPending] = useState<PendingReq[]>([])
  const [brief, setBrief] = useState("")
  const [result, setResult] = useState<any>(null)

  async function refresh() {
    const s = await fetch(`${API_BASE}/api/summary`).then(r=>r.json())
    setSummary(s)
    const r = await fetch(`${API_BASE}/api/requests`).then(r=>r.json())
    setPending(r.pending || [])
  }

  useEffect(()=>{ refresh() }, [])

  async function post(path: string, body?: any) {
    const res = await fetch(`${API_BASE}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined })
    await refresh()
    return res.json().catch(()=>null)
  }

  return (
    <main className="container py-8">
      <h1 className="text-2xl font-semibold mb-6">PM Agent Dashboard</h1>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="border rounded-lg p-4">
          <div className="font-medium mb-2">Summary</div>
          <pre className="text-sm bg-muted p-3 rounded-md overflow-auto max-h-80">{JSON.stringify(summary, null, 2)}</pre>
          <button className="mt-2 px-3 py-2 border rounded-md" onClick={refresh}>Refresh</button>
        </div>

        <div className="border rounded-lg p-4">
          <div className="font-medium mb-2">Workflows</div>
          <input className="w-full border rounded-md px-3 py-2 mb-2" placeholder="Project brief" value={brief} onChange={e=>setBrief(e.target.value)} />
          <div className="space-x-2">
            <button className="px-3 py-2 border rounded-md" onClick={async()=>setResult(await post('/api/workflows/plan', { brief: brief || 'Plan a sample feature'}))}>Run Planning</button>
            <button className="px-3 py-2 border rounded-md" onClick={async()=>setResult(await post('/api/workflows/standup'))}>Daily Standup</button>
            <button className="px-3 py-2 border rounded-md" onClick={async()=>setResult(await post('/api/workflows/monitor'))}>Monitoring Check</button>
          </div>
          <pre className="text-sm bg-muted p-3 rounded-md overflow-auto max-h-80 mt-2">{result ? JSON.stringify(result, null, 2) : ''}</pre>
        </div>
      </div>

      <div className="border rounded-lg p-4 mt-6">
        <div className="font-medium mb-2">Pending Approvals</div>
        <div className="grid gap-4 md:grid-cols-2">
          {pending.map((req)=> (
            <div key={req.id} className="border rounded-md p-3">
              <div className="flex items-center justify-between">
                <div className="font-medium">{req.action_type}</div>
                <div className="text-xs px-2 py-1 bg-secondary rounded-full">{req.risk_level}</div>
              </div>
              <div className="text-sm text-muted-foreground">{req.description}</div>
              <pre className="text-xs bg-muted p-2 rounded-md overflow-auto max-h-48 mt-2">{JSON.stringify(req.proposed_action, null, 2)}</pre>
              <div className="space-x-2 mt-2">
                <button className="px-3 py-2 border rounded-md" onClick={()=>post(`/api/requests/${req.id}/approve`)}>Approve</button>
                <button className="px-3 py-2 border rounded-md" onClick={()=>post(`/api/requests/${req.id}/reject`)}>Reject</button>
                <button className="px-3 py-2 border rounded-md" onClick={async()=>{
                  const text = prompt('Provide modified action JSON')
                  if(!text) return
                  try{
                    const action = JSON.parse(text)
                    await post(`/api/requests/${req.id}/modify`, { action })
                  } catch { alert('Invalid JSON') }
                }}>Modify</button>
              </div>
              <div className="text-xs text-muted-foreground mt-1">ID: {req.id}</div>
            </div>
          ))}
        </div>
      </div>
    </main>
  )
}