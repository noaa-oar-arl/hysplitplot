import sys
import os
import logging
import datetime
import math
import numpy
import geopandas
import shapely.geometry
import cartopy.crs
import cartopy.mpl
import matplotlib.dates
import matplotlib.gridspec
import matplotlib.patches
import matplotlib.pyplot as plt

from hysplit4 import cmdline, io, graph, util
from matplotlib.pyplot import xticks


logger = logging.getLogger(__name__)


class TrajectoryPlotFileReader:
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
        s.view = int(lines[1]) # 1 or 0
        s.output_postscript = lines[2]
        s.map_background = lines[3]
        s.map_projection = int(lines[4])
        s.time_label_interval = int(lines[5])
        s.zoom_factor = s.parse_zoom_factor(lines[6])
        s.color = int(lines[7]) # 1 or 0
        s.vertical_coordinate = int(lines[8])
        s.label_source = util.convert_integer_to_boolean(int(lines[9])) # 1 or 0
        s.ring = util.convert_integer_to_boolean(int(lines[10])) # 1 or 0
        s.map_center = int(lines[11]) # 1 or 0
        s.ring_number = int(lines[12])
        s.ring_distance = float(lines[13])
        s.center_loc[1] = float(lines[14])
        s.center_loc[0] = float(lines[15])

        return s


class TrajectoryPlotSettings:
    """Holds settings for a trajectory plot.

    """

    class GISOutput:
        NONE = 0
        GENERATE_POINTS = 1
        KML = 3
        PARTIAL_KML = 4
        GENERATE_LINES = 5

    class KMLOption:
        NONE = 0
        NO_EXTRA_OVERLAYS = 1
        NO_ENDPOINTS = 2
        BOTH_1_AND_2 = 3

    class Frames:
        ALL_FILES_ON_ONE = 0
        ONE_PER_FILE = 1

    class Color:
        BLACK_AND_WHITE = 0
        COLOR = 1
        ITEMIZED = 2

    class LatLonLabel:
        NONE = 0
        AUTO = 1
        SET = 2

    class MapProjection:
        AUTO = 0
        POLAR = 1
        LAMBERT = 2
        MERCATOR = 3
        CYL_EQU = 4

    class Vertical:
        NOT_SET = -1
        PRESSURE = 0
        ABOVE_GROUND_LEVEL = 1
        THETA = 2
        METEO = 3
        NONE = 4

    class ZoomFactor:
        LEAST_ZOOM = 0
        MOST_ZOOM = 100

    class HeightUnit:
        METER = 0
        FEET = 1

    def __init__(self):
        """Constructor.

        Initializes member variables to their default values.
        """

        # defined in default_tplot
        self.gis_output = self.GISOutput.NONE
        self.view = 1
        self.output_postscript = "trajplot.ps"
        self.map_background = "../graphics/arlmap" # TODO: maps directory
        self.map_projection = self.MapProjection.AUTO
        self.time_label_interval = 6
        self.zoom_factor = 0.50
        self.color = self.Color.COLOR
        self.vertical_coordinate = self.Vertical.NOT_SET
        self.label_source = True
        self.ring = False
        self.map_center = 0
        self.ring_number = -1
        # ring_number values:
        #       -1      skip all related code sections
        #        0      draw no circle but set square map scaling
        #        #      scale square map for # circles
        self.ring_distance = 0.0
        self.center_loc = [0.0, 0.0]    # lon, lat

        # command-line option only
        self.noaa_logo = False
        self.kml_option = self.KMLOption.NONE
        self.end_hour_duration = 0
        self.frames_per_file = self.Frames.ALL_FILES_ON_ONE
        self.lat_lon_label_interval_option = self.LatLonLabel.AUTO
        self.lat_lon_label_interval = 1.0
        self.input_files = "tdump"
        self.output_suffix = "ps"
        self.color_codes = None

        # internally defined
        self.map_color = "#1f77b4"
        self.marker_cycle = ["^", "s", "o"]   # triangle, square, circle
        self.marker_cycle_index = -1
        self.source_label = "\u2605" # TODO: would this work for Python 2 and 3?
        self.source_marker = "*"
        self.source_marker_color= "k"     # black
        self.source_marker_size = 8*8
        self.major_hour_marker_size = 6*6
        self.minor_hour_marker_size = 4*4
        self.terrain_line_color = "k"     # black
        self.terrain_marker = "^"         # triangle
        self.station_marker = "o"
        self.station_marker_color= "k"     # black
        self.station_marker_size = 6*6
        self.color_cycle = None
        self.height_unit = self.HeightUnit.METER

    def dump(self, stream):
        """Dumps the settings to an output stream.

        """
        stream.write("----- begin TrajectoryPlotSettings\n")
        for k, v in self.__dict__.items():
            stream.write("{0} = {1}\n".format(k, v))
        stream.write("----- end TrajectoryPlotSettings\n")

    def process_command_line_arguments(self, args):
        """Processes command-line arguments and updates settings.

        :param args: arguments excluding the program name.
        """
        args = cmdline.CommandLineArguments(args)

        self.noaa_logo              = True if args.has_arg(["+n", "+N"]) else self.noaa_logo
        self.gis_output             = args.get_integer_value("-a", self.gis_output)
        self.kml_option             = args.get_integer_value("-A", self.kml_option)
        self.end_hour_duration      = args.get_integer_value(["-e", "-E"], self.end_hour_duration)
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

        self.input_files            = args.get_string_value(["-i", "-I"], self.input_files)

        self.map_background         = args.get_string_value(["-j", "-J"], self.map_background)
        if self.map_background.startswith(".") and self.map_background.endswith("shapefiles"):
            logger.warning("enter -jshapefiles... not -j./shapefiles...")

        if args.has_arg(["-k", "-K"]):
            str = args.get_value(["-k", "-K"])
            if str.count(":") > 0:
                self.color_codes    = self.parse_color_codes(str)
                self.color          = self.Color.ITEMIZED
            else:
                self.color          = args.get_integer_value(["-k", "-K"], self.color)
                self.color          = max(0, min(1, self.color))

        self.time_label_interval    = args.get_integer_value("-l", self.time_label_interval)

        if args.has_arg("-L"):
            str = args.get_value("-L")
            if str.count(":") > 0:
                self.lat_lon_label_interval = self.parse_lat_lon_label_interval(str)
                self.lat_lon_label_interval_option = self.LatLonLabel.SET
            else:
                self.lat_lon_label_interval_option = args.get_integer_value("-L", self.lat_lon_label_interval_option)
                self.lat_lon_label_interval_option = max(0, min(1, self.lat_lon_label_interval_option))

        self.map_projection         = args.get_integer_value(["-m", "-M"], self.map_projection)
        self.output_postscript      = args.get_string_value(["-o", "-O"], self.output_postscript)
        self.output_suffix          = args.get_string_value(["-p", "-P"], self.output_suffix)
        self.label_source           = args.get_boolean_value(["-s", "-S"], self.label_source)

        self.output_postscript, self.output_suffix = self.adjust_output_filename(self.output_postscript,
                                                                                 self.output_suffix)

        if args.has_arg(["-v", "-V"]):
            self.vertical_coordinate= args.get_integer_value(["-v", "-V"], self.vertical_coordinate)
            self.vertical_coordinate= max(0, min(4, self.vertical_coordinate))

        if args.has_arg(["-z", "-Z"]):
            self.zoom_factor        = self.parse_zoom_factor(args.get_value(["-z", "-Z"]))

    def parse_color_codes(self, str):
        color_codes = []

        divider = str.index(":")
        ntraj = int(str[:divider])
        ncolors = len(str) - divider - 1
        if ntraj != ncolors:
            raise Exception("FATAL ERROR: Mismatch in option (-kn:m) n={0} m={1}".format(ntraj, ncolors))
        for c in str[divider+1:]:
            color_codes.append(c)

        return color_codes

    def parse_lat_lon_label_interval(self, str):
        divider = str.index(":")
        return int(str[divider+1:]) * 0.1

    def parse_ring_option(self, str):
        divider = str.index(":")
        count = int(str[:divider])
        distance = float(str[divider+1:])
        return count, distance

    def parse_map_center(self, str):
        divider = str.index(":")
        lat = float(str[:divider])
        lon = float(str[divider + 1:])
        lat = max(-90.0, min(90.0, lat))
        lon = max(-180.0, min(180.0, lon))
        return [lon, lat]

    def parse_zoom_factor(self, str):
        kMin = TrajectoryPlotSettings.ZoomFactor.LEAST_ZOOM
        kMax = TrajectoryPlotSettings.ZoomFactor.MOST_ZOOM
        return max(kMin, min(kMax, kMax - int(str))) * 0.01

    def adjust_vertical_coordinate(self, plot_data):
        if self.vertical_coordinate == self.Vertical.NOT_SET:
            if plot_data.vertical_motion.startswith("ISOBA"):
                self.vertical_coordinate = self.Vertical.PRESSURE
            elif plot_data.vertical_motion.startswith("THETA"):
                self.vertical_coordinate = self.Vertical.THETA
            else:
                self.vertical_coordinate = self.Vertical.ABOVE_GROUND_LEVEL
        elif self.vertical_coordinate == self.Vertical.THETA:
            # if model run does not have theta values
            if not plot_data.vertical_motion.startswith("THETA"):
                self.vertical_coordinate = self.Vertical.ABOVE_GROUND_LEVEL

    def adjust_output_filename(self, pathname, ext="ps"):
        n, x = os.path.splitext(pathname)

        if ext == "ps": # still default
            if len(x) > 1:
                ext = x[1:] # skip the dot

        return n + "." + ext, ext

    def adjust_ring_distance(self, ext_sz, grid_delta):
        ext_lon, ext_lat = ext_sz
        if self.ring_distance == 0.0:
            # max radius extent adjusted for latitude
            logger.debug("QLON %f, HLAT %f", ext_lon, self.center_loc[1])
            ext_lon = ext_lon * math.cos(self.center_loc[1] / 57.3)
            kspan = util.nearest_int(math.sqrt(ext_lon*ext_lon + ext_lat*ext_lat))
            # circle distance interval in km
            self.ring_distance = 111.0 * grid_delta * kspan / max(self.ring_number, 1)
        else:
            kspan = util.nearest_int(self.ring_distance * max(self.ring_number,1) / (111.0 * grid_delta))
        logger.debug("lon %f, lat %f, delta %f, kspan %d", ext_lon, ext_lat, grid_delta, kspan)

        if self.ring_distance <= 10.0:
            self.ring_distance = int(self.ring_distance) * 1.0
        elif self.ring_distance <= 100.0:
            self.ring_distance = int(self.ring_distance/10.0) * 10.0
        else:
            self.ring_distance = int(self.ring_distance/100.0) * 100.0

        return kspan

    def get_reader(self):
        return TrajectoryPlotFileReader(self)

    def next_marker(self):
        self.marker_cycle_index += 1
        return self.marker_cycle[self.marker_cycle_index % len(self.marker_cycle)]

    def reset_marker_cycle(self):
        self.marker_cycle_index = -1


