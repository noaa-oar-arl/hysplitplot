import logging
import os
import cartopy.crs
import matplotlib.patches
import pytz
from timezonefinder import TimezoneFinder
from hysplit4 import util, const, mapfile, logo, labels, cmdline, stnplot
from abc import abstractmethod


logger = logging.getLogger(__name__)


class AbstractPlotSettings:
    
    def __init__(self):
        self.map_background = "../graphics/arlmap"
        self.map_projection = const.MapProjection.AUTO
        self.zoom_factor = 0.50
        self.ring = False
        self.ring_number = -1
        # ring_number values:
        #       -1      skip all related code sections
        #        0      draw no circle but set square map scaling
        #        #      scale square map for # circles
        self.ring_distance = 0.0
        self.center_loc = [0.0, 0.0]    # lon, lat
        self.output_postscript = "output.ps"
        self.output_suffix = "ps"
        self.output_basename = "output"
        self.noaa_logo = False
        self.lat_lon_label_interval_option = const.LatLonLabel.AUTO
        self.lat_lon_label_interval = 1.0
        self.frames_per_file = const.Frames.ALL_FILES_ON_ONE
        self.gis_output = const.GISOutput.NONE
        self.kml_option = const.KMLOption.NONE
        self.use_source_time_zone = False   # for the --source-time-zone option
        
        # internally defined
        self.interactive_mode = True    # becomes False if the -o or -O option is specified.
        self.map_color = "#1f77b4"
        self.station_marker = "o"
        self.station_marker_color= "k"     # black
        self.station_marker_size = 6*6
        self.height_unit = const.HeightUnit.METERS
        
    
    def _process_cmdline_args(self, args0):
        
        args = cmdline.CommandLineArguments(args0)
        
        self.noaa_logo              = True if args.has_arg(["+n", "+N"]) else self.noaa_logo

        self.frames_per_file        = args.get_integer_value(["-f", "-F"], self.frames_per_file)
        
        if args.has_arg(["-g", "-G"]):
            self.ring = True
            str = args.get_value(["-g", "-G"])
            if str.count(":") > 0:
                self.ring_number, self.ring_distance = self.parse_ring_option(str)
            elif str == "":
                self.ring_number = 4
            else:
                self.ring_number = args.get_integer_value(["-g", "-G"], self.ring_number)
        
        if args.has_arg(["-h", "-H"]):
            str = args.get_value(["-h", "-H"])
            if str.count(":") > 0:
                self.center_loc = self.parse_map_center(str)
                if self.ring_number < 0:
                    self.ring_number = 0

        self.map_background         = args.get_string_value(["-j", "-J"], self.map_background)
        if self.map_background.startswith(".") and self.map_background.endswith("shapefiles"):
            logger.warning("enter -jshapefiles... not -j./shapefiles...")
                       
        if args.has_arg("-L"):
            str = args.get_value("-L")
            if str.count(":") > 0:
                self.lat_lon_label_interval = self.parse_lat_lon_label_interval(str)
                self.lat_lon_label_interval_option = const.LatLonLabel.SET
            else:
                self.lat_lon_label_interval_option = args.get_integer_value("-L", self.lat_lon_label_interval_option)
                self.lat_lon_label_interval_option = max(0, min(1, self.lat_lon_label_interval_option))
 
        self.map_projection         = args.get_integer_value(["-m", "-M"], self.map_projection)

        self.output_postscript      = args.get_string_value(["-o", "-O"], self.output_postscript)
        if args.has_arg(["-o", "-O"]):
            self.interactive_mode = False

        self.output_suffix          = args.get_string_value(["-p", "-P"], self.output_suffix)    
        
        self.output_postscript, self.output_basename, self.output_suffix = \
            util.normalize_output_filename(self.output_postscript, self.output_suffix)
                
        if args.has_arg(["-z", "-Z"]):
            self.zoom_factor        = self.parse_zoom_factor(args.get_value(["-z", "-Z"]))
        
        self.gis_output             = args.get_integer_value("-a", self.gis_output)
        self.kml_option             = args.get_integer_value("-A", self.kml_option)
        
        if args.has_arg(["--source-time-zone"]):
            self.use_source_time_zone   = True
            
    @staticmethod
    def parse_lat_lon_label_interval(str):
        divider = str.index(":")
        return int(str[divider+1:]) * 0.1
    
    @staticmethod
    def parse_ring_option(str):
        divider = str.index(":")
        count = int(str[:divider])
        distance = float(str[divider+1:])
        return count, distance
    
    @staticmethod
    def parse_map_center(str):
        divider = str.index(":")
        lat = float(str[:divider])
        lon = float(str[divider + 1:])
        lat = max(-90.0, min(90.0, lat))
        lon = max(-180.0, min(180.0, lon))
        return [lon, lat]
    
    @staticmethod
    def parse_zoom_factor(str):
        kMin = const.ZoomFactor.LEAST_ZOOM
        kMax = const.ZoomFactor.MOST_ZOOM
        return max(kMin, min(kMax, kMax - int(str))) * 0.01

            
