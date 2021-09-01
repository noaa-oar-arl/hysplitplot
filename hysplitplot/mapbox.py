# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# mapbox.py
#
# For finding the spatial extent of data points.
# ---------------------------------------------------------------------------

import logging
import numpy

from hysplitplot import util


logger = logging.getLogger(__name__)


class MapBox:
    # Longitudes and latitudes have ranges [-180, 180) and [-90, 90],
    # respectively.

    def __init__(self, **kwargs):
        self.hit_map = None
        self.grid_delta = kwargs.get("grid_delta", 1.0)
        self.grid_corner = kwargs.get("grid_corner", [-180.0, -90.0])  # (lon,lat)
        if type(self.grid_corner) is tuple:
            # Convert a tuple to a list so that its element can be updated.
            self.grid_corner = list(self.grid_corner)
        self.grid_corner[0] = self._normalize_lon(self.grid_corner[0])
        grid_size = kwargs.get("grid_size", (360.0, 181.0))
        self.sz = [util.nearest_int(v / self.grid_delta) for v in grid_size]
        self.plume_sz = [0.0, 0.0]      # (lon, lat)
        self.plume_loc = [0, 0]         # lon-, lat-indices
        self.hit_count = 0
        self._i = 0
        self._j = 0
        self.__bbox = None              # bounding box [l, r, b, t] in degrees.

    @property
    def bounding_box(self):
        return self.__bbox

    def _normalize_lon(self, lon):
        # Normalize longitude to [-180, 180).
        if lon < -180.0:
            return lon + 360.0
        elif lon >= 180.0:
            return lon - 360.0
        return lon
    
    def _normalize_lat(self, lat):
        # Normalize latitude to [-90, 90].
        if lat < -90.0:
            return -90.0
        elif lat > 90.0:
            return 90.0
        return lat

    def dump(self, stream):
        stream.write("MapBox: grid delta {0}, sz {1}, corner {2}\n"
                     .format(self.grid_delta, self.sz, self.grid_corner))
        for j in range(self.sz[1]):
            for i in range(self.sz[0]):
                if self.hit_map[i, j] != 0:
                    stream.write("hit_map[{0},{1}] = {2}\n"
                                 .format(i, j, self.hit_map[i, j]))

    def allocate(self):
        self.hit_map = numpy.zeros(self.sz, dtype=int)
        self.hit_count = 0

    def add(self, lonlat):
        lon, lat = lonlat
        lon = self._normalize_lon(lon)
        try:
            i = min(self.sz[0] - 1,
                    int((lon - self.grid_corner[0]) / self.grid_delta))
            j = min(self.sz[1] - 1,
                    int((lat - self.grid_corner[1]) / self.grid_delta))
            # count hits
            self.hit_map[i, j] += 1
            self._i = i
            self._j = j
            self.hit_count += 1
        except IndexError:
            logger.error("out-of-bound mapbox index: lonlat ({:f}, {:f})"
                         "; hit map corner {}, sz {}, grid size {}".format(
                         lon, lat, self.grid_corner, self.sz, self.grid_delta))

    def add_conc(self, conc, lons0, lats):
        lons = [self._normalize_lon(x) for x in lons0]
        inv_delta = 1.0 / self.grid_delta
        iarr = [min(self.sz[0] - 1, int((x - self.grid_corner[0]) * inv_delta)) for x in lons]
        jarr = [min(self.sz[1] - 1, int((y - self.grid_corner[1]) * inv_delta)) for y in lats]
        for j in range(len(lats)):
            for i in range(len(lons)):
                if conc[j, i] > 0:
                    j2 = jarr[j]
                    i2 = iarr[i]
                    self.hit_map[i2, j2] += 1
                    self._i = i2
                    self._j = j2
                    self.hit_count += 1

    def determine_plume_extent(self):
        bottom = 0
        done = False
        for j in range(self.sz[1]):
            for i in range(self.sz[0]):
                if self.hit_map[i, j] > 0:
                    bottom = j
                    done = True
                    break
            if done:
                break

        top = self.sz[1] - 1
        done = False
        for j in range(self.sz[1] - 1, bottom - 1, -1):
            for i in range(self.sz[0]):
                if self.hit_map[i, j] > 0:
                    top = j
                    done = True
                    break
            if done:
                break
            
        left = 0
        done = False
        for i in range(self.sz[0]):
            for j in range(self.sz[1]):
                if self.hit_map[i, j] > 0:
                    left = i
                    done = True
                    break
            if done:
                break
            
        right = self.sz[0] - 1
        done = False
        for i in range(self.sz[0] - 1, left - 1, -1):
            for j in range(self.sz[1]):
                if self.hit_map[i, j] > 0:
                    right = i
                    done = True
                    break
            if done:
                break

        self.plume_sz[0] = self.grid_delta * (right - left + 1)
        self.plume_sz[1] = self.grid_delta * (top - bottom + 1)
        self.plume_loc[0] = left
        self.plume_loc[1] = bottom

        self.__bbox = [self.grid_corner[0] + self.grid_delta * left,
                       self.grid_corner[0] + self.grid_delta * (right + 1),
                       self.grid_corner[1] + self.grid_delta * bottom,
                       self.grid_corner[1] + self.grid_delta * (top + 1)]
        
        logger.debug("plume location: index (%d, %d), lonlat (%f, %f)",
                     self.plume_loc[0], self.plume_loc[1],
                     self.grid_corner[0] + self.plume_loc[0] * self.grid_delta,
                     self.grid_corner[1] + self.plume_loc[1] * self.grid_delta)
        logger.debug("plume size in degs: %f x %f",
                     self.plume_sz[0],
                     self.plume_sz[1])
        logger.debug("plume bbox: {}".format(self.__bbox))

    def need_to_refine_grid(self):
        if self.plume_sz[0] <= 2.0 and self.plume_sz[1] <= 2.0:
            return True
        return False

    def refine_grid(self):
        logger.debug("grid delta {0}, sz {1}, corner {2}"
                     .format(self.grid_delta, self.sz, self.grid_corner))
        # new corner point based on minimum
        self.grid_corner[0] += self.plume_loc[0] * self.grid_delta
        self.grid_corner[1] += self.plume_loc[1] * self.grid_delta
        self.grid_delta = 0.10
        self.sz[1] = int(self.plume_sz[1] / self.grid_delta)
        self.sz[0] = int(self.plume_sz[0] / self.grid_delta)
        self.hit_map = None
        logger.debug("refined: grid delta {0}, sz {1}, corner {2}"
                     .format(self.grid_delta, self.sz, self.grid_corner))

    def clear_hit_map(self):
        self.hit_map.fill(0)
        self.hit_count = 0

    def set_ring_extent(self, settings):
        kspan, ring_distance = util.calc_ring_distance(self.plume_sz,
                                                       self.grid_delta,
                                                       settings.center_loc,
                                                       settings.ring_number,
                                                       settings.ring_distance)
        settings.ring_distance = ring_distance
        logger.debug("set_ring_extent: span %d, distance %g", kspan,
                     ring_distance)

        # plots should be centered about the specified center location.
        # assume that the bounding box is already computed using the plume extent.
        radius_deg = util.km_to_deg(ring_distance * settings.ring_number)
        l = self._normalize_lon(settings.center_loc[0] - radius_deg)
        r = self._normalize_lon(settings.center_loc[0] + radius_deg)
        b = self._normalize_lat(settings.center_loc[1] - radius_deg)
        t = self._normalize_lat(settings.center_loc[1] + radius_deg)
        logger.debug("ring bbox: %f %f %f %f", l, r, b, t)
        
        if self.__bbox is not None:
            self.__bbox[0] = min(self.__bbox[0], l)
            self.__bbox[1] = max(self.__bbox[1], r)
            self.__bbox[2] = min(self.__bbox[2], b)
            self.__bbox[3] = max(self.__bbox[3], t)
        else:
            self.__bbox = [l, r, b, t]
        logger.debug("plume+ring bbox: {}".format(self.__bbox))

    def get_bounding_box_corners(self):
        if self.__bbox is not None:
            l, r, b, t = self.__bbox
            return ((l, b), (r, b), (r, t), (l, t))
        return tuple()