class TrajectoryDataFileReader(io.FormattedTextFileReader):
    """Reads a trajectory data file.

    """

    def __init__(self, trajectoryData):
        io.FormattedTextFileReader.__init__(self)
        self.trajectory_data = trajectoryData

    def read(self, filename, settings):
        """Reads a data file and updates a plot data instance.

        :param filename: name of a trajectory data file.
        """
        pd = self.trajectory_data

        self.open(filename)

        self._read_header(pd)

        # prepare arrays for diagnostic outputs
        v = self.look_ahead("I6")
        ndiagnostics = v[0]

        fmt = "I6"
        for k in range(ndiagnostics):
            fmt += ",A8" if pd.format_version == 0 else ",1X,A8"

        diagnostic = []
        v = self.parse_line(fmt)
        for k in range(1, len(v)):
            diagnostic.append(v[k].strip())

        for t in pd.trajectories:
            t.diagnostic_names = diagnostic
            for var in diagnostic:
                t.others[var] = []

        if pd.format_version == 0:
            fmt = "8I6,F8.1,2F8.3,F8.1"
            for k in range(ndiagnostics):
                fmt += ",F8.1"
        else:
            fmt = "8I6,F8.1,2F9.3,1X,F8.1" # 1X missing in the FORTRAN code
            for k in range(ndiagnostics):
                fmt += ",1X,F8.1"

        firstQ = True
        while self.has_next():
            v = self.parse_line(fmt)
            if settings.end_hour_duration <= 0 or abs(v[8]) <= settings.end_hour_duration:
                g = pd.grids[v[1] - 1] if (v[1] > 0) else None
                t = pd.trajectories[v[0] - 1]
                if firstQ:
                    firstQ = False
                    if t.starting_loc == (99.0, 99.0) and v[1] > 0:
                        t.repair_starting_location(pd.trajectories[v[1] - 1])
                    actual = len(v) - 12
                    if actual != ndiagnostics:
                        logger.error("expected %d diagnostic(s) but found %d in the data file", ndiagnostics, actual)
                t.grids.append(g)
                t.datetimes.append(datetime.datetime(v[2], v[3], v[4], v[5], v[6]))
                t.forecast_hours.append(v[7])
                t.ages.append(v[8])
                t.latitudes.append(v[9])
                t.longitudes.append(v[10])
                t.heights.append(v[11])
                for k in range(ndiagnostics):
                    if 12 + k < len(v):
                        t.others[diagnostic[k]].append(v[12 + k])

        pd.after_reading_file(settings)
        return self.trajectory_data

    def _read_header(self, pd):

        # number of meteorological grids, trajectory format version
        v = self.parse_line("2I6")
        ngrid = v[0]
        pd.format_version = 0 if len(v) == 1 else v[1]

        # meteorological grids
        for k in range(ngrid):
            v = self.parse_line("A8, 5I6")
            g = pd.MeteorologicalGrid()
            g.model = v[0]
            g.datetime = datetime.datetime(v[1], v[2], v[3], v[4])
            g.forecast_hour = v[5]
            pd.grids.append(g)

        # number of trajectories, some trajectory properties
        if pd.format_version == 0:
            v = self.parse_line("I6,2A8")
            ntraj = v[0]
            pd.trajectory_direction = v[1]
            pd.vertical_motion = v[2]
        else:
            v = self.parse_line("I6,1X,A8,1X,A8,1X,A8")
            ntraj = v[0]
            pd.trajectory_direction = v[1]
            pd.vertical_motion = v[2]
            pd.IDLBL = v[3] if len(v) >= 4 else None

        # trajectory starting points
        fmt = "4I6,2F8.3,F8.1" if pd.format_version == 0 else "4I6,2F9.3,F8.1"
        for k in range(ntraj):
            v = self.parse_line(fmt)
            t = pd.Trajectory()
            t.starting_datetime = datetime.datetime(v[0], v[1], v[2], v[3])
            t.starting_loc = (v[5], v[4])
            t.starting_level = v[6]
            pd.trajectories.append(t)

    def adjust_settings(self, filename, settings):
        plot_data = TrajectoryPlotData()
        self.open(filename)
        self._read_header(plot_data)
        settings.adjust_vertical_coordinate(plot_data)


