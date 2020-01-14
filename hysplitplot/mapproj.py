# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# mapproj.py
#
# Provides map projections.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
import cartopy.crs
import logging
import math
import numpy
import shapely

from hysplitplot import util, const


logger = logging.getLogger(__name__)


class MapProjectionFactory:

    @staticmethod
    def create_instance(map_proj, zoom_factor, center_loc, scale, grid_deltas,
                        map_box):
        obj = None

        kproj = AbstractMapProjection.determine_projection(map_proj,
                                                           center_loc)

        if kproj == const.MapProjection.POLAR:
            obj = PolarProjection(kproj, zoom_factor, center_loc, scale,
                                  grid_deltas)
        elif kproj == const.MapProjection.LAMBERT:
            obj = LambertProjection(kproj, zoom_factor, center_loc, scale,
                                    grid_deltas)
        elif kproj == const.MapProjection.MERCATOR:
            obj = MercatorProjection(kproj, zoom_factor, center_loc, scale,
                                     grid_deltas)
        elif kproj == const.MapProjection.CYL_EQU:
            obj = CylindricalEquidistantProjection(kproj, zoom_factor,
                                                   center_loc, scale,
                                                   grid_deltas)
        elif kproj == const.MapProjection.WEB_MERCATOR:
            obj = WebMercatorProjection(kproj, zoom_factor, center_loc, scale,
                                        grid_deltas)
        else:
            raise Exception("unknown map projection {0}".format(kproj))

        obj.do_initial_estimates(map_box, center_loc)

        # Mercator/Lambert grids not permitted to encompass the poles
        if not obj.sanity_check():
            proj = obj.create_sane_projection(kproj, zoom_factor, center_loc,
                                              scale, grid_deltas)
            proj.do_initial_estimates(map_box, center_loc)
            return proj

        return obj


