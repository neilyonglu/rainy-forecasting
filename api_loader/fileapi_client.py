import re
import io
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple

import requests
import streamlit as st
from huggingface_hub import HfApi, hf_hub_url

FILEAPI_BASE = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi"

def _parse_obs_time_iso8601(s: str) -> datetime:
    """解析 ISO 8601 字串為 UTC datetime。"""
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _download_image_bytes(url: str, timeout: int = 20) -> bytes:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.content

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


def ensure_latest_to_hf_streaming(cfg: Dict[str, Any], max_age_minutes: int = 2, debug: bool = False) -> Optional[dict]:
    """
    更新邏輯（不分日期資料夾）：
      1. 從 HF 讀取現有 meta.json（若沒有 → 視為需更新）
      2. 比對 meta.json["obs_time_utc"] 是否超過 max_age_minutes
      3. 若需要更新 → 下載 CWA 最新各 dataset 的 PNG（bytes）並覆蓋上傳
         - PNG 路徑：CWA_dataset/radar_new_png/{dataset_id}.png
         - META 路徑：CWA_dataset/radar_new_png/meta.json
      4. 回傳狀態資訊
    """
    c = cfg["fileapi"]
    base_url = c.get("base_url", FILEAPI_BASE)
    api_key = st.secrets["CWA_API_KEY"]
    timeout = int(c.get("timeout", 20))

    datasets: List[str] = [
        ds["id"] if isinstance(ds, dict) else ds
        for ds in c["datasets"]
    ]
    if not datasets:
        raise RuntimeError("cfg['fileapi']['datasets'] 為空，請設定至少一個 dataset id")
    
    repo_id = st.secrets["HF_REPO_ID"]
    hf_token = st.secrets["HF_TOKEN"]
    api = HfApi(token=hf_token)
    prefix = "radar_new_png"

    # === 讀取 HF 既有 meta.json ===
    meta_url = hf_hub_url(repo_id=repo_id, filename=f"{prefix}/meta.json", repo_type="dataset")
    headers = {"authorization": f"Bearer {hf_token}"}
    need_update = True
    last_obs_time_str = None
    age_min = None

    try:
        r = requests.get(meta_url, headers=headers, timeout=timeout)
        if r.status_code == 200:
            meta = r.json()
            last_obs_time_str = meta.get("obs_time_utc")
            if last_obs_time_str:
                last_dt = _parse_obs_time_iso8601(last_obs_time_str)
                now_utc = datetime.now(timezone.utc)
                age = now_utc - last_dt
                age_min = round(age.total_seconds() / 60.0, 2)
                need_update = age > timedelta(minutes=max_age_minutes)
                if debug:
                    print(f"[HF-meta] last={last_dt} age(min)={age_min} need_update={need_update}")
        else:
            if debug:
                print(f"[HF-meta] 無現有 meta.json（status={r.status_code}），視為需更新")
    except Exception as e:
        if debug:
            print(f"[HF-meta] 無法讀取 meta.json：{e}")
        need_update = True

    # === 若時間在 10 分內，就不更新 ===
    if not need_update:
        return {
            "need_update": False,
            "obs_time_utc": last_obs_time_str,
            "age_minutes": age_min,
            "hf_path_prefix": prefix
        }

    # === 超過時 → 重新抓最新 CWA 圖片 ===
    ds0 = datasets[0]
    j0 = fetch_fileapi_json(base_url, api_key, ds0, timeout=timeout, debug=debug)
    items0 = parse_fileapi_image(j0)
    if not items0:
        if debug: print("[ensure_latest_to_hf_streaming] CWA 無資料")
        return None
    obs_time_str = items0[0].get("obsTime")
    obs_dt_utc = _parse_obs_time_iso8601(obs_time_str)

    urls_map, uploaded = {}, []
    for ds in datasets:
        j2 = fetch_fileapi_json(base_url, api_key, ds, timeout=timeout, debug=debug)
        items2 = parse_fileapi_image(j2)
        if not items2:
            if debug: print(f"[ensure_latest_to_hf_streaming] {ds} 無資料")
            continue
        url2 = items2[0].get("imageUrl")
        if not url2:
            continue
        try:
            img_bytes = _download_image_bytes(url2, timeout=timeout)
            api.upload_file(
                repo_id=repo_id,
                path_or_fileobj=io.BytesIO(img_bytes),
                path_in_repo=f"{prefix}/{ds}.png",
                repo_type="dataset"
            )
            uploaded.append(ds)
            urls_map[ds] = url2
            if debug: print(f"[ensure_latest_to_hf_streaming] uploaded {ds}.png")
        except Exception as e:
            if debug: print(f"上傳 {ds} 失敗：{e}")

    # === 上傳新的 meta.json ===
    new_meta = {
        "obs_time_utc": obs_dt_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "CWA FileAPI",
        "datasets": uploaded,
        "urls": urls_map,
    }
    meta_bytes = io.BytesIO(json.dumps(new_meta, ensure_ascii=False, indent=2).encode("utf-8"))
    api.upload_file(
        repo_id=repo_id,
        path_or_fileobj=meta_bytes,
        path_in_repo=f"{prefix}/meta.json",
        repo_type="dataset"
    )

    if debug:
        print(f"[ensure_latest_to_hf_streaming] 覆蓋更新完成 → obs={new_meta['obs_time_utc']}")

    return {
        "need_update": True,
        "obs_time_utc": new_meta["obs_time_utc"],
        "age_minutes": 0.0,
        "hf_path_prefix": prefix
    }