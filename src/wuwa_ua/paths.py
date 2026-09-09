from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "wuwa-ua"
CONTROL_PORT = 47823


@dataclass(frozen=True)
class ControlEndpoint:
    kind: str
    path: Path | None = None
    host: str = "127.0.0.1"
    port: int = CONTROL_PORT


def _home(env: Mapping[str, str]) -> Path:
    return Path(env.get("HOME") or env.get("USERPROFILE") or ".")


def config_dir(platform: str | None = None, env: Mapping[str, str] | None = None) -> Path:
    platform = platform or sys.platform
    env = env if env is not None else os.environ
    if platform == "win32":
        roaming = env.get("APPDATA")
        if roaming:
            return Path(roaming) / APP_NAME
        return _home(env) / f".{APP_NAME}"
    base = env.get("XDG_CONFIG_HOME") or str(_home(env) / ".config")
    return Path(base) / APP_NAME


def data_dir(platform: str | None = None, env: Mapping[str, str] | None = None) -> Path:
    platform = platform or sys.platform
    env = env if env is not None else os.environ
    if platform == "win32":
        local = env.get("LOCALAPPDATA")
        if local:
            return Path(local) / APP_NAME
        return _home(env) / f".{APP_NAME}"
    base = env.get("XDG_DATA_HOME") or str(_home(env) / ".local/share")
    return Path(base) / APP_NAME


def control_endpoint(
    platform: str | None = None, env: Mapping[str, str] | None = None
) -> ControlEndpoint:
    platform = platform or sys.platform
    env = env if env is not None else os.environ
    if platform == "win32":
        return ControlEndpoint(kind="tcp")
    runtime = env.get("XDG_RUNTIME_DIR") or "/tmp"
    return ControlEndpoint(kind="unix", path=Path(runtime) / f"{APP_NAME}.sock")


CONFIG_PATH = config_dir() / "config.toml"
GLOSSARY_PATH = config_dir() / "glossary.tsv"
SPEAKERS_PATH = config_dir() / "speakers.tsv"
UNKNOWN_SPEAKERS_PATH = config_dir() / "speakers-unknown.tsv"
CACHE_PATH = data_dir() / "cache.sqlite"
HISTORY_PATH = data_dir() / "history.jsonl"
MODELS_PATH = data_dir() / "models"
