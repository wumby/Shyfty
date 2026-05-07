import unittest

from pydantic import ValidationError

from app.core.config import Settings


class ProductionConfigValidationTests(unittest.TestCase):
    def test_rejects_sqlite_in_production(self):
        with self.assertRaises(ValidationError):
            Settings(
                app_env="production",
                database_url="sqlite:////tmp/shyfty.db",
                session_secret="prod-session-secret",
                jwt_secret="prod-jwt-secret",
                frontend_origin="https://web.example.com",
                api_public_url="https://api.example.com",
                allowed_hosts=["api.example.com"],
                admin_emails=["admin@example.com"],
            )

    def test_requires_frontend_origin_and_api_url_in_production(self):
        with self.assertRaises(ValidationError):
            Settings(
                app_env="production",
                database_url="postgresql+psycopg://u:p@db:5432/shyfty",
                session_secret="prod-session-secret",
                jwt_secret="prod-jwt-secret",
                allowed_hosts=["api.example.com"],
                admin_emails=["admin@example.com"],
            )

    def test_enables_cross_site_cookie_mode_for_split_domains(self):
        settings = Settings(
            app_env="production",
            database_url="postgresql+psycopg://u:p@db:5432/shyfty",
            session_secret="prod-session-secret",
            jwt_secret="prod-jwt-secret",
            frontend_origin="https://web.example.com",
            api_public_url="https://api.example.com",
            allowed_hosts=["api.example.com"],
            admin_emails=["admin@example.com"],
            auth_cookie_samesite="lax",
            csrf_cookie_samesite="lax",
        )
        self.assertTrue(settings.cross_site_frontend_backend)
        self.assertEqual(settings.auth_cookie_samesite_effective, "none")
        self.assertEqual(settings.csrf_cookie_samesite_effective, "none")

    def test_production_does_not_auto_run_ingest_by_default(self):
        settings = Settings(
            app_env="production",
            database_url="postgresql+psycopg://u:p@db:5432/shyfty",
            session_secret="prod-session-secret",
            jwt_secret="prod-jwt-secret",
            frontend_origin="https://web.example.com",
            api_public_url="https://api.example.com",
            allowed_hosts=["api.example.com"],
            admin_emails=["admin@example.com"],
        )
        self.assertFalse(settings.sync_run_on_startup)

    def test_requires_admin_emails_in_production(self):
        with self.assertRaises(ValidationError):
            Settings(
                app_env="production",
                database_url="postgresql+psycopg://u:p@db:5432/shyfty",
                session_secret="prod-session-secret",
                jwt_secret="prod-jwt-secret",
                frontend_origin="https://web.example.com",
                api_public_url="https://api.example.com",
                allowed_hosts=["api.example.com"],
            )


if __name__ == "__main__":
    unittest.main()