class AbstractMapProjection(ABC):

    _WGS84 = {"datum": "WGS84", "ellps": "WGS84", "proj": "longlat",
              "no_defs": True}  # epsg4326

    TOLERANCE = 0.5  # xy2ll->ll2xy allows difference <= TOLERANCE*grid
    CONTRACTION = 0.2  # contraction factor when corners are outside map

    def __init__(self, proj_type, zoom_factor, center_loc, scale, grid_deltas):
        self.proj_type = proj_type
        self.zoom_factor = zoom_factor
        self.scale = scale
        self.deltas = grid_deltas       # (dlon, dlat)
        #
        self.crs = None  # to be created by a child class
        self.crs_geodetic = cartopy.crs.Geodetic()
        self.center_loc = center_loc    # (lon, lat)
        self.corners_xy = None      # [x1, x2, y1, y2]
        self.corners_lonlat = None  # [lon_left,lon_right,lat_bottom,lat_top]
        #
        self.reflon = center_loc[0]
        self.tnglat = self.get_tangent_lat(center_loc)

    def calc_xy(self, plon, plat):
        if plat <= -90.0:
            plat = -90.0
        elif plat > 90.0:
            plat = 90.0
        return self.crs.transform_point(plon, plat, self.crs_geodetic)

    def calc_lonlat(self, x, y):
        return self.crs_geodetic.transform_point(x, y, self.crs)

    @abstractmethod
    def get_tangent_lat(self, center_loc):
        pass

    @staticmethod
    def determine_projection(map_proj, center_loc):
        kproj = map_proj
        if map_proj == const.MapProjection.AUTO:
            kproj = const.MapProjection.LAMBERT
            if center_loc[1] > 55.0 or center_loc[1] < -55.0:
                kproj = const.MapProjection.POLAR
            if center_loc[1] < 25.0 and center_loc[1] > -25.0:
                kproj = const.MapProjection.MERCATOR
        logger.debug("map projection %d -> %d", map_proj, kproj)
        return kproj

    def refine_corners(self, center_loc):
        corners_xy = self.validate_corners(self.corners_xy)

        # scale map per aspect ratio
        corners_saved = corners_xy
        corners_xy = self.scale_per_aspect_ratio(corners_xy, self.scale)
        corners_xy = self.choose_corners(corners_xy, corners_saved)
        logger.debug("X, Y asp-zum: %s", corners_xy)

        # projection zoom factor
        corners_saved = corners_xy
        corners_xy = self.zoom_corners(corners_xy, self.zoom_factor)
        corners_xy = self.choose_corners(corners_xy, corners_saved)
        logger.debug("X, Y zum-adj: %s", corners_xy)

        # round map corners to match even grid index for plotting
        corners_saved = [util.nearest_int(a) for a in corners_xy]
        corners_xy = self.round_map_corners(corners_xy)
        corners_xy = self.choose_corners(corners_xy, corners_saved)
        logger.debug("X, Y Adj: %s", corners_xy)

        # alatb, alonl, alatt, alonr will be used later to setup map
        corners_lonlat = self.calc_corners_lonlat(corners_xy)

        # Lambert/Mercator corners should be away from pole
        if self.need_pole_exclusion(corners_lonlat):
            corners_xy, corners_lonlat = self.exclude_pole(corners_xy,
                                                           corners_lonlat)

        self.corners_xy = corners_xy
        self.corners_lonlat = corners_lonlat
        logger.debug("Final: %s", corners_xy)
        logger.debug("Final: lonlat %s", self.corners_lonlat)

    def validate_corners(self, corners):
        x1, x2, y1, y2 = corners

        # save x1, x2, y1, y2 before validation
        x1s, x2s, y1s, y2s = x1, x2, y1, y2

        alonl, alatb = self.calc_lonlat(x1, y1)
        alonr, alatt = self.calc_lonlat(x2, y2)
        x1, y1 = self.calc_xy(alonl, alatb)
        x2, y2 = self.calc_xy(alonr, alatt)

        # move lower left corner toward center
        if max(abs(x1-x1s), abs(y1s-y1)) >= self.TOLERANCE:
            x1 = x1s + self.CONTRACTION*(x2s - x1s)
            y1 = y1s + self.CONTRACTION*(y2s - y1s)

        # move upper right corner toward center
        if max(abs(x2-x2s), abs(y2s-y2)) >= self.TOLERANCE:
            x2 = x2s - self.CONTRACTION*(x2s - x1s)
            y2 = y2s - self.CONTRACTION*(y2s - y1s)

        return (x1, x2, y1, y2)

    def scale_per_aspect_ratio(self, corners_xy, aspect_ratio):
        x1, x2, y1, y2 = corners_xy

        # new map center
        xc = 0.5 * (x1 + x2)
        yc = 0.5 * (y1 + y2)

        # scale map according to aspect ratio
        if abs(x2-x1) <= aspect_ratio*abs(y2 - y1):
            # expand in x-direction
            delx = 0.5 * (y2-y1) * aspect_ratio
            x1 = xc - delx
            x2 = xc + delx
        else:
            # expand in y-direction
            dely = 0.5 * (x2-x1) / aspect_ratio
            y1 = yc - dely
            y2 = yc + dely
        logger.debug("X, Y Asp: %f %f %f %f", x1, y1, x2, y2)

        return (x1, x2, y1, y2)

    def choose_corners(self, corners_new, corners_prev):
        x1, x2, y1, y2 = corners_new

        # save x1, x2, y1, y2
        x1s, x2s, y1s, y2s = x1, x2, y1, y2

        alonl, alatb = self.calc_lonlat(x1, y1)
        alonr, alatt = self.calc_lonlat(x2, y2)
        x1, y1 = self.calc_xy(alonl, alatb)
        x2, y2 = self.calc_xy(alonr, alatt)

        dev = max(abs(x1-x1s), abs(x2-x2s), abs(y1-y1s), abs(y2-y2s))
        if dev >= self.TOLERANCE:
            return corners_prev

        if math.isnan(x1) or math.isnan(y1) or math.isnan(x2) \
                or math.isnan(y2):
            return corners_prev

        return (x1, x2, y1, y2)

    def zoom_corners(self, corners_xy, zoom_factor):
        x1, x2, y1, y2 = corners_xy

        delx = abs(x2-x1)
        dely = abs(y2-y1)
        x_margin = util.sign(zoom_factor * delx * 0.5, x2 - x1)
        y_margin = util.sign(zoom_factor * dely * 0.5, y2 - y1)
        x1 = x1 - x_margin
        x2 = x2 + x_margin
        y1 = y1 - y_margin
        y2 = y2 + y_margin
        logger.debug("X, Y Zum: %f %f %f %f", x1, y1, x2, y2)

        return (x1, x2, y1, y2)

    def round_map_corners(self, corners_xy):
        x1, x2, y1, y2 = corners_xy
        x2b = util.nearest_int(x2)

        y1 = util.nearest_int(y1)
        y2 = util.nearest_int(y2)
        delx = (y2-y1)*self.scale
        if self.proj_type == const.MapProjection.CYL_EQU:
            delx *= 2.0
        x1 = util.nearest_int(x1)
        x2 = x1 + util.nearest_int(delx)
        if x2 <= x2b:
            x2 = x2b

        return (x1, x2, y1, y2)

    def calc_corners_lonlat(self, corners_xy):
        x1, x2, y1, y2 = corners_xy

        alonl, alatb = self.calc_lonlat(x1, y1)
        alonr, alatt = self.calc_lonlat(x2, y2)
        logger.debug("Corners: %f %f %f %f", alonl, alonr, alatb, alatt)

        # map exceeds limits
        if alatt > 90.0 or alatb < -90.0:
            logger.warning("map projection exceeds limits")
            logger.warning("Increase zoom or change/force projection")

        return (alonl, alonr, alatb, alatt)

    def need_pole_exclusion(self, corners_lonlat):
        # A child class may override this.
        return False

    def exclude_pole(self, corners_xy, corners_lonlat):
        x1, x2, y1, y2 = corners_xy
        alonl, alonr, alatb, alatt = corners_lonlat

        if alatt > 80.0:
            alatt = 80.0
            x2, y2 = self.calc_xy(alonr, alatt)
        if alatb < -80.0:
            alatb = -80.0
            x1, y1 = self.calc_xy(alonl, alatb)

        return (x1, x2, y1, y2), (alonl, alonr, alatb, alatt)

    def do_initial_estimates(self, map_box, center_loc):

        # the coordinate reference system must have been set up.
        logger.debug("Map Prj: %d", self.proj_type)
        logger.debug("Center : %f %f", center_loc[1], center_loc[0])
        logger.debug("Tangent: %f  Reflon: %f", self.tnglat, self.reflon)

        # find new map corners
        half_delta = map_box.grid_delta * 0.5
        if center_loc[1] <= -90.0 - map_box.grid_delta \
                or center_loc[1] >= 90.0 + map_box.grid_delta:
            lat1 = util.sign(90.0 - map_box.grid_delta, center_loc[1])
            lat2 = util.sign(90.0 - half_delta, center_loc[1])
            x1, y1 = self.calc_xy(center_loc[0] - half_delta, lat1)
            x2, y2 = self.calc_xy(center_loc[0] + half_delta, lat2)
        else:
            x1, y1 = self.calc_xy(center_loc[0] - half_delta,
                                  center_loc[1] - half_delta)
            x2, y2 = self.calc_xy(center_loc[0] + half_delta,
                                  center_loc[1] + half_delta)

        logger.debug("X, Y Set : %f %f %f %f", x1, y1, x2, y2)
        logger.debug("Grid corner, increment from mapbox or conndx : %f %f %f",
                     map_box.grid_corner[1],
                     map_box.grid_corner[0],
                     map_box.grid_delta)
        logger.debug("1st guess center : %f %f",
                     self.center_loc[1], self.center_loc[0])

        for j in range(map_box.sz[1]):
            for i in range(map_box.sz[0]):
                if map_box.hit_map[i, j] > 0:
                    plon = i * map_box.grid_delta + map_box.grid_corner[0]
                    plat = j * map_box.grid_delta + map_box.grid_corner[1]
                    if plon > 180.0:
                        plon -= 360.0
                    xc, yc = self.calc_xy(plon, plat)
                    x1 = min(x1, xc)
                    y1 = min(y1, yc)
                    x2 = max(x2, xc)
                    y2 = max(y2, yc)
        logger.debug("X, Y Ini: %f %f %f %f", x1, y1, x2, y2)
        self.corners_xy = (x1, x2, y1, y2)

        # find new map center
        xc = 0.5*(x1 + x2)
        yc = 0.5*(y1 + y2)
        qlon, qlat = self.calc_lonlat(xc, yc)
        logger.debug("Center : %f %f", qlat, qlon)
        self.center_loc = (qlon, qlat)

        # compute new map corners
        alonl, alatb = self.calc_lonlat(x1, y1)
        alonr, alatt = self.calc_lonlat(x2, y2)
        self.corners_lonlat = (alonl, alonr, alatb, alatt)
        logger.debug("Corners: %f %f %f %f", alonl, alonr, alatb, alatt)

    def sanity_check(self):
        # A child class may override this.
        return True

    def create_sane_projection(self, map_proj, zoom_factor, center_loc, scale,
                               grid_deltas):
        # A child class should override this if its sanity_check() can
        # return False.
        raise Exception("This should not happen")

    @abstractmethod
    def create_crs(self):
        pass


