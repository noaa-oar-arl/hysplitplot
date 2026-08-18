# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# streetmap.py
#
# Provides classes for drawing map background.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
import logging
import math
import os
import warnings
import contextily
import geopandas
import numpy
import shapely.geometry
from cartopy.mpl.gridliner import Gridliner

from . import const, mapfile, util, meta

logger = logging.getLogger(__name__)


class MapBackgroundFactory:

    @staticmethod
    def create_instance(projection, use_street_map, street_map_selector):
        if projection.proj_type == const.MapProjection.WEB_MERCATOR \
                and use_street_map:
            if street_map_selector == const.StreetMap.STREET:
                o = OpenStreetMap(projection)
            elif street_map_selector == const.StreetMap.TOPO:
                o = OpenTopoMap(projection)
            else:
                logger.warning("Change unknown street map type {} "
                               "to 0.".format(street_map_selector))
                o = OpenStreetMap(projection)
        else:
            o = HYSPLITMapBackground(projection)

        return o


class AbstractMapBackground(ABC):

    def __init__(self, projection):
        self.map_color = "#1f77b4"
        self.color_mode = const.Color.COLOR
        self.lat_lon_label_interval_option = const.LatLonLabel.AUTO
        self.lat_lon_label_interval = 1.0
        self.fix_map_color_fn = None
        self.text_objs = []
        self.projection = projection

    def set_color(self, colr):
        self.map_color = colr

    def set_color_mode(self, color_mode):
        self.color_mode = color_mode

    def override_fix_map_color_fn(self, fn):
        """fn is a function that takes two arguments, color and color_mode."""
        self.fix_map_color_fn = fn

    def set_lat_lon_label_option(self, label_opt, label_interval):
        self.lat_lon_label_interval_option = label_opt
        self.lat_lon_label_interval = label_interval

    def clear_text_objs(self, ax):
        # clear labels from a previous call
        for t in self.text_objs:
            logger.debug('deleting text %d %s', id(t), t.get_text())
            # Errors can occur when the rendering engine attempts to access
            # deleted text objects. An ad hoc solution is to mark these
            # objects as invisible rather than removing them.
            # t.remove()
            t.set_visible(False)
        self.text_objs.clear()

    @abstractmethod
    def draw_underlay(self, ax, corners_xy, crs):
        pass

    @abstractmethod
    def update_extent(self, ax, data_crs):
        pass

    @abstractmethod
    def read_background_map(self, filename):
        pass


