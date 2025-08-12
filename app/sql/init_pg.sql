create table if not exists events(
  delivery_id text primary key,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists tasks(
    id text primary key,
    external_id text,
    provider text,
    payload jsonb,
    score real,
    status text,
    client text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists outbox(
  id bigserial primary key,
  operation_type text not null,
  endpoint text not null,
  request jsonb not null,
  headers jsonb not null default '{}'::jsonb,
  idempotency_key text not null,
  status text not null,
  retry_count int not null default 0,
  next_retry_at timestamptz null,
  error text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists outbox_idem_ux on outbox(idempotency_key);
create index if not exists outbox_status_next_idx on outbox(status, next_retry_at);
