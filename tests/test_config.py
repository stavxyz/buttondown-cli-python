import os
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from bd.config import ConfigError, resolve_config

BD_ENV_KEYS = ("BD_API_KEY", "BD_NEWSLETTER")


@pytest.fixture()
def clean_bd_env():
    """Ensure BD_API_KEY and BD_NEWSLETTER are not in the environment."""
    cleaned = {k: v for k, v in os.environ.items() if k not in BD_ENV_KEYS}
    with patch.dict(os.environ, cleaned, clear=True):
        yield


@pytest.fixture()
def config_file(tmp_path):
    """Return a helper that writes a TOML config file and returns its path."""
    path = tmp_path / "config.toml"

    def _write(content: str) -> Path:
        path.write_text(textwrap.dedent(content))
        return path

    return _write


class TestConfigResolution:
    """Config precedence: CLI flags > env vars > config file."""

    def test_cli_flags_take_precedence_over_everything(self, config_file):
        path = config_file("""\
            [default]
            api_key = "from-file"
        """)
        with patch.dict(os.environ, {"BD_API_KEY": "from-env"}):
            cfg = resolve_config(
                api_key="from-cli",
                newsletter=None,
                config_path=path,
            )
        assert cfg.api_key == "from-cli"

    def test_env_vars_take_precedence_over_config_file(self, config_file):
        path = config_file("""\
            [default]
            api_key = "from-file"
        """)
        with patch.dict(os.environ, {"BD_API_KEY": "from-env"}):
            cfg = resolve_config(
                api_key=None,
                newsletter=None,
                config_path=path,
            )
        assert cfg.api_key == "from-env"

    def test_config_file_used_when_no_flag_or_env(self, clean_bd_env, config_file):
        path = config_file("""\
            [default]
            api_key = "from-file"
            newsletter = "nl-123"
        """)
        cfg = resolve_config(
            api_key=None,
            newsletter=None,
            config_path=path,
        )
        assert cfg.api_key == "from-file"
        assert cfg.newsletter == "nl-123"

    def test_named_profile(self, clean_bd_env, config_file):
        path = config_file("""\
            [default]
            api_key = "default-key"

            [nbbw]
            api_key = "nbbw-key"
            newsletter = "nbbw-newsletter"
        """)
        cfg = resolve_config(
            api_key=None,
            newsletter=None,
            profile="nbbw",
            config_path=path,
        )
        assert cfg.api_key == "nbbw-key"
        assert cfg.newsletter == "nbbw-newsletter"

    def test_missing_api_key_raises_config_error(self, clean_bd_env, tmp_path):
        config_path = tmp_path / "nonexistent.toml"
        with pytest.raises(ConfigError, match="No API key found"):
            resolve_config(
                api_key=None,
                newsletter=None,
                config_path=config_path,
            )

    def test_invalid_toml_raises_config_error(self, clean_bd_env, config_file):
        path = config_file("not valid toml {{{{")
        with pytest.raises(ConfigError, match="Could not parse"):
            resolve_config(api_key=None, newsletter=None, config_path=path)

    def test_missing_profile_warns(self, clean_bd_env, config_file, capsys):
        path = config_file("""\
            [production]
            api_key = "prod-key"
        """)
        with pytest.raises(ConfigError, match="No API key found"):
            resolve_config(
                api_key=None,
                newsletter=None,
                profile="staging",
                config_path=path,
            )
        assert "Profile [staging] not found" in capsys.readouterr().err

    def test_newsletter_is_optional(self, clean_bd_env, config_file):
        path = config_file("""\
            [default]
            api_key = "key-only"
        """)
        cfg = resolve_config(
            api_key=None,
            newsletter=None,
            config_path=path,
        )
        assert cfg.api_key == "key-only"
        assert cfg.newsletter is None
