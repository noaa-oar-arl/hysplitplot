# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# mapbox.py
#
# For finding the spatial extent of data points.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
import logging
import math
import numpy
import operator

from . import util

logger = logging.getLogger(__name__)


class LongitudeInterval:
   """
   An angle interval, [l, r].
   
   Angles are in degrees and they are in the [-180, +180) range.
   """

   def __init__(self, l=0.0, r=0.0):
      self._l = l
      self._r = r

   @staticmethod
   def _normalize_angle(angle):
      """
      Normalize an angle to the range [-180, 180).
      """
      normalized = angle % 360.0
      if normalized < -180.0:
         return normalized + 360.0
      elif normalized >= 180.0:
         return normalized - 360.0
      return normalized

   def is_angle_inside(self, angle):
      if self._l <= self._r:
         return self._l <= angle and angle <= self._r
      else:
         # boundary crossing case
         return (self._l <= angle and angle <= 180.0) or \
                (-180.0 <= angle and angle <= self._r)

   def union(self, angle):
      """
      Compare a target angle with the angle interval [_l, _r)
      and adjusts the interval to enclose the angle if it is
      outside the interval.
      """
      a = LongitudeInterval._normalize_angle(angle)

      if self.is_angle_inside(a):
         return

      if self._l <= self._r:
         if angle < self._l:
            dl = self._l - angle
            dr = (angle + 360.0) - self._r
            if dl <= dr:
               self._l = angle
            else:
               # cross the boundary
               self._r = angle
         else:
            dl = self._l - (angle - 360.0)
            dr = angle - self._r
            if dr <= dl:
               self._r = angle
            else:
               # cross the boundary
               self._l = angle
      else:
         # This is a boundary crossing case.
         # Need to check with two intervals [_l, 180] and [-180, _r].
         dl = self._l - angle
         dr = angle - self._r
         if dl <= dr:
            self._l = angle
         else:
            self._r = angle


class MapBoxFactory:

   @staticmethod
   def create_instance(lat_span=181.0, lon_span=360.0, **kwargs):
      kind = kwargs.get("kind", 0)
      if kind == 1:
         return MapBoxUsingBoundingBox(grid_delta=0.125,
                                       **kwargs)

      # use finer grids for small maps
      if lat_span < 2.0 and lon_span < 2.0:
         mbox = MapBox(grid_size=(lon_span, lat_span),
                       grid_delta=0.10,
                       **kwargs)
      elif lat_span < 5.0 and lon_span < 5.0:
         mbox = MapBox(grid_size=(lon_span, lat_span),
                       grid_delta=0.20,
                       **kwargs)
      else:
         mbox = MapBox()

      return mbox


class AbstractMapBox(ABC):

   def __init__(self, **kwargs):
      # A map projection requires grid_delta and grid_corner.
      self.grid_delta = kwargs.get("grid_delta", 1.0)
      self.grid_corner = kwargs.get("grid_corner", [-180.0, -90.0])  # (lon,lat)
      if type(self.grid_corner) is tuple:
         # Convert a tuple to a list so that its element can be updated.
         self.grid_corner = list(self.grid_corner)
      self.grid_corner[0] = LongitudeInterval._normalize_angle(self.grid_corner[0])
      #
      self.hit_count = 0
      self._bbox = None  # bounding box [l, r, b, t] in degrees.

   @property
   def bounding_box(self):
      return self._bbox

   def get_bounding_box_center(self):
      l, r, t, b = self._bbox
      if l <= r:
         xc = (l + r) * 0.5
      else:
         xc = LongitudeInterval._normalize_angle((l + r + 360.0) * 0.5)
      yc = (t + b) * 0.5
      return (xc, yc,)

   def get_bounding_box_corners(self):
      """
      Note that if the plume crosses the date-line, l > r.
      """
      if self._bbox is not None:
         l, r, b, t = self._bbox
         return ((l, b), (r, b), (r, t), (l, t))

      return tuple()

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

   @abstractmethod
   def allocate(self):
      pass

   @abstractmethod
   def add(self, lonlat):
      pass

   @abstractmethod
   def add_conc(self, conc, lons0, lats):
      pass

   @abstractmethod
   def determine_plume_extent(self):
      pass

   @abstractmethod
   def need_to_refine_grid(self):
      pass

   @abstractmethod
   def refine_grid(self):
      pass

   def clear_hit_map(self):
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
      radius_deg = util.km_to_deg(ring_distance * max(settings.ring_number, 1))
      l = self._normalize_lon(ring_loc[0] - radius_deg)
      r = self._normalize_lon(ring_loc[0] + radius_deg)
      b = self._normalize_lat(ring_loc[1] - radius_deg)
      t = self._normalize_lat(ring_loc[1] + radius_deg)
      logger.debug("ring bbox: %f %f %f %f", l, r, b, t)

      l = util.normalize_lon(l)
      r = util.normalize_lon(r)
      self._bbox = [l, r, b, t]
      logger.debug("final bbox: {}".format(self._bbox))