class TrajectoryPlotData:
    """Holds trajectory data for plotting.

    """

    def __init__(self):
        self.trajectory_direction = None
        self.vertical_motion = None
        self.IDLBL = None   # identifier label: MERGMEAN, MERGLIST
        self.grids = []
        self.trajectories = []
        self.format_version = 1
        self.uniq_start_levels = []

    def is_forward_calculation(self):
        return True if self.trajectory_direction.strip() == "FORWARD" else False

    def get_reader(self):
        """Create and return a reader instance.

        """
        return TrajectoryDataFileReader(self)

    def get_unique_start_datetimes(self):
        all = [t.starting_datetime for t in self.trajectories]
        return all if len(all) == 0 else list(set(all))

    def get_unique_start_locations(self):
        all = [t.starting_loc for t in self.trajectories]
        return all if len(all) == 0 else list(set(all))

    def get_unique_start_levels(self):
        all = [t.starting_level for t in self.trajectories]
        if len(all) > 0:
            all = list(set(all))
            all.sort()
        return all

    def get_latitude_range(self):
        pts = self.trajectories[0].latitudes
        amin = min(pts)
        amax = max(pts)

        for k in range(1, len(self.trajectories)):
            pts = self.trajectories[k].latitudes
            amin = min(amin, min(pts))
            amax = max(amax, max(pts))

        return (amin, amax)

    def get_longitude_range(self):
        pts = self.trajectories[0].longitudes
        amin = min(pts)
        amax = max(pts)

        for k in range(1, len(self.trajectories)):
            pts = self.trajectories[k].longitudes
            amin = min(amin, min(pts))
            amax = max(amax, max(pts))

        return (amin, amax)

    def get_age_range(self):
        pts = self.trajectories[0].ages
        amin = min(pts)
        amax = max(pts)

        for k in range(1, len(self.trajectories)):
            pts = self.trajectories[k].ages
            amin = min(amin, min(pts))
            amax = max(amax, max(pts))

        return (amin, amax)

    def get_datetime_range(self):
        pts = self.trajectories[0].datetimes
        amin = min(pts)
        amax = max(pts)

        for k in range(1, len(self.trajectories)):
            pts = self.trajectories[k].datetimes
            amin = min(amin, min(pts))
            amax = max(amax, max(pts))

        return (amin, amax)

    def get_max_forecast_hour(self):
        pts = self.trajectories[0].forecast_hours
        amax = max(pts)
        
        for k in range(1, len(self.trajectories)):
            pts = self.trajectories[k].forecast_hours
            amax = max(amax, max(pts))
        
        return amax
    
    def get_forecast_init_datetime(self):
        dt = self.trajectories[0].datetimes[0]
        forecast_hour = self.trajectories[0].forecast_hours[0]
        delta = datetime.timedelta(hours=forecast_hour)
        return dt - delta
                
    def after_reading_file(self, settings):
        for k, t in enumerate(self.trajectories):
            t.vertical_coord = AbstractVerticalCoordinate.create_instance(settings, t)
            t.vertical_coord.make_vertical_coordinates()

            if len(t.vertical_coordinates) > 0:
                t.repair_starting_level()

            if settings.color == settings.Color.ITEMIZED:
                if k >= len(settings.color_codes):
                    logger.warning("KLR Traj #%d not defined, default to color 1", k)
                    t.color = '1'
                else:
                    t.color = settings.color_codes[k]

        # determine the starting level index
        self.uniq_start_levels = self.get_unique_start_levels()
        for t in self.trajectories:
            t.starting_level_index = self.uniq_start_levels.index(t.starting_level)

        # create an color cycle instance
        settings.color_cycle = ColorCycleFactory.create_instance(settings, len(self.uniq_start_levels))

    def dump(self, stream):
        stream.write("----- begin TrajectoryPlotData\n")
        for k, v in self.__dict__.items():
            stream.write("{0} = {1}\n".format(k, v))

        for g in self.grids:
            g.dump(stream)

        for t in self.trajectories:
            t.dump(stream)
        stream.write("----- end TrajectoryPlotData\n")

    class MeteorologicalGrid:

        def __init__(self):
            self.model = None
            self.datetime = None
            self.forecast_hour = 0

        def dump(self, stream):
            stream.write("Grid: model {0}, date {1}, forecast hour {2}\n".format(\
                self.model, self.datetime, self.forecast_hour))

    class Trajectory:

        def __init__(self):
            self.starting_datetime = None
            self.starting_loc = (0, 0)
            self.starting_level = 0
            self.starting_level_index = -1  # determined after all starting_levels are collected
            self.diagnostic_names = None
            self.color = None               # when settings.color == Color.itemized
            self.vertical_coord = None      # an AbstractVerticalCoordinate instance
            # below from data points
            self.grids = []
            self.__datetimes = []
            self.__forecast_hours = []
            self.__ages = []
            self.__latitudes = []
            self.__longitudes = []
            self.__heights = []
            self.others = dict()

        def dump(self, stream):
            stream.write("Trajectory: date {0}, latlon {1} {2}, starting level {3}\n".format(
                self.starting_datetime, self.starting_loc[1], self.starting_loc[0], self.starting_level))
            for k in range(len(self.datetimes)):
                stream.write("date {4}, age {0}, latlon {1} {2}, height {3}, pressure {5}\n".format(
                    self.ages[k], self.latitudes[k], self.longitudes[k],
                    self.heights[k], self.datetimes[k], self.others["PRESSURE"][k]))

        @property
        def latitudes(self):
            return self.__latitudes

        @latitudes.setter
        def latitudes(self, lats):
            self.__latitudes = lats
             
        @property
        def longitudes(self):
            return self.__longitudes

        @longitudes.setter
        def longitudes(self, lons):
            self.__longitudes = lons
            
        @property
        def ages(self):
            return self.__ages

        @ages.setter
        def ages(self, ages):
            self.__ages = ages
            
        @property
        def datetimes(self):
            return self.__datetimes
            
        @datetimes.setter
        def datetimes(self, dts):
            self.__datetimes = dts
        
        @property
        def forecast_hours(self):
            return self.__forecast_hours
        
        @forecast_hours.setter
        def forecast_hours(self, hrs):
            self.__forecast_hours = hrs
            
        @property
        def heights(self):
            return self.__heights
        
        @heights.setter
        def heights(self, h):
            self.__heights = h
            
        @property
        def pressures(self):
            return self.others["PRESSURE"] if "PRESSURE" in self.others else None

        @pressures.setter
        def pressures(self, p):
            self.others["PRESSURE"] = p
            
        @property
        def terrain_profile(self):
            return self.others["TERR_MSL"] if "TERR_MSL" in self.others else None

        @terrain_profile.setter
        def terrain_profile(self, p):
            self.others["TERR_MSL"] = p
            
        @property
        def vertical_coordinates(self):
            return self.vertical_coord.values

        @vertical_coordinates.setter
        def vertical_coordinates(self, vc):
            self.vertical_coord.values = vc
        
        def has_terrain_profile(self):
            return True if "TERR_MSL" in self.others else False

        def repair_starting_location(self, t):
            self.starting_loc = (t.longitudes[-2], t.latitudes[-2])
            return

        def repair_starting_level(self):
            self.starting_level = self.vertical_coord.values[0]
            return


