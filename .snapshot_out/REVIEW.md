# Change Summary (chore/ci-snapshot-bot@7478afd)
- Why: <fill in>
- Risk: low | medium | high
- Version: version: unknown
- Rollback: revert above commit or redeploy previous snapshot

## Files Changed
- .archangel.workspace.md
- .env.example
- .github/pull_request_template.md
- .github/workflows/ci.yaml
- .snapshot_out/REVIEW.md
- .snapshot_out/artifacts/pytest.txt
- .snapshot_out/diff.patch
- .snapshot_out/files/.github/workflows/ci.yaml
- .snapshot_out/files/.snapshot_tmp/pytest.txt
- .snapshot_out/files/Makefile
- .snapshot_out/files/app/api_outbox.py
- .snapshot_out/files/app/main.py
- .snapshot_out/files/outbox_worker.py
- .snapshot_out/files/pytest.ini
- .snapshot_out/files/requirements.txt
- .snapshot_out/files/scripts/make_snapshot.sh
- .snapshot_out/files/scripts/review_bundle.py
- .snapshot_out/files/tests/test_outbox_integration.py
- .snapshot_out/files/tests/test_retry.py
- .snapshot_out/manifest.json
- .snapshot_out/status.json
- .snapshot_tmp/pytest.txt
- CLAUDE.md
- Makefile
- app/api.py
- app/api_outbox.py
- app/db_pg.py
- app/main.py
- app/scoring.py
- app/utils/outbox.py
- app/utils/retry.py
- docker-compose.yml
- docs/commands.md
- outbox_worker.py
- pytest.ini
- requirements.txt
- scripts/make_snapshot.sh
- scripts/review_bundle.py
- scripts/score_explain.py
- tests/test_basic.py
- tests/test_outbox_integration.py
- tests/test_outbox_pattern.py
- tests/test_retry.py
- tests/test_retry_backoff.py
- tests/test_retry_simple.py
- tests/test_serena_toggle.py
- tests/test_webhook_idempotent.py

## Tests
```
pytest not found; skipping tests
```

## Decision Trace
- <key decision 1>
- <key decision 2>