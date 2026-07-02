"""Tests for configuration loader."""

from yukinoaaa.infrastructure.config.loader import Settings


def test_settings_default_values() -> None:
    """Verify default setting values are loaded securely."""
    config = Settings()
    assert config.get("app_env") == "development"
    assert config.is_production() is False
    assert config.is_debug() is False
    assert "sqlite" in config.get_database_url() or "memory" in config.get_database_url()


def test_settings_custom_values(monkeypatch) -> None:
    """Verify settings override via environment variables."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    config = Settings()
    assert config.is_production() is True
    assert config.is_debug() is True
    assert config.get("log_level") == "WARNING"
