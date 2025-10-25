# --- plot_tool.py ---
from typing import Optional
from PIL import ImageDraw

def render_preview_pil(img, px: int, py: int, marker_radius_px: Optional[int] = None):
    """在完整雷達圖上畫紅點。"""
    out = img.copy()
    draw = ImageDraw.Draw(out)

    r = marker_radius_px or 2
    # 亮紅填滿 + 深紅描邊
    draw.ellipse(
        (px - r, py - r, px + r, py + r),
        fill=(255, 36, 36),
        outline=(220, 0, 0),
        width=2,
    )
    return out