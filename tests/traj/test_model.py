import pytest
import datetime
import pytz
from hysplit4.traj import plot, model
from hysplit4 import const


@pytest.fixture
def plotData():
    s = plot.TrajectoryPlotSettings()
    d = model.TrajectoryDump()
    r = model.TrajectoryDumpFileReader(d)
    r.set_end_hour_duration(s.end_hour_duration)
    r.set_vertical_coordinate(s.vertical_coordinate, s.height_unit)
    r.read("data/tdump")
    s.vertical_coordinate = r.vertical_coordinate
    return d


@pytest.fixture
def simpleTraj():
    t = model.Trajectory()
    t.longitudes = [0.0, 0.0]
    t.latitudes = [0.0, 0.0]
    t.heights = [10.0, 20.0]
    t.diagnostic_names = ["TERR_MSL"]
    t.others = {"TERR_MSL": [1000.0, 1010.0]}
    return t


def test_TrajectoryDump___init__():
    d = model.TrajectoryDump()

    assert hasattr(d, 'trajectory_direction')
    assert hasattr(d, 'vertical_motion')
    assert d.IDLBL == None
    assert d.grids != None and len(d.grids) == 0
    assert d.trajectories != None and len(d.trajectories) == 0
    assert d.format_version == 1
    assert d.uniq_start_levels != None and len(d.uniq_start_levels) == 0


def test_TrajectoryDump_is_forward_calculation():
    d = model.TrajectoryDump()

    d.trajectory_direction = "FORWARD"
    assert d.is_forward_calculation()

    d.trajectory_direction = " FORWARD "
    assert d.is_forward_calculation()

    d.trajectory_direction = "BACKWARD"
    assert d.is_forward_calculation() == False



def test_TrajectoryDump_has_terrain_profile(plotData):
    d = model.TrajectoryDump()
    assert d.has_terrain_profile() == False
    
    t = plotData.trajectories[0]
    t.others["TERR_MSL"] = [10.0, 500.0]
    assert plotData.has_terrain_profile() == True
    

def test_TrajectoryDump_get_reader():
    d = model.TrajectoryDump()
    r = d.get_reader()

    assert isinstance(r, model.TrajectoryDumpFileReader)
    assert r.trajectory_data is d


def test_TrajectoryDump_get_unique_start_datetimes():
    d = model.TrajectoryDump()

    list = d.get_unique_start_datetimes()
    assert len(list) == 0

    # add one trajectory

    t = model.Trajectory()
    t.starting_datetime = datetime.datetime(2019, 4, 8, 13, 4)
    d.trajectories.append(t)

    list = d.get_unique_start_datetimes()
    assert len(list) == 1
    assert list[0] == datetime.datetime(2019, 4, 8, 13, 4)

    # add one more with the same date and time.

    t = model.Trajectory()
    t.starting_datetime = datetime.datetime(2019, 4, 8, 13, 4)
    d.trajectories.append(t)

    list = d.get_unique_start_datetimes()
    assert len(list) == 1
    assert list[0] == datetime.datetime(2019, 4, 8, 13, 4)

    # add one more with a different date and time.

    t = model.Trajectory()
    t.starting_datetime = datetime.datetime(2019, 4, 8, 13, 8)
    d.trajectories.append(t)

    list = d.get_unique_start_datetimes()
    assert len(list) == 2


def test_TrajectoryDump_get_unique_start_locations():
    d = model.TrajectoryDump()

    list = d.get_unique_start_locations()
    assert len(list) == 0

    # add one trajectory

    t = model.Trajectory()
    t.starting_loc = (-90.0, 40.0)
    d.trajectories.append(t)

    list = d.get_unique_start_locations()
    assert len(list) == 1
    assert list[0] == (-90.0, 40.0)

    # add one more with the same location.

    t = model.Trajectory()
    t.starting_loc = (-90.0, 40.0)
    d.trajectories.append(t)

    list = d.get_unique_start_locations()
    assert len(list) == 1
    assert list[0] == (-90.0, 40.0)

    # add one more with a different location.

    t = model.Trajectory()
    t.starting_loc = (-90.0, 43.0)
    d.trajectories.append(t)

    list = d.get_unique_start_locations()
    assert len(list) == 2


