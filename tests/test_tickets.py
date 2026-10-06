BILLING_TICKET = {
    "title": "Charged twice",
    "description": "I was charged twice for my subscription this month please refund the extra payment",
}
TECH_TICKET = {
    "title": "Dashboard crash",
    "description": "The app crashes every time I open the dashboard and I get a blank screen",
}


def test_create_ticket_is_classified(client, user_headers):
    res = client.post("/tickets", json=BILLING_TICKET, headers=user_headers)
    assert res.status_code == 201
    body = res.json()
    assert body["category"] == "billing"
    assert body["status"] == "open"
    assert 0 < body["confidence"] <= 1


def test_create_requires_login(client):
    assert client.post("/tickets", json=BILLING_TICKET).status_code == 401


def test_validation_on_short_description(client, user_headers):
    res = client.post(
        "/tickets", json={"title": "Help me", "description": "short"}, headers=user_headers
    )
    assert res.status_code == 422


def test_user_only_sees_own_tickets(client, user_headers, other_user_headers):
    client.post("/tickets", json=BILLING_TICKET, headers=user_headers)
    client.post("/tickets", json=TECH_TICKET, headers=other_user_headers)

    mine = client.get("/tickets", headers=user_headers).json()
    assert mine["total"] == 1
    assert mine["items"][0]["title"] == "Charged twice"


def test_agent_sees_everything_and_can_filter(
    client, user_headers, other_user_headers, agent_headers
):
    client.post("/tickets", json=BILLING_TICKET, headers=user_headers)
    client.post("/tickets", json=TECH_TICKET, headers=other_user_headers)

    everything = client.get("/tickets", headers=agent_headers).json()
    assert everything["total"] == 2

    only_billing = client.get("/tickets?category=billing", headers=agent_headers).json()
    assert only_billing["total"] == 1
    assert only_billing["items"][0]["category"] == "billing"


def test_pagination(client, user_headers):
    for i in range(5):
        client.post(
            "/tickets",
            json={"title": f"Ticket number {i}", "description": BILLING_TICKET["description"]},
            headers=user_headers,
        )
    page = client.get("/tickets?page=2&size=2", headers=user_headers).json()
    assert page["total"] == 5
    assert len(page["items"]) == 2
    assert page["page"] == 2


def test_cannot_read_someone_elses_ticket(client, user_headers, other_user_headers):
    ticket_id = client.post("/tickets", json=BILLING_TICKET, headers=user_headers).json()["id"]
    assert client.get(f"/tickets/{ticket_id}", headers=other_user_headers).status_code == 404
    assert client.get(f"/tickets/{ticket_id}", headers=user_headers).status_code == 200


def test_user_cannot_update_ticket(client, user_headers):
    ticket_id = client.post("/tickets", json=BILLING_TICKET, headers=user_headers).json()["id"]
    res = client.patch(f"/tickets/{ticket_id}", json={"status": "closed"}, headers=user_headers)
    assert res.status_code == 403


def test_agent_can_update_and_assign(client, user_headers, agent_headers):
    ticket_id = client.post("/tickets", json=BILLING_TICKET, headers=user_headers).json()["id"]
    agent_id = client.get("/auth/me", headers=agent_headers).json()["id"]

    res = client.patch(
        f"/tickets/{ticket_id}",
        json={"status": "in_progress", "assigned_to": agent_id},
        headers=agent_headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "in_progress"
    assert res.json()["assigned_to"] == agent_id


def test_cannot_assign_to_a_normal_user(client, user_headers, agent_headers):
    ticket_id = client.post("/tickets", json=BILLING_TICKET, headers=user_headers).json()["id"]
    user_id = client.get("/auth/me", headers=user_headers).json()["id"]

    res = client.patch(
        f"/tickets/{ticket_id}", json={"assigned_to": user_id}, headers=agent_headers
    )
    assert res.status_code == 400


def test_stats_are_agent_only(client, user_headers, agent_headers):
    client.post("/tickets", json=BILLING_TICKET, headers=user_headers)

    assert client.get("/tickets/stats", headers=user_headers).status_code == 403

    stats = client.get("/tickets/stats", headers=agent_headers).json()
    assert stats["total"] == 1
    assert stats["by_category"]["billing"] == 1


def test_stats_cache_is_cleared_on_new_ticket(client, user_headers, agent_headers):
    client.post("/tickets", json=BILLING_TICKET, headers=user_headers)
    assert client.get("/tickets/stats", headers=agent_headers).json()["total"] == 1

    client.post("/tickets", json=TECH_TICKET, headers=user_headers)
    assert client.get("/tickets/stats", headers=agent_headers).json()["total"] == 2