class TrajectoryPlotHelper:

    @staticmethod
    def make_ylabel(plot_data, marker, time_label_interval):
        y_label = "Source {0} at".format(marker) if time_label_interval >= 0 else "Source at"

        traj_locations = plot_data.get_unique_start_locations()
        if len(traj_locations) == 1:
            lon, lat = traj_locations[0]
            y_label += "  {0:5.2f} {1}".format(abs(lat), "N" if lat >= 0 else "S")
            y_label += "  {0:6.2f} {1}".format(abs(lon), "E" if lon >= 0 else "W")
        else:
            y_label += " multiple locations"

        return y_label

    @staticmethod
    def has_terrain_profile(plot_data_list):
        for plotData in plot_data_list:
            for t in plotData.trajectories:
                if t.has_terrain_profile():
                    return True
        return False


class TrajectoryPlot:

    _WGS84 = {"init": "epsg:4326"}  # A coordinate reference system.
    _GRIDLINE_DENSITY = 0.25        # 4 gridlines at minimum in each direction

    def __init__(self):
        self.settings = TrajectoryPlotSettings()
        self.data_list = None
        self.projection = None
        self.crs = None
        self.data_crs = cartopy.crs.PlateCarree()
        self.background_maps = []
        self.traj_axes = None
        self.height_axes = None
        self.height_axes_outer = None
        self.labels = graph.LabelsConfig()
        self.cluster_list = None

    def merge_plot_settings(self, filename, args):
        if filename is not None:
            self.settings.get_reader().read(filename)
        self.settings.process_command_line_arguments(args)

    def read_data_files(self):
        input_files = io.make_file_list(self.settings.input_files)

        # adjust settings that are dependent on a trajectory data file.
        if len(input_files) > 0:
            pd = TrajectoryPlotData()
            pd.get_reader().adjust_settings(input_files[0], self.settings)

        self.data_list = []
        for inp in input_files:
            pd = TrajectoryPlotData()
            pd.get_reader().read(inp, self.settings)
            self.data_list.append(pd)

    def make_labels_filename(self):
        s = self.settings.output_suffix
        return "LABELS.CFG" if s == "ps" else "LABELS." + s

    def read_custom_labels_if_exists(self, filename):
        if os.path.exists(filename):
            self.labels.get_reader().read(filename)
            self.labels.after_reading_file(self.settings)

    def get_gridline_spacing(self, corners_lonlat):
        if self.settings.lat_lon_label_interval_option == TrajectoryPlotSettings.LatLonLabel.NONE:
            return 0.0
        elif self.settings.lat_lon_label_interval_option == TrajectoryPlotSettings.LatLonLabel.SET:
            return self.settings.lat_lon_label_interval
        else:
            return self.calc_gridline_spacing(corners_lonlat)

    def calc_gridline_spacing(self, corners_lonlat):
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

    def _fix_map_color(self, clr):
        return clr if self.settings.color != self.settings.Color.BLACK_AND_WHITE else 'k'

    def _initialize_map_projection(self):
        map_opt_passes = 1 if self.settings.ring_number == 0 else 2
        map_box = self._determine_map_limits(self.data_list[0], map_opt_passes)
        map_box.dump(sys.stdout)

        # TODO: check if we are using pbot and ptop.
        pbot, ptop = self._determine_vertical_limit(self.data_list[0], self.settings.vertical_coordinate)

        if self.settings.center_loc == [0.0, 0.0]:
            self.settings.center_loc = self.data_list[0].trajectories[0].starting_loc

        if self.settings.ring and self.settings.ring_number >= 0:
            map_box.determine_plume_extent()
            map_box.clear_hit_map()
            map_box.set_ring_extent(self.settings)
        map_box.dump(sys.stdout)

        self.projection = graph.MapProjection.create_instance(self.settings,
                                                              self.settings.center_loc,
                                                              1.3,
                                                              (map_box.grid_delta, map_box.grid_delta),
                                                              map_box)
        self.projection.refine_corners(map_box, self.settings.center_loc)

        # map projection might have changed.
        self.settings.map_projection = self.projection.proj_type

        self.crs = self.projection.create_crs()

    def read_background_map(self):
        self.background_maps.clear()
        if self.settings.map_background.startswith("shapefiles"):
            shapefiles = graph.ShapeFilesReader().read(self.settings.map_background)
            for sf in shapefiles:
                map = graph.ShapeFileConverter.convert(sf)
                self.background_maps.append(map)
        else:
            filename = self._fix_arlmap_filename(self.settings.map_background)
            if filename is None:
                logger.warning("map background file not found")
            else:
                arlmap = graph.ARLMap().get_reader().read(filename)
                for m in graph.ARLMapConverter.convert(arlmap):
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

    def _determine_map_limits(self, plot_data, map_opt_passes):
        mb = graph.MapBox()

        for ipass in range(map_opt_passes):
            mb.allocate()

            # add source points
            for t in plot_data.trajectories:
                if t.starting_loc != (99.0, 99.0):
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

    def layout(self, ev_handlers=None):

        self._initialize_map_projection()

        fig = plt.figure(
            figsize=(8.5, 11.0),  # letter size
            clear=True,  # clear an existing figure
            constrained_layout=False
        )

        # cluster information
        self._read_cluster_info_if_exists(self.data_list)        

        fig.suptitle(self.make_plot_title(self.data_list[0]))

        outer_grid = matplotlib.gridspec.GridSpec(3, 1,
                                                  wspace=0.0, hspace=0.0,  # no spaces between subplots
                                                  width_ratios=[1.0], height_ratios=[3.0, 1.0, 0.75])

        inner_grid = matplotlib.gridspec.GridSpecFromSubplotSpec(3, 3,
                                                                 wspace=0.0, hspace=0.0,
                                                                 width_ratios=[1, 8, 1], height_ratios=[1, 6, 3],
                                                                 subplot_spec=outer_grid[1, 0])

        self.fig = fig
        self.traj_axes = fig.add_subplot(outer_grid[0, 0], projection=self.crs)
        self.height_axes_outer = fig.add_subplot(outer_grid[1, 0])
        self.height_axes = fig.add_subplot(inner_grid[1, 1])
        self.text_axes = fig.add_subplot(outer_grid[2, 0])

        if ev_handlers is not None:
            self._connect_event_handlers(ev_handlers)

    def make_plot_title(self, plot_data):
        cluster_list = self.cluster_list
        IDLBL = plot_data.IDLBL
        ntraj = len(plot_data.trajectories)

        fig_title = self.labels.get("TITLE")
        
        if IDLBL == "MERGMEAN":
            if plot_data.is_forward_calculation():
                fig_title += "\n{0} forward trajectories".format(cluster_list.total_traj)
            else:
                fig_title += "\n{0} backward trajectories".format(cluster_list.total_traj)
        elif IDLBL == "MERGLIST":
            if plot_data.is_forward_calculation():
                fig_title += "\n{0} forward trajectories starting at various times".format(ntraj)
            else:
                fig_title += "\n{0} backward trajectories ending at various times".format(ntraj)
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
                fig_title += traj_times[0].strftime(" %H%M UTC %d %b %y")
            else:
                fig_title += " various times"

        if len(plot_data.grids) > 0:
            # use the first grid for plotting
            model_name = plot_data.grids[0].model.strip()
            if plot_data.get_max_forecast_hour() > 12:
                init_time_str = plot_data.get_forecast_init_datetime().strftime("%H UTC %d %b");
                fig_title += "\n{0}  {1}  Forecast Initialization".format(init_time_str, model_name)
            else:
                fig_title += "\n{0}  Meteorological Data".format(model_name)

        return fig_title

    def _connect_event_handlers(self, handlers):
        for ev in handlers:
            self.fig.canvas.mpl_connect(ev, handlers[ev])

    @staticmethod
    def _project_extent(extent, data_crs, axes):
        """
        Transform coordinates of an extent in the data CRS to coordinates in the Axes CRS.
        """
        x1, x2, y1, y2 = extent
        bbox = shapely.geometry.LineString([[x1, y1], [x2, y1], [x2, y2], [x1, y2], [x1, y1]])
        projected = axes.projection.project_geometry(bbox, data_crs)
        x1, y1, x2, y2 = projected.bounds
        return (x1, x2, y1, y2)

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

    def update_gridlines(self):
        deltax = deltay = self.get_gridline_spacing(self.projection.corners_lonlat)
        ideltax = ideltay = int(deltax*10.0)
        if ideltax == 0:
            logger.debug("not updating gridlines because deltas are %f, %f", deltax, deltay)
            return

        lonlat_ext = self.traj_axes.get_extent(self.data_crs)
        logger.debug("determining gridlines for extent %s using deltas %f, %f", lonlat_ext, deltax, deltay)

        alonl, alonr, alatb, alatt = lonlat_ext
        # check for crossing dateline
        if util.sign(1.0, alonl) != util.sign(1.0, alonr) and alonr < 0.0:
            alonr += 360.0
            
        xticks = self._collect_tick_values(-1800, 1800, ideltax, 0.1, lonlat_ext[0:2])
        logger.debug("gridlines at lons %s", xticks)
        if len(xticks) == 0 or deltax >= abs(self._GRIDLINE_DENSITY*(alonr - alonl)):
            # recompute deltax with zero latitude span and try again
            deltax = self.calc_gridline_spacing([alonl, alonr, alatb, alatb])
            ideltax = int(deltax*10.0)
            xticks = self._collect_tick_values(-1800, 1800, ideltax, 0.1, lonlat_ext[0:2])
            logger.debug("gridlines at lats %s", xticks)
            
        yticks = self._collect_tick_values(-900+ideltay, 900, ideltay, 0.1, lonlat_ext[2:4])
        logger.debug("gridlines at lats %s", yticks)
        if len(yticks) == 0 or deltay >= abs(self._GRIDLINE_DENSITY*(alatt - alatb)):
            # recompute deltay with zero longitude span and try again
            deltay = self.calc_gridline_spacing([alonl, alonl, alatb, alatt])
            ideltay = int(deltay*10.0)
            yticks = self._collect_tick_values(-900+ideltay, 900, ideltay, 0.1, lonlat_ext[2:4])
            logger.debug("gridlines at lats %s", yticks)
            
        # draw dotted gridlines
        kwargs = {"crs": self.data_crs, "linestyle": ":", "linewidth": 0.5, "color": self.settings.map_color}
        if len(xticks) > 0:
            kwargs["xlocs"] = xticks
        if len(yticks) > 0:
            kwargs["ylocs"] = yticks
        gl = self.traj_axes.gridlines(**kwargs)
        #gl.xformatter = cartopy.mpl.gridliner.LONGITUDE_FORMATTER
        #gl.yformatter = cartopy.mpl.gridliner.LATITUDE_FORMATTER

        # lat/lon line labels
        self._draw_latlon_labels(self.traj_axes, lonlat_ext, deltax, deltay)
    
    def _draw_latlon_labels(self, axes, lonlat_ext, deltax, deltay):
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
            if deltax < 1.0:
                str = "{0:.1f}".format(lon)
            else:
                str = "{0}".format(int(lon))
            axes.text(lon, lat, str, transform=self.data_crs,
                      horizontalalignment="center", verticalalignment="center",
                      color=self.settings.map_color, clip_on=True)
        
        # lat labels
        lon = clon + 0.5 * deltax
        for k in range(-(900-ideltay), 900, ideltay):
            lat = 0.1 * k
            if deltay < 1.0:
                str = "{0:.1f}".format(lat)
            else:
                str = "{0}".format(int(lat))
            axes.text(lon, lat, str, transform=self.data_crs,
                      horizontalalignment="center", verticalalignment="center",
                      color=self.settings.map_color, clip_on=True)

    def _draw_concentric_circles(self, axes):
        lon, lat = self.data_list[0].trajectories[0].starting_loc
        R = self.settings.ring_distance/111.0
        for k in range(self.settings.ring_number):
            radius = R*(k+1)
            circ = matplotlib.patches.CirclePolygon((lon, lat), radius,
                                                    color="k", fill=False, resolution=50,
                                                    transform=self.data_crs)
            axes.add_patch(circ)
            str = "{:d} km".format(int(self.settings.ring_distance * (k+1)))
            axes.text(lon, lat - radius, str, transform=self.data_crs)

    def draw_height_profile(self, terrain_profileQ):
        axes = self.height_axes

        # reset line color and marker cycles to be in sync with the trajectory plot.
        self.settings.color_cycle.reset()
        self.settings.reset_marker_cycle()

        # Invert the y-axis for pressure profile.
        if self.data_list[0].trajectories[0].vertical_coord.need_axis_inversion():
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

        vert_proj = AbstractVerticalProjection.create_instance(axes, self.settings)
        
        # Adjust x-range.
        x_range = None
        for pd in self.data_list:
            x_range = graph.union_ranges(x_range, vert_proj.calc_xrange(pd))
        axes.set_xlim(x_range[0], x_range[1])

        # Invert the x-axis if it is a backward trajectory
        if not self.data_list[0].is_forward_calculation():
            axes.invert_xaxis()

        axes.xaxis.set_major_formatter(vert_proj.create_xlabel_formatter())
        interval_symbol_drawer = vert_proj.create_interval_symbol_drawer()

        for k, plotData in enumerate(self.data_list):
            for t in plotData.trajectories:
                clr = self.settings.color_cycle.next_color(t.starting_level_index, t.color)
                ms = self.settings.next_marker()
                # gather data points
                ages = vert_proj.select_xvalues(t)
                vc = t.vertical_coordinates
                if len(vc) > 0:
                    # draw the source marker
                    axes.scatter(ages[0], vc[0],
                                 s=self.settings.source_marker_size,
                                 marker=self.settings.source_marker,
                                 c=self.settings.source_marker_color,
                                 clip_on=False)
                    # draw a profile.
                    axes.plot(ages, vc, clr)
                    # draw triangle markers along the profile if necessary
                    interval_symbol_drawer.draw(t, ages, vc, c=clr, marker=ms, clip_on=False)
                    # show the value of the first vertical coordinate
                    if k == 0:
                        axes.text(ages[0], vc[0], "{0}  ".format(int(vc[0])),
                                  horizontalalignment="right", verticalalignment="center")
                else:
                    logger.error("skipping a trajectory with no vertical coordinate")

        # draw the terrain profile if it is necessary
        if terrain_profileQ and self.settings.vertical_coordinate == self.settings.Vertical.ABOVE_GROUND_LEVEL:
            for plotData in self.data_list:
                for t in plotData.trajectories:
                    if t.has_terrain_profile():
                        clr = self.settings.terrain_line_color
                        ms = self.settings.terrain_marker
                        # gather data points
                        ages = vert_proj.select_xvalues(t)
                        vc = t.terrain_profile
                        # draw a profile
                        axes.plot(ages, vc, clr)
                        # draw interval markers if necessary
                        interval_symbol_drawer.draw(t, ages, vc, c=clr, marker=ms, clip_on=False)
                        # draw the source marker
                        axes.scatter(ages[0], vc[0],
                                     s=self.settings.source_marker_size,
                                     marker=self.settings.source_marker,
                                     c=self.settings.source_marker_color,
                                     clip_on=False)
                        break

    def make_stationplot_filename(self):
        s = self.settings.output_suffix
        return "STATIONPLOT.CFG" if s == "ps" else "STATIONPLOT." + s

    def _draw_stations_if_exists(self, axes, filename):
        if os.path.exists(filename):
            cfg = graph.StationPlotConfig().get_reader().read(filename)
            for stn in cfg.stations:
                if len(stn.label) > 0:
                    axes.text(stn.longitude, stn.latitude, stn.label,
                              horizontalalignment="center",
                              verticalalignment="center",
                              transform=self.data_crs)
                else:
                    axes.scatter(stn.longitude, stn.latitude,
                                 s=self.settings.station_marker_size,
                                 marker=self.settings.station_marker,
                                 c=self.settings.station_marker_color, clip_on=True,
                                 transform=self.data_crs)

    def draw_trajectory_plot(self):
        axes = self.traj_axes

        # reset line color and marker cycles to be in sync with the height profile plot
        self.settings.color_cycle.reset()
        self.settings.reset_marker_cycle()

        # keep the plot size after zooming
        axes.set_aspect("equal", adjustable="datalim")

        # choose where to draw ticks and tick labels
        axes.tick_params(left="off", labelleft="off",
                         right="off", labelright="on",
                         top="off", labeltop="on",
                         bottom="off", labelbottom="off")
        # place tick labels inside the plot.
        axes.tick_params(axis="y", pad=-22)
        axes.tick_params(axis="x", pad=-22)
        # set tick label color.
        plt.setp(axes.get_xticklabels(), color=self.settings.map_color)
        plt.setp(axes.get_yticklabels(), color=self.settings.map_color)

        # y-label
        axes.set_ylabel(TrajectoryPlotHelper.make_ylabel(self.data_list[0],
                                                         self.settings.source_label,
                                                         self.settings.time_label_interval))

        # set the data range
        axes.set_extent(self.projection.corners_lonlat, self.data_crs)

        # draw the background map
        for o in self.background_maps:
            if isinstance(o.map, geopandas.geoseries.GeoSeries):
                background_map = o.map.to_crs(self.crs.proj4_init)
            else:
                background_map = o.map.copy()
                background_map['geometry'] = background_map['geometry'].to_crs(self.crs.proj4_init)
            clr = self._fix_map_color(o.linecolor)
            background_map.plot(ax=axes, linestyle=o.linestyle, linewidth=o.linewidth, color=o.linecolor)

        # draw optional concentric circles
        if self.settings.ring and self.settings.ring_number > 0:
            self._draw_concentric_circles(axes)

        # place station locations
        self._draw_stations_if_exists(axes, self.make_stationplot_filename())

        # See if the data time span is longer than the specified interval
        interval_symbol_drawer = IntervalSymbolDrawerFactory.create_instance(axes, self.settings)
            
        for plotData in self.data_list:
            for k, t in enumerate(plotData.trajectories):
                # draw a source marker
                if self.settings.label_source == 1:
                    if util.is_valid_lonlat(t.starting_loc):
                        axes.scatter(t.starting_loc[0], t.starting_loc[1],
                                     s=self.settings.source_marker_size,
                                     marker=self.settings.source_marker,
                                     c=self.settings.source_marker_color, clip_on=True,
                                     transform=self.data_crs)
                # gather data points
                lats = t.latitudes
                lons = t.longitudes
                if len(lats) == 0 or len(lons) == 0:
                    continue
                # draw a trajectory
                clr = self.settings.color_cycle.next_color(t.starting_level_index, t.color)
                ms = self.settings.next_marker()
                axes.plot(lons, lats, clr, transform=self.data_crs)
                # draw interval markers
                interval_symbol_drawer.draw(t, lons, lats, c=clr, marker=ms, clip_on=True,
                                            transform=self.data_crs)
                # cluster info
                if self.cluster_list is not None:
                    cluster_label = self.cluster_list.get_label(k)
                    axes.text(lons[-1], lats[-1], cluster_label, horizontalalignment="right",
                              verticalalignment="bottom", transform=self.data_crs)

    def _read_cluster_info_if_exists(self, data_list):
        for data in data_list:
            if data.IDLBL == "MERGMEAN":
                ntraj = len(data.trajectories)
                fn, start_index, candidates = self.make_clusterlist_filename(ntraj)
                if fn is None:
                    logger.error("file not found %s or %s", candidates[0], candidates[1])
                    raise Exception("file not found {0} or {1}".format(candidates[0], candidates[1]))
                self.cluster_list = graph.ClusterList(start_index).get_reader().read(fn)
                break
    
    def make_clusterlist_filename(self, traj_count):
        f1 = "CLUSLIST_{0}".format(traj_count)
        if os.path.exists(f1):
            return f1, 1, f1 # 1-based cluster index
        
        f2 = "CLUSLIST_{0}".format(traj_count - 1)
        if os.path.exists(f2):
            return f2, 0, f2 # 0-based cluster index
        
        return None, 1, (f1, f2)
        
    def draw_bottom_plot(self):
        if self.settings.vertical_coordinate == TrajectoryPlotSettings.Vertical.NONE:
            self._turn_off_spines(self.height_axes_outer, top=True)
            self._turn_off_ticks(self.height_axes_outer)

            self._turn_off_spines(self.height_axes)
            self._turn_off_ticks(self.height_axes)
        else:
            terrainProfileQ = TrajectoryPlotHelper.has_terrain_profile(self.data_list)

            self._turn_off_ticks(self.height_axes_outer)
            str = self.data_list[0].trajectories[0].vertical_coord.get_vertical_label()

            self.height_axes_outer.set_ylabel(str)

            self.draw_height_profile(terrainProfileQ)

    def draw_bottom_text(self):
        self._turn_off_ticks(self.text_axes)
                        
        alt_text_lines = self.labels.get("TXBOXL")
        
        maptext_fname = self.make_maptext_filename()
        if os.path.exists(maptext_fname):
            self._draw_maptext_if_exists(self.text_axes, maptext_fname)
        elif (alt_text_lines is not None) and (len(alt_text_lines) > 0):
            self._draw_alt_text_boxes(self.text_axes, alt_text_lines)
        else:
            top_spineQ = self.settings.vertical_coordinate != TrajectoryPlotSettings.Vertical.NONE
            self._turn_off_spines(self.text_axes, top=top_spineQ)
        
    def make_maptext_filename(self):
        s = self.settings.output_suffix
        return "MAPTEXT.CFG" if s == "ps" else "MAPTEXT." + s

    def _draw_maptext_if_exists(self, axes, filename):
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

    def _draw_alt_text_boxes(self, axes, lines):
        count = 0
        h = 1.0 / (len(lines) + 1)
        t = 1.0 - 0.5 * h
        for k, buff in enumerate(lines):
            axes.text(0.05, t - h*count, buff,
                      verticalalignment="top",
                      transform=axes.transAxes)
            count += 1

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
        
    def draw(self, *args, **kw):
        self.draw_trajectory_plot()
        self.draw_bottom_plot()
        self.draw_bottom_text()
        plt.show(*args, **kw)
        plt.close(self.fig)


