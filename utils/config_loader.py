from __future__ import annotations
from pathlib import Path
import yaml

class ConfigError(RuntimeError):
    pass

def load_config(path: str | Path = "./../config.yaml") -> dict:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Config file is not exists: {p.resolve()}")
    with p.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # 驗證至少要有 api_key
    if not (
        ("fileapi" in cfg and cfg["fileapi"].get("api_key")) or
        ("historyapi" in cfg and cfg["historyapi"].get("api_key"))
    ):
        raise ConfigError("Config file must contain fileapi.api_key or historyapi.api_key")

    return cfg

