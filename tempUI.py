from check_rain import check_rain
from locate.google_api import geocode_and_rain


# ========================================
# 1. 當前位置下雨資訊
# ========================================
def rain_at_current_location(lat: float, lon: float):
    """輸入當前經緯度 → 查詢降雨資訊"""
    # try:
    #     info = gmaps.reverse_geocode((lat, lon))
    #     if not info:
    #         print("⚠️ 無法找到對應地址")
    #         return
    #     address = info[0]["formatted_address"]
    #     print(f"\n📍 當前位置：{address}")
    #     check_rain(lat, lon)
    # except Exception as e:
    #     print(f"❌ 查詢失敗：{e}")
    return


# ========================================
# 2. 指定地點下雨資訊
# ========================================
def rain_at_place(address: str) -> None:
    """
    ### 輸入地名或地址 → 查詢降雨資訊
    #### para:
    - address: 地址或地名"""
    try:
        name, lat, lon = geocode_and_rain(address)
        desc, rng = check_rain(lat, lon, zoom_km=25)
        if name:
            print(f"\n📍 地點：{name})")
            print(f"{desc}, 雨量範圍約 {rng} mm/hr")
    except Exception as e:
        print(f"❌ 查詢失敗：{e}")


# ========================================
# ③ A→B 行經路線下雨資訊
# ========================================
def rain_along_route(origin: str, destination: str, mode="driving"):
    """
    查詢從 A 到 B 沿途路線的降雨資訊
    mode 可選：'driving', 'walking', 'bicycling', 'transit'
    """
    # try:
    #     directions = gmaps.directions(origin, destination, mode=mode, departure_time=datetime.now())
    #     if not directions:
    #         print("⚠️ 無法取得路線資訊")
    #         return

    #     steps = directions[0]["legs"][0]["steps"]
    #     print(f"\n🚗 從 {origin} → {destination}")
    #     print(f"共 {len(steps)} 段路線，逐段檢查降雨：")

    #     for i, step in enumerate(steps):
    #         end_lat = step["end_location"]["lat"]
    #         end_lon = step["end_location"]["lng"]
    #         dist = step["distance"]["text"]
    #         print(f"\n  ➜ 第 {i+1} 段 ({dist})")
    #         check_rain(end_lat, end_lon, zoom_km=20)

    # except Exception as e:
    #     print(f"❌ 路線查詢失敗：{e}")
    return


if __name__ == "__main__":

    # 1. 查目前位置（輸入經緯度）
    # TODO: 自動取得當前位置
    # lat, lon = 25.033964, 121.564468  # 台北101
    # check_rain(lat, lon, zoom_km=25)

    # 2. 查指定地點
    rain_at_place("台北101")

    # TODO
    # 3. 查 A→B 路線
    # rain_along_route("台北車站", "九份老街", mode="driving")