class HYSPLITMapBackground(AbstractMapBackground):

    _GRIDLINE_DENSITY = 0.25  # 4 gridlines at minimum in each direction

    def __init__(self, projection):
        super(HYSPLITMapBackground, self).__init__(projection)
        self.background_maps = []

    def read_background_map(self, filename):
        self.background_maps.clear()
        try:
            if filename.startswith("shapefiles"):
                shapefiles = mapfile.ShapeFilesReader().read(filename)
                for sf in shapefiles:
                    map = mapfile.ShapeFileConverter.convert(sf)
                    self.background_maps.append(map)
            else:
                fname = self._fix_arlmap_filename(filename)
                if fname is None:
                    logger.warning("map background file %s not found", fname)
                else:
                    arlmap = mapfile.ARLMap().get_reader().read(fname)
                    for m in mapfile.ARLMapConverter.convert(arlmap):
                        self.background_maps.append(m)
        except ValueError as ex:
            logger.error(str(ex))

    @staticmethod
    def _fix_arlmap_filename(filename):
        if os.path.exists(filename):
            return filename

        candidates = ["graphics/arlmap", "../graphics/arlmap"]
        for f in candidates:
            if os.path.exists(f):
                return f

        return None

    def _fix_map_color(self, clr, color_mode):
        if self.fix_map_color_fn is not None:
            return self.fix_map_color_fn(clr, color_mode)
        return clr if color_mode != const.Color.BLACK_AND_WHITE else 'k'

    def _is_crossing_bounds(self, xs, outside):
        for k, x in enumerate(xs[1:]):
            # Detect a sign change outside the view.
            if xs[k] * x < 0 and (outside(xs[k]) or outside(x)):
                return True
        return False

    def _remove_spurious_hlines(self, map, corners_xy, crs):
        if not isinstance(map, geopandas.geoseries.GeoSeries):
            raise Exception("Unexpected map type {}".format(map))
        # Work around a map projection issue to remove spurious horizontal
        # lines on the background map.
        xmin, xmax, _, _ = corners_xy
        outside = lambda x: x < xmin or x > xmax
        a = []
        # Examine all geometry objects and check if a line segment goes
        # from min to max or vice versa.
        for o in map.values:
            # Show the object if it is within the view.
            x0, _, x1, _ = o.bounds
            if x0 >= xmin and x1 <= xmax:
                a.append(o)
                continue
            # Check min-max crossing
            if isinstance(o, shapely.geometry.LineString):
                if not self._is_crossing_bounds(o.xy[0], outside):
                    a.append(o)
            elif isinstance(o, shapely.geometry.Polygon):
                if not self._is_crossing_bounds(o.exterior.xy[0], outside):
                    a.append(o)
            elif isinstance(o, shapely.geometry.MultiLineString):
                crossing = False
                for g in o.geoms:
                    if self._is_crossing_bounds(g.xy[0], outside):
                        crossing = True
                        break
                if not crossing:
                    a.append(o)
            elif isinstance(o, shapely.geometry.MultiPolygon):
                crossing = False
                for g in o.geoms:
                    if self._is_crossing_bounds(g.exterior.xy[0], outside):
                        crossing = True
                        break
                if not crossing:
                    a.append(o)
            else:
                raise Exception("Unexpected geometry type {}".format(o))
        gs = geopandas.GeoSeries(a)
        gs.crs = crs.proj4_init
        return gs

    def draw_underlay(self, axes, corners_xy, crs):
        proj4_pars = crs.proj4_init
        for o in self.background_maps:
            if isinstance(o.map, geopandas.geoseries.GeoSeries):
                fixed = self._remove_spurious_hlines(
                    o.map.to_crs(proj4_pars), corners_xy, crs)
            else:
                fixed = o.map.copy()
                fixed['geometry'] = self._remove_spurious_hlines(
                    fixed['geometry'].to_crs(proj4_pars), corners_xy, crs)
            clr = self._fix_map_color(o.linecolor, self.color_mode)
            fixed.plot(ax=axes, linestyle=o.linestyle, linewidth=o.linewidth,
                       facecolor="none", edgecolor=clr)

    def update_extent(self, ax, data_crs):
        clr = self._fix_map_color(self.map_color, self.color_mode)
        self._update_gridlines(ax,
                               self.projection,
                               clr,
                               self.lat_lon_label_interval_option,
                               self.lat_lon_label_interval)

    def _erase_gridlines(self, axes):
        for gl in axes.findobj(match=Gridliner):
           if gl is not None:
              gl.remove()

    def _update_gridlines(self, axes, projection, map_color,
                          latlon_label_opt, latlon_spacing):
        # print plot range in lat-lon
        x1, x2 = axes.get_xlim()
        y1, y2 = axes.get_ylim()
        logger.debug("plot data limits: x %f %f, y %f %f", x1, x2, y1, y2)
        l, b = projection.calc_lonlat(x1, y1)
        r, t = projection.calc_lonlat(x2, y2)
        logger.debug("plot data limits: l %f, b %f, r %f, t %f", l, b, r, t)

        deltax = deltay = self._get_gridline_spacing(projection.corners_lonlat,
                                                     latlon_label_opt,
                                                     latlon_spacing)
        ideltax = ideltay = int(deltax * 100.0)
        if ideltax == 0:
            logger.debug("not updating gridlines because deltas are %f, %f",
                         deltax, deltay)
            return

        # Filter out a cartopy warning to avoid user confusion.
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',
                                    message='Approximating coordinate system*',
                                    category=UserWarning)
            lonlat_ext = axes.get_extent(projection.data_crs)
        logger.debug("determining gridlines for extent %s using deltas %f, %f",
                     lonlat_ext, deltax, deltay)

        alonl, alonr, alatb, alatt = lonlat_ext
        if util.is_crossing_date_line(alonl, alonr):
            alonr += 360.0

        xticks = self._collect_tick_values(-18000, 18000, ideltax,
                                           0.01, lonlat_ext[0:2])
        logger.debug("gridlines at lons %s", xticks)
        if len(xticks) == 0 \
                or deltax >= abs(self._GRIDLINE_DENSITY * (alonr - alonl)):
            # recompute deltax with zero latitude span and try again
            deltax = self._calc_gridline_spacing([alonl, alonr, alatb, alatb])
            ideltax = int(deltax * 100.0)
            xticks = self._collect_tick_values(-18000, 18000, ideltax,
                                               0.01, lonlat_ext[0:2])
            logger.debug("gridlines at lons %s", xticks)

        yticks = self._collect_tick_values(-9000 + ideltay, 9000, ideltay,
                                           0.01, lonlat_ext[2:4])
        logger.debug("gridlines at lats %s", yticks)
        if len(yticks) == 0 \
                or deltay >= abs(self._GRIDLINE_DENSITY * (alatt - alatb)):
            # recompute deltay with zero longitude span and try again
            deltay = self._calc_gridline_spacing([alonl, alonl, alatb, alatt])
            ideltay = int(deltay * 100.0)
            yticks = self._collect_tick_values(-9000 + ideltay, 9000, ideltay,
                                               0.01, lonlat_ext[2:4])
            logger.debug("gridlines at lats %s", yticks)

        # erase gridlines
        self._erase_gridlines(axes)

        # draw dotted gridlines
        kwargs = {"crs": projection.data_crs, "linestyle": ":",
                  "linewidth": 0.5, "color": map_color}
        if len(xticks) > 0:
            kwargs["xlocs"] = xticks
        if len(yticks) > 0:
            kwargs["ylocs"] = yticks
        axes.gridlines(**kwargs)

        # lat/lon line labels
        self._draw_latlon_labels(axes, projection,
                                 deltax, deltay, map_color)

    def _get_gridline_spacing(self, corners_lonlat, latlon_label_opt,
                              latlon_spacing):
        if latlon_label_opt == const.LatLonLabel.NONE:
            return 0.0
        elif latlon_label_opt == const.LatLonLabel.SET:
            return latlon_spacing
        else:
            return self._calc_gridline_spacing(corners_lonlat)

    def _calc_gridline_spacing(self, corners_lonlat):
        # potential gridline spacings
        spacings = [45.0, 30.0, 20.0, 15.0, 10.0, 5.0, 2.0, 1.0, 0.5, 0.2,
                    0.1, 0.05, 0.02]

        alonl, alonr, alatb, alatt = corners_lonlat
        if util.is_crossing_date_line(alonl, alonr):
            alonr += 360.0
        if math.isnan(alatb):
            alatb = self.projection.crs.y_limits[0]
        if math.isnan(alatt):
            alatt = self.projection.crs.y_limits[1]

        logger.debug("calculating gridline spacing for lons %f, %f and "
                     "lats %f, %f", alonl, alonr, alatb, alatt)

        # interval to have at least 4 lat/lon lines on a map
        ref = max(abs(alatt - alatb) * self._GRIDLINE_DENSITY,
                  abs(alonl - alonr) * self._GRIDLINE_DENSITY, spacings[-1])
        logger.debug("searching optimal spacing starting from %f", ref)

        delta = None
        for s in spacings:
            if s <= ref:
                delta = s
                logger.debug("optimal spacing %f", delta)
                break

        if delta is None:
            delta = spacings[-1]
            logger.debug("optimal spacing %f", delta)

        return delta

    @staticmethod
    def _collect_tick_values(istart, iend, idelta, scale, lmt):
        amin, amax = lmt
        logger.debug("collecting tick values in the range [%f, %f] "
                     "using spacing %f", amin, amax, scale * idelta)
        state = 0
        list = []
        for i in range(istart, iend, idelta):
            v = i * scale
            if state == 0:
                if v >= amin:
                    list.append(util.make_int_if_same((i - idelta) * scale))
                    list.append(util.make_int_if_same(v))
                    state = 1
            elif state == 1:
                list.append(util.make_int_if_same(v))
                if v > amax:
                    state = 2

        return list

    def _draw_latlon_labels(self, axes, projection, deltax, deltay,
                            map_color):
        logger.debug("latlon labels at intervals %f, %f", deltax, deltay)
        ideltax = int(deltax * 100.0)
        ideltay = int(deltay * 100.0)
        if ideltax == 0 or ideltay == 0:
            logger.debug("not drawing latlon labels because deltas are %f, %f",
                         deltax, deltay)
            return

        self.clear_text_objs(axes)

        x1, x2, y1, y2 = projection.corners_xy
        clon, clat = projection.calc_lonlat(0.5 * (x1 + x2), 0.5 * (y1 + y2))
        clon = util.nearest_int(clon / deltax) * deltax
        clat = util.nearest_int(clat / deltay) * deltay
        logger.debug("label reference at lon %f, lat %f", clon, clat)

        # lon labels
        lat = (clat - 0.5 * deltay) if (clat > 80.0) else clat + 0.5 * deltay
        for k in range(-(18000 - ideltax), 18000, ideltax):
            lon = 0.01 * k

            # 5/17/2019
            # The clip_on option does not work with the eps/ps renderer.
            # Clipping is done here.
            ax, ay = axes.transLimits.transform(projection.calc_xy(lon, lat))
            if ax < 0.0 or ax > 1.0 or ay < 0.0 or ay > 1.0:
                # logger.debug('out-of-range lon %f, lat %f: ax %f, ay %f',
                #             lon, lat, ax, ay)
                continue

            if deltax < 0.1:
                str = "{0:.2f}".format(lon)
            elif deltax < 1.0:
                str = "{0:.1f}".format(lon)
            else:
                str = "{0}".format(int(lon))
            t = axes.text(lon, lat, str, transform=projection.data_crs,
                          horizontalalignment="center",
                          verticalalignment="center",
                          color=map_color, clip_on=True)
            self.text_objs.append(t)
            logger.debug('new lon label %d %s', id(t), t.get_text())

        # lat labels
        lon = clon + 0.5 * deltax
        for k in range(-(9000 - ideltay), 9000, ideltay):
            lat = 0.01 * k

            # 5/17/2019
            # The clip_on option does not work with the eps/ps renderer.
            # Clipping is done here.
            ax, ay = axes.transLimits.transform(projection.calc_xy(lon, lat))
            if ax < 0.0 or ax > 1.0 or ay < 0.0 or ay > 1.0:
                # logger.debug('out-of-range lon %f, lat %f: ax %f, ay %f',
                #             lon, lat, ax, ay)
                continue

            if deltay < 0.1:
                str = "{0:.2f}".format(lat)
            elif deltay < 1.0:
                str = "{0:.1f}".format(lat)
            else:
                str = "{0}".format(int(lat))
            t = axes.text(lon, lat, str, transform=projection.data_crs,
                          horizontalalignment="center",
                          verticalalignment="center",
                          color=map_color, clip_on=True)
            self.text_objs.append(t)
            logger.debug('new lat label %d %s', id(t), t.get_text())


