from uuid import uuid4

from locust import HttpUser, between, task


class BookTrackerUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        email = f"locust-{uuid4().hex[:10]}@test.com"
        password = "password123"

        register_response = self.client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password},
            name="POST /api/v1/auth/register",
        )

        # Registration can be 201 for a fresh user. If it fails unexpectedly,
        # login will likely fail too, which is useful signal during load testing.
        assert register_response.status_code == 201

        login_response = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
            name="POST /api/v1/auth/login",
        )
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {token}"}

    @task(3)  # 60%
    def list_books(self):
        self.client.get(
            "/api/v1/books",
            headers=self.headers,
            name="GET /api/v1/books",
        )

    @task(1)  # 20%
    def create_book(self):
        suffix = uuid4().hex[:8]
        self.client.post(
            "/api/v1/books/",
            json={
                "title": f"Load Test Book {suffix}",
                "author": "Locust User",
                "isbn": f"locust-{suffix}",
                "genre": "Testing",
                "total_pages": 250,
            },
            headers=self.headers,
            name="POST /api/v1/books",
        )

    @task(1)  # 20%
    def search_books(self):
        self.client.get(
            "/api/v1/books?title=dune",
            headers=self.headers,
            name="GET /api/v1/books?title=...",
        )