def test_TrajectoryDump_get_unique_start_levels():
    d = model.TrajectoryDump()

    list = d.get_unique_start_levels()
    assert len(list) == 0

    # add one trajectory

    t = model.Trajectory()
    t.starting_level = 0.0
    d.trajectories.append(t)

    list = d.get_unique_start_levels()
    assert len(list) == 1
    assert list[0] == 0.0

    # add one more with the same level.

    t = model.Trajectory()
    t.starting_level = 0.0
    d.trajectories.append(t)

    list = d.get_unique_start_levels()
    assert len(list) == 1
    assert list[0] == 0.0

    # add one more with a different level.

    t = model.Trajectory()
    t.starting_level = 500.0
    d.trajectories.append(t)

    list = d.get_unique_start_levels()
    assert len(list) == 2
    assert list[1] == 500.0


def test_TrajectoryDump_get_latitude_range(plotData):
    r = plotData.get_latitude_range()

    assert r[0] == 36.886
    assert r[1] == 40.000


def test_TrajectoryDump_get_longitude_range(plotData):
    r = plotData.get_longitude_range()

    assert r[0] == -90.000
    assert r[1] == -85.285


def test_TrajectoryDump_get_age_range(plotData):
    r = plotData.get_age_range()

    assert r[0] == 0.0
    assert r[1] == 12.0


def test_TrajectoryDump_get_datetime_range(plotData):
    r = plotData.get_datetime_range()
    utc = pytz.utc
    
    assert r[0] == datetime.datetime(1995, 10, 16,  0, 0, 0, 0, utc)
    assert r[1] == datetime.datetime(1995, 10, 16, 12, 0, 0, 0, utc)


def test_TrajectoryDump_get_max_forecast_hour(plotData):
    assert 0.0 == plotData.get_max_forecast_hour()
    
    plotData.trajectories[0].forecast_hours[-1] = 12.0
    assert 12.0 == plotData.get_max_forecast_hour()


def test_TrajectoryDump_get_forecast_init_datetime(plotData):
    r = plotData.get_forecast_init_datetime()
    utc = pytz.utc

    assert r == datetime.datetime(1995, 10, 16,  0, 0, 0, 0, utc)


def test_TrajectoryDump_fix_vertical_coordinates():
    s = plot.TrajectoryPlotSettings()
    d = model.TrajectoryDump()

    t = model.Trajectory()
    t.starting_level = 10.0
    t.longitudes = [0]
    t.latitues = [0]
    t.pressures = [700.0]
    d.trajectories.append(t)

    # Run and check
    d.fix_vertical_coordinates(const.Vertical.PRESSURE, const.HeightUnit.METERS)

    assert isinstance(t.vertical_coord, model.PressureCoordinate)
    assert t.vertical_coord.values[0] == 700.0


def test_TrajectoryDump_fix_start_levels():
    s = plot.TrajectoryPlotSettings()
    d = model.TrajectoryDump()

    # add four trajectories

    t = model.Trajectory()
    t.starting_level = 10.0
    t.pressures = [700.0]
    d.trajectories.append(t)

    t = model.Trajectory()
    t.starting_level = 500.0
    t.pressures = [600.0]
    d.trajectories.append(t)

    t = model.Trajectory()
    t.starting_level = 1000.0
    t.pressures = [500.0]
    d.trajectories.append(t)

    t = model.Trajectory()
    t.starting_level = 500.0
    t.pressures = [600.0]
    d.trajectories.append(t)

    d.fix_vertical_coordinates(const.Vertical.PRESSURE, const.HeightUnit.METERS)
    
    # Run and check
    d.fix_start_levels()

    assert d.uniq_start_levels == [10.0, 500.0, 1000.0]

    assert d.trajectories[0].starting_level_index == 0
    assert d.trajectories[1].starting_level_index == 1
    assert d.trajectories[2].starting_level_index == 2
    assert d.trajectories[3].starting_level_index == 1


def test_MeteorologicalGrid___init__():
    g = model.MeteorologicalGrid()

    assert hasattr(g, 'parent')
    assert hasattr(g, 'model')
    assert hasattr(g, 'datetime')
    assert g.forecast_hour == 0

    p = model.TrajectoryDump()
    g = model.MeteorologicalGrid(p)

    assert g.parent is p
    

