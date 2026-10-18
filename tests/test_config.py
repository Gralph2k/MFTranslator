from pathlib import Path

from bot.config import load_settings

# %TEMP% в этой среде закрыт песочницей, поэтому фикстуру tmp_path не используем.
MISSING_ENV = Path(__file__).resolve().parent.parent / ".tmp" / "нет.env"


def test_proxy_is_read_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_PROXY", "socks5://127.0.0.1:1080")
    settings = load_settings(env_file=MISSING_ENV)
    assert settings.telegram_proxy == "socks5://127.0.0.1:1080"


def test_empty_proxy_is_none(monkeypatch):
    monkeypatch.setenv("TELEGRAM_PROXY", "   ")
    settings = load_settings(env_file=MISSING_ENV)
    assert settings.telegram_proxy is None


def test_empty_key_is_not_treated_as_present(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    settings = load_settings(env_file=MISSING_ENV)
    assert settings.has_llm is False
