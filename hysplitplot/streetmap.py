from abc import ABC, abstractmethod
import contextily
import copy
import geopandas
import logging
import matplotlib.pyplot as plt
import numpy
import os
import shapely.geometry
import urllib

from hysplitplot import const, mapfile, util
from matplotlib.lines import segment_hits
from numpy import isin


logger = logging.getLogger(__name__)


class MapBackgroundFactory:
    
    @staticmethod
    def create_instance(projection_type, use_street_map, street_map_selector):
        if projection_type == const.MapProjection.WEB_MERCATOR and use_street_map:
            if street_map_selector == const.StreetMap.STAMEN_TERRAIN:
                o = StamenStreetMap("TERRAIN")
            elif street_map_selector == const.StreetMap.STAMEN_TONER:
                o = StamenStreetMap("TONER")
            else:
                logger.warning("Change unknown street map type {} to 0.".format(street_map_selector))
                o = StamenStreetMap("TERRAIN")
        else:
            o = HYSPLITMapBackground()
            
        return o


class AbstractMapBackground(ABC):
    
    def __init__(self):
        self.map_color = "#1f77b4"
        self.color_mode = const.Color.COLOR
        self.lat_lon_label_interval_option = const.LatLonLabel.AUTO
        self.lat_lon_label_interval = 1.0
        self.fix_map_color_fn = None
        self.text_objs = []
    
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

    def clear_text_objs(self):
        # clear labels from a previous call
        for t in self.text_objs:
            t.remove()
        self.text_objs.clear()

    @abstractmethod
    def draw_underlay(self, ax, corners_xy, crs):
        pass

    @abstractmethod
    def update_extent(self, ax, projection, data_crs):
        pass
    
    @abstractmethod
    def read_background_map(self, filename):
        pass


