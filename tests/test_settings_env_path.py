"""Settings runtime path regressions; never read the operator's dotenv file."""
from pathlib import Path

from pydantic_settings.sources import DotEnvSettingsSource

from trading_copilot.config import Settings


def test_default_dotenv_is_repository_relative_from_any_cwd(tmp_path, monkeypatch):
    expected = Path(__file__).resolve().parents[1] / ".env"
    reads = []

    def fake_read(path, *args, **kwargs):
        reads.append(Path(path))
        return {"sec_user_agent": "offline-test@example.invalid"}

    # Prevent any real credential file from being read, even when root .env exists.
    monkeypatch.setattr(DotEnvSettingsSource, "_read_env_file", staticmethod(fake_read))
    monkeypatch.setattr(Path, "is_file", lambda self: self == expected)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    monkeypatch.chdir(tmp_path)
    assert Path(Settings.model_config["env_file"]) == expected
    assert Settings().sec_user_agent == "offline-test@example.invalid"
    assert reads == [expected]


def test_explicit_dotenv_and_disable_override_default(tmp_path, monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    monkeypatch.chdir(tmp_path)
    custom = tmp_path / "custom.env"
    custom.write_text("SEC_USER_AGENT=explicit@example.invalid\n")
    (tmp_path / ".env").write_text("SEC_USER_AGENT=wrong-cwd@example.invalid\n")
    assert Settings(_env_file=custom).sec_user_agent == "explicit@example.invalid"
    assert Settings(_env_file=None).sec_user_agent is None
    monkeypatch.setenv("SEC_USER_AGENT", "environment@example.invalid")
    assert Settings(_env_file=custom).sec_user_agent == "environment@example.invalid"