class ColorCycle:

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
        ColorCycle.__init__(self)

    def next_color(self, height_index, color_code):
        k = (int(color_code) - 1) % self.max_colors
        return self._colors[k]


class MonoColorCycle(ColorCycle):

    def __init__(self):
        ColorCycle.__init__(self)

    def next_color(self, height_index, color_code):
        return "k"


class HeightColorCycle(ColorCycle):

    def __init__(self):
        ColorCycle.__init__(self)

    def next_color(self, height_index, color_code):
        return self._colors[height_index % self.max_colors]


class ColorCycleFactory:

    @staticmethod
    def create_instance(settings, height_count):
        if settings.color == settings.Color.COLOR:
            if height_count == 1:
                return ColorCycle(3)
            else:
                return HeightColorCycle()
        elif settings.color == settings.Color.ITEMIZED:
            return ItemizedColorCycle()
        else:
            return MonoColorCycle()


class IntervalSymbolDrawer:

    def __init__(self, axes, settings, interval):
        self.axes = axes
        self.settings = settings
        self.interval = interval


class IdleIntervalSymbolDrawer(IntervalSymbolDrawer):

    def __init__(self, axes, settings, interval):
        IntervalSymbolDrawer.__init__(self, axes, settings, interval)

    def draw(self, trajectory, x, y, **kwargs):
        return


