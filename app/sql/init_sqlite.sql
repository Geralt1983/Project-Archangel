create table if not exists events(
      delivery_id text primary key,
      payload text not null,
      created_at text not null default (datetime('now'))
);

create table if not exists tasks(
    id text primary key,
    external_id text,
    provider text,
    payload text,
    score real,
    status text,
    client text,
    created_at text default (datetime('now')),
    updated_at text default (datetime('now'))
);

create table if not exists outbox(
  id integer primary key autoincrement,
  operation_type text not null,
  endpoint text not null,
  request text not null,
  headers text not null default '{}',
  idempotency_key text not null,
  status text not null,
  retry_count int not null default 0,
  next_retry_at text null,
  error text null,
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now'))
);

create unique index if not exists outbox_idem_ux on outbox(idempotency_key);
create index if not exists outbox_status_next_idx on outbox(status, next_retry_at);
