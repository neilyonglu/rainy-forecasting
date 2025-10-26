# --- utils/plotly_viewer.py ---
import numpy as np
import plotly.express as px
import streamlit as st

def show_zoomable_photo_like_map(
    img_pil,
    center_px,
    center_py,
    px_per_km: float,
    init_km: int = 20,
):
    """以 st.map 風格顯示圖片，可拖曳/縮放；初始視窗=±init_km。"""
    img_arr = np.array(img_pil)
    h, w = img_arr.shape[:2]

    # 初始視窗（以 25 km 半徑 → 直徑 50 km 寬度）
    half_w = (init_km * 2) * px_per_km / 2.0
    half_h = half_w  # 鎖 1:1

    x0 = max(0, center_px - half_w)
    x1 = min(w - 1, center_px + half_w)
    y0 = max(0, center_py - half_h)
    y1 = min(h - 1, center_py + half_h)

    fig = px.imshow(img_arr)
    # 隱藏軸、鎖 1:1
    fig.update_xaxes(
        showticklabels=False,
        range=[x0, x1],
        constrain="domain",
    )
    fig.update_yaxes(
        showticklabels=False,
        range=[y1, y0],
        scaleanchor="x",
        scaleratio=1,
        constrain="domain",
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        dragmode="pan",
        uirevision="keep-range",
    )

    st.markdown(
        '<div class="photo-like-map"><div class="photo-like-map__toolbar"></div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        config=dict(
            displayModeBar=False,  # 視覺更像 st.map
            scrollZoom=True,       # 滾輪縮放
            doubleClick="reset",   # 雙擊回全圖
        ),
    )
    st.markdown('</div>', unsafe_allow_html=True)
