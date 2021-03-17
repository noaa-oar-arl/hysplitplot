# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# plot.py
#
# For producing grid plots.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
import copy
import datetime
import logging
import math
import matplotlib.gridspec
import matplotlib.pyplot as plt
import numpy
import os
import pytz
import shapely  # shapely.errors.TopologicalError
import sys

from hysplitdata import io
from hysplitdata.conc import model
from hysplitdata.const import HeightUnit
from hysplitplot import cmdline, const, mapbox, mapproj, \
                        plotbase, smooth, streetmap, timezone, util
from hysplitplot.conc import helper, cntr, gisout
from hysplitplot.conc.plot import ColorTableFactory
from hysplitplot.grid.helper import GisOutputFilenameForGridPlot, \
                                    KmlOutputFilenameForGridPlot, \
                                    TextOutputForGridPlot


logger = logging.getLogger(__name__)


class GridPlotSettings(plotbase.AbstractPlotSettings):

    def __init__(self):
        super(GridPlotSettings, self).__init__()

        self.input_file = "cdump.bin"
        self.output_filename = "plot.ps"
        self.output_basename = "plot"

        # Index of the selected pollutant. It is 1-based for now but it will
        # be changed to 0-based.  If the index is -1 after the change, all
        # pollutants are selected.
        self.pollutant_index = 1

        self.first_time_index = 1    # 1-based index for now.
        self.last_time_index = 9999  # 1-based index for now.
        self.time_index_step = 1
        self.contour_level_generator = \
            const.ContourLevelGenerator.EXPONENTIAL_DYNAMIC
        self.source_label = "\u2606"    # open star
        self.LEVEL1 = 0  # bottom display level defaults to deposition surface
        self.LEVEL2 = 99999  # top level defaults to whole model atmosphere
        self.exposure_unit = const.ExposureUnit.CONCENTRATION  # KEXP; -e
        self.KMAP = const.ConcentrationMapType.CONCENTRATION
        self.KAVG = const.ConcentrationType.EACH_LEVEL
        self.NDEP = const.DepositionType.TIME
        self.show_max_conc = 1
        self.mass_unit = "mass"
        self.mass_unit_by_user = False
        self.CFACT = 1.0   # conc unit conversion multiplication factor
        self.DEPADJ = 1.0   # deposition unit conversion multiplication factor
        self.IDYNC = 0      # allow colors to change for dyn contours?
        self.KHEMIN = 0     # plot below threshold contour for chemical output
        self.IZRO = 0       # create map(s) even if all values are zero
        self.NSSLBL = 0     # force sample start time label to start of release
        self.color = const.ConcentrationPlotColor.COLOR  # KOLOR
        self.gis_alt_mode = const.GISOutputAltitude.CLAMPED_TO_GROUND
        self.ring = False
        self.ring_number = -1
        # ring_number values:
        #       -1      skip all related code sections
        #        0      draw no circle but set square map scaling
        #        n      scale square map for n circles
        self.ring_distance = 0.0
        self.center_loc = [None, None]    # lon, lat
        self.center_loc_specified = False
        self.science_for_sphere = False     # NSOS
        self.hlevel = 0  # hlevel
        self.CVAL1 = 1.0e-36  # CVAL(1)
        self.DELTA = 1000.0  # DELTA contour value
        self.MINCON = False  # min conc. 
        self.NSCALE = 1  # logarithmic. 0 is for linear.
        self.output_values = False  # for the -f option.

        # internally defined
        self.label_source = True
        self.source_label_color = "k"       # black
        self.source_label_font_size = 12    # font size
        self.user_color = True
        self.user_colors = None             # list of (r, g, b) tuples
        self.user_label = False
        self.contour_levels = None
        self.contour_level_count = 12
        self.pollutant = ""         # name of the selected pollutant
        self.SCALE = 1.0
        self.max_contour_legend_count = 25

    def dump(self, stream):
        """Dumps the settings to an output stream.

        """
        stream.write("----- begin GridPlotSettings\n")
        for k, v in self.__dict__.items():
            stream.write("{0} = {1}\n".format(k, v))
        stream.write("----- end GridPlotSettings\n")

    def process_command_line_arguments(self, args0):
        """Processes command-line arguments and updates settings.

        :param args0: arguments excluding the program name.
        """
        args = cmdline.CommandLineArguments(args0)

        # process options common to trajplot, concplot, etc.
        self._process_cmdline_args(args0)

        self.NSCALE = args.get_integer_value(["-a", "-A"], self.NSCALE)
        self.CFACT = args.get_float_value(["-c", "-C"], self.CFACT)
        self.DELTA = args.get_float_value(["-d", "-D"], self.DELTA)
        self.frames_per_file = args.get_integer_value(["-m", "-M"],
                                                      self.frames_per_file)
        self.output_values = args.get_boolean_value(["-f", "-F"],
                                                    self.output_values)

        self.gis_output = args.get_integer_value(["-g", "-G"], self.gis_output)
        self.gis_output = self.normalize_gis_output_option(self.gis_output)

        self.hlevel = args.get_integer_value(["-h", "-H"], self.hlevel)

        self.input_file = \
            args.get_string_value(["-i", "-I"], self.input_file)
        if len(args.unprocessed_args) > 0:
            self.input_file = args.unprocessed_args[-1]

        self.CVAL1 = args.get_float_value(["-l", "-L"], self.CVAL1)
        if self.CVAL1 == -1.0:
            self.MINCON = True

        self.kml_option = args.get_integer_value(["-k", "-K"], self.kml_option)
        
        if args.has_arg(["-n", "-N"]):
            self.parse_time_indices(args.get_value(["-n", "-N"]))
        self.first_time_index -= 1      # to 0-based indices
        self.last_time_index -= 1

        self.NDEP = args.get_integer_value(["-r", "-R"], self.NDEP)
        self.NDEP = max(0, min(3, self.NDEP))

        self.pollutant_index = args.get_integer_value(["-s", "-S"],
                                                      self.pollutant_index)
        self.pollutant_index -= 1       # to 0-based index
 
        if args.has_arg(["-u", "-U"]):
            self.mass_unit = args.get_value(["-u", "-U"])
            self.mass_unit_by_user = True

        self.center_loc[0] = args.get_float_value(["-x", "-X"], self.center_loc[0])
        self.center_loc[1] = args.get_float_value(["-y", "-Y"], self.center_loc[1])
        if args.has_arg(["-x", "-X", "-y", "-Y"]):
            self.center_loc_specified = True

    @staticmethod
    def normalize_gis_output_option(gisopt):  # TODO: add unit test
        # GRIDPLOT always outputs contour values as log10(value).
        if gisopt == const.GISOutput.GENERATE_POINTS_2:
            return const.GISOutput.GENERATE_POINTS
        return gisopt

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

    def get_reader(self):
        return GridPlotSettingsReader(self)


