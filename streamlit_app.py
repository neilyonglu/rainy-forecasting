import streamlit as st
import pandas as pd
from datetime import datetime

from locate.google_maps_client import geocode_and_name
from api_loader.fileapi_client import ensure_latest_to_hf_streaming
from utils.UI_view import render_rain_view
from utils.geo_session import ensure_location
from utils.config_loader import load_config

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

# -----------------------------
# Mock helpers (only UI demo)
# -----------------------------
def mock_rain_payload(lat=25.00395201092895, lon=121.4007087696093):
    return {
        "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds"),
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "nearest_radar": "樹林雷達",
        "dbz": 33.0,
        "rain_mmph": 8.5,
        "level": "測試",
    }

# Simple reusable cards
def show_result_card(data: dict):
    with st.container(border=True):
        st.markdown(f"**時間**：{data['timestamp_utc']}  ")
        st.markdown(f"**座標**：{data['lat']}, {data['lon']}  ")
        st.markdown(f"**最近雷達**：{data['nearest_radar']}  ")
        col1, col2, col3 = st.columns(3)
        col1.metric("dBZ", f"{data['dbz']:.1f}")
        col2.metric("mm/hr", f"{data['rain_mmph']:.2f}")
        col3.metric("分類", data['level'])
        # 地圖（以單點 DataFrame 呈現）
        df_map = pd.DataFrame({"lat": [data["lat"]], "lon": [data["lon"]]})
        st.map(df_map, zoom=8)


# ---- 啟動時進行 CWA → HF 的 2 分鐘新鮮度檢查 ----
with st.spinner("同步最新雷達圖（如需）…"):
    cfg = load_config("config.yaml")
    sync_info = ensure_latest_to_hf_streaming(cfg, max_age_minutes=10, debug=False)
    if sync_info:
        if sync_info.get("need_update"):
            st.success(f"已更新HF：{sync_info['obs_time_utc']}")
        else:
            st.info(f"已是最新（obs={sync_info['obs_time_utc']}）")


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
    with st.form("form_route"):
        col1, col2 = st.columns(2)
        with col1:
            origin = st.text_input("起點", value="台北車站")
        with col2:
            destination = st.text_input("終點", value="九份老街")
        sample_n = st.slider("沿路取樣點數", 3, 30, 8)
        travel_mode = st.selectbox("模式", ["driving", "transit", "walking", "bicycling"], index=0)
        submitted = st.form_submit_button("規劃 → 預覽 UI", type="primary")
    if submitted:
        st.success(f"示意：從 {origin} → {destination}（{travel_mode}，取樣 {sample_n} 點）")
        # 產生假資料卡片
        for i in range(sample_n):
            lat = 25.03 - i * 0.01
            lon = 121.56 + i * 0.01
            show_result_card(mock_rain_payload(lat, lon))


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