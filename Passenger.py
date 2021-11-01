class Passenger:
    def __init__(self, lat, lon, dest_lat, dest_lon, departure_time, profile):
        self.lat = lat
        self.lon = lon
        self.dest_lat = dest_lat
        self.dest_lon = dest_lon
        self.departure_time = departure_time
        self.vehicle_departure_time = None
        self.depot = None
        self.dest_depot = None
        self.active = True
        self.profile = int(profile)
        self.distance_if_taken_alone = None
        self.distance_in_rideshare = None
        self.setProfileAttr()

    def setProfileAttr(self):
        if self.profile == 0:
            self.delay = 2
            self.miss = .1
        elif self.profile == 1:
            self.delay = 5
            self.miss = .3
        else:
            self.delay = 10
            self.miss = .5

    def __str__(self):
        return "Location: ({0}, {1})\nProfile: {2} Delay: {3} Miss: {4}\nDeparture Time: {5}\nActive?: {6}\n".format(self.lat, self.lon, self.profile, self.delay, self.miss, self.departure_time, self.active)

    def getLocation(self):
        return (self.lat, self.lon)

    def setProfile(self, profile):
        self.profile = profile
        self.setProfileAttr()

    def setActive(self, bool):
        self.active = bool

    def getAnimationDetails(self):
        result = {'pas_idx': id(self), 'lat': self.lat, 'lng': self.lon, 'dest_lat': self.dest_lat, 'dest_lng': self.dest_lon}
        return result
