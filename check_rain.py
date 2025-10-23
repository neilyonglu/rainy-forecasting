import os
import yaml
from datetime import datetime
from typing import Dict, Any

import numpy as np
from PIL import Image

from locate.location import latlon_to_pixel as _latlon_to_pixel
from utils.plot_tool import render_preview_pil as _render_preview_pil
from utils.select_radar import select_best_radar as _select_best_radar

def _dbz_to_rain_intensity(dbz: int):
    if dbz <= 0:
        return "無雨", (0, 0)
    elif dbz < 20:
        return "幾乎無雨", (0, 0.1)
    elif dbz < 30:
        return "小雨", (0.1, 2.5)
    elif dbz < 40:
        return "中雨", (2.5, 10)
    elif dbz < 50:
        return "大雨", (10, 50)
    elif dbz < 60:
        return "豪雨", (50, 100)
    else:
        return "極端強降雨", (100, None)

def _find_nearest_dbz(rgb: tuple) -> tuple:
    """
    ### 在 scale_table 裡找最接近的 RGB 對應 dbz
    #### para:
    - rgb: (R, G, B)
    #### return:
    - (dbz, (R, G, B))
    """
    # 讀 scale_table
    with open(r"./library/rain_intensity_scale.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    rgb = np.array(rgb)
    best_entry, min_dist = None, float("inf")

    for entry in data["rain_intensity_scale"]:
        entry_rgb = np.array(entry["rgb"])
        dist = np.linalg.norm(rgb - entry_rgb)
        if dist < min_dist:
            min_dist = dist
            best_entry = entry

    return best_entry["dbz"], tuple(best_entry["rgb"])


def check_rain(
    lat: float,
    lon: float,
    *,
    return_image: bool = True,
    cfg_path: str = "./config.yaml",
) -> Dict[str, Any]:

    # 0) 讀 config (取得雷達站經緯度)
    with open("./config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    datasets = cfg["fileapi"]["datasets"]
    image_dir = cfg["fileapi"]["image_dir"]

    # 1) 找最近雷達
    best_id = _select_best_radar(lat, lon, datasets)
    radar_info = next((d for d in datasets if d["id"] == best_id), None)

    # 2) 讀雷達 PNG
    img_path = os.path.join(image_dir, f"{best_id}.png")
    if not os.path.exists(img_path):
        raise FileNotFoundError(f"找不到雷達圖：{img_path}")
    img = Image.open(img_path).convert("RGB")
    
    # 3) 經緯度 → 像素
    radar_cfg = {
        "lat0": radar_info["lat"],  # 緯度
        "lon0": radar_info["lon"],  # 經度
        "h": 3600,                  # 影像高
        "w": 3600,                  # 影像寬
        "scale": 11.97              # pixel/km
    }
    px, py = _latlon_to_pixel(lat, lon, radar_cfg)

    # 確保在圖片範圍內
    h, w = img.size[:2]
    px = max(0, min(px, w - 1))
    py = max(0, min(py, h - 1))

    # 4) 取像素 → dBZ
    rgb = img.getpixel((px, py))
    dbz, _ = _find_nearest_dbz(rgb) # 找最近的 color

    # 5) 轉 mm/hr 與等級、中文描述
    desc, rng = _dbz_to_rain_intensity(dbz)

    # 6) 產預覽圖
    preview = _render_preview_pil(
        img=img,
        px=px,
        py=py,
    ) if return_image else None

    # 7) 回傳給前端
    return {
        "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds"),
        "lat": float(lat),
        "lon": float(lon),
        "best_id": best_id,
        "radar_name": radar_info.get("name", best_id),
        "desc": desc,
        "rng": rng,               # (min, max); max=None 表示以上
        "image": preview,         # PIL.Image 或 None
        "px": int(px),
        "py": int(py),
        "px_per_km": 11.97,         # 你的比例
        "image_w": img.size[0],
        "image_h": img.size[1],
    }


if __name__ == "__main__":
    # 北部三景點（樹林雷達）
    # check_rain(25.033964, 121.564468)  # 台北101
    # check_rain(25.206197, 121.693725)  # 野柳地質公園
    check_rain(25.109533, 121.844767)    # 九份老街

    # 中部三景點（南屯雷達）
    # check_rain(24.137426, 120.686017)  # 台中車站
    # check_rain(23.865374, 120.915944)  # 日月潭
    check_rain(24.054154, 121.161496)    # 清境農場

    # 南部三景點（林園雷達）
    # check_rain(22.612747, 120.300683)  # 高雄85大樓
    check_rain(21.945110, 120.799776)    # 墾丁大街
    # check_rain(23.000938, 120.160249)  # 台南安平古堡