import numpy as np

def create_route(passengers, starting_depot, ending_depot, matrix):
    ret_list = []
    remaining_dests = []
    ret_list.append(starting_depot)
    for pax in passengers:
        remaining_dests.append(pax.dest_depot)
    
    curr = starting_depot
    while remaining_dests:
        distances = []
        for i in range(len(remaining_dests)):
            currdist = matrix["{},{};{},{}".format(
                curr.lat, curr.lon, remaining_dests[i].lat, remaining_dests[i].lon)]["distance"]
            distances.append(currdist)
        curr = remaining_dests[np.argmin(distances)]
        remaining_dests.remove(curr)
        ret_list.append(curr)
    if ending_depot:
        ret_list.append(ending_depot)
    res = []
    for i in ret_list:
        if i not in res:
            res.append(i)
    return res