class AbstractStreetMap(AbstractMapBackground):

    def __init__(self, projection):
        super(AbstractStreetMap, self).__init__(projection)
        self.tile_widths = self._compute_tile_widths()
        self.last_extent = None

    @property
    @abstractmethod
    def min_zoom(self):
        pass

    @property
    @abstractmethod
    def max_zoom(self):
        pass

    @property
    @abstractmethod
    def tile_provider(self):
        pass

    def _compute_tile_widths(self):
        tile_widths = numpy.empty(self.max_zoom - self.min_zoom + 1,
                                  dtype=float)
        w = 360.0
        for k in range(len(tile_widths)):
            tile_widths[k] = w
            w *= 0.5
        return tile_widths

    def _compute_initial_zoom(self, lonl, latb, lonr, latt):
        """Find a zoom level that yields about 1 tile horizontally."""
        if util.is_crossing_date_line(lonl, lonr):
            dlon = 180.0 - lonl + lonr + 180.0
        else:
            dlon = abs(lonr - lonl)
        for k in range(len(self.tile_widths)):
            tile_count = dlon / self.tile_widths[k]
            if int(tile_count) >= 1:
                return k
        return self.max_zoom

    def read_background_map(self, filename):
        # Nothing to do
        pass

    def draw_underlay(self, ax, corners_xy, crs):
        # Reset the extent for a new plot.
        self.last_extent = None

    def update_extent(self, ax, data_crs):
        self.draw(ax,
                  self.projection.corners_xy,
                  self.projection.corners_lonlat)

    def draw(self, ax, corners_xy, corners_lonlat):
        # Do nothing if the spatial extent has not changed.
        if self.last_extent == ax.axis():
            return

        # Find a zoom level that does not fail HTTP pulls.
        lonl, lonr, latb, latt = corners_lonlat
        zoom = self._compute_initial_zoom(lonl, latb, lonr, latt)
        logger.debug('draw: corners_xy %s', corners_xy)
        logger.debug('draw: corners_lonlat %s', corners_lonlat)

        # User-Agent string is required per OpenStreetMap policy
        default_user_agent = f'HYSPLITPLOT/{meta.__version__}' \
                              ' (contact: arl.webmaster@noaa.gov)'
        custom_headers = {
            "User-Agent": os.environ.get('OSM_USER_AGENT', default_user_agent)
        }
        contextily.add_basemap(ax, crs=self.projection.crs,
                               source=self.tile_provider,
                               headers=custom_headers,
                               zoom=zoom)
        self.last_extent = corners_xy


