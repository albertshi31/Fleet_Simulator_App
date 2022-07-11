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
