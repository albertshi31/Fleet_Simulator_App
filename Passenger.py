from geopy.distance import distance as calculate_distance_between_latlngs

class Passenger:
    def __init__(self, personID, lat, lng, dest_lat, dest_lng, oxcoord, oycoord, dxcoord, dycoord, odeparturetime, max_delay):
        self.personID = personID
        self.lat = lat
        self.lng = lng
        self.dest_lat = dest_lat
        self.dest_lng = dest_lng
        self.oxcoord = oxcoord
        self.oycoord = oycoord
        self.dxcoord = dxcoord
        self.dycoord = dycoord
        self.odeparturetime = odeparturetime
        self.max_delay = max_delay
        self.missed = None

        # Metrics
        self.trip_length = None
        self.waittime = None
        self.walk_to_okiosk_dist = None
        self.walk_to_dkiosk_dist = None
        self.left_kiosk_time = None

    def __str__(self):
        return "PersonID: {}\nOXYCoords: ({}, {})\nDXYCoords: ({}, {})\nODepartureTime: {}\nMax Delay: {}\n".format(self.personID, self.oxcoord, self.oycoord, self.dxcoord, self.dycoord, self.odeparturetime, self.max_delay)

    def getOXYPixelCoords(self):
        return (self.oxcoord, self.oycoord)

    def getDXYPixelCoords(self):
        return (self.dxcoord, self.dycoord)

    def setOKiosk(self, kiosk):
        self.kiosk = kiosk

    def setDKiosk(self, kiosk):
        self.dest_kiosk = kiosk

    def getDKiosk(self):
        return self.dest_kiosk

    def setMissed(self, curr_time_in_sec):
        self.missed = True
        self.waittime = curr_time_in_sec - self.odeparturetime
        self.left_kiosk_time = curr_time_in_sec

    def setServed(self, curr_time_in_sec):
        self.missed = False
        self.waittime = curr_time_in_sec - self.odeparturetime
        self.left_kiosk_time = curr_time_in_sec

    def setTripInfo(self, duration, distance):
        self.alone_triptime = duration
        self.total_triptime = self.alone_triptime
        self.max_triptime = self.alone_triptime * (1 + self.max_delay)
        self.alone_trip_length = distance
        self.walk_to_okiosk_dist = calculate_distance_between_latlngs((self.lat, self.lng), self.kiosk.getLatLng()).meters
        self.walk_to_dkiosk_dist = calculate_distance_between_latlngs((self.lat, self.lng), self.dest_kiosk.getLatLng()).meters

    def getAloneTripLength(self):
        return self.alone_trip_length

    def getWaittime(self):
        return self.waittime

    def isMissed(self):
        return self.missed

    def getWalkToKioskDistance(self):
        return self.walk_to_okiosk_dist * 1.2

    def getWalkToDestKioskDistance(self):
        return self.walk_to_dkiosk_dist * 1.2

    def getAddedTriptime(self):
        return self.total_triptime - self.alone_triptime

    def getDepartureTime(self):
        return self.odeparturetime

    def getPersonID(self):
        return self.personID
