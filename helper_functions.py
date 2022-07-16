import math
def xypixel_to_latlng(xpixel, ypixel):
    lat = 37.0 + 0.00722814*(ypixel + .5)
    lng = -97.5 + 0.00722814*(xpixel + .5)/math.cos(math.radians(lat))
    return lat, lng

def latlng_to_xypixel(lat, lng):
    xpixel = math.floor(138.348 * (lng + 97.5) * math.cos(math.radians(lat)))
    ypixel = math.floor(138.348 * (lat - 37.0))
    return xpixel, ypixel


from geojson import LineString, GeometryCollection

def create_pixel_grid(north_lat, south_lat, east_lng, west_lng):

    biggest_xpixel, biggest_ypixel = latlng_to_xypixel(north_lat, east_lng)
    smallest_xpixel, smallest_ypixel = latlng_to_xypixel(south_lat, west_lng)

    lst_xpixels = range(smallest_xpixel, biggest_xpixel+1)
    lst_ypixels = range(smallest_ypixel, biggest_ypixel+1)

    # Calculate pixel endpoints at the top of the screen
    lst_top_endpoints = []
    for i, j in zip(lst_xpixels, [biggest_ypixel]*len(lst_xpixels)):
        latitude = 37.0 + 0.00722814*(j)
        longitude = -97.5 + 0.00722814*(i)/math.cos(math.radians(latitude))
        lst_top_endpoints.append((longitude, latitude))

    # Calculate pixel endpoints at the bottom of the screen
    lst_bot_endpoints = []
    for i, j in zip(lst_xpixels, [smallest_ypixel]*len(lst_xpixels)):
        latitude = 37.0 + 0.00722814*(j)
        longitude = -97.5 + 0.00722814*(i)/math.cos(math.radians(latitude))
        lst_bot_endpoints.append((longitude, latitude))

    # Connect top pixel endpoints with those at the bottom
    top_bot_linestrings = []
    for pair in zip(lst_top_endpoints, lst_bot_endpoints):
        top_bot_linestrings.append(LineString(list(pair)))

    # Calculate pixel endpoints on the left side of the screen
    lst_left_endpoints = []
    for j, i in zip(lst_ypixels, [smallest_xpixel]*len(lst_ypixels)):
        latitude = 37.0 + 0.00722814*(j)
        longitude = -97.5 + 0.00722814*(i)/math.cos(math.radians(latitude))
        lst_left_endpoints.append((longitude, latitude))

    # Calculate pixel endpoints on the right side of the screen
    lst_right_endpoints = []
    for j, i in zip(lst_ypixels, [biggest_xpixel]*len(lst_ypixels)):
        latitude = 37.0 + 0.00722814*(j)
        longitude = -97.5 + 0.00722814*(i)/math.cos(math.radians(latitude))
        lst_right_endpoints.append((longitude, latitude))

    # Connect left pixel endpoints with those at the right
    left_right_endpoints = []
    for pair in zip(lst_left_endpoints, lst_right_endpoints):
        left_right_endpoints.append(LineString(list(pair)))

    # Create GeometryCollection from top-bot and left-right linestrings
    all_linestrings = []
    all_linestrings.extend(top_bot_linestrings)
    all_linestrings.extend(left_right_endpoints)
    geometry_collection = GeometryCollection(all_linestrings)

    return geometry_collection

from shapely.geometry import Point, MultiPolygon, Polygon
import requests
def get_locations_precalculated_kiosks(north_lat, south_lat, east_lng, west_lng, feature_geojson_url_path, person_trip_lst_latlngs):
    smallest_xpixel, biggest_ypixel = latlng_to_xypixel(north_lat, west_lng)
    biggest_xpixel, smallest_ypixel = latlng_to_xypixel(south_lat, east_lng)

    lst_xpixels = range(smallest_xpixel, biggest_xpixel+1)
    lst_ypixels = range(smallest_ypixel, biggest_ypixel+1)

    lst_kiosk_pixels = []
    for xpixel in lst_xpixels:
        lst_kiosk_pixels.extend(list(zip([xpixel]*len(lst_ypixels), lst_ypixels)))

    #lst_pixel_boxes = []
    lst_pixel_centroids = []
    for i, j in lst_kiosk_pixels:
        lat, lng = xypixel_to_latlng(i, j)
        p1 = Point((lng, lat))
        lst_pixel_centroids.append(p1)
        # latitude_min = 37.0 + 0.00722814*(j)
        # longitude_min = -97.5 + 0.00722814*(i)/math.cos(math.radians(latitude_min))
        # latitude_max = 37.0 + 0.00722814*(j+1)
        # longitude_max = -97.5 + 0.00722814*(i+1)/math.cos(math.radians(latitude_max))
        #
        # p1 = Polygon([(longitude_min, latitude_min), (longitude_max, latitude_min), (longitude_max, latitude_max), (longitude_min, latitude_max)])
        # lst_pixel_boxes.append((p1, (i,j)))

    count_per_pixel = {}
    for lat, lng in person_trip_lst_latlngs:
        xpixel, ypixel = latlng_to_xypixel(lat, lng)
        if (xpixel, ypixel) in count_per_pixel:
            count_per_pixel[(xpixel, ypixel)] += 1
        else:
            count_per_pixel[(xpixel, ypixel)] = 1

    r = requests.get('https://raw.githubusercontent.com/whosonfirst-data/whosonfirst-data-admin-us/master/data/' + feature_geojson_url_path)
    geometry_data = r.json()['geometry']
    if geometry_data["type"] == "Polygon":
        p2 = Polygon(geometry_data["coordinates"][0])
    elif geometry_data["type"] == "MultiPolygon":
        p2 = MultiPolygon(geometry_data["coordinates"])
    else:
        raise Exception("Polical Boundaries aren't polygons nor multipolygons")

    result_lst_marker_latlngs = []
    for point in lst_pixel_centroids:
        if p2.contains(point) and (latlng_to_xypixel(point.y, point.x)) in count_per_pixel:
            result_lst_marker_latlngs.append((point.y, point.x))

    return result_lst_marker_latlngs
