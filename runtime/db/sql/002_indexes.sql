-- PM Agent Work Graph Indexes
-- Performance indexes for common queries

-- Task indexes
create index if not exists idx_task_project_status on task (project, status);
create index if not exists idx_task_due_at on task (due_at) where due_at is not null;
create index if not exists idx_task_assignee on task (assignee) where assignee is not null;
create index if not exists idx_task_status on task (status);
create index if not exists idx_task_created_at on task (created_at);
create index if not exists idx_task_updated_at on task (updated_at);

-- Edge indexes for graph traversal
create index if not exists idx_edge_src_id_kind on edge (src_id, kind);
create index if not exists idx_edge_dst_id_kind on edge (dst_id, kind);
create index if not exists idx_edge_kind on edge (kind);

-- Node indexes
create index if not exists idx_node_type on node (type);
create index if not exists idx_node_label on node (label);

-- Signal indexes for chronological queries
create index if not exists idx_signal_source_at on signal (source, at desc);
create index if not exists idx_signal_source_id on signal (source_id);

-- Audit indexes for operational queries
create index if not exists idx_audit_run_id_at on audit (run_id, at desc);
create index if not exists idx_audit_agent_tool on audit (agent, tool);
create index if not exists idx_audit_ok on audit (ok);
create index if not exists idx_audit_at on audit (at desc);

-- JSONB indexes for meta and artefacts
create index if not exists idx_task_artefacts on task using gin (artefacts);
create index if not exists idx_node_meta on node using gin (meta);
create index if not exists idx_signal_payload on signal using gin (payload);
create index if not exists idx_audit_links on audit using gin (links);

-- Comments
comment on index idx_task_project_status is 'Fast filtering by project and status';
comment on index idx_edge_src_id_kind is 'Fast graph traversal from source';
comment on index idx_edge_dst_id_kind is 'Fast graph traversal to destination';
comment on index idx_audit_run_id_at is 'Fast audit log retrieval by run';
