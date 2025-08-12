insert or replace into tasks(id, external_id, provider, payload, score, status, client, created_at, updated_at)
    values(?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
