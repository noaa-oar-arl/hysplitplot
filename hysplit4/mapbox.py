import logging
import numpy


logger = logging.getLogger(__name__)


class MapBox:

    def __init__(self):
        self.hit_map = None
        self.sz = [360, 181]
        self.grid_delta = 1.0
        self.grid_corner = [0.0, -90.0] # (lon, lat)
        self.plume_sz = [0.0, 0.0]      # (lon, lat)
        self.plume_loc = [0, 0]         # lon-, lat-indices
        self.hit_count = 0
        self._i = 0
        self._j = 0

    def dump(self, stream):
        stream.write("MapBox: grid delta {0}, sz {1}, corner {2}\n".format(
            self.grid_delta, self.sz, self.grid_corner))
        for j in range(self.sz[1]):
            for i in range(self.sz[0]):
                if self.hit_map[i,j] != 0:
                    stream.write("hit_map[{0},{1}] = {2}\n".format(i, j, self.hit_map[i,j]))

    def allocate(self):
        self.hit_map = numpy.zeros(self.sz, dtype=int)
        self.hit_count = 0

    def add(self, lonlat):
        lon, lat = lonlat
        if lon < 0.0:
            lon += 360.0
        self._i = min(self.sz[0], int((lon - self.grid_corner[0]) / self.grid_delta))
        self._j = min(self.sz[1], int((lat - self.grid_corner[1]) / self.grid_delta))
        # count hits
        self.hit_map[self._i, self._j] += 1
        self.hit_count += 1

    def determine_plume_extent(self):
        self.plume_sz[1] = 0.0
        self.plume_loc[1] = self.sz[1] - 1
        for j in range(self.sz[1]):
            for i in range(self.sz[0]):
                if self.hit_map[i, j] > 0:
                    self.plume_sz[1] += self.grid_delta
                    self.plume_loc[1] = min(self.plume_loc[1], j)
                    break

        self.plume_sz[0] = 0.0
        self.plume_loc[0] = self.sz[0] - 1
        for i in range(self.sz[0]):
            for j in range(self.sz[1]):
                if self.hit_map[i, j] > 0:
                    self.plume_sz[0] += self.grid_delta
                    self.plume_loc[0] = min(self.plume_loc[0], i)
                    break

        return

    def need_to_refine_grid(self):
        return True if (self.plume_sz[0] <= 2.0 and self.plume_sz[1] <= 2.0) else False

    def refine_grid(self):
        # new corner point based on minimum
        self.grid_corner[0] += self.plume_loc[0] * self.grid_delta
        self.grid_corner[1] += self.plume_loc[1] * self.grid_delta
        self.grid_delta = 0.10
        self.sz[1] = int(self.plume_sz[1] / self.grid_delta)
        self.sz[0] = int(self.plume_sz[0] / self.grid_delta)
        self.hit_map = None

    def clear_hit_map(self):
        self.hit_map.fill(0)
        self.hit_count = 0

    def set_ring_extent(self, settings):
        kspan = settings.adjust_ring_distance(self.plume_sz, self.grid_delta)
        logger.debug("set_ring_extent: span %d, distance %g", kspan, settings.ring_distance)
        # plots should be centered about the source point
        self.add(settings.center_loc)
        # set vertical extent of the rings
        half = int(kspan/2)
        for j in range(max(self._j-half, 0), min(self._j+half+1, self.sz[1])):
            self.hit_map[self._i, j] += 1