# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# plot.py
#
# For producing time-of-arrival plots.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
import copy
import datetime
import logging
import matplotlib.gridspec
import matplotlib.pyplot as plt
import numpy
import os
import pytz
import sys

from hysplitdata import io
from hysplitdata.conc import model
from hysplitdata.const import HeightUnit
from hysplitplot import cmdline, const, datem, mapbox, mapproj, \
                        plotbase, smooth, streetmap, timezone, util
from hysplitplot.conc import helper, gisout, cntr
from hysplitplot.conc.plot import ColorTableFactory, LabelledContourLevel
from hysplitplot.toa import helper as thelper


logger = logging.getLogger(__name__)


class TimeOfArrivalPlotSettings(plotbase.AbstractPlotSettings):

    def __init__(self):
        super(TimeOfArrivalPlotSettings, self).__init__()

        self.input_file = "cdump"
        self.output_filename = "toaplot.ps"
        self.output_basename = "toaplot"

        # Index of the selected pollutant. It is 1-based for now but it will
        # be changed to 0-based.  If the index is -1 after the change, all
        # pollutants are selected.
        self.pollutant_index = 1

        self.first_time_index = 1    # 1-based index for now.
        self.last_time_index = 9999  # 1-based index for now.
        self.time_index_step = 1
        self.contour_level_generator = \
            const.ContourLevelGenerator.EXPONENTIAL_DYNAMIC
        self.QFILE = None
        self.source_label = "\u2606"    # open star
        self.this_is_test = 0
        # bottom display level defaults to deposition surface
        self.LEVEL1 = 0
        # top level defaults to whole model atmosphere
        self.LEVEL2 = 99999
        self.KMAP = const.ConcentrationMapType.TIME_OF_ARRIVAL
        self.KAVG = const.ConcentrationType.VERTICAL_AVERAGE
        self.NDEP = const.DepositionType.NONE
        self.show_max_conc = 0
        self.mass_unit = "mass"
        self.mass_unit_by_user = False
        self.CONADJ = 1.0   # conc unit conversion multiplication factor
        self.DEPADJ = 1.0   # deposition unit conversion multiplication factor
        self.IDYNC = 0      # allow colors to change for dyn contours?
        self.KHEMIN = 0     # plot below threshold contour for chemical output
        self.IZRO = 0       # create map(s) even if all values are zero
        self.NSSLBL = 0     # force sample start time label to start of release
        self.color = const.ConcentrationPlotColor.COLOR  # KOLOR
        self.gis_alt_mode = const.GISOutputAltitude.CLAMPED_TO_GROUND
        self.KMLOUT = 0
        self.ring = False
        self.ring_number = -1
        # ring_number values:
        #       -1      skip all related code sections
        #        0      draw no circle but set square map scaling
        #        n      scale square map for n circles
        self.ring_distance = 0.0
        self.center_loc = [0.0, 0.0]    # lon, lat
        self.center_loc_fixed = False

        # internally defined
        self.label_source = True
        self.source_label_color = "k"       # black
        self.source_label_font_size = 12    # font size
        self.user_color = False
        self.user_colors = None             # list of (r, g, b) tuples
        self.user_label = False
        self.contour_levels = None
        self.contour_level_count = 4
        self.pollutant = ""                 # name of the selected pollutant
        self.SCALE = 0.7784433              # aspect ratio of the main plot box
        self.station_marker = "o"
        self.station_marker_color = "k"     # black
        self.station_marker_size = 6*6
        self.max_contour_legend_count = 5

    def dump(self, stream):
        """Dumps the settings to an output stream.

        """
        stream.write("----- begin TimeOfArrivalPlotSettings\n")
        for k, v in self.__dict__.items():
            stream.write("{0} = {1}\n".format(k, v))
        stream.write("----- end TimeOfArrivalPlotSettings\n")

    def process_command_line_arguments(self, args0):
        """Processes command-line arguments and updates settings.

        :param args0: arguments excluding the program name.
        """
        args = cmdline.CommandLineArguments(args0)

        # self.map_projection must be set so that --street-map may override it.
        self.map_projection = args.get_integer_value(["-m", "-M"],
                                                     self.map_projection)

        # process options common to trajplot, concplot, etc.
        self._process_cmdline_args(args0)

        self.gis_output = args.get_integer_value("-a", self.gis_output)
        if self.gis_output == const.GISOutput.GENERATE_POINTS \
                or self.gis_output == const.GISOutput.GENERATE_POINTS_2:
            self.gis_output = const.GISOutput.GENERATE_POINTS_STR

        self.kml_option = args.get_integer_value("-A", self.kml_option)

        self.gis_alt_mode = args.get_integer_value(["+a", "+A"],
                                                   self.gis_alt_mode)

        self.LEVEL1 = args.get_integer_value(["-b", "-B"], self.LEVEL1)
        self.LEVEL1 = max(0, self.LEVEL1)

        self.frames_per_file = args.get_integer_value(["-f", "-F"],
                                                      self.frames_per_file)

        if args.has_arg(["-g", "-G"]):
            self.ring = True
            self.center_loc_fixed = True
            str = args.get_value(["-g", "-G"])
            if str.count(":") > 0:
                self.ring_number, self.ring_distance = \
                    self.parse_ring_option(str)
            elif str == "":
                self.ring_number = 4
            else:
                self.ring_number = args.get_integer_value(["-g", "-G"],
                                                          self.ring_number)

        if args.has_arg(["-h", "-H"]):
            str = args.get_value(["-h", "-H"])
            if str.count(":") > 0:
                self.center_loc = self.parse_map_center(str)
                self.center_loc_fixed = True
                if self.ring_number < 0:
                    self.ring_number = 0

        self.input_file = args.get_string_value(["-i", "-I"], self.input_file)
        if len(args.unprocessed_args) > 0:
            self.input_file = args.unprocessed_args[-1]

        if args.has_arg(["-k", "-K"]):
            self.color = args.get_integer_value(["-k", "-K"], self.color)
            self.color = max(0, min(3, self.color))
            if self.color == const.ConcentrationPlotColor.COLOR or self.color == const.ConcentrationPlotColor.COLOR_NO_LINES:
                self.drawLogoInColor = True
            else:
                self.drawLogoInColor = False

        if args.has_arg("-l"):
            self.source_label = self.parse_source_label(args.get_value("-l"))
            self.label_source = True

        if args.has_arg("-L"):
            str = args.get_value("-L")
            if str.count(":") > 0:
                self.lat_lon_label_interval = \
                    self.parse_lat_lon_label_interval(str)
                self.lat_lon_label_interval_option = const.LatLonLabel.SET
            else:
                self.lat_lon_label_interval_option = \
                    args.get_integer_value("-L",
                                           self.lat_lon_label_interval_option)
                self.lat_lon_label_interval_option = \
                    max(0, min(1, self.lat_lon_label_interval_option))

        if args.has_arg("+l"):
            self.this_is_test = args.get_integer_value("+l", self.this_is_test)
            self.this_is_test = max(0, min(1, self.this_is_test))

        if args.has_arg(["-n", "-N"]):
            self.parse_time_indices(args.get_value(["-n", "-N"]))
        self.first_time_index -= 1      # to 0-based indices
        self.last_time_index -= 1

        self.QFILE = args.get_string_value(["-q", "-Q"], self.QFILE)

        self.pollutant_index = args.get_integer_value(["-s", "-S"],
                                                      self.pollutant_index)
        self.pollutant_index -= 1       # to 0-based index

        self.LEVEL2 = args.get_integer_value(["-t", "-T"], self.LEVEL2)
        self.LEVEL2 = max(0, self.LEVEL2)
        if self.LEVEL1 > self.LEVEL2:
            self.LEVEL1, self.LEVEL2 = self.LEVEL2, self.LEVEL1

        if args.has_arg("-v"):
            self.parse_contour_levels(args.get_value("-v"))
            if self.validate_contour_levels(self.contour_levels):
                self.contour_level_generator = \
                    const.ContourLevelGenerator.USER_SPECIFIED
        else:
            self.setup_contour_styles()

        self.KMLOUT = args.get_integer_value(["-5"], self.KMLOUT)
        self.IZRO = args.get_integer_value("-8", self.IZRO)


    @staticmethod
    def parse_source_label(str):
        c = int(str)
        if c == 72:
            return "*"
        elif c == 73:
            return "\u2606"    # open star
        else:
            return chr(c)

    def parse_time_indices(self, str):
        if str.count(":") > 0:
            divider = str.index(":")
            self.first_time_index = int(str[:divider])
            self.last_time_index = int(str[divider+1:])
            if self.first_time_index > self.last_time_index:
                self.first_time_index = 1
        else:
            self.last_time_index = int(str)
            if self.last_time_index < 0:
                self.time_index_step = abs(self.last_time_index)
                self.last_time_index = 9999

    def setup_contour_styles(self):
        self.contour_level_generator = \
            const.ContourLevelGenerator.USER_SPECIFIED
        self.contour_levels = []

        colors = [
            (0.0000, 0.0000, 1.0000, 0.5),
            (0.0000, 1.0000, 0.0000, 0.5),
            (1.0000, 1.0000, 0.0000, 0.5),
            (1.0000, 0.0000, 0.0000, 0.5),
            (0.5020, 0.5020, 0.5020, 0.5)]

        for k, c in enumerate(colors):
            self.contour_levels.append(LabelledContourLevel(k, "NONE"))

        self.contour_level_count = len(self.contour_levels)
        self.user_color = True
        self.user_colors = colors

    def parse_contour_levels(self, str):
        if str.count(":") > 0:
            self.contour_levels, clrs, self.user_color = \
                self.parse_labeled_contour_levels(str)
            self.user_label = True
            if self.user_color:
                self.user_colors = clrs
        else:
            levels = self.parse_simple_contour_levels(str)
            self.contour_levels = [LabelledContourLevel(v) for v in levels]

        self.contour_level_count = len(self.contour_levels)

        # sort by contour level if the levels are set
        if self.validate_contour_levels(self.contour_levels):
            self.sort_contour_levels_and_colors()

        logger.debug("sorted contour levels: %s", self.contour_levels)

    def sort_contour_levels_and_colors(self):
        if not self.user_color:
            # sort the contour levels only
            self.contour_levels = sorted(self.contour_levels,
                                         key=lambda o: o.level)
        else:
            a = list(zip(self.contour_levels, self.user_colors))
            s = sorted(a, key=lambda t: t[0].level)
            self.contour_levels = [it[0] for it in s]
            self.user_colors = [it[1] for it in s]

    def validate_contour_levels(self, contour_levels):
        # See if the -v option is used without contour levels. 
        for c in contour_levels:
            if (c.level is None):
                return False
        return True

    @staticmethod
    def parse_simple_contour_levels(str):
        """Parse a string that contains floating-point values separated
        by '+' and return the values

        For example, an input of '1E+3+100+10' returns [1000.0, 100.0, 10.0].
        """
        f = []

        tokens = str.split("+")

        k = 0
        while k < len(tokens):
            if tokens[k][-1].upper() == "E":
                t = tokens[k] + tokens[k+1]
                k += 1
            else:
                t = tokens[k]
            f.append(float(t))
            k += 1

        return f

    @staticmethod
    def parse_labeled_contour_levels(str):
        """Parse a string that contains contour levels, colors, and labels and
        return a list of ContourLevel objects.

        For example, an input of '10E+2:USER1:100050200+10E+3:USER2:100070200'
        returns two ContourLevel objects with respective contour levels 1000.0
        and 10000.0.
        """
        list = []
        clrs = []
        color_set = True

        tokens = str.split("+")

        k = 0
        while k < len(tokens):
            if tokens[k][-1].upper() == "E":
                s = tokens[k] + tokens[k+1]
                k += 1
            else:
                s = tokens[k]

            a = s.split(":")

            o = LabelledContourLevel()
            try:
                o.level = float(a[0])
            except ValueError as ex:
                logger.error(ex)
                o.level = None
            o.label = a[1]
            if len(a) > 2:
                r = int(a[2][0:3]) / 255.0
                g = int(a[2][3:6]) / 255.0
                b = int(a[2][6:9]) / 255.0
                clrs.append((r, g, b))
            else:
                color_set = False

            list.append(o)
            k += 1

        return list, clrs, color_set

    def get_reader(self):
        return TimeOfArrivalPlotSettingsReader(self)


