def test_register_and_login(client):
    res = client.post(
        "/auth/register", json={"email": "Jane@Example.com", "password": "password123"}
    )
    assert res.status_code == 201
    assert res.json()["email"] == "jane@example.com"
    assert res.json()["role"] == "user"

    res = client.post(
        "/auth/login", data={"username": "jane@example.com", "password": "password123"}
    )
    assert res.status_code == 200
    assert res.json()["token_type"] == "bearer"


def test_duplicate_email_is_rejected(client):
    body = {"email": "jane@example.com", "password": "password123"}
    client.post("/auth/register", json=body)
    res = client.post("/auth/register", json=body)
    assert res.status_code == 409


def test_wrong_password(client):
    client.post("/auth/register", json={"email": "jane@example.com", "password": "password123"})
    res = client.post("/auth/login", data={"username": "jane@example.com", "password": "nope"})
    assert res.status_code == 401


def test_short_password_is_rejected(client):
    res = client.post("/auth/register", json={"email": "jane@example.com", "password": "short"})
    assert res.status_code == 422


def test_me_needs_a_token(client):
    assert client.get("/auth/me").status_code == 401
    bad = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert bad.status_code == 401


def test_me_returns_current_user(client, user_headers):
    res = client.get("/auth/me", headers=user_headers)
    assert res.status_code == 200
    assert res.json()["email"] == "user@example.com"


def test_agent_email_gets_agent_role(client, agent_headers):
    res = client.get("/auth/me", headers=agent_headers)
    assert res.json()["role"] == "agent"
