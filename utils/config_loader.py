# utils/config_loader.py
from __future__ import annotations
from pathlib import Path
import yaml

class ConfigError(RuntimeError):
    pass

def load_config(path: str | Path = "config.yaml") -> dict:
    """
    載入 YAML 設定。
    - 不再強制要求 fileapi.api_key / historyapi.api_key
    - 僅檢查：
        1) 存在 fileapi 區塊
        2) 存在 fileapi.datasets
    """
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Config file does not exist: {p.resolve()}")

    with p.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # ---- 必備區塊：fileapi ----
    if "fileapi" not in cfg or not isinstance(cfg["fileapi"], dict):
        raise ConfigError("Config must contain 'fileapi' section")

    # ---- 必備欄位：datasets（list）----
    fa = cfg["fileapi"]
    if "datasets" not in fa or not fa["datasets"]:
        raise ConfigError("Config must set 'fileapi.datasets' (list of dataset ids)")

    # 可接受兩種寫法：["O-A0084-001", ...] 或 [{"id": "O-A0084-001"}, ...]
    ds_list = fa["datasets"]
    if not isinstance(ds_list, list):
        raise ConfigError("'fileapi.datasets' must be a list")
    # 不修改原始型別，只做基本檢查
    for i, ds in enumerate(ds_list):
        if isinstance(ds, dict):
            if "id" not in ds:
                raise ConfigError(f"'fileapi.datasets[{i}]' dict must contain 'id'")
        elif not isinstance(ds, str):
            raise ConfigError(f"'fileapi.datasets[{i}]' must be str or dict with 'id'")

    # 其餘欄位皆為選填（例如 api_key 可為空字串；實際會用 st.secrets）
    return cfg