def test_Trajectory___init__():
    t = model.Trajectory()

    assert hasattr(t, 'parent')
    assert hasattr(t, 'starting_datetime')
    assert t.starting_loc == (0, 0)
    assert t.starting_level == 0
    assert t.starting_level_index == -1
    assert t.diagnostic_names == None
    assert t.color == None
    assert t.vertical_coord == None
    assert t.grids != None and len(t.grids) == 0
    assert t.datetimes != None and len(t.datetimes) == 0
    assert t.forecast_hours != None and len(t.forecast_hours) == 0
    assert t.ages != None and len(t.ages) == 0
    assert t.latitudes != None and len(t.latitudes) == 0
    assert t.longitudes != None and len(t.longitudes) == 0
    assert t.heights != None and len(t.heights) == 0
    assert t.others != None and len(t.others) == 0

    p = model.TrajectoryDump()
    t = model.Trajectory(p)

    assert t.parent is p

def test_Trajectory_latitudes(plotData):
    lats = plotData.trajectories[0].latitudes
    assert len(lats) == 13
    assert lats[0] == 40.0
    assert lats[12] == 38.586
    
    plotData.trajectories[0].latitudes = []


def test_Trajectory_longitudes(plotData):
    lons = plotData.trajectories[0].longitudes
    assert len(lons) == 13
    assert lons[0] == -90.0
    assert lons[12] == -88.772

    plotData.trajectories[0].longitudes = []


def test_Trajectory_ages(plotData):
    ages = plotData.trajectories[0].ages
    assert len(ages) == 13
    assert ages[0] == 0.0
    assert ages[12] == 12.0

    plotData.trajectories[0].ages = []
    

def test_Trajectory_datetimes(plotData):
    datetimes = plotData.trajectories[0].datetimes
    utc = pytz.utc
    assert len(datetimes) == 13
    assert datetimes[0] == datetime.datetime(1995, 10, 16, 0, 0, 0, 0, utc)
    assert datetimes[12] == datetime.datetime(1995, 10, 16, 12, 0, 0, 0, utc)

    plotData.trajectories[0].datetimes = []
    
    
def test_Trajectory_forecast_hours(plotData):
    forecast_hours = plotData.trajectories[0].forecast_hours
    assert len(forecast_hours) == 13
    assert forecast_hours[0] == 0
    assert forecast_hours[12] == 0

    plotData.trajectories[0].forecast_hours = []
    

def test_Trajectory_heights(plotData):
    p = plotData.trajectories[0].heights
    assert len(p) == 13
    assert p[0] == 10.0
    assert p[12] == 0.0
    
    plotData.trajectories[0].heights = []
    
    
def test_Trajectory_pressures(plotData):
    p = plotData.trajectories[0].pressures
    assert len(p) == 13
    assert p[0] == 991.7
    assert p[12] == 1001.1

    plotData.trajectories[0].pressures = []
    

def test_Trajectory_terrain_profile(plotData):
    t = plotData.trajectories[0]
    p = t.terrain_profile

    assert p == None

    t.others["TERR_MSL"] = [10.0, 500.0]
    p = t.terrain_profile

    assert p[0] == 10.0
    assert p[1] == 500.0

    t.terrain_profile = []
    

def test_Trajectory_vertical_coordinates(plotData):
    t = plotData.trajectories[0]

    p = t.vertical_coordinates
    assert len(p) == 13
    assert p[0] == 10.0
    assert p[12] == 0.0

    t.vertical_coordinates = []
    

def test_Trajectory_has_terrain_profile(plotData):
    t = plotData.trajectories[0]

    assert t.has_terrain_profile() == False

    t.others["TERR_MSL"] = [10.0, 500.0]

    assert t.has_terrain_profile() == True


def test_Trajectory_repair_starting_location():
    t = model.Trajectory()
    t.longitudes = [0, 1, 2, 3]
    t.latitudes = [1, 2, 3, 4]
    t.starting_loc = (0, 0)
    
    t.repair_starting_location(t)
    
    assert t.starting_loc == (2, 3)


def test_Trajectory_repair_starting_level():
    t = model.Trajectory()
    t.longitudes = [0]
    t.latitudes = [0]
    t.heights = [500.0]
    t.vertical_coord = model.HeightCoordinate(t)
    t.vertical_coord.make_vertical_coordinates()
    #t.vertical_coord.values[0] = 500.0
    t.starting_level = 0
    
    t.repair_starting_level()
    
    assert t.starting_level == 500.0


