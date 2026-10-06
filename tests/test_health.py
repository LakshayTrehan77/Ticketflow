def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_ready_checks_db_and_model(client):
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json() == {"status": "ready"}


def test_metrics_endpoint_exposes_counters(client, user_headers):
    client.post(
        "/tickets",
        json={"title": "Charged twice", "description": "I was charged twice please refund me"},
        headers=user_headers,
    )
    body = client.get("/metrics").text
    assert "http_requests_total" in body
    assert "tickets_created_total" in body
