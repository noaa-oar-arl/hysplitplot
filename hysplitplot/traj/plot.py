# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# plot.py
#
# For producing trajectory plots.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
import cartopy
import copy
import logging
import matplotlib.dates
import matplotlib.gridspec
import matplotlib.patches
import matplotlib.pyplot as plt
import os
import sys

from hysplitdata.const import VerticalCoordinate
from hysplitdata.traj import model
from hysplitplot import clist, cmdline, const, mapbox, mapproj, \
                        plotbase, stnplot, streetmap, timezone, util
from hysplitplot.traj import gisout


logger = logging.getLogger(__name__)


class TrajectoryPlotSettings(plotbase.AbstractPlotSettings):
    """Holds settings for a trajectory plot.

    """

    def __init__(self):
        """Constructor.

        Initializes member variables to their default values.
        """
        super(TrajectoryPlotSettings, self).__init__()

        # defined in default_tplot
        self.view = 1
        self.output_filename = "trajplot.ps"
        self.output_basename = "trajplot"
        self.time_label_interval = 6
        self.vertical_coordinate = VerticalCoordinate.NOT_SET
        self.label_source = True
        self.map_center = 0
        self.color = const.Color.COLOR
        self.color_codes = None

        # command-line option only
        self.end_hour_duration = 0
        self.input_files = "tdump"
        self.ring = False
        self.ring_number = -1
        # ring_number values:
        #       -1      skip all related code sections
        #        0      draw no circle but set square map scaling
        #        n      scale square map for n circles
        self.ring_distance = 0.0
        self.center_loc = [0.0, 0.0]    # lon, lat

        # internally defined
        self.marker_cycle = ["^", "s", "o"]   # triangle, square, circle
        self.marker_cycle_index = -1
        self.source_label = "\u2605"  # filled star
        self.source_marker = "*"
        self.source_marker_color = "k"    # black
        self.source_marker_size = 8*8
        self.major_hour_marker_size = 6*6
        self.minor_hour_marker_size = 4*4
        self.terrain_line_color = "k"     # black
        self.terrain_marker = "^"         # triangle
        self.station_marker = "o"
        self.station_marker_color = "k"   # black
        self.station_marker_size = 6*6
        self.color_cycle = None

    def dump(self, stream):
        """Dumps the settings to an output stream.

        """
        stream.write("----- begin TrajectoryPlotSettings\n")
        for k, v in self.__dict__.items():
            stream.write("{0} = {1}\n".format(k, v))
        stream.write("----- end TrajectoryPlotSettings\n")

    def process_command_line_arguments(self, args0):
        """Processes command-line arguments and updates settings.

        :param args: arguments excluding the program name.
        """
        args = cmdline.CommandLineArguments(args0)

        # self.map_projection must be set so that --street-map may override it.
        self.map_projection = args.get_integer_value(["-m", "-M"],
                                                     self.map_projection)

        # process options common to trajplot, concplot, etc.
        self._process_cmdline_args(args0)

        self.gis_output = args.get_integer_value("-a", self.gis_output)
        self.kml_option = args.get_integer_value("-A", self.kml_option)

        self.end_hour_duration = args.get_integer_value(
            ["-e", "-E"], self.end_hour_duration)

        self.frames_per_file = args.get_integer_value(["-f", "-F"],
                                                      self.frames_per_file)

        if args.has_arg(["-g", "-G"]):
            self.ring = True
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
                if self.ring_number < 0:
                    self.ring_number = 0

        self.input_files = args.get_string_value(
            ["-i", "-I"], self.input_files)

        if args.has_arg(["-k", "-K"]):
            str = args.get_value(["-k", "-K"])
            if str.count(":") > 0:
                self.color_codes = self.parse_color_codes(str)
                self.color = const.Color.ITEMIZED
            else:
                self.color = args.get_integer_value(["-k", "-K"], self.color)
                self.color = max(0, min(1, self.color))

        self.time_label_interval = args.get_integer_value(
            "-l", self.time_label_interval)

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

        self.label_source = args.get_boolean_value(
            ["-s", "-S"], self.label_source)

        if args.has_arg(["-v", "-V"]):
            self.vertical_coordinate = args.get_integer_value(
                ["-v", "-V"], self.vertical_coordinate)
            self.vertical_coordinate = max(0, min(4, self.vertical_coordinate))

    @staticmethod
    def parse_color_codes(str):
        color_codes = []

        divider = str.index(":")
        ntraj = int(str[:divider])
        ncolors = len(str) - divider - 1
        if ntraj != ncolors:
            raise Exception("FATAL ERROR: Mismatch in option (-kn:m) "
                            "n={0} m={1}".format(ntraj, ncolors))
        for c in str[divider+1:]:
            color_codes.append(c)

        return color_codes

    def get_reader(self):
        return TrajectoryPlotSettingsReader(self)

    def next_marker(self):
        self.marker_cycle_index += 1
        return self.marker_cycle[
            self.marker_cycle_index % len(self.marker_cycle)]

    def reset_marker_cycle(self):
        self.marker_cycle_index = -1