class PoleExcludingProjection(AbstractMapProjection):

    def __init__(self, map_proj, zoom_factor, center_loc, scale, grid_deltas):
        super(PoleExcludingProjection, self).__init__(map_proj, zoom_factor,
                                                      center_loc, scale,
                                                      grid_deltas)

    def sanity_check(self):
        if self.need_pole_exclusion(self.corners_lonlat):
            logger.debug("Force polar stereographic!")
            return False
        return True

    def create_sane_projection(self, map_proj, zoom_factor, center_loc, scale,
                               grid_deltas):
        return PolarProjection(map_proj, zoom_factor, center_loc, scale,
                               grid_deltas)

    def need_pole_exclusion(self, corners_lonlat):
        alonl, alonr, alatb, alatt = corners_lonlat
        return True if alatt > 80.0 or alatb < -80.0 else False


class LambertProjection(PoleExcludingProjection):

    def __init__(self, map_proj, zoom_factor, center_loc, scale, grid_deltas):
        super(LambertProjection, self).__init__(map_proj, zoom_factor,
                                                center_loc, scale, grid_deltas)
        self.proj_type = const.MapProjection.LAMBERT
        self.crs = self.create_crs()

    def get_tangent_lat(self, center_loc):
        return center_loc[1]

    def create_crs(self):
        if self.tnglat >= 84.0:
            pars = (self.tnglat-6.0, 89.99)
        elif self.tnglat <= -84.0:
            pars = (-89.99, self.tnglat+6.0)
        else:
            pars = (self.tnglat-6.0, self.tnglat+6.0)
        cutoff_val = -60.0 if self.tnglat > 0 else 60.0
        return cartopy.crs.LambertConformal(central_longitude=self.reflon,
                                            central_latitude=self.tnglat,
                                            standard_parallels=pars,
                                            false_easting=1.0*1000.0,
                                            false_northing=1.0*1000.0,
                                            cutoff=cutoff_val)


