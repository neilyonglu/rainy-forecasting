from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
import requests
import pandas as pd

FILEAPI_BASE = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi"

def fetch_fileapi_json(base_url: str, api_key: str, dataset: str, timeout: int = 20, debug: bool = False) -> Dict[str, Any]:
    """取得單站雷達『最新一張』的 JSON（O-A0084-***）。"""
    url = f"{base_url}/{dataset}"
    params = {"Authorization": api_key, "downloadType": "WEB", "format": "JSON"}
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    j = resp.json()
    if debug:
        print(f"[fileapi-json] {dataset} -> {resp.url}")
        import json as _json
        print(_json.dumps(j, ensure_ascii=False)[:1000])
    return j


def parse_fileapi_image(j: Dict[str, Any]) -> List[dict]:
    """
    解析官方 JSON 結構：
      cwaopendata.dataset.DateTime
      cwaopendata.dataset.resource.ProductURL
    回傳：[{'obsTime','imageUrl','desc'}]
    """
    co = j.get("cwaopendata", {})
    ds = co.get("dataset", {}) if isinstance(co, dict) else {}
    res = ds.get("resource", {}) if isinstance(ds, dict) else {}
    url = res.get("ProductURL") or res.get("resourceURI") or res.get("resource_url")
    t = ds.get("DateTime") or co.get("sent")
    desc = res.get("resourceDesc")
    return ([{"obsTime": t, "imageUrl": url, "desc": desc}] if url else [])

def download_image(url: str, out_dir: Path, filename: str | None = None, timeout: int = 20) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    name = filename or (url.split("/")[-1] or "radar.png")
    p = out_dir / name
    r = requests.get(url, timeout=timeout); r.raise_for_status()
    p.write_bytes(r.content)
    return p

def run_fileapi(cfg: Dict[str, Any], debug: bool = False) -> None:
    c = cfg["fileapi"]
    base_url = c.get("base_url", "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi")
    api_key = c["api_key"]
    timeout = int(c.get("timeout", 20))
    datasets: List[str] = [
        ds["id"] if isinstance(ds, dict) else ds
        for ds in c["datasets"]
    ]
    save_csv = bool(c.get("save_csv", True))
    csv_path = Path(c.get("csv_path", "fileapi_radar_links.csv"))
    do_dl = bool(c.get("download_images", False))
    img_dir = Path(c.get("image_dir", "radar_png"))

    rows: List[dict] = []
    for ds in datasets:
        j = fetch_fileapi_json(base_url, api_key, ds, timeout=timeout, debug=debug)
        items = parse_fileapi_image(j)
        for it in items:
            print(f"{it.get('obsTime')}")
            out = {"dataset": ds, **it}
            if do_dl and it.get("imageUrl"):
                saved = download_image(it["imageUrl"], img_dir, filename=f"{ds}.png", timeout=timeout)
                out["localPath"] = str(saved)
            rows.append(out)


    if save_csv and rows:
        pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"[fileapi] saved {csv_path.resolve()}")
    elif not save_csv:
        print("[fileapi] skip saving CSV (save_csv=false)")


