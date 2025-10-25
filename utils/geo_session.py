# utils/geo_session.py
from __future__ import annotations
from typing import Optional, Tuple, Union

import streamlit as st
from streamlit_geolocation import streamlit_geolocation

# --- session keys ---
SESSION_LAT, SESSION_LON, SESSION_ACC = "user_lat", "user_lon", "user_acc"

# ---------- 基礎存取 ----------
def get_cached_location() -> Optional[Tuple[float, float, Optional[float]]]:
    lat = st.session_state.get(SESSION_LAT)
    lon = st.session_state.get(SESSION_LON)
    acc = st.session_state.get(SESSION_ACC)
    if lat is None or lon is None:
        return None
    return float(lat), float(lon), (float(acc) if acc is not None else None)

def set_location_to_session(
    lat: Union[int, float], lon: Union[int, float], acc_m: Optional[Union[int, float]] = None
) -> None:
    st.session_state[SESSION_LAT] = float(lat)
    st.session_state[SESSION_LON] = float(lon)
    if acc_m is not None:
        st.session_state[SESSION_ACC] = float(acc_m)

def clear_location_session() -> None:
    for k in (SESSION_LAT, SESSION_LON, SESSION_ACC):
        st.session_state.pop(k, None)

# ---------- 取得定位（按鈕） ----------
def fetch_precise_location() -> Optional[Tuple[float, float, Optional[float]]]:
    """
    顯示元件並呼叫瀏覽器 geolocation。
    尚未按按鈕或被拒絕 → 回傳 None；成功 → (lat, lon, acc_m) 並寫入 session。
    """
    payload = streamlit_geolocation()

    if not payload or payload.get("latitude") is None or payload.get("longitude") is None:
        return None

    try:
        lat = float(payload["latitude"])
        lon = float(payload["longitude"])
    except (TypeError, ValueError):
        return None

    acc = None
    if payload.get("accuracy") is not None:
        try:
            acc = float(payload["accuracy"])
        except (TypeError, ValueError):
            acc = None

    set_location_to_session(lat, lon, acc)
    return lat, lon, acc

# ---------- 一站式（先用快取，否則要求授權） ----------
def ensure_location(
    accuracy_threshold_m: Optional[float] = None,
    stop_when_pending: bool = True,
) -> Optional[Tuple[float, float, Optional[float]]]:
    """
    1) 先讀 session；2) 沒有就顯示 geolocation 元件。
    沒按按鈕時回 None（預設 st.stop 讓下方不渲染）。
    """
    cached = get_cached_location()
    if cached:
        lat, lon, acc = cached
        if accuracy_threshold_m and acc and acc > accuracy_threshold_m:
            st.warning(f"目前定位精度 ±{acc:.0f} m（高於門檻 {accuracy_threshold_m:.0f} m），建議到戶外或開啟精準定位後重試。")
        return cached

    st.caption("點下方按鈕授權定位（iOS 請開啟『精確位置』）。")
    got = fetch_precise_location()
    if got:
        lat, lon, acc = got
        if accuracy_threshold_m and acc and acc > accuracy_threshold_m:
            st.warning(f"目前定位精度 ±{acc:.0f} m（高於門檻 {accuracy_threshold_m:.0f} m）。")
        return got

    if stop_when_pending:
        st.stop()
    return None