def test_TrajectoryDumpFileReader___init__():
    d = model.TrajectoryDump()
    r = model.TrajectoryDumpFileReader(d)

    assert r.trajectory_data is d
    assert r.end_hour_duration == 0
    assert r.vertical_coordinate == const.Vertical.PRESSURE
    assert r.height_unit == const.HeightUnit.METERS
    assert r.utc is not None


def test_TrajectoryDumpFileReader_set_end_hour_duration():
    d = model.TrajectoryDump()
    r = model.TrajectoryDumpFileReader(d)
    
    r.set_end_hour_duration(100)
    assert r.end_hour_duration == 100


def test_TrajectoryDumpFileReader_set_vertical_coordinate():
    d = model.TrajectoryDump()
    r = model.TrajectoryDumpFileReader(d)
    
    r.set_vertical_coordinate(100, const.HeightUnit.FEET)
    assert r.vertical_coordinate == 100
    assert r.height_unit == const.HeightUnit.FEET


def test_TrajectoryDumpFileReader_read():
    s = plot.TrajectoryPlotSettings()
    d = model.TrajectoryDump()
    r = model.TrajectoryDumpFileReader(d)
    r.set_end_hour_duration(s.end_hour_duration)
    r.set_vertical_coordinate(s.vertical_coordinate, s.height_unit)
    utc = pytz.utc
    
    o = r.read("data/tdump")
    s.vertical_coordinate = r.vertical_coordinate
    assert isinstance(o, model.TrajectoryDump)

    assert d.format_version == 1
    assert d.IDLBL == None

    assert len(d.grids) == 1
    g = d.grids[0]
    assert g.parent is d
    assert g.model == "    NGM "
    assert g.datetime == datetime.datetime(1995, 10, 16, 0, 0, 0, 0, utc)
    assert g.forecast_hour == 0

    assert len(d.trajectories) == 3
    assert d.trajectory_direction == "FORWARD "
    assert d.vertical_motion == "OMEGA   "

    assert d.uniq_start_levels == [10.0, 500.0, 1000.0]

    t = d.trajectories[0]
    assert t.parent is d
    assert t.starting_datetime == datetime.datetime(1995, 10, 16, 0, 0, 0, 0, utc)
    assert t.starting_loc == (-90.0, 40.0)
    assert t.starting_level == 10.0
    assert t.starting_level_index == 0
    assert len(t.diagnostic_names) == 1
    assert t.diagnostic_names[0] == "PRESSURE"

    t = d.trajectories[1]
    assert t.parent is d
    assert t.starting_datetime == datetime.datetime(1995, 10, 16, 0, 0, 0, 0, utc)
    assert t.starting_loc == (-90.0, 40.0)
    assert t.starting_level == 500.0
    assert t.starting_level_index == 1
    assert len(t.diagnostic_names) == 1
    assert t.diagnostic_names[0] == "PRESSURE"

    t = d.trajectories[2]
    assert t.parent is d
    assert t.starting_datetime == datetime.datetime(1995, 10, 16, 0, 0, 0, 0, utc)
    assert t.starting_loc == (-90.0, 40.0)
    assert t.starting_level == 1000.0
    assert t.starting_level_index == 2
    assert len(t.diagnostic_names) == 1
    assert t.diagnostic_names[0] == "PRESSURE"

    t = d.trajectories[0]
    assert len(t.grids) == 13
    assert len(t.datetimes) == 13
    assert len(t.forecast_hours) == 13
    assert len(t.ages) == 13
    assert len(t.latitudes) == 13
    assert len(t.longitudes) == 13
    assert len(t.heights) == 13
    assert len(t.vertical_coordinates) == 13
    assert len(t.others["PRESSURE"]) == 13

    k = 12
    assert t.grids[k] is d.grids[0]
    assert t.datetimes[k] == datetime.datetime(1995, 10, 16, 12, 0, 0, 0, utc)
    assert t.forecast_hours[k] == 0
    assert t.ages[k] == 12.0
    assert t.latitudes[k] == 38.586
    assert t.longitudes[k] == -88.772
    assert t.heights[k] == 0.0
    assert t.vertical_coordinates[k] == 0.0
    assert t.others["PRESSURE"][k] == 1001.1

    t = d.trajectories[2]
    assert len(t.grids) == 13
    assert len(t.datetimes) == 13
    assert len(t.forecast_hours) == 13
    assert len(t.ages) == 13
    assert len(t.latitudes) == 13
    assert len(t.longitudes) == 13
    assert len(t.heights) == 13
    assert len(t.vertical_coordinates) == 13
    assert len(t.others["PRESSURE"]) == 13

    k = 12
    assert t.grids[k] is d.grids[0]
    assert t.datetimes[k] == datetime.datetime(1995, 10, 16, 12, 0, 0, 0, utc)
    assert t.forecast_hours[k] == 0
    assert t.ages[k] == 12.0
    assert t.latitudes[k] == 36.886
    assert t.longitudes[k] == -85.285
    assert t.heights[k] == 718.4
    assert t.vertical_coordinates[k] == 718.4
    assert t.others["PRESSURE"][k] == 905.6


