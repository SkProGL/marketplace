import requests
import math

def get_coordinates(postcode):
    postcode=postcode.replace(" ","")
    url=f"https://api.postcodes.io/postcodes/{postcode}"

    try:
        response=requests.get(url)
        data=response.json()

        if data["status"]==200:
            result=data["result"]
            return result["latitude"],result["longitude"]
    except Exception as e:
        print(f"Geocoding error: {e}")
    
    return None, None

def calculate_distance(coord1,coord2):
    R=3959

    lat1,lon1=coord1
    lat2,lon2=coord2

    lat1,lon1,lat2,lon2=map(math.radians, [lat1,lon1,lat2,lon2])
    dlat=lat2-lat1
    dlon=lon2-lon1

    a=math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    c=2*math.atan(math.sqrt(a), math.sqrt(1-a))

    return R*c

def calculate_distance(lat1,lon1,lat2,lon2):
    R=3959

    lat1,lon1,lat2,lon2=map(math.radians, [lat1,lon1,lat2,lon2])
    dlat=lat2-lat1
    dlon=lon2-lon1

    a=math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    c=2*math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R*c