class TrajectoryPlotSettingsReader:
    """Reads a configuration file for a trajectory plot.

    """

    def __init__(self, settings):
        self.settings = settings

    def read(self, filename):
        """Reads a trajectory plot configuration file and updates the settings.

        :param filename: name of a configuration file.
        :return:
        """
        logger.debug("reading text file %s", filename)
        with open(filename, "r") as f:
            lines = f.read().splitlines()
            f.close()

        s = self.settings

        s.gis_output = int(lines[0])
        s.view = int(lines[1])  # 1 or 0
        s.output_filename = lines[2]
        s.map_background = lines[3]
        s.map_projection = int(lines[4])
        s.time_label_interval = int(lines[5])
        s.zoom_factor = s.parse_zoom_factor(lines[6])
        s.color = int(lines[7])  # 1 or 0
        s.vertical_coordinate = int(lines[8])
        s.label_source = util.convert_int_to_bool(int(lines[9]))  # 1 or 0
        s.ring = util.convert_int_to_bool(int(lines[10]))  # 1 or 0
        s.map_center = int(lines[11])  # 1 or 0
        s.ring_number = int(lines[12])
        s.ring_distance = float(lines[13])
        s.center_loc[1] = float(lines[14])
        s.center_loc[0] = float(lines[15])

        return s


