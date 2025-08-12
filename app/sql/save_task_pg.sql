insert into tasks(id, external_id, provider, payload, score, status, client, created_at, updated_at)
values(%s, %s, %s, %s::jsonb, %s, %s, %s, %s, now())
on conflict(id) do update set
    external_id = excluded.external_id,
    provider = excluded.provider,
    payload = excluded.payload,
    score = excluded.score,
    status = excluded.status,
    client = excluded.client,
    updated_at = now()
