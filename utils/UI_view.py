# utils/UI_view.py
import streamlit as st
from check_rain import check_rain
from utils.map_zoom import show_zoomable_photo_like_map

def render_rain_view(lat: float, lon: float, place_label: str = "目前位置"):
    """呼叫 check_rain 並顯示結果畫面"""
    st.subheader(f"📍 {place_label}")
    with st.spinner("查詢雷達圖與降雨資料中…"):
        try:
            result = check_rain(lat, lon, return_image=True)
        except Exception as e:
            st.error(f"查雨失敗：{e}")
            return

    if not result:
        st.warning("未取得結果。")
        return

    col1, col2 = st.columns(2)
    col1.metric("", result["desc"])
    col2.metric(
        "mm/hr",
        f"{result['rng'][0]}–{result['rng'][1]}"
        if result['rng'][1] is not None
        else f"{result['rng'][0]}+",
    )

    if result.get("image") is not None:
        show_zoomable_photo_like_map(
            result["image"],
            center_px=result["px"],
            center_py=result["py"],
            px_per_km=result["px_per_km"],
            init_km=20,
        )

    # 地圖定位點
    df = {"lat": [result["lat"]], "lon": [result["lon"]]}
    st.map(df, zoom=9)