class TrajectoryPlot(plotbase.AbstractPlot):

    def __init__(self):
        super(TrajectoryPlot, self).__init__(cartopy.crs.Geodetic())
        self.settings = TrajectoryPlotSettings()
        self.data_list = None
        self.traj_axes = None
        self.height_axes = None
        self.height_axes_outer = None
        self.cluster_list = None
        self.plot_saver_list = None
        self.current_frame = 1

    def merge_plot_settings(self, filename, args):
        if filename is not None:
            self.settings.get_reader().read(filename)
        self.settings.process_command_line_arguments(args)

    def read_data_files(self):
        input_files = util.make_file_list(self.settings.input_files)

        self.data_list = []
        for inp in input_files:
            pd = model.TrajectoryDump()
            r = pd.get_reader()
            r.set_end_hour_duration(self.settings.end_hour_duration)
            r.set_vertical_coordinate(self.settings.vertical_coordinate,
                                      self.settings.height_unit)
            r.read(inp)
            self.settings.vertical_coordinate = r.vertical_coordinate
            self.set_trajectory_color(pd, self.settings)
            self.data_list.append(pd)

        # create an color cycle instance
        self.settings.color_cycle = ColorCycleFactory.create_instance(
            self.settings,
            len(self.data_list[0].uniq_start_levels))

        self.plot_saver_list = self._create_plot_saver_list(self.settings)

        time_zone_helper = timezone.TimeZoneHelper()
        if self.settings.time_zone_str is not None:
            self.time_zone = time_zone_helper.lookup_time_zone(self.settings.time_zone_str)
        elif self.settings.use_source_time_zone:
            self.time_zone = time_zone_helper.get_time_zone_at(
                self.data_list[0].trajectories[0].starting_loc)
        elif self.labels.has("TZONE"):
            self.time_zone = time_zone_helper.lookup_time_zone(self.labels.get("TZONE"))

    @staticmethod
    def has_terrain_profile(tdump_list):
        for tdump in tdump_list:
            if tdump.has_terrain_profile():
                return True
        return False

    def set_trajectory_color(self, plot_data, settings):
        if settings.color == const.Color.ITEMIZED:
            for k, t in enumerate(plot_data.trajectories):
                if k >= len(settings.color_codes):
                    logger.warning("KLR Traj #%d not defined, default "
                                   "to color 1", k)
                    t.color = '1'
                else:
                    t.color = settings.color_codes[k]

    def _make_clusterlist_filename(self, traj_count):
        f1 = "CLUSLIST_{0}".format(traj_count)
        if os.path.exists(f1):
            return f1, 1, f1  # 1-based cluster index

        f2 = "CLUSLIST_{0}".format(traj_count - 1)
        if os.path.exists(f2):
            return f2, 0, f2  # 0-based cluster index

        return None, 1, (f1, f2)

    def _read_cluster_info_if_exists(self, data_list):
        for data in data_list:
            if data.IDLBL == "MERGMEAN":
                ntraj = len(data.trajectories)
                fn, start_index, candidates = \
                    self._make_clusterlist_filename(ntraj)
                if fn is None:
                    logger.error("file not found %s or %s",
                                 candidates[0], candidates[1])
                    raise Exception("file not found {0} or {1}"
                                    .format(candidates[0], candidates[1]))
                self.cluster_list = clist.ClusterList(start_index) \
                    .get_reader().read(fn)
                break

    def _initialize_map_projection(self, data_list):
        map_opt_passes = 1 if self.settings.ring_number == 0 else 2
        map_box = self._determine_map_limits(data_list[0], map_opt_passes)

        # TODO: check if we are using pbot and ptop.
        pbot, ptop = self._determine_vertical_limit(
            data_list[0], self.settings.vertical_coordinate)

        if self.settings.center_loc == [0.0, 0.0]:
            self.settings.center_loc = \
                data_list[0].trajectories[0].starting_loc

        if self.settings.ring and self.settings.ring_number >= 0:
            map_box.determine_plume_extent()
            map_box.clear_hit_map()
            map_box.set_ring_extent(self.settings)

        self.projection = mapproj.MapProjectionFactory.create_instance(
            self.settings.map_projection,
            self.settings.zoom_factor,
            self.settings.center_loc,
            1.3,
            (map_box.grid_delta, map_box.grid_delta),
            map_box)
        self.projection.refine_corners(self.settings.center_loc)

        # The map projection might have changed to avoid singularities.
        if self.street_map is None \
                or self.settings.map_projection != self.projection.proj_type:
            self.street_map = self.create_street_map(
                self.projection,
                self.settings.use_street_map,
                self.settings.street_map_type)

        self.settings.map_projection = self.projection.proj_type
        self.initial_corners_xy = copy.deepcopy(self.projection.corners_xy)
        self.initial_corners_lonlat = copy.deepcopy(
            self.projection.corners_lonlat)

    def _determine_map_limits(self, plot_data, map_opt_passes):
        mb = mapbox.MapBox()

        for ipass in range(map_opt_passes):
            mb.allocate()

            # add source points
            for t in plot_data.trajectories:
                if util.is_valid_lonlat(t.starting_loc):
                    mb.add(t.starting_loc)

            # find trajectory hits
            mb.hit_count = 0
            for t in plot_data.trajectories:
                for k in range(len(t.latitudes)):
                    mb.add((t.longitudes[k], t.latitudes[k]))

            if mb.hit_count == 0:
                raise Exception("no trajectories to plot")

            # first pass only refines grid for small plumes
            if ipass == 0 and map_opt_passes == 2:
                mb.determine_plume_extent()
                if mb.need_to_refine_grid():
                    mb.refine_grid()
                else:
                    break

        return mb

    def _determine_vertical_limit(self, plot_data, vertical_coordinate):
        ptop = pbot = None
        for t in plot_data.trajectories:
            if len(t.vertical_coordinates) > 0:
                if ptop is None:
                    ptop = max(t.vertical_coordinates)
                    pbot = min(t.vertical_coordinates)
                else:
                    ptop = max(ptop, max(t.vertical_coordinates))
                    pbot = min(pbot, min(t.vertical_coordinates))

        if plot_data.trajectories[0].vertical_coord.need_axis_inversion():
            ptop, pbot = pbot, ptop

        return (pbot, ptop)

    def layout(self, data_list, ev_handlers=None):

        self._initialize_map_projection(data_list)

        fig = plt.figure(
            figsize=(8.5, 11.0),  # letter size
            clear=True,  # clear an existing figure
            constrained_layout=False
        )

        # cluster information
        self._read_cluster_info_if_exists(data_list)

        outer_grid = matplotlib.gridspec.GridSpec(
            3, 1,
            wspace=0.0, hspace=0.0,  # no spaces between subplots
            width_ratios=[1.0], height_ratios=[3.0, 1.0, 0.75])

        inner_grid = matplotlib.gridspec.GridSpecFromSubplotSpec(
            3, 3,
            wspace=0.0, hspace=0.0,
            width_ratios=[1, 8, 1], height_ratios=[1, 6, 3],
            subplot_spec=outer_grid[1, 0])

        self.fig = fig
        self.traj_axes = fig.add_subplot(outer_grid[0, 0],
                                         projection=self.projection.crs)
        self.height_axes_outer = fig.add_subplot(outer_grid[1, 0])
        self.height_axes = fig.add_subplot(inner_grid[1, 1])
        self.text_axes = fig.add_subplot(outer_grid[2, 0])

        if ev_handlers is not None and self.settings.interactive_mode:
            self._connect_event_handlers(ev_handlers)

    def make_plot_title(self, plot_data):
        cluster_list = self.cluster_list
        IDLBL = plot_data.IDLBL
        ntraj = len(plot_data.trajectories)

        fig_title = self.labels.get("TITLE")

        if IDLBL == "MERGMEAN":
            if plot_data.is_forward_calculation():
                fig_title += "\n{0} forward trajectories" \
                    .format(cluster_list.total_traj)
            else:
                fig_title += "\n{0} backward trajectories" \
                    .format(cluster_list.total_traj)
        elif IDLBL == "MERGLIST":
            if plot_data.is_forward_calculation():
                fig_title += "\n{0} forward trajectories starting " \
                             "at various times".format(ntraj)
            else:
                fig_title += "\n{0} backward trajectories ending " \
                             "at various times".format(ntraj)
        else:
            if plot_data.is_forward_calculation():
                if ntraj > 1:
                    fig_title += "\nForward trajectories starting at"
                else:
                    fig_title += "\nForward trajectory starting at"
            else:
                if ntraj > 1:
                    fig_title += "\nBackward trajectories ending at"
                else:
                    fig_title += "\nBackward trajectory ending at"

            traj_times = plot_data.get_unique_start_datetimes()
            if len(traj_times) == 1:
                dt = self.adjust_for_time_zone(traj_times[0])
                fig_title += dt.strftime(" %H%M %Z %d %b %Y")
            else:
                fig_title += " various times"

        if len(plot_data.grids) > 0:
            # use the first grid for plotting
            model_name = plot_data.grids[0].model.strip()
            if plot_data.get_max_forecast_hour() > 12:
                dt = self.adjust_for_time_zone(
                    plot_data.get_forecast_init_datetime())
                init_time_str = dt.strftime("%H %Z %d %b")
                fig_title += "\n{0}  {1}  Forecast Initialization" \
                    .format(init_time_str, model_name)
            else:
                fig_title += "\n{0}  Meteorological Data".format(model_name)

        return fig_title

    @staticmethod
    def make_ylabel(plot_data, marker, time_label_interval):
        if time_label_interval >= 0:
            y_label = "Source {0} at".format(marker)
        else:
            y_label = "Source at"

        traj_locations = plot_data.get_unique_start_locations()
        if len(traj_locations) == 1:
            lon, lat = traj_locations[0]
            lat_dir = "N" if lat >= 0 else "S"
            lon_dir = "E" if lon >= 0 else "W"
            y_label += "  {0:5.2f} {1}".format(abs(lat), lat_dir)
            y_label += "  {0:6.2f} {1}".format(abs(lon), lon_dir)
        else:
            y_label += " multiple locations"

        logger.debug("using ylabel %s", y_label)
        return y_label

    def get_street_map_target_axes(self):
        return self.traj_axes

    def draw_height_profile(self, data_list, terrain_profileQ):
        axes = self.height_axes

        # reset line color and marker cycles to be in sync with
        # the trajectory plot.
        self.settings.color_cycle.reset()
        self.settings.reset_marker_cycle()

        # Invert the y-axis for pressure profile.
        if data_list[0].trajectories[0].vertical_coord.need_axis_inversion():
            axes.invert_yaxis()

        # Draw y-tick labels on the right.
        axes.yaxis.tick_right()
        axes.tick_params(right="off")

        # Remove spines except for the bottom one.
        axes.spines["left"].set_visible(False)
        axes.spines["right"].set_visible(False)
        axes.spines["top"].set_visible(False)

        # Add y-gridlines
        axes.grid(True, "major", "y", linestyle="--")

        vert_proj = VerticalProjectionFactory.create_instance(axes,
                                                              self.settings)

        if self.settings.use_source_time_zone:
            time_zone = self.time_zone
        else:
            time_zone = None

        # Adjust x-range.
        x_range = None
        for pd in data_list:
            x_range = util.union_ranges(x_range,
                                        vert_proj.calc_xrange(pd, time_zone))
        axes.set_xlim(x_range[0], x_range[1])

        # Invert the x-axis if it is a backward trajectory
        if not data_list[0].is_forward_calculation():
            axes.invert_xaxis()

        axes.xaxis.set_major_formatter(vert_proj.create_xlabel_formatter())
        interval_symbol_drawer = vert_proj.create_interval_symbol_drawer()

        for k, plotData in enumerate(data_list):
            for t in plotData.trajectories:
                clr = self.settings.color_cycle.next_color(
                    t.starting_level_index, t.color)
                ms = self.settings.next_marker()
                # gather data points
                ages = vert_proj.select_xvalues(t, time_zone)
                vc = t.vertical_coordinates
                if len(vc) > 0:
                    if self.settings.label_source == 1:
                        # draw the source marker
                        axes.scatter(ages[0], vc[0],
                                     s=self.settings.source_marker_size,
                                     marker=self.settings.source_marker,
                                     c=self.settings.source_marker_color,
                                     clip_on=False)
                    # draw a profile.
                    axes.plot(ages, vc, clr)
                    # draw triangle markers along the profile if necessary
                    interval_symbol_drawer.draw(t, ages, vc,
                                                c=clr, marker=ms,
                                                clip_on=False)
                    # show the value of the first vertical coordinate
                    if k == 0:
                        axes.text(ages[0], vc[0], "{0}  ".format(int(vc[0])),
                                  horizontalalignment="right",
                                  verticalalignment="center", clip_on=True)
                else:
                    logger.info("skip drawing a trajectory with no "
                                "vertical coordinate")

        # draw the terrain profile if it is necessary
        if terrain_profileQ and self.settings.vertical_coordinate \
                == VerticalCoordinate.ABOVE_GROUND_LEVEL:
            for plotData in data_list:
                for t in plotData.trajectories:
                    if t.has_terrain_profile():
                        clr = self.settings.terrain_line_color
                        ms = self.settings.terrain_marker
                        # gather data points
                        ages = vert_proj.select_xvalues(t, time_zone)
                        vc = t.terrain_profile
                        # draw a profile
                        axes.plot(ages, vc, clr)
                        # draw interval markers if necessary
                        interval_symbol_drawer.draw(t, ages, vc, c=clr,
                                                    marker=ms, clip_on=False)
                        # draw the source marker
                        axes.scatter(ages[0], vc[0],
                                     s=self.settings.source_marker_size,
                                     marker=self.settings.source_marker,
                                     c=self.settings.source_marker_color,
                                     clip_on=False)
                        break

    def draw_trajectory_plot(self, data_list):
        axes = self.traj_axes

        # plot title
        axes.set_title(self.make_plot_title(data_list[0]))

        # reset line color and marker cycles to be in sync with
        # the height profile plot
        self.settings.color_cycle.reset()
        self.settings.reset_marker_cycle()

        # keep the plot size after zooming
        axes.set_aspect("equal", adjustable="datalim")

        # turn off ticks and tick labels
        axes.tick_params(left="off", labelleft="off",
                         right="off", labelright="off",
                         top="off", labeltop="off",
                         bottom="off", labelbottom="off")

        # y-label
        axes.set_ylabel(self.make_ylabel(data_list[0],
                                         self.settings.source_label,
                                         self.settings.time_label_interval))

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
            self._draw_concentric_circles(
                axes,
                data_list[0].trajectories[0].starting_loc,
                self.settings.ring_number,
                self.settings.ring_distance)

        # place station locations
        self._draw_stations_if_exists(axes, self.settings)

        self.draw_trajectories(self.traj_axes, data_list)
        self.draw_source_markers(self.traj_axes, data_list)

    def draw_trajectories(self, axes, data_list):
        # See if the data time span is longer than the specified interval
        interval_symbol_drawer = IntervalSymbolDrawerFactory.create_instance(
            axes, self.settings)

        for plotData in data_list:
            for k, t in enumerate(plotData.trajectories):
                # gather data points
                lats = t.latitudes
                lons = t.longitudes
                if len(lats) == 0 or len(lons) == 0:
                    continue
                # draw a trajectory
                clr = self.settings.color_cycle.next_color(
                    t.starting_level_index, t.color)
                ms = self.settings.next_marker()
                axes.plot(lons, lats, clr, transform=self.data_crs)
                # draw circles for uncertainty
                if t.has_trajectory_stddevs():
                    self.draw_trajectory_uncertainty(lons, lats,
                                                     t.trajectory_stddevs,
                                                     clr)
                # draw interval markers
                interval_symbol_drawer.draw(t, lons, lats,
                                            c=clr, marker=ms, clip_on=True,
                                            transform=self.data_crs)
                # cluster info
                if self.cluster_list is not None:
                    cluster_label = self.cluster_list.get_label(k)
                    axes.text(lons[-1], lats[-1], cluster_label,
                              horizontalalignment="right",
                              verticalalignment="bottom",
                              clip_on=True,
                              transform=self.data_crs)

    def draw_source_markers(self, axes, data_list):
        # draw a source marker
        if self.settings.label_source == 1:
            for plotData in data_list:
                for k, t in enumerate(plotData.trajectories):
                    if util.is_valid_lonlat(t.starting_loc):
                        axes.scatter(t.starting_loc[0], t.starting_loc[1],
                                     s=self.settings.source_marker_size,
                                     marker=self.settings.source_marker,
                                     c=self.settings.source_marker_color,
                                     clip_on=True,
                                     transform=self.data_crs)

    def draw_trajectory_uncertainty(self, lons, lats, sigmas, clr):
        axes = self.traj_axes
        for k, slonlat in enumerate(sigmas):
            xy = (lons[k], lats[k])
            slon, slat = slonlat
            # The multiplier 2 below is for one sigma radius.
            ellipse = matplotlib.patches.Ellipse(xy, 2*slon, 2*slat,
                                                 color=clr,
                                                 fill=False,
                                                 clip_on=True,
                                                 linewidth=0.33,
                                                 transform=self.data_crs)
            axes.add_artist(ellipse)

    def draw_bottom_plot(self, data_list):
        if self.settings.vertical_coordinate == VerticalCoordinate.NONE:
            self._turn_off_spines(self.height_axes_outer, top=True)
            self._turn_off_ticks(self.height_axes_outer)

            self._turn_off_spines(self.height_axes)
            self._turn_off_ticks(self.height_axes)
        else:
            terrainProfileQ = self.has_terrain_profile(data_list)

            self._turn_off_ticks(self.height_axes_outer)
            str = data_list[0].trajectories[0] \
                .vertical_coord.get_vertical_label()

            self.height_axes_outer.set_ylabel(str)

            self.draw_height_profile(data_list, terrainProfileQ)

    def draw_bottom_text(self):
        self._turn_off_ticks(self.text_axes)

        alt_text_lines = self.labels.get("TXBOXL")

        maptext_fname = self._make_maptext_filename(
            self.settings.output_suffix)
        if os.path.exists(maptext_fname):
            self._draw_maptext_if_exists(self.text_axes, maptext_fname)
        elif (alt_text_lines is not None) and (len(alt_text_lines) > 0):
            self._draw_alt_text_boxes(self.text_axes, alt_text_lines)
        else:
            top_spineQ = \
                self.settings.vertical_coordinate != VerticalCoordinate.NONE
            self._turn_off_spines(self.text_axes, top=top_spineQ)

    def draw(self, ev_handlers=None, *args, **kw):
        if not self.settings.interactive_mode:
            plt.ioff()

        frame_data_it = FrameDataIteratorFactory.create_instance(
            self.settings.frames_per_file, self.data_list)

        for data_list in frame_data_it:
            self.layout(data_list, ev_handlers)

            self.draw_trajectory_plot(data_list)
            self.draw_bottom_plot(data_list)
            self.draw_bottom_text()

            self.fig.canvas.draw()  # to get the plot spines right.
            self.on_update_plot_extent()
            for plot_saver in self.plot_saver_list:
                plot_saver.save(self.fig, self.current_frame)

            if self.settings.interactive_mode:
                plt.show(*args, **kw)

            plt.close(self.fig)
            self.current_frame += 1

        for plot_saver in self.plot_saver_list:
            plot_saver.close()
        self.write_gis_files()

    def write_gis_files(self):
        gis_writers = self._create_gis_writer_list(self.settings,
                                                   self.time_zone)
        for w in gis_writers:
            if w is not None:
                w.output_suffix = self.settings.output_suffix
                w.output_name = self.settings.output_filename
                w.kml_option = self.settings.kml_option
    
                for k, plot_data in enumerate(self.data_list):
                    w.write(k + 1, plot_data)

    def _create_gis_writer_list(self, settings, time_zone):
        gis_writer_list = []
        
        o = gisout.GISFileWriterFactory.create_instance(
                settings.gis_output,
                settings.height_unit,
                time_zone)
        gis_writer_list.append(o)
        
        for gis_opt in settings.additional_gis_outputs:
            o = gisout.GISFileWriterFactory.create_instance(
                    gis_opt,
                    settings.height_unit,
                    time_zone)
            gis_writer_list.append(o)

        return gis_writer_list


