from locate.location import make_aeqd_transform

def calc_distance_km(lat: float, lon: float, radar_lat: float, radar_lon: float) -> float:
    """
    ### 使用 AEQD 投影計算雷達站到目標點距離 (km)
    #### para:
    - lat, lon: 目標點經緯度
    - radar_lat, radar_lon: 雷達站經緯度
    #### return:
    - distance_km: 距離 (km)
    """
    fwd, _ = make_aeqd_transform(radar_lat, radar_lon)
    E, N = fwd.transform(lon, lat)
    distance_km = (E**2 + N**2) ** 0.5 / 1000  # 轉成 km
    return distance_km

def select_best_radar(lat: float, lon: float, datasets: list) -> str:
    """
    ### 根據 AEQD 投影距離挑選最近雷達站
    #### para:
    - lat, lon: 目標點經緯度
    - datasets: 雷達站清單 [{'id','lat','lon',...},...]
    #### return:
    - dict: 最近雷達站資訊 + 'distance_km'
    """
    min_d, best_id = float("inf"), None
    for d in datasets:
        dist = calc_distance_km(lat, lon, d["lat"], d["lon"])
        if dist < min_d:
            min_d, best_id = dist, d["id"]
    return best_id
