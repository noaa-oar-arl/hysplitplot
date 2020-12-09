# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# plotbase.py
#
# Declares a base class for plots.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
import cartopy.crs
import logging
import matplotlib.patches
import os

from hysplitdata.const import HeightUnit
from hysplitplot import cmdline, const, labels, logo, multipage, \
                        stnplot, streetmap, util


logger = logging.getLogger(__name__)


class AbstractPlotSettings(ABC):

    def __init__(self):
        self.map_background = "../graphics/arlmap"
        self.noaa_logo = False
        self.output_filename = "output.ps"
        self.output_basename = "output"
        self.output_suffix = "ps"
        self.output_format = "ps"
        self.zoom_factor = 0.50
        self.interactive_mode = False  # True if --interactive is specified.
        self.additional_output_formats = []
        self.use_source_time_zone = False   # for the --source-time-zone option
        self.time_zone_str = None  # for the --time-zone option
        self.use_street_map = False  # for the --street-map option
        self.street_map_type = 0
        self.map_projection = const.MapProjection.AUTO
        self.gis_output = const.GISOutput.NONE
        self.kml_option = const.KMLOption.NONE
        self.additional_gis_outputs = []

        # internally defined
        self.lat_lon_label_interval_option = const.LatLonLabel.AUTO
        self.lat_lon_label_interval = 1.0
        self.frames_per_file = const.Frames.ALL_FILES_ON_ONE
        self.map_color = "#1f77b4"
        self.station_marker = "o"
        self.station_marker_color = "k"     # black
        self.station_marker_size = 6*6
        self.height_unit = HeightUnit.METERS
        self.street_map_update_delay = 0.3  # in seconds

        self.process_id_set = False

    def _process_cmdline_args(self, args0):
        args = cmdline.CommandLineArguments(args0)

        self.map_background = args.get_string_value(["-j", "-J"],
                                                    self.map_background)
        if self.map_background.startswith(".") \
                and self.map_background.endswith("shapefiles"):
            logger.warning("enter -jshapefiles... not -j./shapefiles...")

        self.noaa_logo = True if args.has_arg(["+n", "+N"]) else self.noaa_logo

        self.output_filename = args.get_string_value(["-o", "-O"],
                                                     self.output_filename)

        output_suffix = args.get_string_value(["-p", "-P"], self.output_suffix)
        if output_suffix != self.output_suffix:
            self.process_id_set = True

        # The output_format is to be normalized with unmodified output_filename
        self.output_format = \
            util.normalize_output_format(
                self.output_filename, output_suffix, self.output_format)
        self.output_filename, self.output_basename, self.output_suffix = \
            util.normalize_output_filename(self.output_filename, output_suffix)

        if args.has_arg(["-z", "-Z"]):
            self.zoom_factor = self.parse_zoom_factor(
                args.get_value(["-z", "-Z"]))

        if args.has_arg(["--interactive"]):
            self.interactive_mode = True

        if args.has_arg(["--more-formats"]):
            val = args.get_value("--more-formats")
            self.additional_output_formats = self.parse_output_formats(val)
        if self.output_format in self.additional_output_formats:
            self.additional_output_formats.remove(self.output_format)

        if args.has_arg(["--more-gis-options"]):
            val = args.get_value("--more-gis-options")
            try:
                a = [int(s) for s in list(set(val.split(",")))]
                self.additional_gis_outputs.extend(a)
            except Exception as ex:
                logger.debug(str(ex))
                logger.error("Discarding the --more-gis-options option because it has an invalid value")
        if self.gis_output in self.additional_gis_outputs:
            self.additional_gis_outputs.remove(self.gis_output)

        if args.has_arg(["--source-time-zone"]):
            self.use_source_time_zone = True

        if args.has_arg(["--street-map"]):
            self.use_street_map = True
            self.street_map_type = args.get_integer_value("--street-map",
                                                          self.street_map_type)
            if self.map_projection != const.MapProjection.WEB_MERCATOR:
                logger.warning("The --street-map option changes the map "
                               "projection to WEB_MERCATOR")
                self.map_projection = const.MapProjection.WEB_MERCATOR

        if args.has_arg(["--time-zone"]):
            if self.use_source_time_zone:
                logger.warning("Discarding the --source-time-zone option "
                               "because of --time-zone")
                self.use_source_time_zone = False
            self.time_zone_str = args.get_string_value("--time-zone",
                                                       self.time_zone_str)

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

    @staticmethod
    def parse_output_formats(s):
        r = []
        if isinstance(s, str):
            for fmt in s.split(","):
                if len(fmt) > 0:
                    if fmt in util.PLOT_FORMATS:
                        if fmt not in r:
                            r.append(fmt)
                    else:
                        logger.warning("Unknown output format %s; ignored",
                                       fmt)
        return r

    def normalize_output_suffix(self, output_format):
        if self.process_id_set:
            suffix = self.output_suffix + "." + output_format
        else:
            suffix = output_format
        return suffix