class MapBox(AbstractMapBox):
    # Longitudes and latitudes have ranges [-180, 180) and [-90, 90],
    # respectively.

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Unit tests check _sz.
        grid_size = kwargs.get("grid_size", (360.0, 181.0))
        self._sz = [util.nearest_int(v / self.grid_delta) for v in grid_size]
        logger.debug("initial mapbox: grid delta {0}, sz {1}, corner {2}"
                     .format(self.grid_delta, self._sz, self.grid_corner))
        self.plume_sz = [0.0, 0.0]  # (lon, lat)
        self.plume_loc = [0, 0]  # lon-, lat-indices
        self._lon_hit_map = None
        self._lat_hit_map = None

    def dump(self, stream):
        stream.write("MapBox: grid delta {0}, sz {1}, corner {2}\n"
                     .format(self.grid_delta, self._sz, self.grid_corner))
        for j in range(self._sz[1]):
            if self._lat_hit_map[j] != 0:
                    stream.write("lat_hit_map[{0}] = {1}\n"
                                 .format(j, self._lat_hit_map[j]))
        for i in range(self._sz[0]):
            if self._lon_hit_map[i] != 0:
                    stream.write("lon_hit_map[{0}] = {1}\n"
                                 .format(i, self._lon_hit_map[i]))

    def allocate(self):
        self._lon_hit_map = numpy.zeros(self._sz[0], dtype=int)
        self._lat_hit_map = numpy.zeros(self._sz[1], dtype=int)
        self.hit_count = 0

    def add(self, lonlat):
        lon, lat = lonlat
        lon = self._normalize_lon(lon)
        try:
            i = int((lon - self.grid_corner[0]) / self.grid_delta) % self._sz[0]
            j = int((lat - self.grid_corner[1]) / self.grid_delta) % self._sz[1]
            # count hits
            self._lon_hit_map[i] += 1
            self._lat_hit_map[j] += 1
            self.hit_count += 1
        except IndexError:
            logger.error("out-of-bound mapbox index: lonlat ({:f}, {:f})"
                         "; hit map corner {}, sz {}, grid size {}".format(
                         lon, lat, self.grid_corner, self._sz, self.grid_delta))

    def add_conc(self, conc, lons0, lats):
        lons = [self._normalize_lon(x) for x in lons0]
        inv_delta = 1.0 / self.grid_delta
        i_precomputed = [int((x - self.grid_corner[0]) * inv_delta) % self._sz[0] for x in lons]
        j_precomputed = [int((y - self.grid_corner[1]) * inv_delta) % self._sz[1] for y in lats]
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
        right = self._sz[0]
        bottom = 0
        top = self._sz[1]

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
            left = right = int((avg - self.grid_corner[0]) / self.grid_delta) % self._sz[0]
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
            self.plume_sz[0] = self.grid_delta * (right + 1 + self._sz[0] - left)
        self.plume_sz[1] = self.grid_delta * (top - bottom + 1)
        self.plume_loc[0] = left
        self.plume_loc[1] = bottom

        l = self.grid_corner[0] + self.grid_delta * left
        r = self.grid_corner[0] + self.grid_delta * (right + 1)
        b = self.grid_corner[1] + self.grid_delta * bottom
        t = self.grid_corner[1] + self.grid_delta * (top + 1)
        l = util.normalize_lon(l)
        r = util.normalize_lon(r)
        self._bbox = [l, r, b, t]

        logger.debug("plume location: index (%d, %d), lonlat (%f, %f)",
                     self.plume_loc[0], self.plume_loc[1],
                     self.grid_corner[0] + self.plume_loc[0] * self.grid_delta,
                     self.grid_corner[1] + self.plume_loc[1] * self.grid_delta)
        logger.debug("plume size in degs: %f x %f",
                     self.plume_sz[0],
                     self.plume_sz[1])
        logger.debug("plume bbox: {}".format(self._bbox))

    def need_to_refine_grid(self):
        if self.plume_sz[0] <= 2.0 and self.plume_sz[1] <= 2.0:
            return True
        return False

    def refine_grid(self):
        logger.debug("grid delta {0}, sz {1}, corner {2}"
                     .format(self.grid_delta, self._sz, self.grid_corner))
        # new corner point based on minimum
        self.grid_corner[0] += self.plume_loc[0] * self.grid_delta
        self.grid_corner[1] += self.plume_loc[1] * self.grid_delta
        self.grid_delta = max(0.01, min(0.1, self.grid_delta * 0.25))
        self._sz[1] = int(self.plume_sz[1] / self.grid_delta)
        self._sz[0] = int(self.plume_sz[0] / self.grid_delta)
        self._lon_hit_map = None
        self._lat_hit_map = None
        logger.debug("refined: grid delta {0}, sz {1}, corner {2}"
                     .format(self.grid_delta, self._sz, self.grid_corner))

    def clear_hit_map(self):
        super().clear_hit_map()
        self._lon_hit_map.fill(0)
        self._lat_hit_map.fill(0)


