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
        self.missed = False

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

    def setMissed(self):
        self.missed = True

    def setAloneAndMaxTravelTimes(self, alone_triptime):
        self.alone_triptime = alone_triptime
        self.total_triptime = self.alone_triptime
        self.max_triptime = self.alone_triptime * (1 + self.max_delay)