class ColorCycle(ABC):

    _colors = ["r", "b", "#00ff00", "c", "m", "y", "#3399cc"]

    def __init__(self, max_colors=7):
        self.max_colors = max(min(7, max_colors), 3)
        self.index = -1

    def next_color(self, height_index, color_code):
        self.index = (self.index + 1) % self.max_colors
        return self._colors[self.index]

    def reset(self):
        self.index = -1


class ItemizedColorCycle(ColorCycle):

    def __init__(self):
        super(ItemizedColorCycle, self).__init__()

    def next_color(self, height_index, color_code):
        k = (int(color_code) - 1) % self.max_colors
        return self._colors[k]


class MonoColorCycle(ColorCycle):

    def __init__(self):
        super(MonoColorCycle, self).__init__()

    def next_color(self, height_index, color_code):
        return "k"


class HeightColorCycle(ColorCycle):

    def __init__(self):
        super(HeightColorCycle, self).__init__()

    def next_color(self, height_index, color_code):
        return self._colors[height_index % self.max_colors]


class ColorCycleFactory:

    @staticmethod
    def create_instance(settings, height_count):
        if settings.color == const.Color.COLOR:
            if height_count == 1:
                return ColorCycle(3)
            else:
                return HeightColorCycle()
        elif settings.color == const.Color.ITEMIZED:
            return ItemizedColorCycle()
        else:
            return MonoColorCycle()


