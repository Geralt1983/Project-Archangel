from app.utils.idempotency import make_idempotency_key

def test_make_idempotency_key_stable():
    p = "clickup"
    endpoint = "/tasks"
    payload = {"a": 1, "b": [3, 2, 1]}
    k1 = make_idempotency_key(p, endpoint, payload)
    k2 = make_idempotency_key(p, endpoint, {"b": [3, 2, 1], "a": 1})  # different order
    assert k1 == k2
    assert len(k1) == 64