class AbstractPlot(ABC):

    def __init__(self, crs=None):
        self.fig = None
        self.projection = None
        self.data_crs = crs if crs is not None else cartopy.crs.PlateCarree()
        self.background_maps = []
        self.labels = labels.LabelsConfig()
        self.time_zone = None  # None implies UTC.
        self.street_map = None
        self.logo_drawer = None
        self.settings = None    # child class should create an instance.
        self.initial_corners_xy = None
        self.initial_corners_lonlat = None

    def _connect_event_handlers(self, handlers):
        for ev in handlers:
            self.fig.canvas.mpl_connect(ev, handlers[ev])

    def compute_pixel_aspect_ratio(self, axes):
        if not self.settings.interactive_mode:
            return 1.0

        # compute the pixel aspect ratio
        w_fig = axes.figure.get_figwidth()
        h_fig = axes.figure.get_figheight()
        w_dis, h_dis = axes.figure.transFigure.transform((w_fig, h_fig))
        pixel_aspect_ratio = h_fig * w_dis / (h_dis * w_fig)

        # TODO: better?
        pixel_aspect_ratio *= 1.0 / 0.953   # empirical adjustment
        logger.debug("fig size %f x %f in; display %f x %f px; pixel aspect"
                     " ratio %f", w_fig, h_fig, w_dis, h_dis,
                     pixel_aspect_ratio)
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

    def create_street_map(self, projection, use_street_map, street_map_type):
        street_map = streetmap.MapBackgroundFactory.create_instance(
            projection, use_street_map, street_map_type)
        street_map.read_background_map(self.settings.map_background)
        street_map.set_color(self.settings.map_color)
        street_map.set_color_mode(self.settings.color)
        street_map.set_lat_lon_label_option(
            self.settings.lat_lon_label_interval_option,
            self.settings.lat_lon_label_interval)
        return street_map

    def update_plot_extents(self, ax):
        xmin, xmax, ymin, ymax = self.projection.corners_xy = ax.axis()
        logger.debug("update_plot_extents: xy: %f %f %f %f",
                     xmin, xmax, ymin, ymax)
        lonl, latb = self.data_crs.transform_point(xmin, ymin,
                                                   self.projection.crs)
        lonr, latt = self.data_crs.transform_point(xmax, ymax,
                                                   self.projection.crs)
        self.projection.corners_lonlat = (lonl, lonr, latb, latt)
        logger.debug("update_plot_extents: lonlat: %f %f %f %f",
                     lonl, lonr, latb, latt)

    def on_update_plot_extent(self):
        ax = self.get_street_map_target_axes()
        self.update_plot_extents(ax)
        self.street_map.update_extent(ax, self.data_crs)
        if self.settings.noaa_logo:
            self._draw_noaa_logo(ax)

    def _make_labels_filename(self, output_suffix):
        if not self.settings.process_id_set:
            return "LABELS.CFG"
        return "LABELS." + output_suffix

    def read_custom_labels_if_exists(self, filename=None):
        if filename is None:
            filename = self._make_labels_filename(self.settings.output_suffix)

        if os.path.exists(filename):
            self.labels.get_reader().read(filename)
            self.labels.after_reading_file(self.settings)

    def update_height_unit(self, labels):
        # default values from labels.cfg
        if labels.has("ALTTD"):
            alttd = labels.get("ALTTD")
            if alttd == "feet" or alttd == "ft":
                self.settings.height_unit = HeightUnit.FEET
            elif alttd == "meters" or alttd == "m":
                self.settings.height_unit = HeightUnit.METERS
            else:
                raise Exception("ALTTD units must be meters or feet in "
                                "LABELS.CFG or its equivalent file: {0}"
                                .format(alttd))

    def _make_stationplot_filename(self, output_suffix):
        if not self.settings.process_id_set:
            return "STATIONPLOT.CFG"
        return "STATIONPLOT." + output_suffix

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

    def _make_maptext_filename(self, output_suffix):
        if not self.settings.process_id_set:
            return "MAPTEXT.CFG"
        return "MAPTEXT." + output_suffix

    def _draw_maptext_if_exists(self, axes, filename=None, filter_fn=None, vskip=0.143):
        if filename is None:
            filename = self._make_maptext_filename(self.settings.output_suffix)

        if filter_fn is None:
            # Compatible with TRAJPLOT.
            filter_fn = lambda s, idx: idx in [0, 2, 3, 4, 8, 14]

        logger.debug('Reading {}'.format(filename))
        if os.path.exists(filename):
            selected_lines = [0, 2, 3, 4, 8, 14]
            with open(filename, "r") as f:
                lines = f.read().splitlines()
                count = 0
                for k, buff in enumerate(lines):
                    if filter_fn(buff, k):
                        axes.text(0.05, 0.928-vskip*count, buff,
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

    def _draw_concentric_circles(self, axes, starting_loc, ring_number,
                                 ring_distance):
        lon, lat = starting_loc
        R = ring_distance/111.0
        for k in range(ring_number):
            radius = R*(k+1)
            circ = matplotlib.patches.CirclePolygon((lon, lat), radius,
                                                    color="k", fill=False,
                                                    resolution=50,
                                                    transform=self.data_crs)
            axes.add_patch(circ)
            str = "{:d} km".format(int(ring_distance * (k+1)))
            axes.text(lon, lat - radius, str, clip_on=True,
                      transform=self.data_crs)

    def _draw_noaa_logo(self, axes):
        # position of the right bottom corner in the display coordinate
        pt_dis = axes.transAxes.transform((1, 0))

        # move it by 10 pixels in each direction
        pt_dis += [-10, +10]

        # bounding box in the display coordinate
        r = self.compute_pixel_aspect_ratio(axes)
        h = 90
        w = h * r
        box_dis = [[pt_dis[0]-w, pt_dis[1]], [pt_dis[0], pt_dis[1]+h]]

        # in the axes coordinate
        box_axes = axes.transAxes.inverted().transform(box_dis)

        if self.logo_drawer is None:
            self.logo_drawer = logo.NOAALogoDrawer()
        else:
            self.logo_drawer.clear()
        self.logo_drawer.draw(axes, box_axes)

    def adjust_for_time_zone(self, dt):
        return dt if self.time_zone is None else dt.astimezone(self.time_zone)

    def _create_plot_saver_list(self, settings):
        plot_saver_list = []

        plot_saver = multipage.PlotFileWriterFactory.create_instance(
            settings.frames_per_file,
            settings.output_basename,
            settings.output_suffix,
            settings.output_format)
        plot_saver_list.append(plot_saver)

        for output_format in settings.additional_output_formats:
            output_suffix = settings.normalize_output_suffix(output_format)
            plot_saver = multipage.PlotFileWriterFactory.create_instance(
                settings.frames_per_file,
                settings.output_basename,
                output_suffix,
                output_format)
            plot_saver_list.append(plot_saver)

        return plot_saver_list