class IntervalSymbolDrawer(ABC):

    def __init__(self, axes, settings, interval):
        self.axes = axes
        self.settings = settings
        self.interval = interval


class NullIntervalSymbolDrawer(IntervalSymbolDrawer):

    def __init__(self, axes, settings, interval):
        super(NullIntervalSymbolDrawer, self).__init__(axes,
                                                       settings,
                                                       interval)

    def draw(self, trajectory, x, y, **kwargs):
        return


class TimeIntervalSymbolDrawer(IntervalSymbolDrawer):

    def __init__(self, axes, settings, interval):
        super(TimeIntervalSymbolDrawer, self).__init__(axes,
                                                       settings,
                                                       abs(interval))

    def draw(self, trajectory, x, y, **kwargs):
        dts = trajectory.datetimes

        x24, y24, x12, y12 = self._filter_data(dts, x, y, self.interval)

        if len(x24) > 0:
            self.axes.scatter(x24, y24,
                              s=self.settings.major_hour_marker_size, **kwargs)

        if len(x12) > 0:
            self.axes.scatter(x12, y12,
                              s=self.settings.minor_hour_marker_size, **kwargs)

    def _filter_data(self, datetimes, x, y, interval, omit_first=True):
        # points at every 00:00
        x24 = []
        y24 = []
        # points at every 1, 3, 6, 12, or 24.
        xint = []
        yint = []
        firstIndex = 1 if omit_first else 0

        if len(x) == len(y) and len(x) > 0:
            for k in range(firstIndex, len(datetimes)):
                if datetimes[k].hour == 0 and datetimes[k].minute == 0:
                    x24.append(x[k])
                    y24.append(y[k])
                elif (datetimes[k].hour % interval) == 0 \
                        and datetimes[k].minute == 0:
                    xint.append(x[k])
                    yint.append(y[k])

        return x24, y24, xint, yint