class TimeIntervalSymbolDrawer(IntervalSymbolDrawer):

    def __init__(self, axes, settings, interval):
        IntervalSymbolDrawer.__init__(self, axes, settings, abs(interval))

    def draw(self, trajectory, x, y, **kwargs):
        dts = trajectory.datetimes

        x24, y24, x12, y12 = self._filter_data(dts, x, y, self.interval)

        if len(x24) > 0:
            self.axes.scatter(x24, y24, s=self.settings.major_hour_marker_size, **kwargs)

        if len(x12) > 0:
            self.axes.scatter(x12, y12, s=self.settings.minor_hour_marker_size, **kwargs)

    def _filter_data(self, datetimes, x, y, interval, omit_first=True):
        x24 = []; y24 = []  # at every 00:00
        xint = []; yint = []  # at every 1, 3, 6, 12, or 24.
        firstIndex = 1 if omit_first else 0

        if len(x) == len(y) and len(x) > 0:
            for k in range(firstIndex, len(datetimes)):
                if datetimes[k].hour == 0 and datetimes[k].minute == 0:
                    x24.append(x[k])
                    y24.append(y[k])
                elif (datetimes[k].hour % interval) == 0 and datetimes[k].minute == 0:
                    xint.append(x[k])
                    yint.append(y[k])

        return x24, y24, xint, yint