class HYSPLITMapBackground(AbstractMapBackground):
        
    _GRIDLINE_DENSITY = 0.25        # 4 gridlines at minimum in each direction

    def __init__(self):
        super(HYSPLITMapBackground, self).__init__()
        self.background_maps = []
        self.frozen_collection_count = None

    def read_background_map(self, filename):
        self.background_maps.clear()
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
        # Work around a map projection issue to remove spurious horizontal lines on the background map.
        xmin, xmax, _, _ = corners_xy
        outside = lambda x: x < xmin or x > xmax
        a = []
        # Examine all geometry objects and check if a line segment goes from min to max or vice versa.
        for o in map.values:
            # Show the object if it is within the view.
            x0, _, x1, _ = o.bounds
            if x0 >= xmin and x1 <= xmax:
                a.append( o )
                continue
            # Check min-max crossing
            if isinstance(o, shapely.geometry.LineString):
                if not self._is_crossing_bounds(o.xy[0], outside):
                    a.append( o )
            elif isinstance(o, shapely.geometry.Polygon):
                if not self._is_crossing_bounds(o.exterior.xy[0], outside):
                    a.append( o )
            elif isinstance(o, shapely.geometry.MultiLineString):
                crossing = False
                for g in o.geoms:
                    if self._is_crossing_bounds(g.xy[0], outside):
                        crossing = True
                        break
                if not crossing:
                    a.append( o )
            elif isinstance(o, shapely.geometry.MultiPolygon):
                crossing = False
                for g in o.geoms:
                    if self._is_crossing_bounds(g.exterior.xy[0], outside):
                        crossing = True
                        break
                if not crossing:
                    a.append( o )
            else:
                raise Exception("Unexpected geometry type {}".format(o))
        gs = geopandas.GeoSeries(a)
        gs.crs = crs.proj4_init
        return gs
    
    def draw_underlay(self, axes, corners_xy, crs):
        for o in self.background_maps:
            if isinstance(o.map, geopandas.geoseries.GeoSeries):
                fixed = self._remove_spurious_hlines( o.map.to_crs(crs.proj4_init), corners_xy, crs )
            else:
                fixed = o.map.copy()
                fixed['geometry'] = self._remove_spurious_hlines( fixed['geometry'].to_crs(crs.proj4_init), corners_xy, crs )
            clr = self._fix_map_color(o.linecolor, self.color_mode)
            fixed.plot(ax=axes, linestyle=o.linestyle, linewidth=o.linewidth, facecolor="none", edgecolor=clr)        
    
    def update_extent(self, ax, projection, data_crs):
        clr = self._fix_map_color(self.map_color, self.color_mode)
        self._update_gridlines(ax,
                               projection,
                               data_crs,
                               clr,
                               self.lat_lon_label_interval_option,
                               self.lat_lon_label_interval)
    
    def _erase_gridlines(self, axes):
        # From reading cartopy source code, gridliners are added to the collecitons.
        axes._gridliners.clear()

        # this works because gridlines are the last arrivals to the collections.               
        if self.frozen_collection_count is None:
            self.frozen_collection_count = len(axes.collections)
        else:
            a = copy.copy(axes.collections)
            for k in range(self.frozen_collection_count, len(a)):
                axes.collections.remove( a[k] )
    
    def _update_gridlines(self, axes, projection, data_crs, map_color, latlon_label_opt, latlon_spacing):
        deltax = deltay = self._get_gridline_spacing(projection.corners_lonlat,
                                                     latlon_label_opt,
                                                     latlon_spacing)
        ideltax = ideltay = int(deltax*10.0)
        if ideltax == 0:
            logger.debug("not updating gridlines because deltas are %f, %f", deltax, deltay)
            return

        lonlat_ext = axes.get_extent(data_crs)
        logger.debug("determining gridlines for extent %s using deltas %f, %f", lonlat_ext, deltax, deltay)

        alonl, alonr, alatb, alatt = lonlat_ext
        # check for crossing dateline
        if util.sign(1.0, alonl) != util.sign(1.0, alonr) and alonr < 0.0:
            alonr += 360.0
            
        xticks = self._collect_tick_values(-1800, 1800, ideltax, 0.1, lonlat_ext[0:2])
        logger.debug("gridlines at lons %s", xticks)
        if len(xticks) == 0 or deltax >= abs(self._GRIDLINE_DENSITY*(alonr - alonl)):
            # recompute deltax with zero latitude span and try again
            deltax = self._calc_gridline_spacing([alonl, alonr, alatb, alatb])
            ideltax = int(deltax*10.0)
            xticks = self._collect_tick_values(-1800, 1800, ideltax, 0.1, lonlat_ext[0:2])
            logger.debug("gridlines at lats %s", xticks)
            
        yticks = self._collect_tick_values(-900+ideltay, 900, ideltay, 0.1, lonlat_ext[2:4])
        logger.debug("gridlines at lats %s", yticks)
        if len(yticks) == 0 or deltay >= abs(self._GRIDLINE_DENSITY*(alatt - alatb)):
            # recompute deltay with zero longitude span and try again
            deltay = self._calc_gridline_spacing([alonl, alonl, alatb, alatt])
            ideltay = int(deltay*10.0)
            yticks = self._collect_tick_values(-900+ideltay, 900, ideltay, 0.1, lonlat_ext[2:4])
            logger.debug("gridlines at lats %s", yticks)

        # erase gridlines
        self._erase_gridlines(axes)
        
        # draw dotted gridlines
        kwargs = {"crs": data_crs, "linestyle": ":", "linewidth": 0.5, "color": map_color}
        if len(xticks) > 0:
            kwargs["xlocs"] = xticks
        if len(yticks) > 0:
            kwargs["ylocs"] = yticks
        gl = axes.gridlines(**kwargs)
        
        # lat/lon line labels
        self._draw_latlon_labels(axes, projection, data_crs, deltax, deltay, map_color)
            
    def _get_gridline_spacing(self, corners_lonlat, latlon_label_opt, latlon_spacing):
        if latlon_label_opt == const.LatLonLabel.NONE:
            return 0.0
        elif latlon_label_opt == const.LatLonLabel.SET:
            return latlon_spacing
        else:
            return self._calc_gridline_spacing(corners_lonlat)

    def _calc_gridline_spacing(self, corners_lonlat):
        # potential gridline spacings
        spacings = [45.0, 30.0, 20.0, 15.0, 10.0, 5.0, 2.0, 1.0, 0.5, 0.2]

        alonl, alonr, alatb, alatt = corners_lonlat

        # check for crossing dateline
        if util.sign(1.0, alonl) != util.sign(1.0, alonr) and alonr < 0.0:
            alonr += 360.0

        logger.debug("calculating gridline spacing for lons %f, %f and lats %f, %f", alonl, alonr, alatb, alatt)

        # interval to have at least 4 lat/lon lines on a map
        ref = max(abs(alatt-alatb)*self._GRIDLINE_DENSITY, abs(alonl-alonr)*self._GRIDLINE_DENSITY, spacings[-1])
        logger.debug("searching optimal spacing starting from %f", ref)
                     
        delta = None
        for s in spacings:
            if s <= ref:
                delta = s
                logger.debug("optimal spacing %f", delta)
                break;
        
        if delta is None:
            delta = spacings[-1]
            logger.debug("optimal spacing %f", delta)
            
        return delta

    @staticmethod
    def _collect_tick_values(istart, iend, idelta, scale, lmt):
        amin, amax = lmt
        logger.debug("collecting tick values in the range [%f, %f] using spacing %f", amin, amax, scale*idelta)
        state = 0
        list = []
        for i in range(istart, iend, idelta):
            v = i * scale
            if state == 0:
                if v >= amin:
                    list.append( util.make_int_if_same((i - idelta) * scale) )
                    list.append( util.make_int_if_same(v) )
                    state = 1
            elif state == 1:
                list.append( util.make_int_if_same(v) )
                if v > amax:
                    state = 2
            
        return list

    def _draw_latlon_labels(self, axes, projection, data_crs, deltax, deltay, map_color):
        logger.debug("latlon labels at intervals %f, %f", deltax, deltay)
        ideltax = int(deltax*10.0)
        ideltay = int(deltay*10.0)
        if ideltax == 0 or ideltay == 0:
            logger.debug("not drawing latlon labels because deltas are %f, %f", deltax, deltay)
            return
        
        self.clear_text_objs()
        
        x1, x2, y1, y2 = projection.corners_xy
        clon, clat = projection.calc_lonlat(0.5*(x1+x2), 0.5*(y1+y2))
        clon = util.nearest_int(clon/deltax)*deltax
        clat = util.nearest_int(clat/deltay)*deltay
        logger.debug("label reference at lon %f, lat %f", clon, clat)
            
        # lon labels
        lat = (clat - 0.5 * deltay) if (clat > 80.0) else clat + 0.5 * deltay
        for k in range(-(1800-ideltax), 1800, ideltax):
            lon = 0.1 * k
            
            # 5/17/2019
            # The clip_on option does not work with the eps/ps renderer. It is done here.
            ax, ay = axes.transLimits.transform(projection.crs.transform_point(lon, lat, data_crs))
            if ax < 0.0 or ax > 1.0 or ay < 0.0 or ay > 1.0:
                continue
            
            str = "{0:.1f}".format(lon) if deltax < 1.0 else "{0}".format(int(lon))
            t = axes.text(lon, lat, str, transform=data_crs,
                          horizontalalignment="center", verticalalignment="center",
                          color=map_color, clip_on=True)
            self.text_objs.append(t)
        
        # lat labels
        lon = clon + 0.5 * deltax
        for k in range(-(900-ideltay), 900, ideltay):
            lat = 0.1 * k
                        
            # 5/17/2019
            # The clip_on option does not work with the eps/ps renderer. It is done here.
            ax, ay = axes.transLimits.transform(projection.crs.transform_point(lon, lat, data_crs))
            if ax < 0.0 or ax > 1.0 or ay < 0.0 or ay > 1.0:
                continue
            
            str = "{0:.1f}".format(lat) if deltay < 1.0 else "{0}".format(int(lat))
            t = axes.text(lon, lat, str, transform=data_crs,
                          horizontalalignment="center", verticalalignment="center",
                          color=map_color, clip_on=True)
            self.text_objs.append(t)

