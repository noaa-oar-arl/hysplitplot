from abc import ABC, abstractmethod
import cartopy.crs
import logging
import matplotlib.patches
import os
import pytz
from timezonefinder import TimezoneFinder

from hysplitdata.const import HeightUnit
from hysplitplot import cmdline, const, labels, logo, stnplot, util


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
        self.output_filename = "output.ps"
        self.output_basename = "output"
        self.output_suffix = "ps"
        self.output_format = "ps"
        self.noaa_logo = False
        self.lat_lon_label_interval_option = const.LatLonLabel.AUTO
        self.lat_lon_label_interval = 1.0
        self.frames_per_file = const.Frames.ALL_FILES_ON_ONE
        self.gis_output = const.GISOutput.NONE
        self.kml_option = const.KMLOption.NONE
        self.use_source_time_zone = False   # for the --source-time-zone option
        self.use_street_map = False # for the --street-map option
        
        # internally defined
        self.interactive_mode = True    # becomes False if the -o or -O option is specified.
        self.map_color = "#1f77b4"
        self.station_marker = "o"
        self.station_marker_color= "k"     # black
        self.station_marker_size = 6*6
        self.height_unit = HeightUnit.METERS
        self.street_map_update_delay = 0.3  # in seconds
        self.street_map_type = 0
        
    
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

        self.output_filename        = args.get_string_value(["-o", "-O"], self.output_filename)
        if args.has_arg(["-o", "-O"]):
            self.interactive_mode = False

        self.output_suffix          = args.get_string_value(["-p", "-P"], self.output_suffix)    
        
        # The output_format is to be normalized with unmodified output_filename.
        self.output_format = \
            util.normalize_output_format(self.output_filename, self.output_suffix, self.output_format)
        self.output_filename, self.output_basename, self.output_suffix = \
            util.normalize_output_filename(self.output_filename, self.output_suffix)

        if args.has_arg(["-z", "-Z"]):
            self.zoom_factor        = self.parse_zoom_factor(args.get_value(["-z", "-Z"]))
        
        self.gis_output             = args.get_integer_value("-a", self.gis_output)
        self.kml_option             = args.get_integer_value("-A", self.kml_option)
        
        if args.has_arg(["--source-time-zone"]):
            self.use_source_time_zone   = True
        
        if args.has_arg(["--street-map"]):
            self.use_street_map         = True
            self.street_map_type        = args.get_integer_value("--street-map", self.street_map_type)
            if self.map_projection != const.MapProjection.WEB_MERCATOR:
                logger.warning("The --street-map option changes the map projection to WEB_MERCATOR")
                self.map_projection     = const.MapProjection.WEB_MERCATOR
            
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

            
class AbstractPlot(ABC):
    
    def __init__(self):
        self.fig = None
        self.projection = None
        self.data_crs = cartopy.crs.PlateCarree()
        self.background_maps = []
        self.labels = labels.LabelsConfig()
        self.time_zone = None
        self.time_zone_finder = TimezoneFinder()
        self.street_map = None
        
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
    
    @abstractmethod
    def get_street_map_target_axes(self):
        pass
    
    def update_plot_extents(self, ax):
        xmin, xmax, ymin, ymax = self.projection.corners_xy = ax.axis()
        lonl, latb = self.data_crs.transform_point(xmin, ymin, self.projection.crs)
        lonr, latt = self.data_crs.transform_point(xmax, ymax, self.projection.crs)
        self.projection.corners_lonlat = (lonl, lonr, latb, latt)
        
    def on_update_plot_extent(self):
        ax = self.get_street_map_target_axes()
        self.update_plot_extents(ax)
        self.street_map.update_extent(ax, self.projection, self.data_crs)

    @staticmethod
    def _make_labels_filename(output_suffix):
        return "LABELS.CFG" if output_suffix == "ps" else "LABELS." + output_suffix

    def read_custom_labels_if_exists(self, filename=None):
        if filename is None:
            filename = self._make_labels_filename(self.settings.output_suffix)
            
        if os.path.exists(filename):
            self.labels.get_reader().read(filename)
            self.labels.after_reading_file(self.settings)

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
                              verticalalignment="center", clip_on=True,
                              transform=self.data_crs)
                else:
                    axes.scatter(stn.longitude, stn.latitude,
                                 s=settings.station_marker_size,
                                 marker=settings.station_marker,
                                 c=settings.station_marker_color, clip_on=True,
                                 transform=self.data_crs)

    def _draw_datem(self, axes, settings, datem, starting_dt, ending_dt):
        for m in datem.make_plot_data(starting_dt, ending_dt):
            axes.scatter(m.longitude, m.latitude,
                         s=settings.station_marker_size,
                         marker="+",
                         c=settings.station_marker_color, clip_on=True,
                         transform=self.data_crs)
            if m.value_str is not None:
                axes.text(m.longitude, m.latitude, m.value_str,
                          horizontalalignment="left",
                          verticalalignment="center", clip_on=True,
                          transform=self.data_crs) 
        
    @staticmethod
    def _make_maptext_filename(output_suffix):
        return "MAPTEXT.CFG" if output_suffix == "ps" else "MAPTEXT." + output_suffix

    def _draw_maptext_if_exists(self, axes, filename=None, filter_fn=None):
        if filename is None:
            filename = self._make_maptext_filename(self.settings.output_suffix)
            
        if os.path.exists(filename):
            selected_lines = [0, 2, 3, 4, 8, 14]
            with open(filename, "r") as f:
                lines = f.read().splitlines()
                count = 0
                for k, buff in enumerate(lines):
                    if (k in selected_lines) and ((filter_fn is None) or filter_fn(buff)):
                        axes.text(0.05, 0.928-0.143*count, buff,
                                  verticalalignment="top", clip_on=True,
                                  transform=axes.transAxes)
                        count += 1

    def _draw_alt_text_boxes(self, axes, lines):
        count = 0
        h = 1.0 / (len(lines) + 1)
        t = 1.0 - 0.5 * h
        for k, buff in enumerate(lines):
            axes.text(0.05, t - h*count, buff,
                      verticalalignment="top", clip_on=True,
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
            axes.text(lon, lat - radius, str, clip_on=True, transform=self.data_crs)
        
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

        time_zone = None
        time_zone_name = None
        try:
            time_zone_name = self.time_zone_finder.timezone_at(lng=lon, lat=lat)
            if time_zone_name is None:
                time_zone_name = self.time_zone_finder.closest_timezone_at(lng=lon, lat=lat)
            logger.warning("cannot find time zone for lon %f, lat %f: using UTC", lon, lat)
            
            time_zone = pytz.timezone(time_zone_name)
        except ValueError as ex:
            logger.error("cannot find time zone for lon {}, lat {}: {}".format(lon, lat, ex))
            pass
        except pytz.exceptions.UnknownTimeZoneError as ex:
            logger.error("unknown time zone {} for lon {}, lat {}: {}".format(time_zone_name, lon, lat, ex))
            pass
        
        return pytz.utc if time_zone is None else time_zone
    
    def adjust_for_time_zone(self, dt):
        return dt if self.time_zone is None else dt.astimezone(self.time_zone)
