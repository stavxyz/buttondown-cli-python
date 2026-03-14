from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "bd" / "config.toml"


@dataclass
class Config:
    api_key: str
    newsletter: Optional[str] = None


def _load_profile(config_path: Path, profile: str) -> dict:
    """Load a named profile from the TOML config file."""
    if not config_path.exists():
        return {}
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
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
        print(
            "Error: No API key found. Provide --api-key, set BD_API_KEY, "
            f"or add api_key to [{profile}] in {config_path}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    return Config(api_key=resolved_api_key, newsletter=resolved_newsletter)
