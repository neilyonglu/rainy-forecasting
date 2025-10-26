import streamlit as st
import pandas as pd
from datetime import datetime

from locate.google_maps_client import geocode_and_name
from api_loader.fileapi_client import ensure_latest_to_hf_streaming
from utils.UI_view import render_rain_view
from utils.geo_session import ensure_location
from utils.config_loader import load_config

def sync_hf_once() -> dict | None:
    # 已同步過就直接回傳上次資訊
    if st.session_state.get("hf_synced_once"):
        return st.session_state.get("hf_sync_info")

    cfg = load_config("config.yaml")
    info = ensure_latest_to_hf_streaming(cfg, max_age_minutes=2, debug=False)

    # 記錄這次結果，整個 Session 期間不再重跑
    st.session_state["hf_synced_once"] = True
    st.session_state["hf_sync_info"] = info
    return info

# Page config
st.set_page_config(page_title="Rainy Forecasting", page_icon="🌧️", layout="wide")
st.title("🌧️ Rainy Forecasting")

# custom CSS
st.markdown(
    '<link rel="stylesheet" href="static/style.css">',
    unsafe_allow_html=True,
)


# =============================
# Navigation
# =============================
PAGES = {
    0: "🏠 首頁",
    1: "🔍 指定地址雨勢",
    2: "🧭 行徑路線雨勢",
    3: "⚙️ 設定",
    4: "ℹ️ 說明",
}
mode = st.radio("", list(PAGES.keys()), index=0, format_func=lambda x: PAGES[x], horizontal=True)


# --- App 啟動：只做一次，同一個使用者 Session 之後不再動 ---
with st.spinner("初始化：同步最新雷達圖（只在第一次載入）…"):
    info = sync_hf_once()
    if info:
        if info.get("need_update"):
            st.success(f"已更新至 HF（obs={info['obs_time_utc']}）")
        else:
            st.info(f"HF 已是最新（obs={info['obs_time_utc']}，{info['age_minutes']} 分鐘前資料）")


# =============================
# Pages
# =============================
if mode == 0:  # Home
    st.header(PAGES[mode])

    loc = ensure_location(accuracy_threshold_m=50)
    if loc:
        lat, lon, acc = loc
        label = f"目前位置（±{acc:.0f} m）" if acc is not None else "目前位置"
        render_rain_view(lat, lon, place_label=label)


elif mode == 1:  # Address lookup
    st.header(PAGES[mode])

    with st.form("form_addr"):
        address = st.text_input("地址 / 地名", placeholder="例如: 台北101、安平古堡")
        submitted = st.form_submit_button("查詢雨勢", type="primary")
    if submitted and address:
        name, lat, lon = geocode_and_name(address)
        render_rain_view(lat, lon, name)


elif mode == 2:  # Route lookup
    st.header(PAGES[mode])


elif mode == 3:  # Settings
    st.header(PAGES[mode])
    st.toggle("深色模式（跟隨系統）", value=True, disabled=True)
    st.selectbox("語言", ["繁體中文", "English"], index=0, disabled=True)
    st.selectbox("單位", ["mm/hr", "inch/hr"], index=0, disabled=True)
    st.selectbox("資料來源", ["CWA FileAPI", "歷史 API", "Hugging Face Dataset", "本地快取"], index=0)
    st.slider("地圖縮放預設", 5, 12, 8)
    st.segmented_control = st.radio("查詢預設模式", ["定位", "地址", "路線"], horizontal=True)
    st.caption("此頁為 UI 外觀，功能稍後接上。")


elif mode == 4:  # Info / About
    st.header(PAGES[mode])
    st.markdown(
        "- **定位查雨**：取得經緯度 → 查詢附近雷達 dBZ → 轉換為雨量與等級。"
        "- **地址查雨**：將地址轉經緯度再查詢。"
        "- **路線查雨**：從 A→B 生成路徑，沿路多點取樣估計降雨。"
        "- **資料檔**：上傳 radar 轉換/預測輸出，做點上取值與視覺化。"
    )
    st.info("目前為 UI 版型，尚未連接真實資料或演算法。")


# ---- Footer ----
st.divider()
st.caption("Rainy Forecasting UI prototype © 2025 Developed by Neil and ChatGPT")