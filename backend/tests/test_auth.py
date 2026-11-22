from tests.conftest import register_user


def test_register_login_and_profile(client) -> None:
    account = register_user(client)
    assert account["user"]["email"] == "jordan@example.com"
    assert account["access_token"]

    duplicate = client.post(
        "/api/auth/register",
        json={"full_name": "Other", "email": "JORDAN@example.com", "password": "Secure-test-pass-92"},
    )
    assert duplicate.status_code == 409

    login = client.post(
        "/api/auth/login",
        json={"email": "JORDAN@example.com", "password": "Secure-test-pass-92"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["full_name"] == "Jordan Rivera"

    updated = client.patch("/api/auth/me", headers=headers, json={"full_name": "Jordan R."})
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Jordan R."

    logout = client.post("/api/auth/logout", headers=headers)
    assert logout.status_code == 204


def test_auth_rejects_bad_credentials_and_protected_access(client) -> None:
    register_user(client)
    bad_login = client.post(
        "/api/auth/login",
        json={"email": "jordan@example.com", "password": "incorrect-password"},
    )
    assert bad_login.status_code == 401
    assert client.get("/api/resumes").status_code == 401