class AbstractPlot:
    
    _GRIDLINE_DENSITY = 0.25        # 4 gridlines at minimum in each direction

    def __init__(self):
        self.fig = None
        self.projection = None
        self.crs = None
        self.data_crs = cartopy.crs.PlateCarree()
        self.background_maps = []
        self.labels = labels.LabelsConfig()
        self.source_time_zone = None
        self.time_zone_finder = TimezoneFinder()
        
    def _connect_event_handlers(self, handlers):
        for ev in handlers:
            self.fig.canvas.mpl_connect(ev, handlers[ev])
       
    @staticmethod
    def compute_pixel_aspect_ratio(axes):
        # compute the pixel aspect ratio
        w_fig = axes.figure.get_figwidth()
        h_fig = axes.figure.get_figheight()
        w_dis, h_dis = axes.figure.transFigure.transform((w_fig, h_fig))
        pixel_aspect_ratio = h_fig * w_dis / (h_dis * w_fig)
        
        # TODO: better?
        pixel_aspect_ratio *= 1.0 / 0.953   # empirical adjustment
        logger.debug("fig size %f x %f in; display %f x %f px; pixel aspect ratio %f",
                     w_fig, h_fig, w_dis, h_dis, pixel_aspect_ratio)
        
        return pixel_aspect_ratio
                
    def _turn_off_spines(self, axes, **kw):
        left = kw["left"] if "left" in kw else False
        right = kw["right"] if "right" in kw else False
        top = kw["top"] if "top" in kw else False
        bottom = kw["bottom"] if "bottom" in kw else False
        axes.spines["left"].set_visible(left)
        axes.spines["right"].set_visible(right)
        axes.spines["top"].set_visible(top)
        axes.spines["bottom"].set_visible(bottom)
    
    def _turn_off_ticks(self, axes):
        axes.set_xticks([])
        axes.set_yticks([])

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
                
    def _update_gridlines(self, axes, map_color, latlon_label_opt, latlon_spacing):
        deltax = deltay = self._get_gridline_spacing(self.projection.corners_lonlat,
                                                     latlon_label_opt,
                                                     latlon_spacing)
        ideltax = ideltay = int(deltax*10.0)
        if ideltax == 0:
            logger.debug("not updating gridlines because deltas are %f, %f", deltax, deltay)
            return

        lonlat_ext = axes.get_extent(self.data_crs)
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
            
        # draw dotted gridlines
        kwargs = {"crs": self.data_crs, "linestyle": ":", "linewidth": 0.5, "color": map_color}
        if len(xticks) > 0:
            kwargs["xlocs"] = xticks
        if len(yticks) > 0:
            kwargs["ylocs"] = yticks
        gl = axes.gridlines(**kwargs)
        
        # lat/lon line labels
        self._draw_latlon_labels(axes, lonlat_ext, deltax, deltay, map_color)
    
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
    def _fix_arlmap_filename(filename):
        if os.path.exists(filename):
            return filename

        candidates = ["graphics/arlmap", "../graphics/arlmap"]
        for f in candidates:
            if os.path.exists(f):
                return f
    
        return None
    
    def load_background_map(self, filename):
        background_maps = []
        if filename.startswith("shapefiles"):
            shapefiles = mapfile.ShapeFilesReader().read(filename)
            for sf in shapefiles:
                map = mapfile.ShapeFileConverter.convert(sf)
                background_maps.append(map)
        else:
            fname = self._fix_arlmap_filename(filename)
            if fname is None:
                logger.warning("map background file %s not found", fname)
            else:
                arlmap = mapfile.ARLMap().get_reader().read(fname)
                for m in mapfile.ARLMapConverter.convert(arlmap):
                    background_maps.append(m)
        return background_maps

    @staticmethod
    def _make_labels_filename(output_suffix):
        return "LABELS.CFG" if output_suffix == "ps" else "LABELS." + output_suffix

    def read_custom_labels_if_exists(self, filename=None):
        if filename is None:
            filename = self._make_labels_filename(self.settings.output_suffix)
            
        if os.path.exists(filename):
            self.labels.get_reader().read(filename)
            self.labels.after_reading_file(self.settings)

    def _draw_latlon_labels(self, axes, lonlat_ext, deltax, deltay, map_color):
        logger.debug("latlon labels at intervals %f, %f", deltax, deltay)
        ideltax = int(deltax*10.0)
        ideltay = int(deltay*10.0)
        if ideltax == 0 or ideltay == 0:
            logger.debug("not drawing latlon labels because deltas are %f, %f", deltax, deltay)
            return
        
        x1, x2, y1, y2 = self.projection.corners_xy
        clon, clat = self.projection.coord.calc_lonlat(0.5*(x1+x2), 0.5*(y1+y2))
        clon = util.nearest_int(clon/deltax)*deltax
        clat = util.nearest_int(clat/deltay)*deltay
        logger.debug("label reference at lon %f, lat %f", clon, clat)
        
        # lon labels
        lat = (clat - 0.5 * deltay) if (clat > 80.0) else clat + 0.5 * deltay
        for k in range(-(1800-ideltax), 1800, ideltax):
            lon = 0.1 * k
            
            # 5/17/2019
            # The clip_on option does not work with the eps/ps renderer. It is done here.
            ax, ay = axes.transLimits.transform(self.crs.transform_point(lon, lat, self.data_crs))
            if ax < 0.0 or ax > 1.0 or ay < 0.0 or ay > 1.0:
                continue
            
            str = "{0:.1f}".format(lon) if deltax < 1.0 else "{0}".format(int(lon))
            axes.text(lon, lat, str, transform=self.data_crs,
                      horizontalalignment="center", verticalalignment="center",
                      color=map_color, clip_on=True)
        
        # lat labels
        lon = clon + 0.5 * deltax
        for k in range(-(900-ideltay), 900, ideltay):
            lat = 0.1 * k
                        
            # 5/17/2019
            # The clip_on option does not work with the eps/ps renderer. It is done here.
            ax, ay = axes.transLimits.transform(self.crs.transform_point(lon, lat, self.data_crs))
            if ax < 0.0 or ax > 1.0 or ay < 0.0 or ay > 1.0:
                continue
            
            str = "{0:.1f}".format(lat) if deltay < 1.0 else "{0}".format(int(lat))
            axes.text(lon, lat, str, transform=self.data_crs,
                      horizontalalignment="center", verticalalignment="center",
                      color=map_color, clip_on=True)

    @staticmethod
    def _make_stationplot_filename(output_suffix):
        return "STATIONPLOT.CFG" if output_suffix == "ps" else "STATIONPLOT." + output_suffix

    def _draw_stations_if_exists(self, axes, settings, filename=None):
        if filename is None:
            filename = self._make_stationplot_filename(settings.output_suffix)
            
        if os.path.exists(filename):
            cfg = stnplot.StationPlotConfig().get_reader().read(filename)
            for stn in cfg.stations:
                if len(stn.label) > 0:
                    axes.text(stn.longitude, stn.latitude, stn.label,
                              horizontalalignment="center",
                              verticalalignment="center",
                              transform=self.data_crs)
                else:
                    axes.scatter(stn.longitude, stn.latitude,
                                 s=settings.station_marker_size,
                                 marker=settings.station_marker,
                                 c=settings.station_marker_color, clip_on=True,
                                 transform=self.data_crs)

    @staticmethod
    def _make_maptext_filename(output_suffix):
        return "MAPTEXT.CFG" if output_suffix == "ps" else "MAPTEXT." + output_suffix

    def _draw_maptext_if_exists(self, axes, filename=None):
        if filename is None:
            filename = self._make_maptext_filename(self.settings.output_suffix)
            
        if os.path.exists(filename):
            selected_lines = [0, 2, 3, 4, 8, 14]
            with open(filename, "r") as f:
                lines = f.read().splitlines()
                count = 0
                for k, buff in enumerate(lines):
                    if k in selected_lines:
                        axes.text(0.05, 0.928-0.143*count, buff,
                                  verticalalignment="top",
                                  transform=axes.transAxes)
                        count += 1

    def _draw_concentric_circles(self, axes, starting_loc, ring_number, ring_distance):
        lon, lat = starting_loc
        R = ring_distance/111.0
        for k in range(ring_number):
            radius = R*(k+1)
            circ = matplotlib.patches.CirclePolygon((lon, lat), radius,
                                                    color="k", fill=False, resolution=50,
                                                    transform=self.data_crs)
            axes.add_patch(circ)
            str = "{:d} km".format(int(ring_distance * (k+1)))
            axes.text(lon, lat - radius, str, transform=self.data_crs)
        
    def _draw_noaa_logo(self, axes):
        # position of the right bottom corner in the display coordinate
        pt_dis = axes.transAxes.transform((1, 0))
        
        # move it by 10 pixels in each direction
        pt_dis += [-10, +10]
        
        # bounding box in the display coordinate
        h = 90; w = h * self.compute_pixel_aspect_ratio(axes)
        box_dis = [[pt_dis[0]-w, pt_dis[1]], [pt_dis[0], pt_dis[1]+h]]

        # in the axes coordinate        
        box_axes = axes.transAxes.inverted().transform(box_dis)
         
        logo.NOAALogoDrawer().draw(axes, box_axes)
    
    def get_time_zone_at(self, lonlat):
        lon, lat = lonlat
        time_zone_name = None
        try:
            time_zone_name = self.time_zone_finder.timezone_at(lng=lon, lat=lat)
            if time_zone_name is None:
                time_zone_name = self.time_zone_finder.closest_timezone_at(lng=lon, lat=lat)
            logger.warning("cannot find time zone for lon {}, lat {}: using UTC".format(lon, lat))
        except ValueError as ex:
            logger.error("cannot find time zone for lon {}, lat {}: {}".format(lon, lat, ex))
            pass
        
        return pytz.utc if time_zone_name is None else pytz.timezone(time_zone_name)
    
    def adjust_for_time_zone(self, dt):
        return dt if self.source_time_zone is None else dt.astimezone(self.source_time_zone)
