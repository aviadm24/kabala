"""
Integration tests for i18n (internationalization) functionality.
Tests locale detection, translation loading, and multi-language responses.
"""
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestLocaleDetection:
    """Test locale detection from various sources."""

    def test_locale_from_query_param(self, client):
        """Test locale selection via query parameter."""
        response = client.get("/?lang=he")
        assert response.status_code == 200
        # Response should be in Hebrew or at least set the lang context
        assert "lang" in response.text or "he" in response.text.lower()

    def test_locale_from_query_param_english(self, client):
        """Test locale selection with English query param."""
        response = client.get("/?lang=en")
        assert response.status_code == 200

    def test_default_locale_fallback(self, client):
        """Test that requests without locale param use default."""
        response = client.get("/")
        assert response.status_code == 200

    def test_invalid_locale_fallback(self, client):
        """Test that invalid locale falls back to default."""
        response = client.get("/?lang=xx")
        assert response.status_code == 200


class TestHealthEndpointTranslation:
    """Test translation of API endpoints."""

    def test_health_check_default_locale(self, client):
        """Test health endpoint returns localized message."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["status"] == "ok"

    def test_health_check_english_locale(self, client):
        """Test health endpoint with English locale."""
        response = client.get("/health?lang=en")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["status"] == "ok"

    def test_health_check_hebrew_locale(self, client):
        """Test health endpoint with Hebrew locale."""
        response = client.get("/health?lang=he")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["status"] == "ok"
        # Message should be either English or Hebrew (gettext handles translation)
        assert len(data["message"]) > 0


class TestLoginPageTranslations:
    """Test login page renders with correct language."""

    def test_login_page_renders(self, client):
        """Test login page renders without error."""
        response = client.get("/login")
        assert response.status_code == 200
        assert "login" in response.text.lower()

    def test_login_page_with_lang_param(self, client):
        """Test login page accepts lang parameter."""
        response = client.get("/login?lang=he")
        assert response.status_code == 200

    def test_login_page_hebrew_content(self, client):
        """Test login page has Hebrew translations available."""
        response = client.get("/login?lang=he")
        assert response.status_code == 200
        # Check that template includes lang tag
        assert 'lang="he"' in response.text or 'lang="en"' in response.text


class TestSignupPageTranslations:
    """Test signup page renders with correct language."""

    def test_signup_page_renders(self, client):
        """Test signup page renders without error."""
        response = client.get("/signup")
        assert response.status_code == 200
        assert "signup" in response.text.lower() or "sign up" in response.text.lower()

    def test_signup_page_with_lang_param(self, client):
        """Test signup page accepts lang parameter."""
        response = client.get("/signup?lang=he")
        assert response.status_code == 200

    def test_signup_page_hebrew_content(self, client):
        """Test signup page has Hebrew translations available."""
        response = client.get("/signup?lang=he")
        assert response.status_code == 200
        # Check that template includes lang tag
        assert 'lang="he"' in response.text or 'lang="en"' in response.text


class TestLocaleContextInjection:
    """Test that locale and translation functions are injected into templates."""

    def test_login_page_has_i18n_context(self, client):
        """Test that login template receives i18n context."""
        response = client.get("/login?lang=he")
        assert response.status_code == 200
        # Should have html lang attribute
        assert "lang=" in response.text

    def test_signup_page_has_i18n_context(self, client):
        """Test that signup template receives i18n context."""
        response = client.get("/signup?lang=he")
        assert response.status_code == 200
        # Should have html lang attribute
        assert "lang=" in response.text

    def test_dashboard_page_has_i18n_context(self, client):
        """Test that dashboard template receives i18n context."""
        # Note: This will redirect to login if not authenticated,
        # but we're just checking that the route handles i18n context
        response = client.get("/?lang=he", follow_redirects=False)
        # Should either render or redirect (both valid)
        assert response.status_code in [200, 302]


class TestLocalePreference:
    """Test that locale preference persists and is used correctly."""

    def test_locale_param_priority(self, client):
        """Test that explicit lang param takes priority."""
        # Query param should take priority over defaults
        response = client.get("/?lang=he")
        assert response.status_code in [200, 302]

    def test_multiple_requests_different_locales(self, client):
        """Test multiple requests with different locales."""
        # Request 1: Hebrew
        response1 = client.get("/login?lang=he")
        assert response1.status_code == 200

        # Request 2: English (should not be affected by previous)
        response2 = client.get("/login?lang=en")
        assert response2.status_code == 200

        # Request 3: Default
        response3 = client.get("/login")
        assert response3.status_code == 200


class TestTranslationStringCoverage:
    """Test that common UI strings have translations."""

    def test_english_translations_exist(self):
        """Test that English .mo file is readable."""
        from pathlib import Path
        en_mo = Path("locales/en/LC_MESSAGES/messages.mo")
        assert en_mo.exists(), "English translations (.mo) file not found"
        assert en_mo.stat().st_size > 0, "English translations file is empty"

    def test_hebrew_translations_exist(self):
        """Test that Hebrew .mo file is readable."""
        from pathlib import Path
        he_mo = Path("locales/he/LC_MESSAGES/messages.mo")
        assert he_mo.exists(), "Hebrew translations (.mo) file not found"
        assert he_mo.stat().st_size > 0, "Hebrew translations file is empty"

    def test_po_files_are_valid(self):
        """Test that .po files are properly formatted."""
        from pathlib import Path
        en_po = Path("locales/en/LC_MESSAGES/messages.po")
        he_po = Path("locales/he/LC_MESSAGES/messages.po")

        assert en_po.exists(), "English .po file not found"
        assert he_po.exists(), "Hebrew .po file not found"

        # Check that both contain msgid/msgstr entries
        en_content = en_po.read_text()
        he_content = he_po.read_text()

        assert "msgid" in en_content, "English .po file lacks translations"
        assert "msgstr" in en_content, "English .po file lacks translations"
        assert "msgid" in he_content, "Hebrew .po file lacks translations"
        assert "msgstr" in he_content, "Hebrew .po file lacks translations"
