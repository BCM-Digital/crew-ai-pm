-- PM Agent Work Graph Schema
-- Creates task tracking, graph nodes/edges, signals, and audit tables

-- Task table for project work items
create table if not exists task (
  id           text primary key,
  source       text not null,                       -- outlook|teams|calendar|manual
  project      text not null,
  title        text not null check (char_length(title) <= 100),
  description  text not null,
  priority     text not null check (priority in ('P0','P1','P2','P3')),
  status       text not null check (status in ('new','planned','waiting','blocked','done')),
  assignee     text,
  due_at       timestamptz,
  next_action  text,
  artefacts    jsonb default '[]'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- Graph nodes for entities (people, messages, docs, events, repos, services, projects)
create table if not exists node (
  id        text primary key,
  type      text not null,                          -- person|message|doc|event|repo|service|project
  label     text not null,
  meta      jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- Graph edges for relationships
create table if not exists edge (
  id        text primary key,
  src_id    text not null references node(id) on delete cascade,
  dst_id    text not null references node(id) on delete cascade,
  kind      text not null,                          -- mentions|assigned_to|relates_to|depends_on|authored_by|belongs_to_project
  created_at timestamptz not null default now()
);

-- Signal table for incoming events
create table if not exists signal (
  id        text primary key,
  source    text not null,
  source_id text not null,
  payload   jsonb not null,
  at        timestamptz not null default now()
);

-- Audit log for tool invocations
create table if not exists audit (
  id         text primary key,
  run_id     text not null,
  agent      text not null,
  tool       text not null,
  input_hash text not null,
  ok         boolean not null,
  error_code text,
  at         timestamptz not null default now(),
  links      jsonb default '[]'::jsonb
);

-- Trigger to update task.updated_at automatically
create or replace function update_task_timestamp()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger task_update_timestamp
  before update on task
  for each row
  execute function update_task_timestamp();

-- Comments
comment on table task is 'Work items tracked across projects';
comment on table node is 'Graph entities for work graph';
comment on table edge is 'Relationships between graph entities';
comment on table signal is 'Incoming events from external systems';
comment on table audit is 'Audit log for agent tool invocations';
