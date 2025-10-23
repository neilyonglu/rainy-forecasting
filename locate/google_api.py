import googlemaps
import yaml

def load_google_client(config_path="./api_keys.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return googlemaps.Client(key=cfg["google"]["geocoding_api_key"])

gmaps = load_google_client()

def geocode_and_rain(address: str) -> tuple:
    """
    ### 地址轉經緯度
    #### para:
    - address: 地址或地名
    #### return:
    - (name, lat, lon)"""
    result = gmaps.geocode(address, region="TW", components={"country": "TW"})
    if not result:
        raise ValueError("找不到地點")
    loc = result[0]["geometry"]["location"]
    name = result[0]["formatted_address"]

    return name, loc["lat"], loc["lng"]
    

# Example usage:

# # Look up an address with reverse geocoding
# reverse_geocode_result = gmaps.reverse_geocode((40.714224, -73.961452))

# # Request directions via public transit
# now = datetime.now()
# directions_result = gmaps.directions("Sydney Town Hall",
#                                      "Parramatta, NSW",
#                                      mode="transit",
#                                      departure_time=now)

# # Validate an address with address validation
# addressvalidation_result =  gmaps.addressvalidation(['1600 Amphitheatre Pk'], 
#                                                     regionCode='US',
#                                                     locality='Mountain View', 
#                                                     enableUspsCass=True)

# Get an Address Descriptor of a location in the reverse geocoding response
# address_descriptor_result = gmaps.reverse_geocode((40.714224, -73.961452), enable_address_descriptor=True)

# print(reverse_geocode_result)
# print(directions_result)
# print(addressvalidation_result)
# print(address_descriptor_result)