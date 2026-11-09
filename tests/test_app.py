import pytest

from app import create_app
from extentions import db
from models import User


@pytest.fixture
def app():
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-session-secret",
            "JWT_SECRET_KEY": "test-jwt-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
        }
    )
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def register_web_user(client, username="janedoe", email="jane@example.com", password="correct-horse"):
    return client.post(
        "/register",
        data={
            "username": username,
            "email": email,
            "password": password,
            "name": "Jane Doe",
            "gender": "female",
        },
        follow_redirects=True,
    )


def create_api_user(client, email="jane@example.com", username="janedoe"):
    return client.post(
        "/api/v1/users/",
        json={
            "email": email,
            "username": username,
            "password": "correct-horse",
            "name": "Jane Doe",
            "gender": "female",
        },
    )


def test_app_factory_registers_web_and_api_routes(client):
    assert client.get("/").status_code == 200
    login_page = client.get("/")
    assert b"Sign in to your account" in login_page.data
    assert b'name="username"' in login_page.data
    assert b'name="password"' in login_page.data
    assert b'data-loading-text="Signing in..."' in login_page.data

    register_page = client.get("/register")
    assert register_page.status_code == 200
    assert b'name="name"' in register_page.data
    assert b'name="gender"' in register_page.data
    assert b'data-loading-text="Creating account..."' in register_page.data

    for asset in (
        "css/bootstrap.min.css",
        "css/now-ui-kit.min.css",
        "style.css",
        "auth.js",
        "img/auth-background.jpg",
    ):
        response = client.get(f"/static/{asset}")
        assert response.status_code == 200, asset

    response = client.get("/api/v1/users/")
    assert response.status_code == 200
    assert response.get_json() == []


def test_registration_hashes_password_and_web_login_checks_it(client, app):
    response = register_web_user(client)
    assert b"You have successfully registered!" in response.data

    with app.app_context():
        user = User.query.filter_by(username="janedoe").one()
        assert user.password_hash != "correct-horse"
        assert user.check_password("correct-horse")

    failed_login = client.post("/", data={"username": "janedoe", "password": "wrong"})
    assert b"Incorrect username or password" in failed_login.data

    login_response = client.post(
        "/", data={"username": "janedoe", "password": "correct-horse"}
    )
    assert login_response.status_code == 302
    assert login_response.headers["Location"].endswith("/home")


def test_registration_rejects_duplicate_and_invalid_values(client):
    register_web_user(client)

    duplicate = register_web_user(client, username="anotheruser", email="JANE@example.com")
    assert b"already exists" in duplicate.data

    invalid = client.post(
        "/register",
        data={
            "username": "x!",
            "email": "not-an-email",
            "password": "short",
            "name": "Jane Doe",
            "gender": "female",
        },
    )
    assert b"Username must be" in invalid.data


def test_profile_requires_login_and_never_renders_password(client):
    assert client.get("/profile").status_code == 302
    register_web_user(client)
    client.post("/", data={"username": "janedoe", "password": "correct-horse"})

    response = client.get("/profile")
    assert response.status_code == 200
    assert b"jane@example.com" in response.data
    assert b"correct-horse" not in response.data
    assert b"password_hash" not in response.data


@pytest.mark.parametrize("payload", [None, [], {}, {"email": "not-json-fields"}])
def test_api_user_creation_returns_400_for_malformed_or_missing_data(client, payload):
    response = client.post("/api/v1/users/", json=payload)
    assert response.status_code == 400
    assert response.is_json


def test_api_registration_login_and_jwt_profile(client):
    response = create_api_user(client)
    assert response.status_code == 201

    duplicate = create_api_user(client, email="JANE@example.com", username="otheruser")
    assert duplicate.status_code == 409

    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "JANE@example.com", "password": "correct-horse"},
    )
    assert login_response.status_code == 200
    token = login_response.get_json()["token"]

    profile = client.get(
        "/api/v1/users/profile", headers={"Authorization": f"Bearer {token}"}
    )
    assert profile.status_code == 200
    assert profile.get_json()["user"] == {
        "id": 1,
        "email": "jane@example.com",
        "username": "janedoe",
        "name": "Jane Doe",
        "gender": "female",
    }


def test_api_patch_rejects_unexpected_fields_and_updates_allowed_fields(client, app):
    create_api_user(client)
    login = client.post(
        "/api/v1/users/login",
        json={"email": "jane@example.com", "password": "correct-horse"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['token']}"}

    invalid = client.patch(
        "/api/v1/users/",
        json={"id": 1, "password_hash": "attacker-controlled"},
        headers=headers,
    )
    assert invalid.status_code == 400

    updated = client.patch(
        "/api/v1/users/", json={"id": 1, "name": "Jane Smith"}, headers=headers
    )
    assert updated.status_code == 200
    with app.app_context():
        assert db.session.get(User, 1).name == "Jane Smith"


def test_api_user_cannot_update_or_delete_another_account(client, app):
    create_api_user(client)
    second_user = client.post(
        "/api/v1/users/",
        json={
            "email": "john@example.com",
            "username": "johndoe",
            "password": "correct-horse",
            "name": "John Doe",
            "gender": "male",
        },
    )
    assert second_user.status_code == 201
    login = client.post(
        "/api/v1/users/login",
        json={"email": "jane@example.com", "password": "correct-horse"},
    )
    headers = {"Authorization": f"Bearer {login.get_json()['token']}"}

    update = client.patch(
        "/api/v1/users/", json={"id": 2, "name": "Changed"}, headers=headers
    )
    delete = client.delete("/api/v1/users/2", headers=headers)
    assert update.status_code == 403
    assert delete.status_code == 403

    with app.app_context():
        assert db.session.get(User, 2).name == "John Doe"