def test_TrajectoryDumpFileReader_read_fmt0():
    s = plot.TrajectoryPlotSettings()
    d = model.TrajectoryDump()
    r = model.TrajectoryDumpFileReader(d)
    r.set_end_hour_duration(s.end_hour_duration)
    r.set_vertical_coordinate(s.vertical_coordinate, s.height_unit)
    utc = pytz.utc
    
    r.read("data/tdump_fmt0")
    s.vertical_coordinate = r.vertical_coordinate
    
    assert d.format_version == 0
    assert d.IDLBL == None

    assert len(d.grids) == 1
    g = d.grids[0]
    assert g.parent is d
    assert g.model == "    NGM "
    assert g.datetime == datetime.datetime(1995, 10, 16, 0, 0, 0, 0, utc)
    assert g.forecast_hour == 0

    assert len(d.trajectories) == 3
    assert d.trajectory_direction == "FORWARD "
    assert d.vertical_motion == "OMEGA   "

    assert d.uniq_start_levels == [10.0, 500.0, 1000.0]

    t = d.trajectories[0]
    assert t.parent is d
    assert t.starting_datetime == datetime.datetime(1995, 10, 16, 0, 0, 0, 0, utc)
    assert t.starting_loc == (-90.0, 40.0)
    assert t.starting_level == 10.0
    assert t.starting_level_index == 0
    assert len(t.diagnostic_names) == 1
    assert t.diagnostic_names[0] == "PRESSURE"

    t = d.trajectories[1]
    assert t.parent is d
    assert t.starting_datetime == datetime.datetime(1995, 10, 16, 0, 0, 0, 0, utc)
    assert t.starting_loc == (-90.0, 40.0)
    assert t.starting_level == 500.0
    assert t.starting_level_index == 1
    assert len(t.diagnostic_names) == 1
    assert t.diagnostic_names[0] == "PRESSURE"

    t = d.trajectories[2]
    assert t.parent is d
    assert t.starting_datetime == datetime.datetime(1995, 10, 16, 0, 0, 0, 0, utc)
    assert t.starting_loc == (-90.0, 40.0)
    assert t.starting_level == 1000.0
    assert t.starting_level_index == 2
    assert len(t.diagnostic_names) == 1
    assert t.diagnostic_names[0] == "PRESSURE"

    t = d.trajectories[0]
    assert len(t.grids) == 13
    assert len(t.datetimes) == 13
    assert len(t.forecast_hours) == 13
    assert len(t.ages) == 13
    assert len(t.latitudes) == 13
    assert len(t.longitudes) == 13
    assert len(t.heights) == 13
    assert len(t.vertical_coordinates) == 13
    assert len(t.others["PRESSURE"]) == 13

    k = 12
    assert t.grids[k] is d.grids[0]
    assert t.datetimes[k] == datetime.datetime(1995, 10, 16, 12, 0, 0, 0, utc)
    assert t.forecast_hours[k] == 0
    assert t.ages[k] == 12.0
    assert t.latitudes[k] == 38.586
    assert t.longitudes[k] == -88.772
    assert t.heights[k] == 0.0
    assert t.vertical_coordinates[k] == 0.0
    assert t.others["PRESSURE"][k] == 1001.1

    t = d.trajectories[2]
    assert len(t.grids) == 13
    assert len(t.datetimes) == 13
    assert len(t.forecast_hours) == 13
    assert len(t.ages) == 13
    assert len(t.latitudes) == 13
    assert len(t.longitudes) == 13
    assert len(t.heights) == 13
    assert len(t.vertical_coordinates) == 13
    assert len(t.others["PRESSURE"]) == 13

    k = 12
    assert t.grids[k] is d.grids[0]
    assert t.datetimes[k] == datetime.datetime(1995, 10, 16, 12, 0, 0, 0, utc)
    assert t.forecast_hours[k] == 0
    assert t.ages[k] == 12.0
    assert t.latitudes[k] == 36.886
    assert t.longitudes[k] == -85.285
    assert t.heights[k] == 718.4
    assert t.vertical_coordinates[k] == 718.4
    assert t.others["PRESSURE"][k] == 905.6