class PolarProjection(AbstractMapProjection):

    def __init__(self, map_proj, zoom_factor, center_loc, scale, grid_deltas):
        super(PolarProjection, self).__init__(map_proj, zoom_factor,
                                              center_loc, scale, grid_deltas)
        self.proj_type = const.MapProjection.POLAR
        self.crs = self.create_crs()

    def get_tangent_lat(self, center_loc):
        return 90.0 if center_loc[1] >= 0.0 else -90.0

    def create_crs(self):
        if self.center_loc[1] >= 0.0:
            return cartopy.crs.NorthPolarStereo(central_longitude=self.reflon)
        else:
            return cartopy.crs.SouthPolarStereo(central_longitude=self.reflon)


class MercatorProjection(PoleExcludingProjection):

    def __init__(self, map_proj, zoom_factor, center_loc, scale, grid_deltas):
        super(MercatorProjection, self).__init__(map_proj, zoom_factor,
                                                 center_loc, scale,
                                                 grid_deltas)
        self.proj_type = const.MapProjection.MERCATOR
        self.crs = self.create_crs()

    def get_tangent_lat(self, center_loc):
        return 0.0

    def create_crs(self):
        return cartopy.crs.Mercator(central_longitude=self.reflon,
                                    min_latitude=-80.0,
                                    max_latitude=84.0,
                                    latitude_true_scale=self.tnglat,
                                    false_easting=1.0*1000.0,
                                    false_northing=1.0*1000.0)