class AgeIntervalSymbolDrawer(IntervalSymbolDrawer):

    def __init__(self, axes, settings, interval):
        super(AgeIntervalSymbolDrawer, self).__init__(axes,
                                                      settings,
                                                      abs(interval))

    def draw(self, trajectory, x, y, **kwargs):
        ages = trajectory.ages

        x24, y24, x12, y12 = self._filter_data(ages, x, y, self.interval)

        if len(x24) > 0:
            self.axes.scatter(x24, y24,
                              s=self.settings.major_hour_marker_size, **kwargs)

        if len(x12) > 0:
            self.axes.scatter(x12, y12,
                              s=self.settings.minor_hour_marker_size, **kwargs)

    def _filter_data(self, ages, x, y, interval, omit_first=True):
        # points at every 00:00
        x24 = []
        y24 = []
        # points at every 1, 3, 6, 12, or 24.
        xint = []
        yint = []
        firstIndex = 1 if omit_first else 0

        if len(x) == len(y) and len(x) > 0:
            for k in range(firstIndex, len(ages)):
                if (ages[k] % 24.0) == 0:
                    x24.append(x[k])
                    y24.append(y[k])
                elif (ages[k] % interval) == 0:
                    xint.append(x[k])
                    yint.append(y[k])

        return x24, y24, xint, yint


