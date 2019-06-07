import logging
import datetime
import numpy

from hysplit4 import io, const


logger = logging.getLogger(__name__)


class TrajectoryDump:
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

    def has_terrain_profile(self):
        for t in self.trajectories:
            if t.has_terrain_profile():
                return True
        return False
    
    def get_reader(self):
        """Create and return a reader instance.

        """
        return TrajectoryDumpFileReader(self)

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
           
    def fix_vertical_coordinates(self, vert_coord, height_unit):
        for t in self.trajectories:
            t.vertical_coord = VerticalCoordinateFactory.create_instance(vert_coord, height_unit, t)
            t.vertical_coord.make_vertical_coordinates()
                
    def fix_start_levels(self):
        # The starting level needs to be fixed when the terrain height is added.
        # Or its unit is other than meter.
        for t in self.trajectories:
            t.repair_starting_level()
                
        # determine the starting level index
        self.uniq_start_levels = self.get_unique_start_levels()
        for t in self.trajectories:
            t.starting_level_index = self.uniq_start_levels.index(t.starting_level)

    def dump(self, stream):
        stream.write("----- begin TrajectoryDump\n")
        for k, v in self.__dict__.items():
            stream.write("{0} = {1}\n".format(k, v))

        for g in self.grids:
            g.dump(stream)

        for t in self.trajectories:
            t.dump(stream)
        stream.write("----- end TrajectoryDump\n")

class MeteorologicalGrid:

    def __init__(self, parent=None):
        self.parent = parent            # a TrajectoryDump instance
        self.model = None
        self.datetime = None
        self.forecast_hour = 0

    def dump(self, stream):
        stream.write("Grid: model {0}, date {1}, forecast hour {2}\n".format(\
            self.model, self.datetime, self.forecast_hour))

class Trajectory:

    def __init__(self, parent=None):
        self.parent = parent            # a TrajectoryDump instance
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
        self.starting_level = self.vertical_coord.repair_starting_level(self.starting_level)
        return


class TrajectoryDumpFileReader(io.FormattedTextFileReader):
    """Reads a trajectory data file.

    """

    def __init__(self, trajectoryData):
        io.FormattedTextFileReader.__init__(self)
        self.trajectory_data = trajectoryData
        self.end_hour_duration = 0
        self.vertical_coordinate = const.Vertical.PRESSURE
        self.height_unit = const.HeightUnit.METERS
    
    def set_end_hour_duration(self, v):
        self.end_hour_duration = v
        
    def set_vertical_coordinate(self, vc, hu):
        self.vertical_coordinate = vc
        self.height_unit = hu

    def read(self, filename):
        """Reads a data file and updates a plot data instance.

        :param filename: name of a trajectory data file.
        """
        pd = self.trajectory_data

        self.open(filename)
        self._read_header(pd)
        self.adjust_vertical_coordinate(pd.vertical_motion)
        
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
            if self.end_hour_duration <= 0 or abs(v[8]) <= self.end_hour_duration:
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

        pd.fix_vertical_coordinates(self.vertical_coordinate, self.height_unit)
        pd.fix_start_levels()
        
        return self.trajectory_data
                
    def adjust_vertical_coordinate(self, vert_motion):
        if self.vertical_coordinate == const.Vertical.NOT_SET:
            if vert_motion.startswith("ISOBA"):
                self.vertical_coordinate = const.Vertical.PRESSURE
            elif vert_motion.startswith("THETA"):
                self.vertical_coordinate = const.Vertical.THETA
            else:
                self.vertical_coordinate = const.Vertical.ABOVE_GROUND_LEVEL
        elif self.vertical_coordinate == const.Vertical.THETA:
            # if model run does not have theta values
            if not vert_motion.startswith("THETA"):
                self.vertical_coordinate = const.Vertical.ABOVE_GROUND_LEVEL
                
    def _read_header(self, pd):

        # number of meteorological grids, trajectory format version
        v = self.parse_line("2I6")
        ngrid = v[0]
        pd.format_version = 0 if len(v) == 1 else v[1]

        # meteorological grids
        for k in range(ngrid):
            v = self.parse_line("A8, 5I6")
            g = MeteorologicalGrid(pd)
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
            t = Trajectory(pd)
            t.starting_datetime = datetime.datetime(v[0], v[1], v[2], v[3])
            t.starting_loc = (v[5], v[4])
            t.starting_level = v[6]
            pd.trajectories.append(t)

    
class AbstractVerticalCoordinate:
    
    def __init__(self, traj):
        self.t = traj
        self.values = []
    
    def scale(self, scale_factor):
        self.values = [v*scale_factor for v in self.values]
    
    def need_axis_inversion(self):
        return False
    
    def repair_starting_level(self, v):
        return v
 
    
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
    
    def __init__(self, traj, unit=const.HeightUnit.METERS):
        AbstractVerticalCoordinate.__init__(self, traj)
        self.unit = unit
        
    def make_vertical_coordinates(self):
        self.values = numpy.add(self.t.heights, self.t.terrain_profile)
        if self.unit == const.HeightUnit.FEET:
            self.scale(1.0 / 0.3048)    # meter to feet
    
    def get_vertical_label(self):
        return "Meters MSL" if self.unit == const.HeightUnit.METERS else "Feet MSL"
    
    def repair_starting_level(self, v):
        return self.values[0]
 

class HeightCoordinate(AbstractVerticalCoordinate):
    
    def __init__(self, traj, unit=const.HeightUnit.METERS):
        AbstractVerticalCoordinate.__init__(self, traj)
        self.unit = unit

    def make_vertical_coordinates(self):
        self.values = self.t.heights
        if self.unit == const.HeightUnit.FEET:
            self.scale(1.0 / 0.3048)    # meter to feet
     
    def get_vertical_label(self):
        return "Meters AGL" if self.unit == const.HeightUnit.METERS else "Feet AGL"
       
    def repair_starting_level(self, v):
        return self.values[0]
 
    
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
            

class VerticalCoordinateFactory:
       
    @staticmethod
    def create_instance(vert_coord, height_unit, traj):
        
        if vert_coord == const.Vertical.PRESSURE:
            return PressureCoordinate(traj)
        elif vert_coord == const.Vertical.ABOVE_GROUND_LEVEL:
            if traj.has_terrain_profile():
                return TerrainHeightCoordinate(traj, height_unit)
            else:
                return HeightCoordinate(traj, height_unit)
        elif vert_coord == const.Vertical.THETA:
            if "THETA" in traj.others:
                return ThetaCoordinate(traj)
        elif vert_coord == const.Vertical.METEO:
                return OtherVerticalCoordinate(traj)
        
        return BlankVerticalCoordinate(traj)
