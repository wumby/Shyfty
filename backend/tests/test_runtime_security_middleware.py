import unittest

from fastapi.testclient import TestClient

from app.main import create_app


class RuntimeSecurityMiddlewareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_health_allows_configured_host(self) -> None:
        response = self.client.get("/api/health", headers={"Host": "localhost"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_rejects_disallowed_host(self) -> None:
        response = self.client.get("/api/health", headers={"Host": "evil.example.com"})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
