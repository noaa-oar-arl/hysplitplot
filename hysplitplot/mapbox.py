# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# mapbox.py
#
# For finding the spatial extent of data points.
# ---------------------------------------------------------------------------

import logging
import numpy
import operator

from hysplitplot import util


logger = logging.getLogger(__name__)


class MapBox:
    # Longitudes and latitudes have ranges [-180, 180) and [-90, 90],
    # respectively.

    def __init__(self, **kwargs):
        self._lon_hit_map = None
        self._lat_hit_map = None
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
        self.__bbox = None              # bounding box [l, r, b, t] in degrees.

    @property
    def bounding_box(self):
        return self.__bbox

    def _normalize_lon(self, lon):
        # Normalize longitude to start from the minimum longitude value.
        dlon = lon - self.grid_corner[0]
        if dlon < 0:
            return lon + 360.0
        elif dlon >= 360.0:
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
            if self._lat_hit_map[j] != 0:
                    stream.write("lat_hit_map[{0}] = {1}\n"
                                 .format(j, self._lat_hit_map[j]))
        for i in range(self.sz[0]):
            if self._lon_hit_map[i] != 0:
                    stream.write("lon_hit_map[{0}] = {1}\n"
                                 .format(i, self._lon_hit_map[i]))

    def allocate(self):
        self._lon_hit_map = numpy.zeros(self.sz[0], dtype=int)
        self._lat_hit_map = numpy.zeros(self.sz[1], dtype=int)
        self.hit_count = 0

    def add(self, lonlat):
        lon, lat = lonlat
        lon = self._normalize_lon(lon)
        try:
            i = int((lon - self.grid_corner[0]) / self.grid_delta) % self.sz[0]
            j = int((lat - self.grid_corner[1]) / self.grid_delta) % self.sz[1]
            # count hits
            self._lon_hit_map[i] += 1
            self._lat_hit_map[j] += 1
            self.hit_count += 1
        except IndexError:
            logger.error("out-of-bound mapbox index: lonlat ({:f}, {:f})"
                         "; hit map corner {}, sz {}, grid size {}".format(
                         lon, lat, self.grid_corner, self.sz, self.grid_delta))

    def add_conc(self, conc, lons0, lats):
        lons = [self._normalize_lon(x) for x in lons0]
        inv_delta = 1.0 / self.grid_delta
        i_precomputed = [int((x - self.grid_corner[0]) * inv_delta) % self.sz[0] for x in lons]
        j_precomputed = [int((y - self.grid_corner[1]) * inv_delta) % self.sz[1] for y in lats]
        for lat_index in range(len(lats)):
            lon_indices = numpy.where(conc[lat_index] > 0)[0]
            if len(lon_indices) > 0:
                j = j_precomputed[lat_index]
                i_array = operator.itemgetter(*lon_indices)(i_precomputed)
                if isinstance(i_array, tuple):
                    for i in i_array:
                        self._lon_hit_map[i] += 1
                        self._lat_hit_map[j] += 1
                        self.hit_count += 1
                else:
                    i = i_array
                    self._lon_hit_map[i] += 1
                    self._lat_hit_map[j] += 1
                    self.hit_count += 1

    def determine_plume_extent(self):
        left = 0
        right = self.sz[0]
        bottom = 0
        top = self.sz[1]

        lat_indices = numpy.where(self._lat_hit_map > 0)[0]
        if len(lat_indices) > 0:
            bottom = min(lat_indices)
            top = max(lat_indices)

        lon_indices = numpy.where(self._lon_hit_map > 0)[0]
        if len(lon_indices) > 0:
            lons = [self.grid_corner[0] + i * self.grid_delta for i in lon_indices]
            weights = operator.itemgetter(*lon_indices)(self._lon_hit_map)
            if len(lon_indices) == 1:
                weights = [weights]
            avg = util.calc_lon_average(lons, weights)
            # search the min and the max of longitude deltas
            delta_min = delta_max = 0.0
            left = right = int((avg - self.grid_corner[0]) / self.grid_delta) % self.sz[0]
            for k, lon in enumerate(lons):
                delta = lon - avg
                if delta < -180.0:
                    delta += 360.0
                elif delta >= 180.0:
                    delta -= 360.0

                if delta < delta_min:
                    delta_min = delta
                    left = lon_indices[k]
                elif delta > delta_max:
                    delta_max = delta
                    right = lon_indices[k]

        if right >= left:
            self.plume_sz[0] = self.grid_delta * (right - left + 1)
        else:
            self.plume_sz[0] = self.grid_delta * (right + 1 + self.sz[0] - left)
        self.plume_sz[1] = self.grid_delta * (top - bottom + 1)
        self.plume_loc[0] = left
        self.plume_loc[1] = bottom

        l = self.grid_corner[0] + self.grid_delta * left
        r = self.grid_corner[0] + self.grid_delta * (right + 1)
        b = self.grid_corner[1] + self.grid_delta * bottom
        t = self.grid_corner[1] + self.grid_delta * (top + 1)
        l = util.normalize_lon(l)
        r = util.normalize_lon(r)
        self.__bbox = [l, r, b, t]

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
        self._lon_hit_map = None
        self._lat_hit_map = None
        logger.debug("refined: grid delta {0}, sz {1}, corner {2}"
                     .format(self.grid_delta, self.sz, self.grid_corner))

    def clear_hit_map(self):
        self._lon_hit_map.fill(0)
        self._lat_hit_map.fill(0)
        self.hit_count = 0

    def set_ring_extent(self, settings, ring_loc):
        kspan, ring_distance = util.calc_ring_distance(self.plume_sz,
                                                       self.grid_delta,
                                                       ring_loc,
                                                       settings.ring_number,
                                                       settings.ring_distance)
        settings.ring_distance = ring_distance
        logger.debug("set_ring_extent: span %d, distance %g", kspan,
                     ring_distance)

        # plots should be centered about the specified center location.
        # assume that the bounding box is already computed using the plume extent.
        radius_deg = util.km_to_deg(ring_distance * settings.ring_number)
        l = self._normalize_lon(ring_loc[0] - radius_deg)
        r = self._normalize_lon(ring_loc[0] + radius_deg)
        b = self._normalize_lat(ring_loc[1] - radius_deg)
        t = self._normalize_lat(ring_loc[1] + radius_deg)
        logger.debug("ring bbox: %f %f %f %f", l, r, b, t)

        l = util.normalize_lon(l)
        r = util.normalize_lon(r)
        self.__bbox = [l, r, b, t]
        logger.debug("final bbox: {}".format(self.__bbox))

    def get_bounding_box_corners(self):
        """
        Note that if the plume crosses the date-line, l > r.
        """
        if self.__bbox is not None:
            l, r, b, t = self.__bbox
            return ((l, b), (r, b), (r, t), (l, t))

        return tuple()