def test_TrajectoryDumpFileReader_adjust_vertical_coordinate():
    d = model.TrajectoryDump()
    r = model.TrajectoryDumpFileReader(d)

    r.vertical_coordinate = const.Vertical.NOT_SET
    r.adjust_vertical_coordinate("ISOBA")
    assert r.vertical_coordinate == const.Vertical.PRESSURE

    r.vertical_coordinate = const.Vertical.NOT_SET
    r.adjust_vertical_coordinate("THETA")
    assert r.vertical_coordinate == const.Vertical.THETA

    r.vertical_coordinate = const.Vertical.NOT_SET
    r.adjust_vertical_coordinate("SOMETHING")
    assert r.vertical_coordinate == const.Vertical.ABOVE_GROUND_LEVEL

    r.vertical_coordinate = const.Vertical.THETA
    r.adjust_vertical_coordinate("PRESSURE")
    assert r.vertical_coordinate == const.Vertical.ABOVE_GROUND_LEVEL

    r.vertical_coordinate = const.Vertical.THETA
    r.adjust_vertical_coordinate("THETA")
    assert r.vertical_coordinate == const.Vertical.THETA


def test_AbstractVerticalCoordinate___init__():
    t = model.Trajectory()
    vc = model.AbstractVerticalCoordinate(t)
    assert vc.t is t
    assert vc.values != None and len(vc.values) == 0


def test_AbstractVerticalCoordinate_scale():
    t = model.Trajectory()
    vc = model.AbstractVerticalCoordinate(t)
    vc.values = [1.0, 2.0]
    vc.scale(2.0)
    assert vc.values == pytest.approx((2.0, 4.0))
    

def test_AbstractVerticalCoordinate_need_axis_inversion():
    t = model.Trajectory()
    vc = model.AbstractVerticalCoordinate(t)
    assert not vc.need_axis_inversion()


def test_AbstractVerticalCoordinate_repair_starting_level():
    t = model.Trajectory()
    vc = model.AbstractVerticalCoordinate(t)
    assert vc.repair_starting_level(100.0) == 100.0

    
def test_BlankVerticalCoordinate___init__(simpleTraj):
    vc = model.BlankVerticalCoordinate(simpleTraj)
    assert vc.t is simpleTraj
    

def test_BlankVerticalCoordinate_make_vertical_coordinates(simpleTraj):
    vc = simpleTraj.vertical_coord = model.BlankVerticalCoordinate(simpleTraj)
    vc.make_vertical_coordinates()
    h = simpleTraj.vertical_coordinates
    assert len(h) == 2
    assert h[0] == 0.0
     

def test_BlankVerticalCoordinate_get_vertical_label(simpleTraj):
    vc = simpleTraj.vertical_coord = model.BlankVerticalCoordinate(simpleTraj)
    assert vc.get_vertical_label() == ""


def test_PressureCoordinate___init__(simpleTraj):
    vc = model.PressureCoordinate(simpleTraj)
    assert vc.t is simpleTraj
    

def test_PressureCoordinate_make_vertical_coordinates(simpleTraj):
    simpleTraj.diagnostic_names.append("PRESSURE")
    simpleTraj.others["PRESSURE"] = [1001.0, 1002.0]
    
    vc = simpleTraj.vertical_coord = model.PressureCoordinate(simpleTraj)
    vc.make_vertical_coordinates()
    
    p = simpleTraj.vertical_coordinates
    assert len(p) == 2
    assert p[0] == 1001.0
    assert p[1] == 1002.0
    

def test_PressureCoordinate_get_vertical_label(simpleTraj):
    vc = simpleTraj.vertical_coord = model.PressureCoordinate(simpleTraj)
    assert vc.get_vertical_label() == "hPa"
    

