from functools import lru_cache
from pyproj import CRS, Transformer

@lru_cache(maxsize=None)
def make_aeqd_transform(lat0: float, lon0: float) -> tuple:
    """
    ### 建立 AEQD 投影轉換器
    #### para:
    - lat0, lon0: 投影中心經緯度
    #### return:
    - (fwd, inv): Transformer (forward, inverse)
    """
    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +datum=WGS84 +units=m +no_defs"
    )
    wgs84 = CRS.from_epsg(4326)
    fwd = Transformer.from_crs(wgs84, aeqd, always_xy=True)   # (lon,lat) -> (E,N)
    inv = Transformer.from_crs(aeqd, wgs84, always_xy=True)   # (E,N) -> (lon,lat)

    return fwd, inv

def latlon_to_pixel(lat: float, lon: float, radar_cfg) -> tuple:
    """
    ### 經緯度轉像素座標
    #### para:
    - lat, lon: 經緯度
    - radar_cfg: 雷達站設定 (lat0, lon0, h, w, scale)
    #### return:
    - (x, y): 像素座標
    """
    _fwd, _inv = make_aeqd_transform(radar_cfg["lat0"], radar_cfg["lon0"])
    
    # AEQD: 距雷達中心的當地平面座標 (公尺)
    E, N = _fwd.transform(lon, lat)
    km_per_m = 1.0 / 1000.0
    x0 = radar_cfg.get("cx", radar_cfg["w"] / 2)
    y0 = radar_cfg.get("cy", radar_cfg["h"] / 2)
    x = x0 + (E * km_per_m) * radar_cfg["scale"]
    y = y0 - (N * km_per_m) * radar_cfg["scale"]

    return int(round(x)), int(round(y))