class IntervalSymbolDrawerFactory:

    @staticmethod
    def create_instance(axes, settings):
        time_interval = settings.time_label_interval
        if time_interval > 0:
            return TimeIntervalSymbolDrawer(axes, settings, time_interval)
        elif time_interval < 0:
            return AgeIntervalSymbolDrawer(axes, settings, -time_interval)
        else:
            return NullIntervalSymbolDrawer(axes, settings, time_interval)


class AbstractVerticalProjection(ABC):

    def __init__(self, axes, settings, time_interval):
        self.axes = axes
        self.settings = settings
        self.time_interval = time_interval

    @abstractmethod
    def calc_xrange(self, plot_data, time_zone=None):
        pass

    @abstractmethod
    def create_xlabel_formatter(self):
        pass

    @abstractmethod
    def select_xvalues(self, trajectory, time_zone=None):
        pass

    def create_interval_symbol_drawer(self):
        return IntervalSymbolDrawerFactory.create_instance(self.axes,
                                                           self.settings)


class TimeVerticalProjection(AbstractVerticalProjection):

    def __init__(self, axes, settings, time_interval):
        super(TimeVerticalProjection, self).__init__(axes,
                                                     settings,
                                                     time_interval)

    def calc_xrange(self, plot_data, time_zone=None):
        r = plot_data.get_datetime_range()
        if time_zone is None:
            return r
        # See _format_datetime() for the reason why tzinfo is removed
        # after applying the timezone.
        return [x.astimezone(time_zone).replace(tzinfo=None) for x in r]

    def create_xlabel_formatter(self):
        return plt.FuncFormatter(self._format_datetime)

    @staticmethod
    def _format_datetime(value, position):
        if position is not None:
            # The value argument is a floating point number representing
            # a datetime in UTC and only in UTC.  Since this is a static
            # method, a timezone object cannot be accessed (without resorting
            # to a global variable).  An ad hoc solution is to receive a naive
            # datetime value that is unaware of timezone.  select_xvalues()
            # returns "naive" datetime values for this reason.
            dt = matplotlib.dates.num2date(value)
            if dt.minute == 0 and dt.second == 0:
                if dt.hour == 0:
                    return "{0:d}\n{1:d}/{2:d}".format(dt.hour,
                                                       dt.month,
                                                       dt.day)
                else:
                    return "{0:d}".format(dt.hour)
        return ""

    def select_xvalues(self, t, time_zone=None):
        if time_zone is None:
            return t.datetimes
        # See _format_datetime() for the reason why tzinfo is removed
        # after applying the timezone.
        return [x.astimezone(time_zone).replace(tzinfo=None)
                for x in t.datetimes]


