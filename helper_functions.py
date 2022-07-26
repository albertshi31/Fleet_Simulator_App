import math
def xypixel_to_latlng(xpixel, ypixel):
    lat = 37.0 + 0.00722814*(ypixel + .5)
    lng = -97.5 + 0.00722814*(xpixel + .5)/math.cos(math.radians(lat))
    return lat, lng

def latlng_to_xypixel(lat, lng):
    xpixel = math.floor(138.348 * (lng + 97.5) * math.cos(math.radians(lat)))
    ypixel = math.floor(138.348 * (lat - 37.0))
    return xpixel, ypixel


from geojson import Polygon, Feature, FeatureCollection

def create_pixel_grid(north_lat, south_lat, east_lng, west_lng):

    biggest_xpixel, smallest_ypixel = latlng_to_xypixel(south_lat, east_lng)
    smallest_xpixel, biggest_ypixel = latlng_to_xypixel(north_lat, west_lng)

    lst_xpixels = range(smallest_xpixel, biggest_xpixel+1)
    lst_ypixels = range(smallest_ypixel, biggest_ypixel+1)

    lst_pixel_polygons = []
    # Create Polygon objects for each pixel, going row by row
    for i in lst_xpixels:
        for j in lst_ypixels:
            bottom_left_lat = 37.0 + 0.00722814*(j)
            bottom_left_lng = -97.5 + 0.00722814*(i)/math.cos(math.radians(bottom_left_lat))
            bottom_left = (bottom_left_lng, bottom_left_lat)

            bottom_right_lat = 37.0 + 0.00722814*(j)
            bottom_right_lng = -97.5 + 0.00722814*(i+1)/math.cos(math.radians(bottom_right_lat))
            bottom_right = (bottom_right_lng, bottom_right_lat)

            top_right_lat = 37.0 + 0.00722814*(j+1)
            top_right_lng = -97.5 + 0.00722814*(i+1)/math.cos(math.radians(top_right_lat))
            top_right = (top_right_lng, top_right_lat)

            top_left_lat = 37.0 + 0.00722814*(j+1)
            top_left_lng = -97.5 + 0.00722814*(i)/math.cos(math.radians(top_left_lat))
            top_left = (top_left_lng, top_left_lat)

            xypixel = Polygon([bottom_left, bottom_right, top_right, top_left])
            lst_pixel_polygons.append((xypixel, i, j))

    lst_features = []
    for pixel_polygon, i, j in lst_pixel_polygons:
        new_feature = Feature(geometry=pixel_polygon, properties={"x_coord": i, "y_coord": j})
        lst_features.append(new_feature)
    feature_collection = FeatureCollection(lst_features)

    # for i, j in zip(lst_xpixels, [biggest_ypixel]*len(lst_xpixels)):
    #
    # # Calculate pixel endpoints at the top of the screen
    # lst_top_endpoints = []
    # for i, j in zip(lst_xpixels, [biggest_ypixel]*len(lst_xpixels)):
    #     latitude = 37.0 + 0.00722814*(j)
    #     longitude = -97.5 + 0.00722814*(i)/math.cos(math.radians(latitude))
    #     lst_top_endpoints.append((longitude, latitude))
    #
    # # Calculate pixel endpoints at the bottom of the screen
    # lst_bot_endpoints = []
    # for i, j in zip(lst_xpixels, [smallest_ypixel]*len(lst_xpixels)):
    #     latitude = 37.0 + 0.00722814*(j)
    #     longitude = -97.5 + 0.00722814*(i)/math.cos(math.radians(latitude))
    #     lst_bot_endpoints.append((longitude, latitude))
    #
    # # Connect top pixel endpoints with those at the bottom
    # top_bot_linestrings = []
    # for pair in zip(lst_top_endpoints, lst_bot_endpoints):
    #     top_bot_linestrings.append(LineString(list(pair)))
    #
    # # Calculate pixel endpoints on the left side of the screen
    # lst_left_endpoints = []
    # for j, i in zip(lst_ypixels, [smallest_xpixel]*len(lst_ypixels)):
    #     latitude = 37.0 + 0.00722814*(j)
    #     longitude = -97.5 + 0.00722814*(i)/math.cos(math.radians(latitude))
    #     lst_left_endpoints.append((longitude, latitude))
    #
    # # Calculate pixel endpoints on the right side of the screen
    # lst_right_endpoints = []
    # for j, i in zip(lst_ypixels, [biggest_xpixel]*len(lst_ypixels)):
    #     latitude = 37.0 + 0.00722814*(j)
    #     longitude = -97.5 + 0.00722814*(i)/math.cos(math.radians(latitude))
    #     lst_right_endpoints.append((longitude, latitude))
    #
    # # Connect left pixel endpoints with those at the right
    # left_right_endpoints = []
    # for pair in zip(lst_left_endpoints, lst_right_endpoints):
    #     left_right_endpoints.append(LineString(list(pair)))
    #
    # # Create GeometryCollection from top-bot and left-right linestrings
    # all_linestrings = []
    # all_linestrings.extend(top_bot_linestrings)
    # all_linestrings.extend(left_right_endpoints)
    # geometry_collection = GeometryCollection(all_linestrings)

    return feature_collection

from shapely.geometry import Point, MultiPolygon, Polygon
import requests
# Given a boundary and set of regions, returns the list of (lat,lng) of kiosks whose centroids are contained in the regions
def get_locations_kiosks_in_regions(north_lat, south_lat, east_lng, west_lng, regions_osm_geojsons):
    smallest_xpixel, biggest_ypixel = latlng_to_xypixel(north_lat, west_lng)
    biggest_xpixel, smallest_ypixel = latlng_to_xypixel(south_lat, east_lng)

    lst_xpixels = range(smallest_xpixel, biggest_xpixel+1)
    lst_ypixels = range(smallest_ypixel, biggest_ypixel+1)

    lst_kiosk_pixels_in_boundary = []
    for xpixel in lst_xpixels:
        for ypixel in lst_ypixels:
            lst_kiosk_pixels_in_boundary.append((xpixel, ypixel))

    lst_pixel_centroids = []
    for i, j in lst_kiosk_pixels_in_boundary:
        lat, lng = xypixel_to_latlng(i, j) # Gets centroid of xypixel in lat, lng coords
        p1 = Point((lng, lat))
        lst_pixel_centroids.append(p1)

    lst_region_shapes = []
    for geojson in regions_osm_geojsons:
        geometry_data = geojson["geometry"]
        if geometry_data["type"] == "Polygon":
            p2 = Polygon(geometry_data["coordinates"][0])
        elif geometry_data["type"] == "MultiPolygon":
            p2 = MultiPolygon(geometry_data["coordinates"])
        else:
            raise Exception("Polical Boundaries aren't polygons nor multipolygons")
        lst_region_shapes.append(p2)

    print(len(lst_kiosk_pixels_in_boundary))
    result_lst_kiosk_pixels = []
    for point in lst_pixel_centroids:
        for region_shape in lst_region_shapes:
            if region_shape.contains(point):
                kiosk_pixel = latlng_to_xypixel(point.y, point.x)
                result_lst_kiosk_pixels.append(kiosk_pixel)
                break

    return result_lst_kiosk_pixels
