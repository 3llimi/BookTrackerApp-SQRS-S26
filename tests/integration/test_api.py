def test_openapi_schema_is_available(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "Book Tracker API"
    assert "/api/v1/auth/login" in data["paths"]
    assert "/api/v1/books/" in data["paths"]


def test_docs_page_is_available(client):
    response = client.get("/docs")
    assert response.status_code == 200


def test_unknown_route_returns_404(client):
    response = client.get("/api/v1/this-route-does-not-exist")
    assert response.status_code == 404