def test_PressureCoordinate_need_axis_inversion(simpleTraj):
    vc = simpleTraj.vertical_coord = model.PressureCoordinate(simpleTraj)
    assert vc.need_axis_inversion() == True


def test_TerrainHeightCoordinate___init__(simpleTraj):
    vc = simpleTraj.vertical_coord = model.TerrainHeightCoordinate(simpleTraj)
    assert vc.t is simpleTraj
    assert vc.unit == const.HeightUnit.METERS
    
    vc = simpleTraj.vertical_coord = model.TerrainHeightCoordinate(simpleTraj, const.HeightUnit.FEET)
    assert vc.t is simpleTraj
    assert vc.unit == const.HeightUnit.FEET
    

def test_TerrainHeightCoordinate_make_vertical_coordinates(simpleTraj):
    # with terrain
    simpleTraj.diagnostic_names.append("TERR_MSL")
    simpleTraj.others["TERR_MSL"] = [500.0, 550.0]
 
    vc = simpleTraj.vertical_coord = model.TerrainHeightCoordinate(simpleTraj)
    vc.make_vertical_coordinates()
    
    h = simpleTraj.vertical_coordinates
    assert len(h) == 2
    assert h[0] == 510.0
    assert h[1] == 570.0
    
    # with terrain and in feet
    vc = simpleTraj.vertical_coord = model.TerrainHeightCoordinate(simpleTraj, const.HeightUnit.FEET)
    vc.make_vertical_coordinates()
    
    h = simpleTraj.vertical_coordinates
    assert len(h) == 2
    assert h[0] == pytest.approx(510.0 * 3.28084)
    assert h[1] == pytest.approx(570.0 * 3.28084)
    

def test_TerrainHeightCoordinate_get_vertical_label(simpleTraj):
    vc = simpleTraj.vertical_coord = model.TerrainHeightCoordinate(simpleTraj)
    assert vc.get_vertical_label() == "Meters MSL"
        
    vc = simpleTraj.vertical_coord = model.TerrainHeightCoordinate(simpleTraj, const.HeightUnit.FEET)
    assert vc.get_vertical_label() == "Feet MSL"


def test_TerrainHeightCoordinate_repair_starting_level(simpleTraj):
    vc = simpleTraj.vertical_coord = model.TerrainHeightCoordinate(simpleTraj)
    vc.make_vertical_coordinates()
    assert vc.repair_starting_level(0) == pytest.approx(1010.0)
        
    vc = simpleTraj.vertical_coord = model.TerrainHeightCoordinate(simpleTraj, const.HeightUnit.FEET)
    vc.make_vertical_coordinates()
    assert vc.repair_starting_level(0) == pytest.approx(3313.65)


def test_HeightCoordinate___init__(simpleTraj):
    vc = simpleTraj.vertical_coord = model.HeightCoordinate(simpleTraj)
    assert vc.t is simpleTraj
    assert vc.unit == const.HeightUnit.METERS
    
    vc = simpleTraj.vertical_coord = model.HeightCoordinate(simpleTraj, const.HeightUnit.FEET)
    assert vc.t is simpleTraj
    assert vc.unit == const.HeightUnit.FEET
    

def test_HeightCoordinate_make_vertical_coordinates(simpleTraj):
    # without terrain
    vc = simpleTraj.vertical_coord = model.HeightCoordinate(simpleTraj)
    vc.make_vertical_coordinates()
    
    h = simpleTraj.vertical_coordinates
    assert len(h) == 2
    assert h[0] == 10.0
    assert h[1] == 20.0
    
    # without terrain and in feet
    vc = simpleTraj.vertical_coord = model.HeightCoordinate(simpleTraj,  const.HeightUnit.FEET)
    vc.make_vertical_coordinates()
    
    h = simpleTraj.vertical_coordinates
    assert len(h) == 2
    assert h[0] == pytest.approx(10.0 * 3.28084)
    assert h[1] == pytest.approx(20.0 * 3.28084)


def test_HeightCoordinate_get_vertical_label(simpleTraj):
    vc = simpleTraj.vertical_coord = model.HeightCoordinate(simpleTraj)
    assert vc.get_vertical_label() == "Meters AGL"
        
    vc = simpleTraj.vertical_coord = model.HeightCoordinate(simpleTraj, const.HeightUnit.FEET)
    assert vc.get_vertical_label() == "Feet AGL"