class AbstractStreetMap(AbstractMapBackground):
    
    def __init__(self):
        super(AbstractStreetMap, self).__init__()
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
    def tile_url(self):
        pass
    
    @property
    @abstractmethod
    def attribution(self):
        pass
    
    def _compute_tile_widths(self):
        tile_widths = numpy.empty(self.max_zoom - self.min_zoom + 1, dtype=float)
        w = 360.0
        for k in range(len(tile_widths)):
            tile_widths[k] = w; w *= 0.5
        return tile_widths

    def _compute_initial_zoom(self, lonl, latb, lonr, latt):
        """Find a zoom level that yields about 1 tile horizontally."""
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
        # Nothing to do
        pass
    
    def update_extent(self, ax, projection, data_crs):
        self.draw(ax,
                  projection.corners_xy,
                  projection.corners_lonlat)

    def draw(self, ax, corners_xy, corners_lonlat):
        # Do nothing if the spatial extent has not changed.
        if self.last_extent == ax.axis():
            return
        
        lonl, lonr, latb, latt = corners_lonlat
        zoom = self._compute_initial_zoom(lonl, latb, lonr, latt)
            
        # The return value of ax.axis() is assumed to be the same as corners_xy. 
        xmin, xmax, ymin, ymax = corners_xy
        
        # Find a zoom level that does not fail HTTP pulls.
        ntiles = 0
        continueQ = True
        while continueQ:
            try:
                ntiles = contextily.howmany(xmin, ymin, xmax, ymax, zoom)
                if ntiles > 0:
                    basemap, extent = contextily.bounds2img(xmin, ymin, xmax, ymax, zoom=zoom, url=self.tile_url)
                continueQ = False
            except urllib.error.HTTPError as ex:
                logger.error("Could not pull street map images at zoom level {}: {}".format(zoom, ex))
                if zoom == 0:
                    continueQ = False
                else:
                    zoom -= 1

        if ntiles > 0:
            # Ad hoc fix because ax.imshow() incorrectly shows the basemap.
            if 0 == 1:
                ax.imshow(basemap, extent=extent, interpolation="bilinear")
            else:
                saved = None if ax is plt.gca() else plt.gca()
                if saved is not None:
                    plt.sca(ax)
                        
                plt.imshow(basemap, extent=extent, interpolation='bilinear')
                    
                if saved is not None:
                    plt.sca(saved)
        
            self.last_extent = corners_xy 
            
        ax.axis( corners_xy )
        
        self.clear_text_objs()
        
        str = " {}".format(self.attribution)
        t = ax.text(0, 0, str, fontsize=8,
                    horizontalalignment="left", verticalalignment="bottom",
                    transform=ax.transAxes)
        self.text_objs.append( t )


class StamenStreetMap(AbstractStreetMap):
    
    urls = {"TERRAIN": contextily.sources.ST_TERRAIN,
            "TONER": contextily.sources.ST_TONER_LITE}
    
    def __init__(self, stamen_type):
        super(StamenStreetMap, self).__init__()
        if stamen_type not in StamenStreetMap.urls:
            logger.warning("Change unknown type '%s' to 'TERRAIN'", stamen_type)
            stamen_type = "TERRAIN"
        self.__tile_url = StamenStreetMap.urls.get(stamen_type)
        self.__attribution = "Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL."
    
    @property
    def min_zoom(self):
        return 0
    
    @property
    def max_zoom(self):
        return 15 # 19 from openstreetmap.org. Reduced to 15 to avoid HTTP errors.
    
    @property
    def tile_url(self):
        return self.__tile_url
    
    @property
    def attribution(self):
        return self.__attribution

