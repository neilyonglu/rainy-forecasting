import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime

from check_rain import check_rain
from locate.google_api import geocode_and_name
from utils.zoom_viewr import show_zoomable_photo_like_map

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


# =============================
# Pages
# =============================
if mode == 0:  # Home
    st.header(PAGES[mode])

    # 讀取 URL 上的 lat/lon，如果沒有就觸發瀏覽器定位（只會跑一次）
    qp = st.query_params  # Streamlit 1.30+ 新API；舊版可用 st.experimental_get_query_params()
    lat_q = qp.get("lat", None)
    lon_q = qp.get("lon", None)

    # 第一次進來沒有 lat/lon：注入 JS 來拿 geolocation，拿到後把 lat/lon 寫回網址並 reload
    if not lat_q or not lon_q:
        st.info("正在請求瀏覽器定位權限…若被阻擋請允許定位。")
        components.html(
            """
            <script>
            (function () {
            // 用『父視窗』的 URL，而不是 iframe 的
            const url = new URL(window.parent.location.href);

            // 若已經有 lat/lon，就不再觸發
            if (url.searchParams.get("lat") && url.searchParams.get("lon")) return;

            if (!navigator.geolocation) {
                url.searchParams.set("geo_error", "no_support");
                window.parent.location.replace(url.toString());
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (pos) => {
                const lat = pos.coords.latitude.toFixed(6);
                const lon = pos.coords.longitude.toFixed(6);
                url.searchParams.set("lat", lat);
                url.searchParams.set("lon", lon);
                // 這次重載的是『父視窗』（整個 app）
                window.parent.location.replace(url.toString());
                },
                (err) => {
                // 拒絕或逾時 → 回寫旗標到父視窗 URL 再重載
                url.searchParams.set("geo_denied", String(err.code || 1));
                window.parent.location.replace(url.toString());
                },
                { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }
            );
            })();
            </script>
            """,
            height=0,
        )
        # 呈現一個友善的 fallback 提示（第一次載入時會顯示，拿到定位後自動重載）
        st.stop()

    # 有 lat/lon 或使用者拒絕權限（有 geo_denied）
    lat = None
    lon = None
    try:
        if lat_q and lon_q:
            lat = float(lat_q if isinstance(lat_q, str) else lat_q[0])
            lon = float(lon_q if isinstance(lon_q, str) else lon_q[0])
    except Exception:
        lat = lon = None

    if lat is None or lon is None:
        # 走到這裡通常表示使用者拒絕定位或取值失敗
        st.warning("無法取得定位（可能是拒絕權限或瀏覽器不支援）。你可以改用「🔍 指定地址雨勢」頁面查詢。")
        # 提供一個快速手動輸入（不影響你原本「指定地址雨勢」頁）
        with st.form("manual_loc"):
            c1, c2 = st.columns(2)
            with c1:
                lat_in = st.text_input("緯度", placeholder="例如 25.033964")
            with c2:
                lon_in = st.text_input("經度", placeholder="例如 121.564468")
            go = st.form_submit_button("用這組座標查雨", type="primary")
        if go:
            try:
                lat = float(lat_in.strip())
                lon = float(lon_in.strip())
                # 把手動輸入也同步寫回網址，之後重整仍保留
                st.query_params.update({"lat": f"{lat:.6f}", "lon": f"{lon:.6f}"})
            except Exception:
                st.error("座標格式不正確。")
                st.stop()
        else:
            st.stop()

    # === 真正查雨（沿用你既有的 check_rain 與卡片視覺） ===
    with st.spinner("查詢你當前位置的雨勢…"):
        try:
            result = check_rain(lat, lon, return_image=True)
        except Exception as e:
            st.error(f"check_rain 失敗：{e}")
            result = None

    if not result:
        st.stop()

    # 主要資訊
    col1, col2 = st.columns(2)
    col1.metric("雨勢", result.get("desc", ""))
    rng = result.get("rng")
    col2.metric("mm/hr", f"{rng[0]}–{rng[1]}" if rng and rng[1] is not None else (f"{rng[0]}+" if rng else ""))

    # 影像（可拖曳縮放的雷達圖）
    if result.get("image") is not None:
        try:
            show_zoomable_photo_like_map(
                result["image"],
                center_px=result.get("px"),
                center_py=result.get("py"),
                px_per_km=result.get("px_per_km"),
                init_km=25,  # 你之前希望首頁預設 25 公里
            )
        except Exception as e:
            st.caption(f"影像檢視器顯示失敗：{e}")

    # 地圖標點
    df_map = pd.DataFrame({"lat": [result.get("lat", lat)], "lon": [result.get("lon", lon)]})
    st.map(df_map, zoom=9)
    st.caption(f"定位座標：{lat:.6f}, {lon:.6f}")


elif mode == 1:  # Address lookup
    st.header(PAGES[mode])

    with st.form("form_addr"):
        address = st.text_input("地址 / 地名", placeholder="例如: 台北101、安平古堡")
        submitted = st.form_submit_button("查詢雨勢", type="primary")

    if submitted:
        with st.spinner("地理編碼中..."):
            try:
                name, lat, lon = geocode_and_name(address)  # ← 你的函式，回傳 tuple
            except ValueError as e:
                st.warning("找不到此位置。換個關鍵詞試試？")
                st.error(f"Geocoding 失敗：{e}")
                name = lat = lon = None

        if name is not None:
            st.success(name)  # show address name

            with st.spinner("查詢雨勢中..."):
                try:
                    result = check_rain(lat, lon, return_image=True)
                except Exception as e:
                    st.error(f"check_rain 失敗：{e}")
                    result  = None

            if result:
                # 顯示主要資訊
                col1, col2 = st.columns(2)
                col1.metric("", result['desc'])
                col2.metric(
                    "mm/hr",
                    f"{result['rng'][0]}–{result['rng'][1]}"
                    if result['rng'][1] is not None
                    else f"{result['rng'][0]}+"
                )

                if result.get("image") is not None:
                    show_zoomable_photo_like_map(
                        result["image"],
                        center_px=result["px"],
                        center_py=result["py"],
                        px_per_km=result["px_per_km"],
                        init_km=25,
                    )

                # 顯示地圖標點
                df_map = pd.DataFrame({"lat": [result["lat"]], "lon": [result["lon"]]})
                st.map(df_map, zoom=9)


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