class AgeIntervalSymbolDrawer(IntervalSymbolDrawer):

    def __init__(self, axes, settings, interval):
        IntervalSymbolDrawer.__init__(self, axes, settings, abs(interval))

    def draw(self, trajectory, x, y, **kwargs):
        ages = trajectory.ages

        x24, y24, x12, y12 = self._filter_data(ages, x, y, self.interval)

        if len(x24) > 0:
            self.axes.scatter(x24, y24, s=self.settings.major_hour_marker_size, **kwargs)

        if len(x12) > 0:
            self.axes.scatter(x12, y12, s=self.settings.minor_hour_marker_size, **kwargs)

    def _filter_data(self, ages, x, y, interval, omit_first=True):
        x24 = []; y24 = []  # at every 00:00
        xint = []; yint = []  # at every 1, 3, 6, 12, or 24.
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
            return IdleIntervalSymbolDrawer(axes, settings, time_interval)
        

class AbstractVerticalProjection:
 
    def __init__(self, axes, settings, time_interval):
        self.axes = axes
        self.settings = settings
        self.time_interval = time_interval
        
    def calc_xrange(self, plot_data):
        # should be overriden by a child class
        return None
    
    def create_xlabel_formatter(self):
        # should be overriden by a child class
        return None
    
    def select_xvalues(self, trajectory):
        # should be overriden by a child class
        return None
    
    def create_interval_symbol_drawer(self):
        return IntervalSymbolDrawerFactory.create_instance(self.axes, self.settings)
   
    @staticmethod
    def create_instance(axes, settings):
        time_interval = settings.time_label_interval
        if time_interval >= 0:
            return TimeVerticalProjection(axes, settings, time_interval)
        else:
            return AgeVerticalProjection(axes, settings, time_interval)

    