class MapBoxUsingBoundingBox(AbstractMapBox):

   def __init__(self, **kwargs):
      super().__init__(**kwargs)
      self._left = 0  # min longitude in deg, [-180, 180)
      self._right = 0  # max longitude in deg, [-180, 180)
      self._top = 0  # min latitude in deg, [-90, 90]
      self._bottom = 0  # max latitude in deg, [-90, 90]

   def allocate(self):
      pass

   def add(self, lonlat):
      """
      If the given coordinate is outside the bounding box, inflate the box.
      """
      lon, lat = lonlat
      lon = LongitudeInterval._normalize_angle(lon)
      if self._bbox is None:
         self._bbox = [lon, lon, lat, lat]
      else:
         l, r, b, t = self._bbox

         interval = LongitudeInterval(l, r)
         if not interval.is_angle_inside(lon):
            interval.union(lon)
            l = interval._l
            r = interval._r

         if lat < b:
            b = lat
         elif lat > t:
            t = lat

         self._bbox = [l, r, b, t]
      self.hit_count += 1

   def add_conc(self, conc, lons0, lats0):
      """
      Inflate the bounding box to contain all lat-lon coordinates
      where concentration values are nonzero.
      """
      rows, cols = numpy.where(conc > 0)
      if len(rows) == 0:
         return

      lats = [self._normalize_lat(lats0[j]) for j in rows]
      lat_min = min(lats)
      lat_max = max(lats)

      lons = [LongitudeInterval._normalize_angle(lons0[i]) for i in cols]
      if self._bbox is None:
         interval = LongitudeInterval(lons[0], lons[0])
      else:
         interval = LongitudeInterval(self._bbox[0], self._bbox[1])
      for lon in lons:
         interval.union(lon)

      if self._bbox is None:
         self._bbox = [interval._l, interval._r, lat_min, lat_max]
      else:
         _, _, b, t = self._bbox

         if lat_min < b:
            b = lat_min
         elif lat_max > t:
            t = lat_max

         self._bbox = [interval._l, interval._r, b, t]

      self.hit_count += len(rows)

   def determine_plume_extent(self):
      l, r, b, t = self._bbox
      logger.debug('mapbox: bounding box l,r,b,t=%f,%f,%f,%f', l, r, b, t)

   def need_to_refine_grid(self):
      return False

   def refine_grid(self):
      pass