def test_HeightCoordinate_repair_starting_level(simpleTraj):
    vc = simpleTraj.vertical_coord = model.HeightCoordinate(simpleTraj)
    vc.make_vertical_coordinates()
    assert vc.repair_starting_level(0) == pytest.approx(10.0)
        
    vc = simpleTraj.vertical_coord = model.HeightCoordinate(simpleTraj, const.HeightUnit.FEET)
    vc.make_vertical_coordinates()
    assert vc.repair_starting_level(0) == pytest.approx(32.8084)


def test_ThetaCoordinate___init__(simpleTraj):
    simpleTraj.vertical_coord =  vc = model.ThetaCoordinate(simpleTraj)
    assert vc.t is simpleTraj
    

def test_ThetaCoordinate_make_vertical_coordinates(simpleTraj):
    # theta
    simpleTraj.diagnostic_names.append("THETA")
    simpleTraj.others["THETA"] = [1500.0, 1550.0]
    
    vc = simpleTraj.vertical_coord = model.ThetaCoordinate(simpleTraj)
    vc.make_vertical_coordinates()
    
    h = simpleTraj.vertical_coordinates
    assert len(h) == 2
    assert h[0] == 1500.0
    assert h[1] == 1550.0
 

def test_ThetaCoordinate_get_vertical_label(simpleTraj):
    vc = simpleTraj.vertical_coord = model.ThetaCoordinate(simpleTraj)
    assert vc.get_vertical_label() == "Theta"
    

def test_OtherVerticalCoordinate___init__(simpleTraj):
    vc = simpleTraj.vertical_coord = model.OtherVerticalCoordinate(simpleTraj)
    assert vc.t is simpleTraj
    

def test_OtherVerticalCoordinate_make_vertical_coordinates(simpleTraj):
    # something else
    simpleTraj.diagnostic_names.append("SUN_FLUX")
    simpleTraj.others["SUN_FLUX"] = [50.0, 55.0]
    
    vc = simpleTraj.vertical_coord = model.OtherVerticalCoordinate(simpleTraj)
    vc.make_vertical_coordinates()
    
    h = simpleTraj.vertical_coordinates
    assert len(h) == 2
    assert h[0] == 50.0
    assert h[1] == 55.0
    

def test_OtherVerticalCoordinate_get_vertical_label(simpleTraj):
    simpleTraj.diagnostic_names.append("SUN_FLUX")
    simpleTraj.others["SUN_FLUX"] = [50.0, 55.0]
    
    vc = simpleTraj.vertical_coord = model.OtherVerticalCoordinate(simpleTraj)
    
    assert vc.get_vertical_label() == "SUN_FLUX"


def test_VerticalCoordinateFactory_create_instance():
    s = plot.TrajectoryPlotSettings()
    t = model.Trajectory()
    
    s.vertical_coordinate = const.Vertical.PRESSURE
    vc = model.VerticalCoordinateFactory.create_instance(s.vertical_coordinate, s.height_unit, t)
    assert isinstance(vc, model.PressureCoordinate)
    
    s.vertical_coordinate = const.Vertical.ABOVE_GROUND_LEVEL
    vc = model.VerticalCoordinateFactory.create_instance(s.vertical_coordinate, s.height_unit, t)
    assert isinstance(vc, model.HeightCoordinate)
    
    t.others["TERR_MSL"] = [1.0, 2.0]
    s.vertical_coordinate = const.Vertical.ABOVE_GROUND_LEVEL
    vc = model.VerticalCoordinateFactory.create_instance(s.vertical_coordinate, s.height_unit, t)
    assert isinstance(vc, model.TerrainHeightCoordinate)
    
    t.others["THETA"] = [0.0, 1.0]
    s.vertical_coordinate = const.Vertical.THETA
    vc = model.VerticalCoordinateFactory.create_instance(s.vertical_coordinate, s.height_unit, t)
    assert isinstance(vc, model.ThetaCoordinate)
    
    s.vertical_coordinate = const.Vertical.METEO
    vc = model.VerticalCoordinateFactory.create_instance(s.vertical_coordinate, s.height_unit, t)
    assert isinstance(vc, model.OtherVerticalCoordinate)
    
    s.vertical_coordinate = const.Vertical.NONE
    vc = model.VerticalCoordinateFactory.create_instance(s.vertical_coordinate, s.height_unit, t)
    assert isinstance(vc, model.BlankVerticalCoordinate)
