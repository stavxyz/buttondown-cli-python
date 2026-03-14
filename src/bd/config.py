from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "bd" / "config.toml"


class ConfigError(Exception):
    """Raised when configuration cannot be resolved."""


@dataclass
class Config:
    api_key: str
    newsletter: Optional[str] = None


def _load_profile(config_path: Path, profile: str) -> dict:
    """Load a named profile from the TOML config file."""
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(
            f"Could not parse config file {config_path}: {e}\n"
            "Fix the TOML syntax or delete the file to use CLI flags / env vars instead."
        )
    except OSError as e:
        raise ConfigError(f"Could not read config file {config_path}: {e}")

    if profile not in data and profile != "default":
        available = ", ".join(data.keys()) or "(none)"
        print(
            f"Warning: Profile [{profile}] not found in {config_path}. "
            f"Available profiles: {available}",
            file=sys.stderr,
        )
        return {}

    return data.get(profile, {})


def resolve_config(
    *,
    api_key: Optional[str],
    newsletter: Optional[str],
    profile: str = "default",
    config_path: Optional[Path] = None,
) -> Config:
    """Resolve config with precedence: CLI flags > env vars > config file."""
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    file_config = _load_profile(config_path, profile)

    resolved_api_key = (
        api_key
        or os.environ.get("BD_API_KEY")
        or file_config.get("api_key")
    )
    resolved_newsletter = (
        newsletter
        or os.environ.get("BD_NEWSLETTER")
        or file_config.get("newsletter")
    )

    if not resolved_api_key:
        raise ConfigError(
            "No API key found. Provide --api-key, set BD_API_KEY, "
            f"or add api_key to [{profile}] in {config_path}"
        )

    return Config(api_key=resolved_api_key, newsletter=resolved_newsletter)