class StamenStreetMap(AbstractStreetMap):

    providers = {"TERRAIN": contextily.providers.Stadia.StamenTerrain,
            "TONER": contextily.providers.Stadia.StamenTonerLite}

    def __init__(self, projection, stamen_type):
        super(StamenStreetMap, self).__init__(projection)
        if stamen_type not in StamenStreetMap.providers:
            logger.warning("Change unknown type '%s' to 'TERRAIN'",
                           stamen_type)
            stamen_type = "TERRAIN"
        self.__tile_provider = StamenStreetMap.providers.get(stamen_type)

    @property
    def min_zoom(self):
        return 0

    @property
    def max_zoom(self):
        # 19 from openstreetmap.org.
        # Reduced to 15 to avoid HTTP errors.
        return 15

    @property
    def tile_provider(self):
        return self.__tile_provider


class OpenStreetMap(AbstractStreetMap):

    def __init__(self, projection):
        super(OpenStreetMap, self).__init__(projection)
        self.__tile_provider = contextily.providers.OpenStreetMap.Mapnik

    @property
    def min_zoom(self):
        return 0

    @property
    def max_zoom(self):
        # 19 from openstreetmap.org.
        # Reduced to 15 to avoid HTTP errors.
        return 15

    @property
    def tile_provider(self):
        return self.__tile_provider


class OpenTopoMap(AbstractStreetMap):

    def __init__(self, projection):
        super(OpenTopoMap, self).__init__(projection)
        self.__tile_provider = contextily.providers.OpenTopoMap

    @property
    def min_zoom(self):
        return 0

    @property
    def max_zoom(self):
        # 19 from openstreetmap.org.
        # Reduced to 15 to avoid HTTP errors.
        return 15

    @property
    def tile_provider(self):
        return self.__tile_provider