class TimeOfArrivalPlotSettingsReader:

    def __init__(self, settings):
        self.settings = settings

    def read(self, filename):
        logger.debug("reading text file %s", filename)
        with open(filename, "r") as f:
            lines = f.read().splitlines()
            f.close()

        s = self.settings

        s.map_background = lines[0]
        s.map_projection = int(lines[1])
        # num_polid, l 3
        s.zoom_factor = s.parse_zoom_factor(lines[3])
        s.color = int(lines[4])  # 1 or 0
        # cval, l 6
        # fixed, l 7
        # cscale, l 8
        # dscale, l 9
        # smooth, l 10
        # remove, l 11
        # expose, l 12
        # frame, l 13
        # mass, l 14
        s.ring = util.convert_int_to_bool(int(lines[14]))  # 1 or 0
        s.map_center = int(lines[15])  # 1 or 0
        s.ring_number = int(lines[16])
        s.ring_distance = float(lines[17])
        # qpnt, l 19
        s.center_loc[1] = float(lines[19])
        s.center_loc[0] = float(lines[20])

        return s


class TimeOfArrivalPlot(plotbase.AbstractPlot):

    def __init__(self):
        super(TimeOfArrivalPlot, self).__init__()
        self.settings = TimeOfArrivalPlotSettings()
        self.cdump = None
        self.time_selector = None
        self.level_selector = None
        self.pollutant_selector = None
        self.conc_type = None
        self.conc_map = None
        self.depo_map = None
        self.prev_forecast_time = None
        self.length_factory = None
        self.toa_generator = None

        self.fig = None
        self.conc_outer = None
        self.conc_axes = None
        self.legends_axes = None
        self.text_axes = None
        self.plot_saver_list = None

        self.TFACT = 1.0
        self.initial_time = None
        self.contour_labels = None
        self.current_frame = 1
        self.time_period_count = 0
        self.datem = None

    def merge_plot_settings(self, filename, args):
        if filename is not None:
            self.settings.get_reader().read(filename)
        self.settings.process_command_line_arguments(args)

    def get_street_map_target_axes(self):
        return self.conc_axes

    def read_data_files(self):
        if not os.path.exists(self.settings.input_file):
            raise Exception("File not found: {0}"
                            .format(self.settings.input_file))

        # read only one file.
        self.cdump = cdump = model.ConcentrationDump().get_reader().read(
            self.settings.input_file)

        # create selectors
        self.time_selector = helper.TimeIndexSelector(
            self.settings.first_time_index,
            self.settings.last_time_index,
            self.settings.time_index_step)
        self.pollutant_selector = helper.PollutantSelector(
            self.settings.pollutant_index)
        self.level_selector = helper.VerticalLevelSelector(
            self.settings.LEVEL1,
            self.settings.LEVEL2)

        # limit time indices. assume that the last concentration grid has
        # the largest time index.
        self.time_selector.normalize(cdump.grids[-1].time_index)
        logger.debug("time iteration is limited to index range [%d, %d]",
                     self.time_selector.first, self.time_selector.last)

        logger.debug("level iteration is limited to height range "
                     "[%.1f, %.1f] in meters",
                     self.level_selector.min,
                     self.level_selector.max)

        # normalize pollutant index and name
        self.pollutant_selector.normalize(len(cdump.pollutants) - 1)
        self.settings.pollutant_index = self.pollutant_selector.index
        self.settings.pollutant = cdump.get_pollutant(
            self.settings.pollutant_index)

        if len(cdump.pollutants) > 1:
            logger.info("Multiple pollutant species in file")
            for k, name in enumerate(cdump.pollutants):
                if k == self.settings.pollutant_index:
                    logger.info("%d - %s <--- selected", k+1, name)
                else:
                    logger.info("%d - %s", k+1, name)

        # if only one non-depositing level, change -d2 to -d1.
        if self.settings.KAVG == const.ConcentrationType.VERTICAL_AVERAGE:
            if len(cdump.release_heights) == 1 \
                    or (len(cdump.release_heights) == 2
                        and cdump.release_heights[0] == 0):
                logger.warning("Changing -d2 to -d1 since single layer")
                self.settings.KAVG = const.ConcentrationType.EACH_LEVEL

        self.conc_type = helper.ConcentrationTypeFactory.create_instance(
            self.settings.KAVG)
        if self.settings.KAVG == 1:
            # for the above-ground concentration plots
            self.conc_type.set_alt_KAVG(3)
        if self.labels.has("LAYER"):
            self.conc_type.set_custom_layer_str(self.labels.get("LAYER"))
        if self.settings.KMLOUT != 0:
            # Use -o prefix name for output kml file. Otherwise, 'HYSPLIT' will be used.
            self.conc_type.kml_filename_maker.output_basename = self.settings.output_basename

        self.plot_saver_list = self._create_plot_saver_list(self.settings)

        self._post_file_processing(self.cdump)

        self.conc_map = helper.ConcentrationMapFactory.create_instance(
            self.settings.KMAP, self.settings.KHEMIN)
        self.depo_map = helper.DepositionMapFactory.create_instance(
            self.settings.KMAP, self.settings.KHEMIN)
        if self.labels.has("MAPID"):
            self.conc_map.map_id = self.labels.get("MAPID")
            self.depo_map.map_id = self.labels.get("MAPID")

        self.depo_sum = helper.DepositSumFactory.create_instance(
            self.settings.NDEP, self.cdump.has_ground_level_grid())

        time_zone_helper = timezone.TimeZoneHelper()
        if self.settings.time_zone_str is not None:
            self.time_zone = time_zone_helper.lookup_time_zone(self.settings.time_zone_str)
        elif self.settings.use_source_time_zone:
            self.time_zone = time_zone_helper.get_time_zone_at(self.cdump.release_locs[0])
        elif self.labels.has("TZONE"):
            self.time_zone = time_zone_helper.lookup_time_zone(self.labels.get("TZONE"))

        if self.settings.QFILE is not None:
            if os.path.exists(self.settings.QFILE):
                self.datem = datem.Datem().get_reader().read(
                    self.settings.QFILE)

        self.toa_generator = thelper.TimeOfArrivalGenerator(
            self.time_selector, self.conc_type)
        self.toa_generator.process_conc_data(cdump)

    def _post_file_processing(self, cdump):

        self.conc_type.initialize(cdump,
                                  self.level_selector,
                                  self.pollutant_selector)

        # find min and max values by examining all grids of interest
        for t_index in self.time_selector:
            t_grids = helper.TimeIndexGridFilter(
                cdump.grids,
                helper.TimeIndexSelector(t_index, t_index))
            self.conc_type.update_min_max(t_grids)

        self.conc_type.normalize_min_max()

        self.conc_type.scale_conc(self.settings.CONADJ,
                                  self.settings.DEPADJ)

        self._normalize_settings(cdump)

        self.length_factory = util.AbstractLengthFactory.create_factory(
            self.settings.height_unit)

    def _normalize_settings(self, cdump):
        s = self.settings

        if s.LEVEL1 < cdump.vert_levels[0]:
            s.LEVEL1 = cdump.vert_levels[0]
        if s.LEVEL2 > cdump.vert_levels[-1]:
            s.LEVEL2 = cdump.vert_levels[-1]
        logger.debug("normalized LEVELs to %f, %f", s.LEVEL1, s.LEVEL2)

        self.update_height_unit(self.labels)

        if self.contour_labels is None:
            if self.settings.contour_levels is not None:
                self.contour_labels = \
                    [c.label for c in self.settings.contour_levels]
            else:
                self.contour_labels = [""] * self.settings.contour_level_count

    @staticmethod
    def _fix_map_color(color, color_mode):
        if color_mode == const.ConcentrationPlotColor.BLACK_AND_WHITE \
                or color_mode == const.ConcentrationPlotColor.BW_NO_LINES:
            return "k"
        return color

    def layout(self, grid, event_handlers=None):

        fig = plt.figure(
            figsize=(8.5, 11.0),  # letter size
            clear=True,  # clear an existing figure
            constrained_layout=False)

        outer_grid = matplotlib.gridspec.GridSpec(
            2, 1,
            wspace=0.0, hspace=0.075,
            width_ratios=[1.0], height_ratios=[3.25, 1.50])

        inner_grid = matplotlib.gridspec.GridSpecFromSubplotSpec(
            1, 2,
            wspace=0.02, hspace=0.0,
            width_ratios=[2, 1], height_ratios=[1],
            subplot_spec=outer_grid[0, 0])

        self.fig = fig
        self.conc_outer = fig.add_subplot(outer_grid[0, 0])
        self.conc_axes = fig.add_subplot(inner_grid[0, 0],
                                         projection=self.projection.crs)
        self.legends_axes = fig.add_subplot(inner_grid[0, 1])
        self.text_axes = fig.add_subplot(outer_grid[1, 0])

        if event_handlers is not None and self.settings.interactive_mode:
            self._connect_event_handlers(event_handlers)

    def make_plot_title(self, toa, conc_grid,
                        lower_vert_level, upper_vert_level):
        s = self.settings

        fig_title = self.labels.get("TITLE")

        fig_title += "\n"
        starting_dt = self.adjust_for_time_zone(toa.grid.starting_datetime)
        ending_dt = self.adjust_for_time_zone(toa.grid.ending_datetime)
        fig_title += toa.get_map_id_line(lower_vert_level, upper_vert_level,
                                         starting_dt, ending_dt)

        if not conc_grid.is_forward_calculation():
            fig_title += " [backward]"

        if self.settings.pollutant_index == -1:
            pollutant = self.settings.pollutant
        else:
            pollutant = conc_grid.pollutant

        if not conc_grid.is_forward_calculation():
            fig_title += "\n{0} Calculation started at".format(pollutant)
        else:
            fig_title += "\n{0} Release started at".format(pollutant)

        dt = self.adjust_for_time_zone(conc_grid.parent.release_datetimes[0])
        fig_title += dt.strftime(" %H%M %d %b %Y (%Z)")

        return fig_title

    def make_ylabel(self, cdump, marker):
        y_label = "Source {0} at".format(marker)

        release_locs = cdump.get_unique_start_locations()
        if len(release_locs) == 1:
            lon, lat = release_locs[0]
            lat_dir = "N" if lat >= 0 else "S"
            lon_dir = "E" if lon >= 0 else "W"
            y_label += "  {0:5.2f} {1}".format(abs(lat), lat_dir)
            y_label += "  {0:6.2f} {1}".format(abs(lon), lon_dir)
        else:
            y_label += " multiple locations"

        release_heights = cdump.get_unique_start_levels()
        if len(release_heights) == 1:
            height_min = self.length_factory.create_instance(
                release_heights[0])
            y_label += "      from {0}".format(height_min)
        else:
            height_min = self.length_factory.create_instance(
                min(release_heights))
            height_max = self.length_factory.create_instance(
                max(release_heights))
            y_label += "      from {0} to {1}".format(height_min, height_max)

        logger.debug("using ylabel %s", y_label)
        return y_label

    def make_xlabel(self, g):
        curr_forecast_time = g.ending_datetime \
            - datetime.timedelta(hours=g.ending_forecast_hr)

        if g.ending_forecast_hr > 12 \
                and (self.prev_forecast_time is None
                     or self.prev_forecast_time == curr_forecast_time):
            ts = self.adjust_for_time_zone(curr_forecast_time) \
                .strftime("%H%M %d %b %Y")
            x_label = "{0} {1} FORECAST INITIALIZATION" \
                .format(ts, self.cdump.meteo_model)
        else:
            x_label = "{0} METEOROLOGICAL DATA".format(self.cdump.meteo_model)

        self.prev_forecast_time = curr_forecast_time

        logger.debug("using xlabel %s", x_label)
        return x_label

    def _initialize_map_projection(self, cdump):
        map_opt_passes = 1 if self.settings.ring_number == 0 else 2
        map_box = self._determine_map_limits(cdump, map_opt_passes)

        if self.settings.center_loc == [0.0, 0.0]:
            self.settings.center_loc = self.cdump.release_locs[0]

        if self.settings.ring and self.settings.ring_number >= 0:
            map_box.clear_hit_map()
            map_box.set_ring_extent(self.settings,
                                    self.cdump.release_locs[0])

        self.projection = mapproj.MapProjectionFactory.create_instance(
            self.settings.map_projection,
            self.settings.zoom_factor,
            self.settings.center_loc,
            self.settings.SCALE,
            self.cdump.grid_deltas,
            map_box,
            self.settings.center_loc_fixed)
        self.projection.refine_corners(self.settings.center_loc)

        # The map projection might have changed to avoid singularities.
        if self.street_map is None \
                or self.settings.map_projection != self.projection.proj_type:
            self.street_map = self.create_street_map(
                self.projection,
                self.settings.use_street_map,
                self.settings.street_map_type)
            self.street_map.override_fix_map_color_fn(
                TimeOfArrivalPlot._fix_map_color)

        self.settings.map_projection = self.projection.proj_type
        self.initial_corners_xy = copy.deepcopy(self.projection.corners_xy)
        self.initial_corners_lonlat = copy.deepcopy(
            self.projection.corners_lonlat)

    def _create_map_box_instance(self, cdump):
        lat_span = cdump.grid_sz[1] * cdump.grid_deltas[1]
        lon_span = cdump.grid_sz[0] * cdump.grid_deltas[0]

        # use finer grids for small maps
        if lat_span < 2.0 and lon_span < 2.0:
            mbox = mapbox.MapBox(grid_corner=cdump.grid_loc,
                                 grid_size=(lon_span, lat_span),
                                 grid_delta=0.10)
        elif lat_span < 5.0 and lon_span < 5.0:
            mbox = mapbox.MapBox(grid_corner=cdump.grid_loc,
                                 grid_size=(lon_span, lat_span),
                                 grid_delta=0.20)
        else:
            mbox = mapbox.MapBox()

        return mbox

    def _determine_map_limits(self, cdump, map_opt_passes):
        mbox = self._create_map_box_instance(cdump)

        # summation of all concentration grids of interest
        conc = helper.sum_conc_grids_of_interest(cdump.grids,
                                                 self.level_selector,
                                                 self.pollutant_selector,
                                                 self.time_selector)

        for ipass in range(map_opt_passes):
            mbox.allocate()

            # add release points
            for loc in cdump.release_locs:
                if util.is_valid_lonlat(loc):
                    mbox.add(loc)

            # find trajectory hits
            mbox.hit_count = 0
            if conc is not None:
                mbox.add_conc(conc, cdump.longitudes, cdump.latitudes)

            if mbox.hit_count == 0:
                if self.settings.IZRO == 0:
                    raise Exception("ALL concentrations are ZERO - no maps")
                else:
                    logger.info("ALL concentrations are ZERO")

            # first pass only refines grid for small plumes
            if ipass == 0 and map_opt_passes == 2:
                mbox.determine_plume_extent()
                if mbox.need_to_refine_grid():
                    mbox.refine_grid()
                else:
                    break

        mbox.determine_plume_extent()

        return mbox

    def draw_toa_contour_plot(self, toa_data):
        """
        Draws a time-of-arrival plot and returns the contour data points.
        """
        contour_set = None
        axes = self.conc_axes

        # keep the plot size after zooming
        axes.set_aspect("equal", adjustable="datalim")

        # turn off ticks and tick labels
        axes.tick_params(left="off", labelleft="off",
                         right="off", labelright="off",
                         top="off", labeltop="off",
                         bottom="off", labelbottom="off")

        # y-label
        axes.set_ylabel(self.make_ylabel(self.cdump,
                                         self.settings.source_label))

        # set_yticks([]) is necessary to make the y-label visible.
        axes.set_yticks([])

        # set the data range
        axes.axis(self.initial_corners_xy)

        # draw the background map
        self.street_map.draw_underlay(axes,
                                      self.initial_corners_xy,
                                      self.projection.crs)

        # draw optional concentric circles
        if self.settings.ring and self.settings.ring_number > 0:
            self._draw_concentric_circles(axes,
                                          self.cdump.release_locs[0],
                                          self.settings.ring_number,
                                          self.settings.ring_distance)

        # draw a source marker
        if self.settings.label_source:
            x = []
            y = []
            for loc in toa_data.grid.parent.release_locs:
                if util.is_valid_lonlat(loc):
                    x.append(loc[0])
                    y.append(loc[1])

            for k in range(len(x)):
                axes.text(x[k], y[k], self.settings.source_label,
                          color=self.settings.source_label_color,
                          fontsize=self.settings.source_label_font_size,
                          horizontalalignment="center",
                          verticalalignment="center", clip_on=True,
                          transform=self.data_crs)

        if toa_data.has_data():
            logger.debug("Drawing contour at levels %s using colors %s",
                         toa_data.contour_levels,
                         toa_data.fill_colors)

            # Adjust contour levels and prepend 0.5 to the array so that
            # half-way values match the TOA values exactly. This is important
            # to correctly get the KML polygon geometry.
            contour_levels = [x + 0.5 for x in toa_data.contour_levels]
            contour_levels.insert(0, 0.5)

            try:
                # draw filled contours
                contour_set = axes.contourf(toa_data.longitudes,
                                            toa_data.latitudes,
                                            toa_data.data,
                                            contour_levels,
                                            colors=toa_data.fill_colors,
                                            transform=self.data_crs)
                if self.settings.color != const.ConcentrationPlotColor.COLOR_NO_LINES and \
                        self.settings.color != const.ConcentrationPlotColor.BW_NO_LINES:
                    # draw contour lines
                    for c in contour_set.collections:
                        c.set_edgecolor('k')
                        c.set_linewidth(0.25)
            except ValueError as ex:
                logger.warning("Cannot generate contours: {}".format(str(ex)))

        # place station locations
        self._draw_stations_if_exists(axes, self.settings)

        # draw DATEM data
        if self.datem is not None:
            self._draw_datem(axes,
                             self.settings,
                             self.datem,
                             toa_data.grid.starting_datetime,
                             toa_data.grid.ending_datetime)

        return contour_set

    def get_conc_unit(self, conc_map, settings):
        # default values from labels.cfg
        mass_unit = self.labels.get("UNITS")
        volume_unit = self.labels.get("VOLUM")

        if settings.mass_unit_by_user:
            mass_unit = settings.mass_unit
        elif not self.labels.has("UNITS"):
            mass_unit = conc_map.guess_mass_unit(settings.mass_unit)

        if not self.labels.has("VOLUM"):
            volume_unit = conc_map.guess_volume_unit(settings.mass_unit)

        return "{0}{1}".format(mass_unit, volume_unit)

    def _limit_contour_levels_for_legends(self, contour_levels,
                                          max_legend_count=25):
        if len(contour_levels) > max_legend_count:
            logger.warning("Number of contour levels exceed %d: not all "
                           "legends will be displayed", max_legend_count)
            return contour_levels[:max_legend_count]
        return contour_levels

    def draw_contour_legends(self, grid, conc_map, contour_labels,
                             contour_levels, fill_colors):
        axes = self.legends_axes
        s = self.settings

        self._turn_off_ticks(axes)

        font_sz = 9.0  # TODO: to be computed
        small_font_sz = 0.8 * font_sz

        line_skip = 1 / 20.0
        small_line_skip = 0.8 * line_skip

        x = 0.05
        y = 1.0 - small_line_skip * 0.5

        if conc_map.has_banner():
            str = conc_map.get_banner()
            axes.text(0.5, y, str, color="r", fontsize=small_font_sz,
                      horizontalalignment="center", verticalalignment="top",
                      clip_on=True, transform=axes.transAxes)
            y -= small_line_skip

        if grid.nonzero_conc_count == 0:
            return

        dy = line_skip if s.contour_level_count <= 16 else line_skip * 0.65
        dx = 0.25

        logger.debug("contour_level_count %d", s.contour_level_count)
        logger.debug("contour levels %s", contour_levels)
        logger.debug("contour colors %s", fill_colors)
        logger.debug("contour labels %s", contour_labels)

        labels = copy.deepcopy(contour_labels)
        labels.reverse()

        colors = copy.deepcopy(fill_colors)
        colors.reverse()

        display_levels = self._limit_contour_levels_for_legends(
            contour_levels, s.max_contour_legend_count)
        for k, level in enumerate(reversed(display_levels)):
            clr = colors[k]

            box = matplotlib.patches.Rectangle((x, y-dy), dx, dy, color=clr,
                                               transform=axes.transAxes)
            axes.add_patch(box)

            str = "{}".format(level)
            axes.text(x + dx + x, y-0.5*dy, str, color="k", fontsize=font_sz,
                      horizontalalignment="left", verticalalignment="center",
                      clip_on=True, transform=axes.transAxes)

            y -= dy

        y = conc_map.draw_explanation_text(axes, x, y,
                                           small_font_sz, small_line_skip,
                                           labels)

        if self.settings.this_is_test:
            y -= small_line_skip * 1.5
            axes.hlines(y-small_line_skip * 0.5, 0.05, 0.95,
                        color="k",
                        linewidth=0.125,
                        transform=axes.transAxes)

            y -= small_line_skip
            axes.text(0.5, y, "THIS IS A TEST", color="r",
                      fontsize=small_font_sz,
                      horizontalalignment="center", verticalalignment="top",
                      clip_on=True,
                      transform=axes.transAxes)

            axes.hlines(y-small_line_skip, 0.05, 0.95,
                        color="k",
                        linewidth=0.125,
                        transform=axes.transAxes)

    def draw_bottom_text(self):
        self._turn_off_ticks(self.text_axes)

        alt_text_lines = self.labels.get("TXBOXL")

        map_text_filename = self._make_maptext_filename(
            self.settings.output_suffix)
        if os.path.exists(map_text_filename):
            filter_fn = lambda s, idx: not s.startswith("Traj") and \
                                       idx in [2, 4, 7, 8, 9, 10, 11, 12, 13, 14]
            self._draw_maptext_if_exists(self.text_axes,
                                         map_text_filename,
                                         filter_fn,
                                         vskip=0.090)
        elif (alt_text_lines is not None) and (len(alt_text_lines) > 0):
            self._draw_alt_text_boxes(self.text_axes, alt_text_lines)
        else:
            self._turn_off_spines(self.text_axes)

    def _write_gisout(self, gis_writers, g, lower_vert_level, upper_vert_level,
                      quad_contour_set, contour_levels, color_table,
                      scaling_factor, time_intervals):
        """
        Create GIS output files in as many formats as requested.
        """
        if g.extension.max_locs is None:
            g.extension.max_locs = helper.find_max_locs(g)

        min_conc, max_conc = self.conc_type.get_plot_conc_range(g,
                                                                scaling_factor)

        contour_set = cntr.convert_matplotlib_quadcontourset(quad_contour_set)
        for k, contour in enumerate(contour_set.contours):
            contour.raw_color = color_table.raw_colors[k]
            contour.color = color_table.colors[k]
            contour.level = contour_levels[k]
            contour.level_str = contour_levels[k]
            contour.label = self.contour_labels[k]
        contour_set.concentration_unit = self.get_conc_unit(self.conc_map,
                                                            self.settings)
        contour_set.min_concentration = min_conc
        contour_set.max_concentration = max_conc
        contour_set.min_concentration_str = self.conc_map.format_conc(min_conc)
        contour_set.max_concentration_str = self.conc_map.format_conc(max_conc)
        contour_set.time_of_arrivals = time_intervals

        # change the order of appearance for the contours.
        contour_set.contour_orders.reverse()

        for w in gis_writers:
            basename = w.make_output_basename(
                    g,
                    self.conc_type,
                    self.depo_sum,
                    upper_vert_level)
            w.write(basename, g, contour_set,
                    lower_vert_level, upper_vert_level)

    def draw_toa_plot_above_ground(self, toa_data, event_handlers,
                                   color_table, gis_writers=None,
                                   *args, **kwargs):
        g = toa_data.grid

        self.layout(g, event_handlers)

        self._turn_off_spines(self.conc_outer)
        self._turn_off_ticks(self.conc_outer)

        LEVEL0 = self.conc_type.get_lower_level(g.vert_level,
                                                self.cdump.vert_levels)
        LEVEL2 = self.conc_type.get_upper_level(g.vert_level,
                                                self.settings.LEVEL2)

        level1 = self.length_factory.create_instance(LEVEL0)
        level2 = self.length_factory.create_instance(LEVEL2)

        conc_scaling_factor = 1.0

        # plot title
        title = self.make_plot_title(toa_data, g, level1, level2)
        self.conc_outer.set_title(title)
        self.conc_outer.set_xlabel(self.make_xlabel(g))

        quad_contour_set = self.draw_toa_contour_plot(toa_data)
        self.draw_contour_legends(g, self.conc_map, self.contour_labels,
                                  toa_data.display_levels,
                                  toa_data.fill_colors)
        self.draw_bottom_text()

        if isinstance(gis_writers, list) and len(gis_writers) > 0:
            self._write_gisout(gis_writers, g, level1, level2,
                               quad_contour_set, toa_data.display_levels,
                               color_table, conc_scaling_factor,
                               toa_data.time_intervals)

        self.fig.canvas.draw()  # to get the plot spines right.
        self.on_update_plot_extent()
        for plot_saver in self.plot_saver_list:
            plot_saver.save(self.fig, self.current_frame)

        if self.settings.interactive_mode:
            plt.show(*args, **kwargs)

        plt.close(self.fig)
        self.current_frame += 1

    def draw_toa_plot_on_ground(self, toa_data, event_handlers,
                                color_table, gis_writers=None, *args, **kwargs):
        g = toa_data.grid

        self.layout(g, event_handlers)

        self._turn_off_spines(self.conc_outer)
        self._turn_off_ticks(self.conc_outer)

        level1 = self.length_factory.create_instance(0)
        level2 = self.length_factory.create_instance(0)

        conc_scaling_factor = 1.0

        # plot title
        title = self.make_plot_title(toa_data, g, level1, level2)
        self.conc_outer.set_title(title)
        self.conc_outer.set_xlabel(self.make_xlabel(g))

        quad_contour_set = self.draw_toa_contour_plot(toa_data)
        self.draw_contour_legends(g, self.conc_map, self.contour_labels,
                                  toa_data.display_levels,
                                  toa_data.fill_colors)
        self.draw_bottom_text()

        if isinstance(gis_writers, list) and len(gis_writers) > 0:
            self._write_gisout(gis_writers, g, level1, level2,
                               quad_contour_set, toa_data.display_levels,
                               color_table, conc_scaling_factor,
                               toa_data.time_intervals)

        self.fig.canvas.draw()  # to get the plot spines right.
        self.on_update_plot_extent()
        for plot_saver in self.plot_saver_list:
            plot_saver.save(self.fig, self.current_frame)

        if self.settings.interactive_mode:
            plt.show(*args, **kwargs)

        plt.close(self.fig)
        self.current_frame += 1

    def _create_gis_writer_list(self, settings, time_zone):
        gis_writer_list = []
        
        o = gisout.GISFileWriterFactory.create_instance(
                settings.gis_output,
                settings.kml_option,
                time_zone)
        gis_writer_list.append(o)
        
        for gis_opt in settings.additional_gis_outputs:
            o = gisout.GISFileWriterFactory.create_instance(
                    gis_opt,
                    settings.kml_option,
                    time_zone)
            gis_writer_list.append(o)
        
        for w in gis_writer_list:
            w.initialize(settings.gis_alt_mode,
                         settings.output_basename,
                         settings.output_suffix,
                         settings.KMAP,
                         settings.NSSLBL,
                         settings.show_max_conc,
                         settings.NDEP)

        return gis_writer_list

    def draw(self, ev_handlers=None, *args, **kwargs):
        if not self.settings.interactive_mode:
            plt.ioff()

        color_table = ColorTableFactory.create_instance(self.settings)

        gis_writers = self._create_gis_writer_list(self.settings, self.time_zone)

        self._initialize_map_projection(self.cdump)

        fill_colors = color_table.colors

        toa_data = self.toa_generator.make_plume_data(
            thelper.TimeOfArrival.DAY_0, fill_colors)
        toa_data.grid.time_index = 0    # for GIS output file name.
        self.draw_toa_plot_above_ground(toa_data, ev_handlers, color_table,
                                        gis_writers, *args, **kwargs)

        toa_data = self.toa_generator.make_plume_data(
            thelper.TimeOfArrival.DAY_1, fill_colors)
        toa_data.grid.time_index = 1    # for GIS output file name.
        self.draw_toa_plot_above_ground(toa_data, ev_handlers, color_table,
                                        gis_writers, *args, **kwargs)

        toa_data = self.toa_generator.make_plume_data(
            thelper.TimeOfArrival.DAY_2, fill_colors)
        toa_data.grid.time_index = 2    # for GIS output file name.
        self.draw_toa_plot_above_ground(toa_data, ev_handlers, color_table,
                                        gis_writers, *args, **kwargs)

        toa_data = self.toa_generator.make_deposition_data(
            thelper.TimeOfArrival.DAY_0, fill_colors)
        toa_data.grid.time_index = 0    # for GIS output file name.
        self.draw_toa_plot_on_ground(toa_data, ev_handlers, color_table,
                                     gis_writers, *args, **kwargs)

        toa_data = self.toa_generator.make_deposition_data(
            thelper.TimeOfArrival.DAY_1, fill_colors)
        toa_data.grid.time_index = 1    # for GIS output file name.
        self.draw_toa_plot_on_ground(toa_data, ev_handlers, color_table,
                                     gis_writers, *args, **kwargs)

        toa_data = self.toa_generator.make_deposition_data(
            thelper.TimeOfArrival.DAY_2, fill_colors)
        toa_data.grid.time_index = 2    # for GIS output file name.
        self.draw_toa_plot_on_ground(toa_data, ev_handlers, color_table,
                                     gis_writers, *args, **kwargs)

        self.time_period_count = self.toa_generator.time_period_count

        for plot_saver in self.plot_saver_list:
            plot_saver.close()
        for w in gis_writers:
            w.finalize()

    def get_plot_count_str(self):
        plot_saver = self.plot_saver_list[0]
        if plot_saver.file_count > 1:
            return "{} output files".format(plot_saver.file_count)

        self.time_period_count = self.toa_generator.time_period_count
        s = "{} time period".format(self.time_period_count)
        if self.time_period_count > 1:
            s += "s"

        return s