class AgeVerticalProjection(AbstractVerticalProjection):

    def __init__(self, axes, settings, time_interval):
        super(AgeVerticalProjection, self).__init__(axes,
                                                    settings,
                                                    time_interval)

    def calc_xrange(self, plot_data, time_zone=None):
        return plot_data.get_age_range()

    def create_xlabel_formatter(self):
        return plt.FuncFormatter(self._format_age)

    @staticmethod
    def _format_age(value, position):
        if position is not None:
            return "{0:.1f}".format(value)
        return ""

    def select_xvalues(self, t, time_zone=None):
        return t.ages


class VerticalProjectionFactory:

    @staticmethod
    def create_instance(axes, settings):
        time_interval = settings.time_label_interval
        if time_interval >= 0:
            return TimeVerticalProjection(axes, settings, time_interval)
        else:
            return AgeVerticalProjection(axes, settings, time_interval)


class FrameDataIteratorFactory:

    @staticmethod
    def create_instance(frame_opt, tdump_list):
        if frame_opt == const.Frames.ALL_FILES_ON_ONE:
            return AllAtOnceFrameDataIterator(tdump_list)
        else:
            return OneByOneFrameDataIterator(tdump_list)


class AbstractFrameDataIterator(ABC):

    def __init__(self, tdump_list):
        self.tdump_list = tdump_list

    @abstractmethod
    def __iter__(self):
        pass


class AllAtOnceFrameDataIterator(AbstractFrameDataIterator):

    def __init__(self, tdump_list):
        super(AllAtOnceFrameDataIterator, self).__init__(tdump_list)

    def __iter__(self):
        return iter([self.tdump_list])


class OneByOneFrameDataIterator(AbstractFrameDataIterator):

    def __init__(self, tdump_list):
        super(OneByOneFrameDataIterator, self).__init__(tdump_list)

    def __iter__(self):
        return iter([[o] for o in self.tdump_list])
