from __future__ import annotations
from typing import Dict, Any, List, Tuple
from pathlib import Path
import json, requests, numpy as np, pandas as pd
import xml.etree.ElementTree as ET

def fetch_history_index_json(index_url: str, timeout: int = 30, debug: bool = False) -> Dict[str, Any]:
    """抓『時間清單 JSON』（含多個 time[].ProductURL）。"""
    r = requests.get(index_url, timeout=timeout)
    r.raise_for_status()
    j = r.json()
    if debug:
        print(f"[history-index] {index_url}")
        print(json.dumps(j, ensure_ascii=False)[:1000])
    return j

def parse_history_index(j: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    解析你提供的 index JSON：
      dataset.resources.resource.data.time: [{DateTime, UpdateTime, ProductURL}, ...]
    回傳：[{dt, url}, ...]
    """
    ds = j.get("dataset", {}) if isinstance(j, dict) else {}
    res = ds.get("resources", {}).get("resource", {}) if isinstance(ds, dict) else {}
    data = res.get("data", {}) if isinstance(res, dict) else {}
    times = data.get("time", []) if isinstance(data, dict) else []
    return [{"dt": t.get("DateTime"), "url": t.get("ProductURL")} for t in times if t.get("DateTime") and t.get("ProductURL")]

def fetch_grid_xml(product_url: str, timeout: int = 60) -> str:
    r = requests.get(product_url, timeout=timeout)
    r.raise_for_status()
    return r.text

def parse_grid_xml(xml_text: str) -> Dict[str, Any]:
    """
    解析 O-A0059-001 單筆 XML（格點 dBZ）。
    重要欄位：
      StartPointLongitude/Latitude, GridResolution, GridDimensionX/Y, DateTime
      contents/content -> 逗號分隔的科學記號 dBZ（-99/ -999 視為 NaN）
    """
    root = ET.fromstring(xml_text)
    ns_uri = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
    ns = {'c': ns_uri} if ns_uri else {}
    def F(node, path):
        el = node.find(path, ns) if ns else node.find(path)
        return (el.text or "").strip() if el is not None and el.text else None

    dataset = root.find('c:dataset', ns) if ns else root.find('dataset')
    dsinfo = dataset.find('c:datasetInfo', ns) if ns else dataset.find('datasetInfo')
    pset = dsinfo.find('c:parameterSet', ns) if ns else dsinfo.find('parameterSet')

    dt = F(pset, 'c:DateTime' if ns else 'DateTime')
    lon0 = float(F(pset, 'c:StartPointLongitude' if ns else 'StartPointLongitude'))
    lat0 = float(F(pset, 'c:StartPointLatitude'  if ns else 'StartPointLatitude'))
    dx = float(F(pset, 'c:GridResolution'        if ns else 'GridResolution'))
    nx = int(F(pset, 'c:GridDimensionX'          if ns else 'GridDimensionX'))
    ny = int(F(pset, 'c:GridDimensionY'          if ns else 'GridDimensionY'))

    contents = dataset.find('c:contents', ns) if ns else dataset.find('contents')
    s = F(contents, 'c:content' if ns else 'content')
    vals = np.array([float(x) for x in s.split(',') if x], dtype=np.float32)
    if vals.size != nx * ny:
        raise ValueError(f"grid size mismatch: got {vals.size} vs nx*ny={nx*ny}")

    arr = vals.reshape((ny, nx))
    arr = np.where((arr <= -990) | (arr == -99.0) | (arr == -999.0), np.nan, arr)

    # 經緯度網格（左下角起點；經度向右遞增、緯度向上遞增）
    j = np.arange(nx, dtype=np.float32); i = np.arange(ny, dtype=np.float32)
    lon_grid, lat_grid = np.meshgrid(lon0 + j * dx, lat0 + i * dx)

    return {"dt": dt, "nx": nx, "ny": ny, "dx_deg": dx, "lon0": lon0, "lat0": lat0,
            "dbz": arr, "lon_grid": lon_grid, "lat_grid": lat_grid}

def save_csv(meta: Dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    flat = meta["dbz"].astype(np.float32).ravel().tolist()
    df = pd.DataFrame([{
        "dt": meta["dt"], "nx": meta["nx"], "ny": meta["ny"], "dx_deg": meta["dx_deg"],
        "lon0": meta["lon0"], "lat0": meta["lat0"], "values": flat
    }])
    p = out_dir / f"radar_grid_{meta['dt'].replace(':','').replace('-','')}.csv"
    df.to_csv(p, index=False, encoding="utf-8-sig")
    return p


def run_historyapi(cfg: Dict[str, Any], debug: bool = False) -> None:
    c = cfg["historyapi"]
    index_url = c["index_url"]; timeout = int(c.get("timeout", 30))
    limit = c.get("limit"); out_dir = Path(c.get("out_dir", "radar_grids"))

    idx_json = fetch_history_index_json(index_url, timeout=timeout, debug=debug)
    items = parse_history_index(idx_json)
    if limit: items = items[:int(limit)]

    for k, it in enumerate(items, 1):
        print(f"[{k}/{len(items)}] {it['dt']} -> {it['url']}")
        xml_text = fetch_grid_xml(it["url"], timeout=timeout)
        meta = parse_grid_xml(xml_text)
        p = save_csv(meta, out_dir)
        print("  saved:", p)