class GridPlotSettingsReader:

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


class GridPlot(plotbase.AbstractPlot):

    MAX_CONTOUR_LEVELS = 32

    def __init__(self):
        super(GridPlot, self).__init__()
        self.settings = GridPlotSettings()
        self.cdump = None
        self.time_selector = None
        self.level_selector = None
        self.pollutant_selector = None
        self.conc_type = None
        self.conc_map = None
        self.value_output_writer = None
        self.prev_forecast_time = None
        self.length_factory = None

        self.fig = None
        self.conc_outer = None
        self.conc_axes = None
        self.legends_axes = None
        self.text_axes = None
        self.plot_saver_list = None

        self.initial_time = None
        self.contour_labels = None
        self.current_frame = 1
        self.time_period_count = 0

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
        self.cdump = cdump = model.ConcentrationDump().get_reader() \
            .read(self.settings.input_file)

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

        # limit time indices. assume that the last concentration grid
        # has the largest time index.
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
        self.settings.pollutant = \
            cdump.get_pollutant(self.settings.pollutant_index)

        if len(cdump.pollutants) > 1:
            logger.info("Multiple pollutant species in file")
            for k, name in enumerate(cdump.pollutants):
                if k == self.settings.pollutant_index:
                    logger.info("%d - %s <--- selected", k+1, name)
                else:
                    logger.info("%d - %s", k+1, name)

        # make sure the requested level exists
        self.settings.hlevel = self._adjust_vertical_level(cdump, self.settings.hlevel)
        if self.settings.hlevel == 0:
            self.settings.KMAP = const.ConcentrationMapType.DEPOSITION

        self.conc_type = helper.ConcentrationTypeFactory.create_instance(
            self.settings.KAVG)
        self.conc_type.gis_filename_maker = GisOutputFilenameForGridPlot()
        self.conc_type.kml_filename_maker = KmlOutputFilenameForGridPlot()

        self.plot_saver_list = self._create_plot_saver_list(self.settings)

        self._post_file_processing(self.cdump)

        self.conc_map = helper.ConcentrationMapFactory.create_instance(
            self.settings.KMAP, self.settings.KHEMIN)

        if self.labels.has("MAPID"):
            self.conc_map.map_id = self.labels.get("MAPID")

        self.depo_sum = helper.DepositSumFactory.create_instance(
            self.settings.NDEP, self.cdump.has_ground_level_grid())

        if self.settings.output_values:
            self.value_output_writer = TextOutputForGridPlot()
 
        time_zone_helper = timezone.TimeZoneHelper()
        if self.settings.time_zone_str is not None:
            self.time_zone = time_zone_helper.lookup_time_zone(self.settings.time_zone_str)
        elif self.settings.use_source_time_zone:
            self.time_zone = time_zone_helper.get_time_zone_at(self.cdump.release_locs[0])
        elif self.labels.has("TZONE"):
            self.time_zone = time_zone_helper.lookup_time_zone(self.labels.get("TZONE"))

    def _adjust_vertical_level(self, cdump, level):
        if level in cdump.vert_levels:
            return level
        if len(cdump.vert_levels) == 1:
            return cdump.vert_levels[0]
        logger.error("FALTAL ERROR: requested output height does not exist in input file")
        logger.error("valid choices are: {}".format(cdump.vert_levels))
        raise Exception("Invalid output height {}: check your -h or -H option"
                        .format(level))

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

        self.conc_type.scale_conc(self.settings.CFACT,
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

        if s.exposure_unit == const.ExposureUnit.CHEMICAL_THRESHOLDS:
            s.KMAP = const.ConcentrationMapType.THRESHOLD_LEVELS
        elif s.exposure_unit == const.ExposureUnit.VOLCANIC_ASH:
            s.KMAP = const.ConcentrationMapType.VOLCANIC_ERUPTION
        elif s.exposure_unit == const.ExposureUnit.MASS_LOADING:
            s.KMAP = const.ConcentrationMapType.MASS_LOADING
        else:
            s.KMAP = s.exposure_unit + 1

        self.update_height_unit(self.labels)

        if self.contour_labels is None:
            if self.settings.contour_levels is not None:
                self.contour_labels = [c.label
                                       for c in self.settings.contour_levels]
            else:
                self.contour_labels = [""] * self.settings.contour_level_count

    @staticmethod
    def _fix_map_color(color, color_mode):
        if color_mode == const.ConcentrationPlotColor.BLACK_AND_WHITE or \
           color_mode == const.ConcentrationPlotColor.BW_NO_LINES:
            return "k"
        return color

    def layout(self, grid, event_handlers=None):

        fig = plt.figure(
            figsize=(8.5, 11.0),  # letter size
            clear=True,  # clear an existing figure
            constrained_layout=False
        )

        outer_grid = matplotlib.gridspec.GridSpec(
            2, 1,
            wspace=0.0,
            hspace=0.075,
            width_ratios=[1.0],
            height_ratios=[3.25, 1.50])

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

    def make_plot_title(self, conc_grid, conc_map, lower_vert_level,
                        upper_vert_level, starting_datetime):
        s = self.settings

        fig_title = self.labels.get("TITLE")

        conc_unit = self.get_conc_unit_escaped(conc_map, s)
        fig_title += "\n"
        fig_title += conc_map.get_map_id_line(self.conc_type,
                                              conc_unit,
                                              lower_vert_level,
                                              upper_vert_level)

        if s.NSSLBL == 1:
            dt = self.adjust_for_time_zone(
                conc_grid.parent.release_datetimes[0])
        else:
            dt = self.adjust_for_time_zone(starting_datetime)
        fig_title += dt.strftime("\nIntegrated from %H%M %d %b to")

        dt = self.adjust_for_time_zone(conc_grid.ending_datetime)
        fig_title += dt.strftime(" %H%M %d %b %Y (%Z)")

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
            x_label = "{0} {1} FORECAST INITIALIZATION".format(
                ts,
                self.cdump.meteo_model)
        else:
            x_label = "{0} METEOROLOGICAL DATA".format(self.cdump.meteo_model)

        self.prev_forecast_time = curr_forecast_time

        logger.debug("using xlabel %s", x_label)
        return x_label

    def _initialize_map_projection(self, cdump):
        if self.settings.center_loc[0] is None:
            self.settings.center_loc[0] = self.cdump.release_locs[0][0]
        if self.settings.center_loc[1] is None:
            self.settings.center_loc[1] = self.cdump.release_locs[0][1]

        if self.settings.center_loc_specified:
            self.settings.ring = True
            self.settings.ring_number = 0
            ring_radius = 2 * max(
                abs(self.settings.center_loc[0] - self.cdump.release_locs[0][0]),
                abs(self.settings.center_loc[1] - self.cdump.release_locs[0][1])
            )
            self.settings.ring_distance = ring_radius * 111.0  # convert degrees to km.

        map_opt_passes = 1 if self.settings.ring_number == 0 else 2
        map_box = self._determine_map_limits(cdump, map_opt_passes)

        if self.settings.ring and self.settings.ring_number >= 0:
            map_box.determine_plume_extent()
            map_box.clear_hit_map()
            map_box.set_ring_extent(self.settings)

        self.projection = mapproj.MapProjectionFactory.create_instance(
            self.settings.map_projection,
            self.settings.zoom_factor,
            self.settings.center_loc,
            self.settings.SCALE,
            self.cdump.grid_deltas,
            map_box)
        self.projection.refine_corners(self.settings.center_loc)

        # The map projection might have changed to avoid singularities.
        if self.street_map is None \
                or self.settings.map_projection != self.projection.proj_type:
            self.street_map = self.create_street_map(
                self.projection,
                self.settings.use_street_map,
                self.settings.street_map_type)
            self.street_map.override_fix_map_color_fn(
                GridPlot._fix_map_color)

        self.settings.map_projection = self.projection.proj_type
        self.initial_corners_xy = copy.deepcopy(self.projection.corners_xy)
        self.initial_corners_lonlat = \
            copy.deepcopy(self.projection.corners_lonlat)

    def _create_map_box_instance(self, cdump):
        start_corner = cdump.grid_loc
        lat_span = cdump.grid_sz[1] * cdump.grid_deltas[1]
        lon_span = cdump.grid_sz[0] * cdump.grid_deltas[0]

        # adjust the region of interest if the ring option is set.
        if self.settings.ring:
            ring_radius = self.settings.ring_distance / 111.0  # km to deg
            l = min(self.settings.center_loc[0] - ring_radius, cdump.grid_loc[0])
            r = max(self.settings.center_loc[0] + ring_radius, cdump.grid_loc[0])
            lon_span = min(360.0, r - l)
            b = min(self.settings.center_loc[1] - ring_radius, cdump.grid_loc[1])
            t = max(self.settings.center_loc[1] + ring_radius, cdump.grid_loc[1])
            lat_span = min(180.0, t - b)
            # normalize angles
            b = max(-90.0, min(90.0, b))
            while l > 360.0:
                l -= 360.0
            while l < 0.0:
                l += 360.0
            start_corner = [l, b]
            logger.debug('region of interest: l {}, r {}, b {}, t {}'.format(l, r, b, t))
            logger.debug('corner {}; span lon {}, lat {}'.format(start_corner, lon_span, lat_span))

        # use finer grids for small maps
        if lat_span < 2.0 and lon_span < 2.0:
            mbox = mapbox.MapBox(grid_corner=start_corner,
                                 grid_size=(lon_span, lat_span),
                                 grid_delta=0.10)
        elif lat_span < 5.0 and lon_span < 5.0:
            mbox = mapbox.MapBox(grid_corner=start_corner,
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
                for j in range(len(cdump.latitudes)):
                    for i in range(len(cdump.longitudes)):
                        if conc[j, i] > 0:
                            mbox.add((cdump.longitudes[i], cdump.latitudes[j]))

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

        return mbox

    def _build_grid_rect_list(self,
                              conc : numpy.ndarray,
                              longitudes : [float],
                              latitudes : [float],
                              dx : float,
                              dy : float,
                              contour_levels : []) -> [] :
        ncol = len(longitudes)
        contour_levels_len = len(contour_levels)
        rect_list = [[] for _ in range(contour_levels_len)]

        # create a composite list where each element is
        # a pair of array index and concentration value.
        flat_conc = numpy.reshape(conc, -1, order='C')
        comp_list = list(zip(range(len(flat_conc)), flat_conc))

        # find non-zero concentrations
        selected = list(filter(lambda x: x[1] > 0, comp_list))

        if self.value_output_writer is not None:
            if len(selected) > 0:
                for v in selected:
                    j = int(v[0] / ncol)
                    i = v[0] - j * ncol
                    self.value_output_writer.write(i, j, v[1])

        hx = 0.5 * dx
        hy = 0.5 * dy
        # The following loop works when the contour level increases at each step.
        for k, level in enumerate(contour_levels):
            if level > 0:
                # collect data points whose concentration is greater than
                # or equal to the current contour level.
                selected = list(filter(lambda x: x[1] >= level, selected))
                # filter data points for plotting
                if k < contour_levels_len - 1:
                    next_level = contour_levels[k + 1]
                    pts = list(filter(lambda x: x[1] < next_level, selected))
                else:
                    pts = selected

                if len(pts) > 0:
                    for v in pts:
                        j = int(v[0] / ncol)
                        i = v[0] - j * ncol
                        lat = latitudes[j]
                        lon = longitudes[i]
                        r = matplotlib.patches.Rectangle((lon-hx, lat-hy), dx, dy)
                        rect_list[k].append(r)

        return rect_list

    def draw_concentration_plot(self, conc_grid, scaled_conc : numpy.ndarray, conc_map,
                                contour_levels, fill_colors, color_skip=1):
        """
        Draws a concentration grid plot and returns collections of rectangles.
        """
        rect_list = None
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

        logger.debug("Drawing contour at levels %s using colors %s",
                     contour_levels, fill_colors)

        # draw a source marker
        if self.settings.label_source:
            x = []
            y = []
            for loc in conc_grid.parent.release_locs:
                if util.is_valid_lonlat(loc):
                    x.append(loc[0])
                    y.append(loc[1])

            for k in range(len(x)):
                axes.text(x[k], y[k], self.settings.source_label,
                          color=self.settings.source_label_color,
                          fontsize=self.settings.source_label_font_size,
                          horizontalalignment="center",
                          verticalalignment="center",
                          clip_on=True,
                          transform=self.data_crs)

        contour_levels_len = len(contour_levels)
        if conc_grid.nonzero_conc_count > 0 and contour_levels_len > 1:
            # draw filled contours
            # TODO: delete patches of previous drawing?
            
            try:
                dx = conc_grid.parent.grid_deltas[0]
                dy = conc_grid.parent.grid_deltas[1]
                rect_list = self._build_grid_rect_list(scaled_conc,
                                                       conc_grid.longitudes,
                                                       conc_grid.latitudes,
                                                       dx, dy,
                                                       contour_levels)
                for k, rects in enumerate(rect_list):
                    if len(rects) > 0:
                        if color_skip > 1:
                            idx = contour_levels_len - 1 - (contour_levels_len - 1 - k) * color_skip
                            logger.debug('color at k %d, idx %d', k, idx)
                            clr = fill_colors[idx % contour_levels_len]
                        else:
                            clr = fill_colors[k]
                        rectangles = matplotlib.collections.PatchCollection(rects)
                        rectangles.set_transform(self.data_crs)
                        rectangles.set_color(clr)
                        axes.add_collection(rectangles)
            except ValueError as ex:
                logger.error("cannot generate contours: {}".format(str(ex)))

        # place station locations
        self._draw_stations_if_exists(axes, self.settings)

        return rect_list

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

    def get_conc_unit_escaped(self, conc_map, settings):
        return self._escape_str_for_matplotlib(self.get_conc_unit(conc_map, settings))

    def _limit_contour_levels_for_legends(self, contour_levels,
                                          max_legend_count=25):
        if len(contour_levels) > max_legend_count:
            logger.warning("Number of contour levels exceed %d: "
                           "not all legends will be displayed",
                           max_legend_count)
            return contour_levels[:max_legend_count]
        return contour_levels

    def draw_contour_legends(self, grid, conc_map, contour_labels,
                             contour_levels, fill_colors, conc_scaling_factor,
                             color_skip=1):
        axes = self.legends_axes
        s = self.settings

        min_conc, max_conc = self.conc_type.get_plot_conc_range(
            grid,
            conc_scaling_factor)
        logger.debug("concentration plot min %g, max %g", min_conc, max_conc)

        self._turn_off_ticks(axes)

        font_sz = 9.0  # TODO: to be computed
        small_font_sz = 0.8 * font_sz

        line_skip = 1 / 20.0
        small_line_skip = 0.8 * line_skip

        x = 0.05
        y = 1.0 - small_line_skip * 0.5

        conc_unit = self.get_conc_unit_escaped(conc_map, s)

        if conc_map.has_banner():
            str = conc_map.get_banner()
            axes.text(0.5, y, str,
                      color="r",
                      fontsize=small_font_sz,
                      horizontalalignment="center",
                      verticalalignment="top",
                      clip_on=True,
                      transform=axes.transAxes)
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

        contour_levels_len = len(contour_levels)

        display_levels = self._limit_contour_levels_for_legends(
            contour_levels,
            s.max_contour_legend_count)
        for k, level in enumerate(reversed(display_levels)):
            if color_skip > 1:
                idx = k * color_skip
                logger.debug('legend color at k %d, idx %d', k, idx)
                clr = colors[idx] if idx < contour_levels_len else None
            else:
                clr = colors[k]

            if clr is not None:
                box = matplotlib.patches.Rectangle((x, y-dy), dx, dy,
                                                   color=clr,
                                                   transform=axes.transAxes)
                axes.add_patch(box)

            if k < len(labels):
                label = "NR" if level == -1.0 else labels[k]
                axes.text(x+0.5*dx, y-0.5*dy, label,
                          color="k",
                          fontsize=font_sz,
                          horizontalalignment="center",
                          verticalalignment="center",
                          clip_on=True,
                          transform=axes.transAxes)

            v = conc_map.format_conc(level)
            str = ">{0} ${1}$".format(v, conc_unit)
            axes.text(x + dx + x, y-0.5*dy, str,
                      color="k",
                      fontsize=font_sz,
                      horizontalalignment="left",
                      verticalalignment="center",
                      clip_on=True,
                      transform=axes.transAxes)

            y -= dy

        if max_conc > 0 and (s.show_max_conc == 1 or s.show_max_conc == 2):
            y -= line_skip * 0.5

            str = "Maximum: {0:.1e} ${1}$".format(max_conc, conc_unit)
            axes.text(x, y, str,
                      color="k",
                      fontsize=font_sz,
                      horizontalalignment="left",
                      verticalalignment="top",
                      clip_on=True,
                      transform=axes.transAxes)
            y -= line_skip

            str = "Minimum: {0:.1e} ${1}$".format(min_conc, conc_unit)
            axes.text(x, y, str,
                      color="k",
                      fontsize=font_sz,
                      horizontalalignment="left",
                      verticalalignment="top",
                      clip_on=True,
                      transform=axes.transAxes)
            y -= line_skip

        y = conc_map.draw_explanation_text(axes, x, y,
                                           small_font_sz,
                                           small_line_skip,
                                           labels)

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

    def _write_gisout(self, gis_writer, g, lower_vert_level, upper_vert_level,
                      rect_collections, contour_levels, color_table,
                      scaling_factor):
        if g.extension.max_locs is None:
            g.extension.max_locs = helper.find_max_locs(g)

        min_conc, max_conc = self.conc_type.get_plot_conc_range(g,
                                                                scaling_factor)

        contour_set = cntr.convert_matplotlib_rectangle_collections(rect_collections)
        contour_set.raw_colors = color_table.raw_colors
        contour_set.colors = color_table.colors
        contour_set.levels = contour_levels
        contour_set.levels_str = [self.conc_map.format_conc(level)
                                  for level in contour_levels]
        contour_set.labels = self.contour_labels
        contour_set.concentration_unit = self.get_conc_unit(self.conc_map,
                                                            self.settings)
        contour_set.min_concentration = min_conc
        contour_set.max_concentration = max_conc
        contour_set.min_concentration_str = self.conc_map.format_conc(min_conc)
        contour_set.max_concentration_str = self.conc_map.format_conc(max_conc)

        basename = gis_writer.make_output_basename(
            g,
            self.conc_type,
            self.depo_sum,
            upper_vert_level)

        gis_writer.write(basename, g, contour_set,
                         lower_vert_level, upper_vert_level,
                         distinguishable_vert_level=False)

    def draw_conc_grid(self, g, event_handlers, level_generator,
                               color_table, gis_writer=None, *args, **kwargs):

        self.layout(g, event_handlers)

        self._turn_off_spines(self.conc_outer)
        self._turn_off_ticks(self.conc_outer)

        LEVEL0 = self.conc_type.get_lower_level(g.vert_level,
                                                self.cdump.vert_levels)
        LEVEL2 = self.conc_type.get_upper_level(g.vert_level,
                                                self.settings.LEVEL2)

        level1 = self.length_factory.create_instance(LEVEL0)
        level2 = self.length_factory.create_instance(LEVEL2)

        conc_scaling_factor = self.settings.CFACT

        min_conc, max_conc = self.conc_type.get_plot_conc_range(
            g, conc_scaling_factor)

        # Use 1.0e-36 in place of min_conc to be compatible with Fortran GRIDPLOT.
        contour_levels = level_generator.make_levels(
            1.0e-36, max_conc, self.settings.contour_level_count, self.settings.DELTA)
        logger.debug('conc levels {}'.format(contour_levels))

        scaled_conc = numpy.copy(g.conc)
        if conc_scaling_factor != 1.0:
            scaled_conc *= conc_scaling_factor

        # plot title
        title = self.make_plot_title(g, self.conc_map, level1, level2,
                                     g.starting_datetime)
        self.conc_outer.set_title(title)
        self.conc_outer.set_xlabel(self.make_xlabel(g))

        # compute the color skip when the number of contours is less than
        # the number of colors.
        color_skip = 0
        if self.settings.MINCON:
            max_conc_idx = len(contour_levels) - 1
            min_conc_idx = 0
            for k in range(1, len(contour_levels)):
                if max_conc < contour_levels[k]:
                    max_conc_idx = k - 1
                    break
            for k in range(len(contour_levels) - 1, -1, -1):
                if min_conc > contour_levels[k]:
                    min_conc_idx = k
                    break
            color_skip = max(1, int(len(contour_levels)/(max_conc_idx - min_conc_idx + 1)))
            logger.debug('min_conc_idx %d, max_conc_idx %d, color_skip %d',
                         min_conc_idx, max_conc_idx, color_skip)
        
        quad_contour_set = self.draw_concentration_plot(g,
                                                        scaled_conc,
                                                        self.conc_map,
                                                        contour_levels,
                                                        color_table.colors,
                                                        color_skip=color_skip)
        self.draw_contour_legends(g,
                                  self.conc_map,
                                  self.contour_labels,
                                  contour_levels,
                                  color_table.colors,
                                  conc_scaling_factor,
                                  color_skip=color_skip)
        self.draw_bottom_text()

        if gis_writer is not None:
            self._write_gisout(gis_writer, g, level1, level2,
                               quad_contour_set, contour_levels,
                               color_table, conc_scaling_factor)

        self.fig.canvas.draw()  # to get the plot spines right.
        self.on_update_plot_extent()
        for plot_saver in self.plot_saver_list:
            plot_saver.save(self.fig, self.current_frame)

        if self.settings.interactive_mode:
            plt.show(*args, **kwargs)

        plt.close(self.fig)
        self.current_frame += 1

    def draw(self, ev_handlers=None, *args, **kwargs):
        if not self.settings.interactive_mode:
            plt.ioff()

        level_generator = ContourLevelGeneratorFactory.create_instance(
            self.settings.NSCALE,
            self.settings.MINCON)

        # Create a color table.
        self.settings.contour_levels = []
        self.settings.user_colors = \
                [(0.0, 0.0, 1.0), (0.5, 0.0, 1.0), (0.0, 0.5 , 1.0),
                (0.0, 1.0, 1.0), (0.0, 1.0, 0.5), (0.0, 0.5 , 0.0),
                (0.5, 1.0, 0.0), (1.0, 1.0, 0.0), (1.0, 0.75, 0.0),
                (1.0, 0.5, 0.0), (1.0, 0.3, 0.0), (1.0, 0.0 , 0.0)]
        self.user_label = False
        color_table = ColorTableFactory.create_instance(self.settings)

        gis_writer = gisout.GISFileWriterFactory.create_instance(
            self.settings.gis_output,
            self.settings.kml_option,
            self.time_zone)

        gis_writer.initialize(self.settings.gis_alt_mode,
                              self.settings.output_basename,
                              self.settings.output_suffix,
                              self.settings.KMAP,
                              self.settings.NSSLBL,
                              self.settings.show_max_conc,
                              self.settings.NDEP)

        self._initialize_map_projection(self.cdump)

        self.depo_sum.initialize(self.cdump.grids,
                                 self.time_selector,
                                 self.pollutant_selector)
        
        for t_index in self.time_selector:
            t_grids = helper.TimeIndexGridFilter(self.cdump.grids,
                                                 helper.TimeIndexSelector(t_index, t_index))
            initial_timeQ = (t_index == self.time_selector.first)

            grids_above_ground, grids_on_ground = self.conc_type.prepare_grids_for_plotting(t_grids)
            logger.debug("grid counts: above the ground %d, on the ground %d",
                         len(grids_above_ground), len(grids_on_ground))

            self.depo_sum.add(grids_on_ground, initial_timeQ)

            if self.value_output_writer is not None:
                self.value_output_writer.open(t_index)

            if self.settings.hlevel == 0 and self.settings.NDEP == const.DepositionType.SUM:
                # draw total deposition using the grid on the ground
                grids = self.depo_sum.get_grids_to_plot(grids_on_ground,
                                                        t_index == self.time_selector.last)
                # expect only one grid, i.e. len(grids) == 1.
                for g in grids:
                    self.draw_conc_grid(g, ev_handlers, level_gen_depo,
                                        color_table, gis_writer,
                                        *args, **kwargs)
            else:
                for g in grids_above_ground:
                    if g.vert_level == self.settings.hlevel:
                        self.draw_conc_grid(g, ev_handlers, level_generator,
                                            color_table, gis_writer,
                                            *args, **kwargs)

            if self.value_output_writer is not None:
                self.value_output_writer.close()

            self.time_period_count += 1

        for plot_saver in self.plot_saver_list:
            plot_saver.close()
        if gis_writer is not None:
            gis_writer.finalize()

    def get_plot_count_str(self):
        plot_saver = self.plot_saver_list[0]
        if plot_saver.file_count > 1:
            return "{} output files".format(plot_saver.file_count)

        s = "{} time period".format(self.time_period_count)
        if self.time_period_count > 1:
            s += "s"

        return s


class ContourLevelGeneratorFactory:

    LINEAR = 0
    LOGARITHMIC = 1
    EXPONENTIAL = 1  # the same as LOGARITHMIC

    @staticmethod
    def create_instance(scale, dynamic):
        if scale == ContourLevelGeneratorFactory.LINEAR:
            if dynamic:
                return LinearDynamicLevelGenerator()
            else:
                return LinearFixedLevelGenerator()
        elif scale == ContourLevelGeneratorFactory.LOGARITHMIC:
            if dynamic:
                return ExponentialDynamicLevelGenerator()
            else:
                return ExponentialFixedLevelGenerator()
        else:
            raise Exception("unknown method {0} for contour level "
                            "generation".format(scale))


class AbstractContourLevelGenerator(ABC):

    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def make_levels(self, min_conc, max_conc, max_levels, delta):
        pass

    def _compute_interval(self, min_conc, max_conc):
        if max_conc > 0:
            nexp = int(math.log10(max_conc))
            if nexp < 0:
                nexp -= 1
        else:
            nexp = 0
        cint = math.pow(10.0, nexp)
        return cint

    def need_to_skip_intervals(self, min_conc, max_conc, cntr_levels):
        count = len(cntr_levels)
        mxv = count - 1
        for k in range(1, count):
            if max_conc < cntr_levels[k]:
                mxv = k - 1
                break
        mnv = 0
        for k in range(count - 1, -1, -1):
            if min_conc >= cntr_levels[k]:  # Use >= to fix the FORTRAN code. TODO: remove this comment
                mnv = k
                break
        irng = mxv - mnv + 1
        return True if count > irng else False


class ExponentialDynamicLevelGenerator(AbstractContourLevelGenerator):

    def __init__(self, **kwargs):
        super(ExponentialDynamicLevelGenerator, self).__init__(**kwargs)

    def make_levels(self, min_conc, max_conc, max_levels, delta):
        logger.debug("making %d levels using min_conc %g, max_conc %g",
                     max_levels, min_conc, max_conc)

        cint = self._compute_interval(min_conc, max_conc)

        # Use a numpy ndarray to allow the *= operator.
        levels = numpy.empty(max_levels, dtype=float)

        levels[max_levels - 1] = cint
        delta_inverse = 1.0 / delta
        for k in range(max_levels - 2, -1, -1):
            v = levels[k + 1] * delta_inverse
            if v > 1.0:
                v = util.nearest_int(v)
            levels[k] = v
        logger.debug("contour levels: %s", levels)

        return levels


class ExponentialFixedLevelGenerator(ExponentialDynamicLevelGenerator):

    def __init__(self, **kwargs):
        super(ExponentialFixedLevelGenerator, self).__init__(**kwargs)

    def make_levels(self, min_conc, max_conc, max_levels, delta):
        levels = numpy.empty(max_levels, dtype=float)
        levels[0] = min_conc
        for k in range(1, max_levels):
            v = delta * levels[k - 1]
            if v > 1:
                v = util.nearest_int(v)
            levels[k] = v
        logger.debug("contour levels: %s using min %g, levels %d",
                     levels, min_conc, max_levels)
        return levels


class LinearDynamicLevelGenerator(AbstractContourLevelGenerator):

    def __init__(self):
        super(LinearDynamicLevelGenerator, self).__init__()

    def make_levels(self, min_conc, max_conc, max_levels, delta):
        cint = self._compute_interval(min_conc, max_conc)

        levels = numpy.empty(max_levels, dtype=float)
        for k in range(max_levels):
            v = cint - delta * (max_levels - 1 - k)
            if v < 0.0:
                v = 0.0
            elif v > 1.0:
                v = util.nearest_int(v)
            levels[k] = v
        logger.debug("contour levels: %s using max %g, levels %d",
                     levels, max_conc, max_levels)

        return levels


class LinearFixedLevelGenerator(LinearDynamicLevelGenerator):

    def __init__(self):
        super(LinearFixedLevelGenerator, self).__init__()

    def make_levels(self, min_conc, max_conc, max_levels, delta):
        levels = numpy.empty(max_levels, dtype=float)
        for k in range(max_levels):
            v = min_conc + delta * k
            if v > 1:
                v = util.nearest_int(v)
            levels[k] = v
        logger.debug("contour levels: %s using min %g, levels %d",
                     levels, min_conc, max_levels)
        return levels