class TimeVerticalProjection(AbstractVerticalProjection):
    
    def __init__(self, axes, settings, time_interval):
        AbstractVerticalProjection.__init__(self, axes, settings, time_interval)
        
    def calc_xrange(self, plot_data):
        return plot_data.get_datetime_range()
    
    def create_xlabel_formatter(self):
        return plt.FuncFormatter(self._format_datetime)
    
    @staticmethod
    def _format_datetime(value, position):
        if position != None:
            dt = matplotlib.dates.num2date(value)
            if dt.minute == 0 and dt.second == 0:
                if dt.hour == 0:
                    return "{0:d}\n{1:d}/{2:d}".format(dt.hour, dt.month, dt.day)
                else:
                    return "{0:d}".format(dt.hour)
        return ""
    
    def select_xvalues(self, t):
        return t.datetimes
   
    
class AgeVerticalProjection(AbstractVerticalProjection):
    
    def __init__(self, axes, settings, time_interval):
        AbstractVerticalProjection.__init__(self, axes, settings, time_interval)
        
    def calc_xrange(self, plot_data):
        return plot_data.get_age_range()
    
    def create_xlabel_formatter(self):
        return plt.FuncFormatter(self._format_age)
    
    @staticmethod
    def _format_age(value, position):
        if position != None:
            return "{0:.1f}".format(value)
        return ""
    
    def select_xvalues(self, t):
        return t.ages
    
    
class AbstractVerticalCoordinate:
    
    def __init__(self, traj):
        self.t = traj
        self.values = []
    
    def scale(self, scale_factor):
        self.values = [v*scale_factor for v in self.values]
    
    def need_axis_inversion(self):
        return False
    
    @staticmethod
    def create_instance(settings, traj):
        vc = settings.vertical_coordinate
        
        if vc == TrajectoryPlotSettings.Vertical.PRESSURE:
            return PressureCoordinate(traj)
        elif vc == TrajectoryPlotSettings.Vertical.ABOVE_GROUND_LEVEL:
            if traj.has_terrain_profile():
                return TerrainHeightCoordinate(traj, settings.height_unit)
            else:
                return HeightCoordinate(traj, settings.height_unit)
        elif vc == TrajectoryPlotSettings.Vertical.THETA:
            if "THETA" in traj.others:
                return ThetaCoordinate(traj)
        elif vc == TrajectoryPlotSettings.Vertical.METEO:
                return OtherVerticalCoordinate(traj)
        
        return BlankVerticalCoordinate(traj)

    
class BlankVerticalCoordinate(AbstractVerticalCoordinate):
    
    def __init__(self, traj):
        AbstractVerticalCoordinate.__init__(self, traj)
        
    def make_vertical_coordinates(self):
        self.values = numpy.zeros(len(self.t.longitudes))
        
    def get_vertical_label(self):
        return ""

        
class PressureCoordinate(AbstractVerticalCoordinate):
    
    def __init__(self, traj):
        AbstractVerticalCoordinate.__init__(self, traj)
    
    def make_vertical_coordinates(self):
        self.values = self.t.pressures
    
    def get_vertical_label(self):
        return "hPa"
    
    def need_axis_inversion(self):
        return True
    
    
class TerrainHeightCoordinate(AbstractVerticalCoordinate):
    
    def __init__(self, traj, unit=TrajectoryPlotSettings.HeightUnit.METER):
        AbstractVerticalCoordinate.__init__(self, traj)
        self.unit = unit
        
    def make_vertical_coordinates(self):
        self.values = numpy.add(self.t.heights, self.t.terrain_profile)
        if self.unit == TrajectoryPlotSettings.HeightUnit.FEET:
            self.scale(1.0 / 0.3048)    # meter to feet
    
    def get_vertical_label(self):
        return "Meters MSL" if self.unit == TrajectoryPlotSettings.HeightUnit.METER else "Feet MSL"


class HeightCoordinate(AbstractVerticalCoordinate):
    
    def __init__(self, traj, unit=TrajectoryPlotSettings.HeightUnit.METER):
        AbstractVerticalCoordinate.__init__(self, traj)
        self.unit = unit

    def make_vertical_coordinates(self):
        self.values = self.t.heights
        if self.unit == TrajectoryPlotSettings.HeightUnit.FEET:
            self.scale(1.0 / 0.3048)    # meter to feet
     
    def get_vertical_label(self):
        return "Meters AGL" if self.unit == TrajectoryPlotSettings.HeightUnit.METER else "Feet AGL"
   
    
class ThetaCoordinate(AbstractVerticalCoordinate):
    
    def __init__(self, traj):
        AbstractVerticalCoordinate.__init__(self, traj)

    def make_vertical_coordinates(self):
        self.values = self.t.others["THETA"]

    def get_vertical_label(self):
        return "Theta"
    

class OtherVerticalCoordinate(AbstractVerticalCoordinate):
    
    def __init__(self, traj):
        AbstractVerticalCoordinate.__init__(self, traj)
    
    def make_vertical_coordinates(self):
        self.values = self.t.others[self.t.diagnostic_names[-1]]
    
    def get_vertical_label(self):
        return self.t.diagnostic_names[-1]