class CylindricalEquidistantProjection(AbstractMapProjection):

    def __init__(self, map_proj, zoom_factor, center_loc, scale, grid_deltas):
        super(CylindricalEquidistantProjection, self).__init__(map_proj,
                                                               zoom_factor,
                                                               center_loc,
                                                               scale,
                                                               grid_deltas)
        self.proj_type = const.MapProjection.CYL_EQU
        self.crs = self.create_crs()

    def get_tangent_lat(self, center_loc):
        return 0.0

    def create_crs(self):
        return cartopy.crs.LambertCylindrical(central_longitude=self.reflon)


class WebMercatorProjection(PoleExcludingProjection):

    def __init__(self, map_proj, zoom_factor, center_loc, scale, grid_deltas):
        super(WebMercatorProjection, self).__init__(map_proj, zoom_factor,
                                                    center_loc, scale,
                                                    grid_deltas)
        self.proj_type = const.MapProjection.WEB_MERCATOR
        self.crs = self.create_crs()

    def get_tangent_lat(self, center_loc):
        return 0.0

    def create_crs(self):
        return WebMercatorCRS(self.reflon)


class WebMercatorCRS(cartopy.crs.Projection):
    """Derived from cartopy.crs.epsg(3857). WebMercatorCRS does not require
       Internet connection. It can set the central longitude to a non-zero
       value, which is useful when an extent crosses the dateline."""

    def __init__(self, central_longitude):
        self.central_longitude = central_longitude

        globe = cartopy.crs.Globe(semimajor_axis="6378137",
                                  semiminor_axis="6378137", nadgrids="@null")
        other_terms = [['proj', 'merc'],
                       ['lat_ts', '0.0'], ['lon_0', central_longitude],
                       ['x_0', '0.0'], ['y_0', '0'],
                       ['k', '1.0'],
                       ['units', 'm'],
                       ['wktext', None], ['no_defs', None]]
        super(WebMercatorCRS, self).__init__(other_terms, globe)

        minlon, maxlon = self._determine_longitude_bounds(central_longitude)
        x0, x1, y0, y1 = (minlon, maxlon, -85.06, 85.06)
        geodetic = cartopy.crs.Geodetic()
        lons = numpy.array([x0, x0, x1, x1])
        lats = numpy.array([y0, y1, y1, y0])
        points = self.transform_points(geodetic, lons, lats)
        x = points[:, 0]
        y = points[:, 1]
        self.bounds = (x.min(), x.max(), y.min(), y.max())

    def __repr__(self):
        return 'WebMercatorCRS(central_longitude={})' \
          .format(self.central_longitude)

    @property
    def boundary(self):
        x0, x1, y0, y1 = self.bounds
        return shapely.geometry.LineString([(x0, y0), (x0, y1), (x1, y1),
                                            (x1, y0), (x0, y0)])

    @property
    def x_limits(self):
        x0, x1, y0, y1 = self.bounds
        return (x0, x1)

    @property
    def y_limits(self):
        x0, x1, y0, y1 = self.bounds
        return (y0, y1)

    @property
    def threshold(self):
        x0, x1, y0, y1 = self.bounds
        return min(x1 - x0, y1 - y0) / 100.
