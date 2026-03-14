import os
import textwrap
from pathlib import Path
from unittest.mock import patch

from bd.config import resolve_config


class TestConfigResolution:
    """Config precedence: CLI flags > env vars > config file."""

    def test_cli_flags_take_precedence_over_everything(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(textwrap.dedent("""\
            [default]
            api_key = "from-file"
        """))
        with patch.dict(os.environ, {"BD_API_KEY": "from-env"}):
            cfg = resolve_config(
                api_key="from-cli",
                newsletter=None,
                profile="default",
                config_path=config_file,
            )
        assert cfg.api_key == "from-cli"

    def test_env_vars_take_precedence_over_config_file(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(textwrap.dedent("""\
            [default]
            api_key = "from-file"
        """))
        with patch.dict(os.environ, {"BD_API_KEY": "from-env"}):
            cfg = resolve_config(
                api_key=None,
                newsletter=None,
                profile="default",
                config_path=config_file,
            )
        assert cfg.api_key == "from-env"

    def test_config_file_used_when_no_flag_or_env(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(textwrap.dedent("""\
            [default]
            api_key = "from-file"
            newsletter = "nl-123"
        """))
        with patch.dict(os.environ, {}, clear=True):
            env_keys = ["BD_API_KEY", "BD_NEWSLETTER"]
            cleaned = {k: v for k, v in os.environ.items() if k not in env_keys}
            with patch.dict(os.environ, cleaned, clear=True):
                cfg = resolve_config(
                    api_key=None,
                    newsletter=None,
                    profile="default",
                    config_path=config_file,
                )
        assert cfg.api_key == "from-file"
        assert cfg.newsletter == "nl-123"

    def test_named_profile(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(textwrap.dedent("""\
            [default]
            api_key = "default-key"

            [nbbw]
            api_key = "nbbw-key"
            newsletter = "nbbw-newsletter"
        """))
        with patch.dict(os.environ, {}, clear=True):
            env_keys = ["BD_API_KEY", "BD_NEWSLETTER"]
            cleaned = {k: v for k, v in os.environ.items() if k not in env_keys}
            with patch.dict(os.environ, cleaned, clear=True):
                cfg = resolve_config(
                    api_key=None,
                    newsletter=None,
                    profile="nbbw",
                    config_path=config_file,
                )
        assert cfg.api_key == "nbbw-key"
        assert cfg.newsletter == "nbbw-newsletter"

    def test_missing_api_key_raises_error(self, tmp_path):
        config_file = tmp_path / "nonexistent.toml"
        import pytest
        with patch.dict(os.environ, {}, clear=True):
            env_keys = ["BD_API_KEY", "BD_NEWSLETTER"]
            cleaned = {k: v for k, v in os.environ.items() if k not in env_keys}
            with patch.dict(os.environ, cleaned, clear=True):
                with pytest.raises(SystemExit):
                    resolve_config(
                        api_key=None,
                        newsletter=None,
                        profile="default",
                        config_path=config_file,
                    )

    def test_newsletter_is_optional(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(textwrap.dedent("""\
            [default]
            api_key = "key-only"
        """))
        with patch.dict(os.environ, {}, clear=True):
            env_keys = ["BD_API_KEY", "BD_NEWSLETTER"]
            cleaned = {k: v for k, v in os.environ.items() if k not in env_keys}
            with patch.dict(os.environ, cleaned, clear=True):
                cfg = resolve_config(
                    api_key=None,
                    newsletter=None,
                    profile="default",
                    config_path=config_file,
                )
        assert cfg.api_key == "key-only"
        assert cfg.newsletter is None
