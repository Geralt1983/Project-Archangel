#!/usr/bin/env python3
import argparse
from typing import Dict, Any
from app.db_pg import init, get_conn
from app.utils.outbox import OutboxManager
from app.utils.retry import retry, default_httpx_retryable, next_backoff

# Stub dispatch. Replace with real provider calls.
def dispatch(op_type: str, endpoint: str, payload: Dict[str, Any], headers: Dict[str, Any]) -> None:
    """
    Implement your provider RPC here, e.g.:
      - POST to ClickUp/Trello/Todoist
      - Add comment, create checklist, etc.
    Must raise on failure.
    """
    # Example no-op: pretend success
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--max-tries", type=int, default=5)
    args = ap.parse_args()

    init()  # ensure tables exist
    ob = OutboxManager(get_conn)
    batch = ob.pick_batch(limit=args.limit)

    delivered = 0
    failed = 0
    dead = 0
    picked = len(batch)

    for op in batch:
        ob.mark_inflight(op.id)

        def _call():
            return dispatch(op.operation_type, op.endpoint, op.request, op.headers)

        try:
            retry(_call, max_tries=args.max_tries, retry_if=default_httpx_retryable())
            ob.mark_delivered(op.id)
            delivered += 1
        except Exception as e:
            # schedule retry or dead-letter after N tries
            rc = op.retry_count + 1
            if rc >= args.max_tries:
                ob.dead_letter(op.id, str(e))
                dead += 1
            else:
                ob.mark_failed(op.id, retry_in_seconds=int(next_backoff(rc)), error=str(e))
                failed += 1

    print(f"[metrics] outbox.worker delivered={delivered} failed={failed} dead={dead} picked={picked}")


if __name__ == "__main__":
    main()