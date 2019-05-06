import pytest
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates
import cartopy.crs
from hysplit4.traj import plot
from hysplit4 import graph


@pytest.fixture
def plotData():
    s = plot.TrajectoryPlotSettings()
    d = plot.TrajectoryPlotData()
    r = plot.TrajectoryDataFileReader(d)
    r.adjust_settings("data/tdump", s)
    r.read("data/tdump", s)
    return d


def blank_event_handler(event):
    # do nothing
    return


def cleanup_plot(p):
    if p.fig is not None:
        plt.close(p.fig)


def test_TrajectoryPlotFileReader___init__():
    s = plot.TrajectoryPlotSettings()
    r = plot.TrajectoryPlotFileReader(s)

    assert r.settings is s


def test_TrajectoryPlotFileReader_read():
    s = plot.TrajectoryPlotSettings()
    r = plot.TrajectoryPlotFileReader(s)

    o = r.read("data/default_tplot")
    assert isinstance(o, plot.TrajectoryPlotSettings)

    assert s.gis_output == 0
    assert s.view == 1
    assert s.output_postscript == "trajplot"
    assert s.map_background == "../graphics/arlmap"
    assert s.map_projection == 0
    assert s.time_label_interval == 12
    assert s.zoom_factor == 0.50
    assert s.color == 1
    assert s.vertical_coordinate == 0
    assert s.label_source == False
    assert s.ring == False
    assert s.map_center == 1
    assert s.ring_number == 4
    assert s.ring_distance == 100.0
    assert s.center_loc == [-90.0, 40.0]


def test_TrajectoryPlotSettings___init__():
    s = plot.TrajectoryPlotSettings()

    assert s.gis_output == 0
    assert s.view == 1
    assert s.output_postscript == "trajplot.ps"
    assert s.map_background == "../graphics/arlmap"
    assert s.map_projection == 0
    assert s.time_label_interval == 6
    assert s.zoom_factor == 0.5
    assert s.color == 1
    assert s.vertical_coordinate == s.Vertical.NOT_SET
    assert s.label_source == True
    assert s.ring == False
    assert s.map_center == 0
    assert s.ring_number == -1
    assert s.ring_distance == 0.0
    assert s.center_loc == [0.0, 0.0]

    assert s.noaa_logo == False
    assert s.kml_option == 0
    assert s.end_hour_duration == 0
    assert s.frames_per_file == 0
    assert s.lat_lon_label_interval_option == 1
    assert s.lat_lon_label_interval == 1.0
    assert s.input_files == "tdump"
    assert s.output_suffix == "ps"
    assert s.color_codes == None

    assert s.map_color != None
    assert len(s.marker_cycle) > 0
    assert s.marker_cycle_index == -1
    assert s.source_label != None
    assert s.source_marker != None
    assert s.source_marker_color != None
    assert s.source_marker_size > 0
    assert s.major_hour_marker_size > 0
    assert s.minor_hour_marker_size > 0
    assert s.station_marker != None
    assert s.station_marker_color != None
    assert s.station_marker_size > 0
    assert s.color_cycle == None
    assert s.height_unit == s.HeightUnit.METER


def test_TrajectoryPlotSettings_process_command_line_arguments():
    s = plot.TrajectoryPlotSettings()

    s.process_command_line_arguments(["-a1", "-itrajcalc", "-j../graphics/else",
                                   "-k0", "-l4", "-m1", "-oplot", "-s0", "-v1", "-z10"])

    assert s.gis_output == 1
    assert s.input_files == "trajcalc"
    assert s.map_background == "../graphics/else"
    assert s.color == 0
    assert s.time_label_interval == 4
    assert s.map_projection == 1
    assert s.output_postscript == "plot.ps"
    assert s.label_source == False
    assert s.vertical_coordinate == 1
    assert s.zoom_factor == 0.90

    # test +n
    s.noaa_logo = False
    s.process_command_line_arguments(["+n"])
    assert s.noaa_logo == True

    # test +N
    s.noaa_logo = False
    s.process_command_line_arguments(["+N"])
    assert s.noaa_logo == True

    # test -A
    s.kml_option = 0
    s.process_command_line_arguments(["-A3"])
    assert s.kml_option == 3

    # test -e or -E
    s.end_hour_duration = 0
    s.process_command_line_arguments(["-e12"])
    assert s.end_hour_duration == 12

    s.process_command_line_arguments(["-E15"])
    assert s.end_hour_duration == 15

    # test -f or -F
    s.frames_per_file = 0
    s.process_command_line_arguments(["-f2"])
    assert s.frames_per_file == 2

    s.process_command_line_arguments(["-F5"])
    assert s.frames_per_file == 5

    # test -k or -K
    s.color = 0
    s.color_codes = []

    s.process_command_line_arguments(["-k1"])
    assert s.color == 1

    s.process_command_line_arguments(["-K0"])
    assert s.color == 0

    s.process_command_line_arguments(["-k2"])
    assert s.color == 1

    s.process_command_line_arguments(["-K-1"])
    assert s.color == 0

    s.process_command_line_arguments(["-k3:123"])
    assert s.color_codes == ["1", "2", "3"]
    assert s.color == 2

    # test -L
    s.lat_lon_label_interval_option = 0
    s.lat_lon_label_interval = 0

    s.process_command_line_arguments(["-L1"])
    assert s.lat_lon_label_interval_option == 1

    s.process_command_line_arguments(["-L2:50"])
    assert s.lat_lon_label_interval_option == 2
    assert s.lat_lon_label_interval == 5.0

    # test -g or -G
    s.ring_number = 0
    s.ring_distance = 0.0

    s.process_command_line_arguments(["-g"])
    assert s.ring_number == 4
    assert s.ring_distance == 0.0

    s.process_command_line_arguments(["-G9"])
    assert s.ring_number == 9
    assert s.ring_distance == 0.0

    s.process_command_line_arguments(["-G5:5.5"])
    assert s.ring_number == 5
    assert s.ring_distance == 5.5

    # test -h or -H
    s.center_loc = [0.0, 0.0]

    s.process_command_line_arguments(["-h"])
    assert s.center_loc == [0.0, 0.0]

    s.process_command_line_arguments(["-H12.3:45.6"])
    assert s.center_loc == [45.6, 12.3]

    s.process_command_line_arguments(["-h-112.3:-195.6"])
    assert s.center_loc == [-180.0, -90.0]

    s.process_command_line_arguments(["-H112.3:195.6"])
    assert s.center_loc == [180.0, 90.0]

    # test -p or -P
    s.output_suffix = "ps"

    s.process_command_line_arguments(["-ppdf"])
    assert s.output_suffix == "pdf"

    s.process_command_line_arguments(["-Ppng"])
    assert s.output_suffix == "png"


def test_TrajectoryPlotSettings_parse_color_codes():
    s = plot.TrajectoryPlotSettings()

    codes = s.parse_color_codes("3:abc")

    assert len(codes) == 3
    assert codes[0] == "a"
    assert codes[1] == "b"
    assert codes[2] == "c"

    try:
        codes = s.parse_color_codes("3:ab")
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "FATAL ERROR: Mismatch in option (-kn:m) n=3 m=2"


def test_TrajectoryPlotSettings_parse_lat_lon_label_interval():
    s = plot.TrajectoryPlotSettings()

    mapdel = s.parse_lat_lon_label_interval("2:50")
    assert mapdel == 5.0


def test_TrajectoryPlotSettings_parse_ring_option():
    s = plot.TrajectoryPlotSettings()

    count, distance = s.parse_ring_option("2:50")
    assert count == 2
    assert distance == 50.0


def test_TrajectoryPlotSettings_parse_map_center():
    s = plot.TrajectoryPlotSettings()

    loc = s.parse_map_center("45.0:-120.0")
    assert loc == [-120.0, 45.0]


def test_TrajectoryPlotSettings_parse_zoom_factor():
    s = plot.TrajectoryPlotSettings()

    assert s.parse_zoom_factor("-10") == 1.0
    assert s.parse_zoom_factor("10") == .90
    assert s.parse_zoom_factor("90") == .10
    assert s.parse_zoom_factor("120") == 0.0


def test_TrajectoryPlotSettings_adjust_vertical_coordinate():
    s = plot.TrajectoryPlotSettings()
    pd = plot.TrajectoryPlotData()

    s.vertical_coordinate = s.Vertical.NOT_SET
    pd.vertical_motion = "ISOBA"
    s.adjust_vertical_coordinate(pd)
    assert s.vertical_coordinate == s.Vertical.PRESSURE

    s.vertical_coordinate = s.Vertical.NOT_SET
    pd.vertical_motion = "THETA"
    s.adjust_vertical_coordinate(pd)
    assert s.vertical_coordinate == s.Vertical.THETA

    s.vertical_coordinate = s.Vertical.NOT_SET
    pd.vertical_motion = "SOMETHING"
    s.adjust_vertical_coordinate(pd)
    assert s.vertical_coordinate == s.Vertical.ABOVE_GROUND_LEVEL

    s.vertical_coordinate = s.Vertical.THETA
    pd.vertical_motion = "PRESSURE"
    s.adjust_vertical_coordinate(pd)
    assert s.vertical_coordinate == s.Vertical.ABOVE_GROUND_LEVEL

    s.vertical_coordinate = s.Vertical.THETA
    pd.vertical_motion = "THETA"
    s.adjust_vertical_coordinate(pd)
    assert s.vertical_coordinate == s.Vertical.THETA


def test_TrajectoryPlotSettings_adjust_output_filename():
    s = plot.TrajectoryPlotSettings()

    n, x = s.adjust_output_filename("output.PS", "ps")
    assert n, x == ("output.PS", "PS")

    n, x = s.adjust_output_filename("output.pdf", "ps")
    assert n, x == ("output.pdf", "pdf")

    n, x = s.adjust_output_filename("output.", "ps")
    assert n, x == ("output.ps", "pdf")

    n, x = s.adjust_output_filename("output", "ps")
    assert n, x == ("output.ps", "ps")


def test_TrajectoryPlotSettings_adjust_ring_distance():
    s = plot.TrajectoryPlotSettings()
    s.ring_number = 5
    s.ring_distance = 105.0

    kspan = s.adjust_ring_distance((40.0, 10.0), 1.0)
    assert kspan == 5
    assert s.ring_distance == 100.0


def test_TrajectoryPlotSettings_get_reader():
    s = plot.TrajectoryPlotSettings()
    r = s.get_reader()

    assert isinstance(r, plot.TrajectoryPlotFileReader)
    assert r.settings is s


def test_TrajectoryPlotSettings_next_marker():
    s = plot.TrajectoryPlotSettings()

    for m in s.marker_cycle:
        assert s.next_marker() == m

    assert s.next_marker() == s.marker_cycle[0]


def test_TrajectoryPlotSettings_reset_marker_cycle():
    s = plot.TrajectoryPlotSettings()

    s.next_marker()
    assert s.marker_cycle_index != -1

    s.reset_marker_cycle()
    assert s.marker_cycle_index == -1


def test_TrajectoryDataFileReader___init__():
    d = plot.TrajectoryPlotData()
    r = plot.TrajectoryDataFileReader(d)

    assert r.trajectory_data is d


def test_TrajectoryDataFileReader_read():
    s = plot.TrajectoryPlotSettings()
    d = plot.TrajectoryPlotData()
    r = plot.TrajectoryDataFileReader(d)

    r.adjust_settings("data/tdump", s)
    o = r.read("data/tdump", s)
    assert isinstance(o, plot.TrajectoryPlotData)

    assert d.format_version == 1
    assert d.IDLBL == None

    assert len(d.grids) == 1
    g = d.grids[0]
    assert g.model == "    NGM "
    assert g.datetime == datetime.datetime(95, 10, 16, 0, 0)
    assert g.forecast_hour == 0

    assert len(d.trajectories) == 3
    assert d.trajectory_direction == "FORWARD "
    assert d.vertical_motion == "OMEGA   "

    assert d.uniq_start_levels == [10.0, 500.0, 1000.0]

    t = d.trajectories[0]
    assert t.starting_datetime == datetime.datetime(95, 10, 16, 0, 0)
    assert t.starting_loc == (-90.0, 40.0)
    assert t.starting_level == 10.0
    assert t.starting_level_index == 0
    assert len(t.diagnostic_names) == 1
    assert t.diagnostic_names[0] == "PRESSURE"

    t = d.trajectories[1]
    assert t.starting_datetime == datetime.datetime(95, 10, 16, 0, 0)
    assert t.starting_loc == (-90.0, 40.0)
    assert t.starting_level == 500.0
    assert t.starting_level_index == 1
    assert len(t.diagnostic_names) == 1
    assert t.diagnostic_names[0] == "PRESSURE"

    t = d.trajectories[2]
    assert t.starting_datetime == datetime.datetime(95, 10, 16, 0, 0)
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
    assert t.datetimes[k] == datetime.datetime(95, 10, 16, 12, 0)
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
    assert t.datetimes[k] == datetime.datetime(95, 10, 16, 12, 0)
    assert t.forecast_hours[k] == 0
    assert t.ages[k] == 12.0
    assert t.latitudes[k] == 36.886
    assert t.longitudes[k] == -85.285
    assert t.heights[k] == 718.4
    assert t.vertical_coordinates[k] == 718.4
    assert t.others["PRESSURE"][k] == 905.6


def test_TrajectoryDataFileReader_read_fmt0():
    s = plot.TrajectoryPlotSettings()
    d = plot.TrajectoryPlotData()
    r = plot.TrajectoryDataFileReader(d)

    r.adjust_settings("data/tdump_fmt0", s)
    r.read("data/tdump_fmt0", s)

    assert d.format_version == 0
    assert d.IDLBL == None

    # TODO: modify lines below for trajectory format 0.
    assert len(d.grids) == 1
    g = d.grids[0]
    assert g.model == "    NGM "
    assert g.datetime == datetime.datetime(95, 10, 16, 0, 0)
    assert g.forecast_hour == 0

    assert len(d.trajectories) == 3
    assert d.trajectory_direction == "FORWARD "
    assert d.vertical_motion == "OMEGA   "

    assert d.uniq_start_levels == [10.0, 500.0, 1000.0]

    t = d.trajectories[0]
    assert t.starting_datetime == datetime.datetime(95, 10, 16, 0, 0)
    assert t.starting_loc == (-90.0, 40.0)
    assert t.starting_level == 10.0
    assert t.starting_level_index == 0
    assert len(t.diagnostic_names) == 1
    assert t.diagnostic_names[0] == "PRESSURE"

    t = d.trajectories[1]
    assert t.starting_datetime == datetime.datetime(95, 10, 16, 0, 0)
    assert t.starting_loc == (-90.0, 40.0)
    assert t.starting_level == 500.0
    assert t.starting_level_index == 1
    assert len(t.diagnostic_names) == 1
    assert t.diagnostic_names[0] == "PRESSURE"

    t = d.trajectories[2]
    assert t.starting_datetime == datetime.datetime(95, 10, 16, 0, 0)
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
    assert t.datetimes[k] == datetime.datetime(95, 10, 16, 12, 0)
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
    assert t.datetimes[k] == datetime.datetime(95, 10, 16, 12, 0)
    assert t.forecast_hours[k] == 0
    assert t.ages[k] == 12.0
    assert t.latitudes[k] == 36.886
    assert t.longitudes[k] == -85.285
    assert t.heights[k] == 718.4
    assert t.vertical_coordinates[k] == 718.4
    assert t.others["PRESSURE"][k] == 905.6


def test_TrajectoryDataFileReader_adjust_settings():
    s = plot.TrajectoryPlotSettings()
    d = plot.TrajectoryPlotData()
    r = plot.TrajectoryDataFileReader(d)

    assert s.vertical_coordinate == s.Vertical.NOT_SET

    r.adjust_settings("data/tdump", s)

    assert s.vertical_coordinate == s.Vertical.ABOVE_GROUND_LEVEL


def test_TrajectoryPlotData___init__():
    d = plot.TrajectoryPlotData()

    assert hasattr(d, 'trajectory_direction')
    assert hasattr(d, 'vertical_motion')
    assert d.IDLBL == None
    assert d.grids != None and len(d.grids) == 0
    assert d.trajectories != None and len(d.trajectories) == 0
    assert d.format_version == 1
    assert d.uniq_start_levels != None and len(d.uniq_start_levels) == 0


def test_TrajectoryPlotData_is_forward_calculation():
    d = plot.TrajectoryPlotData()

    d.trajectory_direction = "FORWARD"
    assert d.is_forward_calculation()

    d.trajectory_direction = " FORWARD "
    assert d.is_forward_calculation()

    d.trajectory_direction = "BACKWARD"
    assert d.is_forward_calculation() == False


def test_TrajectoryPlotData_get_reader():
    d = plot.TrajectoryPlotData()
    r = d.get_reader()

    assert isinstance(r, plot.TrajectoryDataFileReader)
    assert r.trajectory_data is d


def test_TrajectoryPlotData_get_unique_start_datetimes():
    d = plot.TrajectoryPlotData()

    list = d.get_unique_start_datetimes()
    assert len(list) == 0

    # add one trajectory

    t = plot.TrajectoryPlotData.Trajectory()
    t.starting_datetime = datetime.datetime(2019, 4, 8, 13, 4)
    d.trajectories.append(t)

    list = d.get_unique_start_datetimes()
    assert len(list) == 1
    assert list[0] == datetime.datetime(2019, 4, 8, 13, 4)

    # add one more with the same date and time.

    t = plot.TrajectoryPlotData.Trajectory()
    t.starting_datetime = datetime.datetime(2019, 4, 8, 13, 4)
    d.trajectories.append(t)

    list = d.get_unique_start_datetimes()
    assert len(list) == 1
    assert list[0] == datetime.datetime(2019, 4, 8, 13, 4)

    # add one more with a different date and time.

    t = plot.TrajectoryPlotData.Trajectory()
    t.starting_datetime = datetime.datetime(2019, 4, 8, 13, 8)
    d.trajectories.append(t)

    list = d.get_unique_start_datetimes()
    assert len(list) == 2


def test_TrajectoryPlotData_get_unique_start_locations():
    d = plot.TrajectoryPlotData()

    list = d.get_unique_start_locations()
    assert len(list) == 0

    # add one trajectory

    t = plot.TrajectoryPlotData.Trajectory()
    t.starting_loc = (-90.0, 40.0)
    d.trajectories.append(t)

    list = d.get_unique_start_locations()
    assert len(list) == 1
    assert list[0] == (-90.0, 40.0)

    # add one more with the same location.

    t = plot.TrajectoryPlotData.Trajectory()
    t.starting_loc = (-90.0, 40.0)
    d.trajectories.append(t)

    list = d.get_unique_start_locations()
    assert len(list) == 1
    assert list[0] == (-90.0, 40.0)

    # add one more with a different location.

    t = plot.TrajectoryPlotData.Trajectory()
    t.starting_loc = (-90.0, 43.0)
    d.trajectories.append(t)

    list = d.get_unique_start_locations()
    assert len(list) == 2


def test_TrajectoryPlotData_get_unique_start_levels():
    d = plot.TrajectoryPlotData()

    list = d.get_unique_start_levels()
    assert len(list) == 0

    # add one trajectory

    t = plot.TrajectoryPlotData.Trajectory()
    t.starting_level = 0.0
    d.trajectories.append(t)

    list = d.get_unique_start_levels()
    assert len(list) == 1
    assert list[0] == 0.0

    # add one more with the same level.

    t = plot.TrajectoryPlotData.Trajectory()
    t.starting_level = 0.0
    d.trajectories.append(t)

    list = d.get_unique_start_levels()
    assert len(list) == 1
    assert list[0] == 0.0

    # add one more with a different level.

    t = plot.TrajectoryPlotData.Trajectory()
    t.starting_level = 500.0
    d.trajectories.append(t)

    list = d.get_unique_start_levels()
    assert len(list) == 2
    assert list[1] == 500.0


def test_TrajectoryPlotData_get_latitude_range(plotData):
    r = plotData.get_latitude_range()

    assert r[0] == 36.886
    assert r[1] == 40.000


def test_TrajectoryPlotData_get_longitude_range(plotData):
    r = plotData.get_longitude_range()

    assert r[0] == -90.000
    assert r[1] == -85.285


def test_TrajectoryPlotData_get_age_range(plotData):
    r = plotData.get_age_range()

    assert r[0] == 0.0
    assert r[1] == 12.0


def test_TrajectoryPlotData_get_datetime_range(plotData):
    r = plotData.get_datetime_range()

    assert r[0] == datetime.datetime(95, 10, 16,  0, 0)
    assert r[1] == datetime.datetime(95, 10, 16, 12, 0)


def test_TrajectoryPlotData_after_reading_file():
    s = plot.TrajectoryPlotSettings()
    d = plot.TrajectoryPlotData()
    s.color = s.Color.ITEMIZED
    s.color_codes = ['2', '3']

    # add four trajectories

    t = plot.TrajectoryPlotData.Trajectory()
    t.starting_level = 10.0
    d.trajectories.append(t)

    t = plot.TrajectoryPlotData.Trajectory()
    t.starting_level = 500.0
    d.trajectories.append(t)

    t = plot.TrajectoryPlotData.Trajectory()
    t.starting_level = 1000.0
    d.trajectories.append(t)

    t = plot.TrajectoryPlotData.Trajectory()
    t.starting_level = 500.0
    d.trajectories.append(t)

    # Run and check

    d.after_reading_file(s)

    assert d.trajectories[0].starting_level_index == 0
    assert d.trajectories[1].starting_level_index == 1
    assert d.trajectories[2].starting_level_index == 2
    assert d.trajectories[3].starting_level_index == 1

    assert d.trajectories[0].color == '2'
    assert d.trajectories[1].color == '3'
    assert d.trajectories[2].color == '1'
    assert d.trajectories[3].color == '1'

    assert d.uniq_start_levels == [10.0, 500.0, 1000.0]

    assert isinstance(s.color_cycle, plot.ColorCycle)


def test_MeteorologicalGrid___init__():
    g = plot.TrajectoryPlotData.MeteorologicalGrid()

    assert hasattr(g, 'model')
    assert hasattr(g, 'datetime')
    assert g.forecast_hour == 0


def test_Trajectory___init__():
    t = plot.TrajectoryPlotData.Trajectory()

    assert hasattr(t, 'starting_datetime')
    assert t.starting_loc == (0, 0)
    assert t.starting_level == 0
    assert t.starting_level_index == -1
    assert t.diagnostic_names == None
    assert t.color == None
    assert t.grids != None and len(t.grids) == 0
    assert t.datetimes != None and len(t.datetimes) == 0
    assert t.forecast_hours != None and len(t.forecast_hours) == 0
    assert t.ages != None and len(t.ages) == 0
    assert t.latitudes != None and len(t.latitudes) == 0
    assert t.longitudes != None and len(t.longitudes) == 0
    assert t.heights != None and len(t.heights) == 0
    assert t.vertical_coordinates != None and len(t.vertical_coordinates) == 0
    assert t.others != None and len(t.others) == 0


def test_Trajectory_collect_latitude(plotData):
    lats = plotData.trajectories[0].collect_latitude()
    assert len(lats) == 13
    assert lats[0] == 40.0
    assert lats[12] == 38.586


def test_Trajectory_collect_longitude(plotData):
    lons = plotData.trajectories[0].collect_longitude()
    assert len(lons) == 13
    assert lons[0] == -90.0
    assert lons[12] == -88.772


def test_Trajectory_collect_age(plotData):
    ages = plotData.trajectories[0].collect_age()
    assert len(ages) == 13
    assert ages[0] == 0.0
    assert ages[12] == 12.0


def test_Trajectory_collect_datetime(plotData):
    datetimes = plotData.trajectories[0].collect_datetime()
    assert len(datetimes) == 13
    assert datetimes[0] == datetime.datetime(95, 10, 16, 0, 0)
    assert datetimes[12] == datetime.datetime(95, 10, 16, 12, 0)


def test_Trajectory_collect_pressure(plotData):
    p = plotData.trajectories[0].collect_pressure()
    assert len(p) == 13
    assert p[0] == 991.7
    assert p[12] == 1001.1


def test_Trajectory_collect_terrain_profile(plotData):
    t = plotData.trajectories[0]
    p = t.collect_terrain_profile()

    assert p == None

    t.others["TERR_MSL"] = [10.0, 500.0]
    p = t.collect_terrain_profile()

    assert p[0] == 10.0
    assert p[1] == 500.0


def test_Trajectory_collect_vertical_coordinate(plotData):
    t = plotData.trajectories[0]

    p = t.collect_vertical_coordinate()
    assert len(p) == 13
    assert p[0] == 10.0
    assert p[12] == 0.0


def test_Trajectory_has_terrain_profile(plotData):
    t = plotData.trajectories[0]

    assert t.has_terrain_profile() == False

    t.others["TERR_MSL"] = [10.0, 500.0]

    assert t.has_terrain_profile() == True


def test_Trajectory_make_vertical_coordinates():
    t = plot.TrajectoryPlotData.Trajectory()

    t.diagnostic_names = ["PRESSURE"]
    t.others["PRESSURE"] = [1001.0, 1002.0]
    t.make_vertical_coordinates(plot.TrajectoryPlotSettings.Vertical.PRESSURE)
    p = t.collect_vertical_coordinate()
    assert len(p) == 2
    assert p[0] == 1001.0
    assert p[1] == 1002.0

    # without terrain
    t.heights = [10.0, 20.0]
    t.make_vertical_coordinates(plot.TrajectoryPlotSettings.Vertical.ABOVE_GROUND_LEVEL)
    h = t.collect_vertical_coordinate()
    assert len(h) == 2
    assert h[0] == 10.0
    assert h[1] == 20.0

    # without terrain and in feet
    t.heights = [10.0, 20.0]
    t.make_vertical_coordinates(plot.TrajectoryPlotSettings.Vertical.ABOVE_GROUND_LEVEL,
                                plot.TrajectoryPlotSettings.HeightUnit.FEET)
    h = t.collect_vertical_coordinate()
    assert len(h) == 2
    assert h[0] == pytest.approx(10.0 * 3.28084)
    assert h[1] == pytest.approx(20.0 * 3.28084)
    
    # with terrain
    t.diagnostic_names.append("TERR_MSL")
    t.others["TERR_MSL"] = [500.0, 550.0]
    t.make_vertical_coordinates(plot.TrajectoryPlotSettings.Vertical.ABOVE_GROUND_LEVEL)
    h = t.collect_vertical_coordinate()
    assert len(h) == 2
    assert h[0] == 510.0
    assert h[1] == 570.0
    
    # with terrain and in feet
    t.diagnostic_names.append("TERR_MSL")
    t.others["TERR_MSL"] = [500.0, 550.0]
    t.make_vertical_coordinates(plot.TrajectoryPlotSettings.Vertical.ABOVE_GROUND_LEVEL,
                                plot.TrajectoryPlotSettings.HeightUnit.FEET)
    h = t.collect_vertical_coordinate()
    assert len(h) == 2
    assert h[0] == pytest.approx(510.0 * 3.28084)
    assert h[1] == pytest.approx(570.0 * 3.28084)
    
    # theta
    t.diagnostic_names.append("THETA")
    t.others["THETA"] = [1500.0, 1550.0]
    t.make_vertical_coordinates(plot.TrajectoryPlotSettings.Vertical.THETA)
    h = t.collect_vertical_coordinate()
    assert len(h) == 2
    assert h[0] == 1500.0
    assert h[1] == 1550.0

    # something else
    t.diagnostic_names.append("SUN_FLUX")
    t.others["SUN_FLUX"] = [50.0, 55.0]
    t.make_vertical_coordinates(plot.TrajectoryPlotSettings.Vertical.METEO)
    h = t.collect_vertical_coordinate()
    assert len(h) == 2
    assert h[0] == 50.0
    assert h[1] == 55.0

    # not set
    t.vertical_coordinates = None
    t.make_vertical_coordinates(plot.TrajectoryPlotSettings.Vertical.NOT_SET)
    h = t.collect_vertical_coordinate()
    assert h == None

    # none
    t.vertical_coordinates = None
    t.make_vertical_coordinates(plot.TrajectoryPlotSettings.Vertical.NONE)
    h = t.collect_vertical_coordinate()
    assert h == None

    return


def test_Trajectory_repair_starting_location():
    return


def test_Trajectory_repair_starting_level():
    return


def test_TrajectoryPlotHelper_make_plot_title(plotData):
    labels_cfg = graph.LabelsConfig()
    title = plot.TrajectoryPlotHelper.make_plot_title(plotData, labels_cfg)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "Forward trajectories starting at 0000 UTC 16 Oct 95\n" + \
           "NGM Meteorological Data"

    # Change the model name

    plotData.grids[0].model = " TEST "
    title = plot.TrajectoryPlotHelper.make_plot_title(plotData, labels_cfg)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "Forward trajectories starting at 0000 UTC 16 Oct 95\n" + \
           "TEST Meteorological Data"

    # Add a grid

    g = plot.TrajectoryPlotData.MeteorologicalGrid()
    g.model = "TEST"
    plotData.grids.append(g)
    title = plot.TrajectoryPlotHelper.make_plot_title(plotData, labels_cfg)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "Forward trajectories starting at 0000 UTC 16 Oct 95\n" + \
           "Various Meteorological Data"

    # Change the starting time of a trajectory

    t = plotData.trajectories[2]
    t.starting_datetime = datetime.datetime(93, 10, 16, 1, 0)
    title = plot.TrajectoryPlotHelper.make_plot_title(plotData, labels_cfg)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "Forward trajectories starting at various times\n" + \
           "Various Meteorological Data"

    # Change direction

    plotData.trajectory_direction = "BACKWARD"
    title = plot.TrajectoryPlotHelper.make_plot_title(plotData, labels_cfg)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "Backward trajectories ending at various times\n" + \
           "Various Meteorological Data"

    # With one trajectory

    plotData.trajectories.pop()
    plotData.trajectories.pop()
    title = plot.TrajectoryPlotHelper.make_plot_title(plotData, labels_cfg)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "Backward trajectory ending at 0000 UTC 16 Oct 95\n" + \
           "Various Meteorological Data"

    # Change direction

    plotData.trajectory_direction = "FORWARD"
    title = plot.TrajectoryPlotHelper.make_plot_title(plotData, labels_cfg)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "Forward trajectory starting at 0000 UTC 16 Oct 95\n" + \
           "Various Meteorological Data"


def test_TrajectoryPlotHelper_make_ylabel():
    plotData = plot.TrajectoryPlotData()
    t = plot.TrajectoryPlotData.Trajectory()
    t.starting_loc = (30.0, 20.0)
    plotData.trajectories.append(t)

    label = plot.TrajectoryPlotHelper.make_ylabel(plotData, "*", 6)
    assert label == "Source * at  20.00 N   30.00 E"

    # no marker when the time label interval is negative
    label = plot.TrajectoryPlotHelper.make_ylabel(plotData, "*", -6)
    assert label == "Source at  20.00 N   30.00 E"

    # negative longitude

    t.starting_loc = (-30.0, 20.0)

    label = plot.TrajectoryPlotHelper.make_ylabel(plotData, "*", 6)
    assert label == "Source * at  20.00 N   30.00 W"

    # negative latitude

    t.starting_loc = (-30.0, -20.0)

    label = plot.TrajectoryPlotHelper.make_ylabel(plotData, "*", 6)
    assert label == "Source * at  20.00 S   30.00 W"

    # add a trajectory with a different starting location

    t = plot.TrajectoryPlotData.Trajectory()
    t.starting_loc = (30.0, 25.0)
    plotData.trajectories.append(t)

    label = plot.TrajectoryPlotHelper.make_ylabel(plotData, "*", 6)
    assert label == "Source * at multiple locations"


def test_TrajectoryPlotHelper_has_terrain_profile(plotData):
    assert plot.TrajectoryPlotHelper.has_terrain_profile([plotData]) == False

    plotData.trajectories[0].others["TERR_MSL"] = []
    assert plot.TrajectoryPlotHelper.has_terrain_profile([plotData]) == True

    plotData.trajectories[0].others["TERR_MSL"].append(0.0)
    assert plot.TrajectoryPlotHelper.has_terrain_profile([plotData]) == True


def test_TrajectoryPlotHelper_make_vertical_label(plotData):
    height_unit = plot.TrajectoryPlotSettings.HeightUnit.METER
    assert "hPa" == plot.TrajectoryPlotHelper.make_vertical_label(0, plotData, height_unit, False)
    assert "Meters AGL" == plot.TrajectoryPlotHelper.make_vertical_label(1, plotData, height_unit, False)
    assert "Meters MSL" == plot.TrajectoryPlotHelper.make_vertical_label(1, plotData, height_unit, True)
    height_unit = plot.TrajectoryPlotSettings.HeightUnit.FEET
    assert "Feet AGL" == plot.TrajectoryPlotHelper.make_vertical_label(1, plotData, height_unit, False)
    assert "Feet MSL" == plot.TrajectoryPlotHelper.make_vertical_label(1, plotData, height_unit, True)
    assert "Theta" == plot.TrajectoryPlotHelper.make_vertical_label(2, plotData, height_unit)
    assert "PRESSURE" == plot.TrajectoryPlotHelper.make_vertical_label(3, plotData, height_unit)
    assert "" == plot.TrajectoryPlotHelper.make_vertical_label(4, plotData, height_unit)


def test_TrapjectoyPlot___init__():
    p = plot.TrajectoryPlot()

    assert hasattr(p, "settings")
    assert hasattr(p, "data_list")
    assert hasattr(p, "projection")
    assert hasattr(p, "crs")
    assert hasattr(p, "data_crs")
    assert hasattr(p, "background_maps")
    assert hasattr(p, "traj_axes")
    assert hasattr(p, "height_axes")
    assert hasattr(p, "height_axes_outer")
    assert isinstance(p.labels, graph.LabelsConfig)


def test_TrajectoryPlot_merge_plot_settings():
    p = plot.TrajectoryPlot()

    p.merge_plot_settings("data/default_tplot", ["-a1"])

    assert p.settings.gis_output == 1


def test_TrajectoryPlot_read_data_files():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump"])

    p.read_data_files()

    assert len(p.data_list) == 1
    assert len(p.data_list[0].trajectories) == 3


def test_TrajectoryPlot_make_labels_filename():
    p = plot.TrajectoryPlot()
    s = p.settings

    s.output_suffix = "ps"
    assert p.make_labels_filename() == "LABELS.CFG"

    s.output_suffix = "pdf"
    assert p.make_labels_filename() == "LABELS.pdf"


def test_TrajectoryPlot_read_custom_labels_if_exists():
    p = plot.TrajectoryPlot()
    assert p.labels.get("TITLE") == "NOAA HYSPLIT MODEL"

    p.read_custom_labels_if_exists("data/nonexistent")
    assert p.labels.get("TITLE") == "NOAA HYSPLIT MODEL"

    p.read_custom_labels_if_exists("data/LABELS.CFG")
    assert p.labels.get("TITLE") == "Sagebrush Exp #5"


def test_TrajectoryPlot_get_gridline_spacing():
    p = plot.TrajectoryPlot()
    s = p.settings

    s.lat_lon_label_interval_option = plot.TrajectoryPlotSettings.LatLonLabel.NONE
    assert p.get_gridline_spacing([-130.0, -110.0, 45.0, 55.0]) == 0.0

    s.lat_lon_label_interval_option = plot.TrajectoryPlotSettings.LatLonLabel.SET
    s.lat_lon_label_interval = 3.14
    assert p.get_gridline_spacing([-130.0, -110.0, 45.0, 55.0]) == 3.14

    s.lat_lon_label_interval_option = plot.TrajectoryPlotSettings.LatLonLabel.AUTO
    assert p.get_gridline_spacing([-130.0, -110.0, 45.0, 55.0]) == 5.0


def test_TrajectoryPlot_calc_gridline_spacing():
    p = plot.TrajectoryPlot()
    assert p.calc_gridline_spacing([-130.0, -110.0, 45.0, 55.0]) == 5.0
    assert p.calc_gridline_spacing([-120.0, -110.0, 35.0, 55.0]) == 5.0
    # across the dateline
    assert p.calc_gridline_spacing([+350.0, -10.0, 35.0, 55.0]) == 5.0
    # test min.
    assert p.calc_gridline_spacing([0.0, 0.1, 0.0, 0.1]) == 0.2


def test_TrajectoryPlot__fix_map_color():
    p = plot.TrajectoryPlot()
    s = p.settings

    s.color = s.Color.BLACK_AND_WHITE
    assert p._fix_map_color('#6699cc') == 'k' # black

    s.color = s.Color.COLOR
    assert p._fix_map_color('#6699cc') == '#6699cc'

    s.color = s.Color.ITEMIZED
    assert p._fix_map_color('#6699cc') == '#6699cc'


def test_TrajectoryPlot__initialize_map_projection():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump"])
    p.read_data_files()

    p._initialize_map_projection()

    assert isinstance(p.projection, graph.MapProjection)
    assert p.crs is not None


def test_TrajectoryPlot_read_background_map():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-jdata/arlmap_truncated"])

    crs = p.read_background_map()

    assert p.background_maps is not None
    assert len(p.background_maps) > 0
    assert isinstance(p.background_maps[0], graph.DrawableBackgroundMap)
    assert p.background_maps[0].map.crs == plot.TrajectoryPlot._WGS84


def test_TrajectoryPlot__fix_arlmap_filename():
    assert plot.TrajectoryPlot._fix_arlmap_filename("data/arlmap_truncated") == "data/arlmap_truncated"
    assert plot.TrajectoryPlot._fix_arlmap_filename("data/nonexistent") == None


def test_TrajectoryPlot__determine_map_limits(plotData):
    p = plot.TrajectoryPlot()

    mb = p._determine_map_limits(plotData, 2)

    assert mb.grid_corner== [0.0, -90.0]
    assert mb.grid_delta == 1.0
    assert mb.sz == [360, 181]
    assert mb.plume_sz == [5.0, 5.0]
    assert mb.plume_loc == [270, 126]

    nil_plot_data = plot.TrajectoryPlotData()

    try:
        mb2 = p._determine_map_limits(nil_plot_data, 2)
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "no trajectories to plot"


def test_TrajectoryPlot__determine_vertical_limit(plotData):
    p = plot.TrajectoryPlot()

    # ensure vertical coordinates are pressures
    p.settings.vertical_coordinate = plot.TrajectoryPlotSettings.Vertical.PRESSURE
    plotData.after_reading_file(p.settings)
    low, high = p._determine_vertical_limit(plotData, plot.TrajectoryPlotSettings.Vertical.PRESSURE)
    assert low == 1001.1
    assert high == 879.8

    # ensure vertical coordinates are heights
    p.settings.vertical_coordinate = plot.TrajectoryPlotSettings.Vertical.ABOVE_GROUND_LEVEL
    plotData.after_reading_file(p.settings)
    low, high = p._determine_vertical_limit(plotData, plot.TrajectoryPlotSettings.Vertical.ABOVE_GROUND_LEVEL)
    assert low == 0.0
    assert high == 1000.0

    for t in plotData.trajectories:
        t.vertical_coordinates = []
    low, high = p._determine_vertical_limit(plotData, plot.TrajectoryPlotSettings.Vertical.ABOVE_GROUND_LEVEL)
    assert low is None
    assert high is None
    

def test_TrajectoryPlot_layout():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump"])
    p.read_data_files()

    p.layout()

    assert p.fig is not None
    assert p.traj_axes is not None
    assert p.height_axes is not None
    assert p.height_axes_outer is not None
    assert p.text_axes is not None

    cleanup_plot(p)


def test_TrajectoryPlot__connect_event_handlers():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump"])
    p.read_data_files()
    p.layout()

    try:
        p._connect_event_handlers({"resize_event" : blank_event_handler})
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_TrajectoryPlot__project_extent():
    data_crs = cartopy.crs.PlateCarree()
    data_ext = [-120.0, -80.0, 35.0, 55.0] # x1, x2, y1, y2
    crs = cartopy.crs.LambertConformal()
    axes = plt.subplot(111, projection=crs)

    ext = plot.TrajectoryPlot._project_extent(data_ext, data_crs, axes)

    assert ext[0] == pytest.approx(-2159075.665180272)
    assert ext[1] == pytest.approx( 1448741.4180984693)
    assert ext[2] == pytest.approx( -432644.9997258249)
    assert ext[3] == pytest.approx( 2002857.3004982674)

    plt.close(axes.get_figure())


def test_TrajectoryPlot__collect_tick_values():
    t = plot.TrajectoryPlot._collect_tick_values(-1800, 1800, 100, 0.1, (-120, -80))
    assert t == pytest.approx((-130, -120, -110, -100, -90, -80, -70))


def test_TrajectoryPlot_update_gridlines():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.read_background_map()
    p.layout()

    try:
        p.update_gridlines()
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_TrajectoryPlot__draw_concentric_circles():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated", "-g4:100"])
    p.read_data_files()
    p.read_background_map()
    p.layout()

    try:
        p._draw_concentric_circles(p.traj_axes)
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_TrajectoryPlot_draw_height_profile():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.read_background_map()
    p.layout()

    # See if no exception is thrown.
    try:
        p.draw_height_profile(False)
        p.draw_height_profile(True)
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_TrajectoryPlot_make_stationplot_filename():
    p = plot.TrajectoryPlot()
    s = p.settings

    s.output_suffix = "ps"
    assert p.make_stationplot_filename() == "STATIONPLOT.CFG"

    s.output_suffix = "pdf"
    assert p.make_stationplot_filename() == "STATIONPLOT.pdf"


def test_TrajectoryPlot__draw_stations_if_exists():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.read_background_map()
    p.layout()

    # See if no exception is thrown.
    try:
        p._draw_stations_if_exists(p.traj_axes, "data/STATIONPLOT.CFG")
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_TrajectoryPlot_draw_trajectory_plot():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.read_background_map()
    p.layout()

    # See if no exception is thrown.
    try:
        p.draw_trajectory_plot()
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_TrajectoryPlot_draw_bottom_plot():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.read_background_map()
    p.layout()

    # See if no exception is thrown.
    try:
        p.draw_bottom_plot()
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_TrajectoryPlot_draw_bottom_text():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.read_background_map()
    p.layout()

    # See if no exception is thrown.
    try:
        p.draw_bottom_text()
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))
    

def test_TrajectoryPlot_make_maptext_filename():
    p = plot.TrajectoryPlot()
    s = p.settings

    s.output_suffix = "ps"
    assert p.make_maptext_filename() == "MAPTEXT.CFG"

    s.output_suffix = "pdf"
    assert p.make_maptext_filename() == "MAPTEXT.pdf"


def test_TrajectoryPlot__draw_maptext_if_exists():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.read_background_map()
    p.layout()

    # See if no exception is thrown.
    try:
        p._draw_maptext_if_exists(p.text_axes, "data/MAPTEXT.CFG")
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_TrajectoryPlot__draw_alt_text_boxes():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.read_background_map()
    p.layout()

    # See if no exception is thrown.
    try:
        p._draw_alt_text_boxes(p.text_axes, ["line 1", "line 2"])
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))
    

def test_TrajectoryPlot__turn_off_spines():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.read_background_map()
    p.layout()

    # See if no exception is thrown.
    try:
        p._turn_off_spines(p.text_axes)
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_TrajectoryPlot__turn_off_ticks():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.read_background_map()
    p.layout()

    # See if no exception is thrown.
    try:
        p._turn_off_ticks(p.text_axes)
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_TrajectoryPlot_draw():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.read_background_map()
    p.layout()

    # See if no exception is thrown.
    try:
        p.draw(block=False)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_ColorCycle___init__():
    cc = plot.ColorCycle()
    assert cc.max_colors == 7
    assert cc.index == -1

    cc = plot.ColorCycle(8)
    assert cc.max_colors == 7

    cc = plot.ColorCycle(0)
    assert cc.max_colors == 3


def test_ColorCycle_next_color():
    cc = plot.ColorCycle()
    for c in cc._colors:
        assert cc.next_color(0, 0) == c
    assert cc.next_color(0, 0) == "r"


def test_ColorCycle_reset():
    cc = plot.ColorCycle()
    assert cc.next_color(0, 0) == "r"
    cc.reset()
    assert cc.index == -1
    assert cc.next_color(0, 0) == "r"


def test_ItemizedColorCycle___init__():
    try:
        cc = plot.ItemizedColorCycle()
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(str(ex)))


def test_ItemizedColorCycle_next_color():
    cc = plot.ItemizedColorCycle()
    assert cc.next_color(None, "0") == "#3399cc"
    assert cc.next_color(None, "1") == "r"
    assert cc.next_color(None, "2") == "b"
    assert cc.next_color(None, "7") == "#3399cc"
    assert cc.next_color(None, "8") == "r"


def test_MonoColorCycle___init__():
    try:
        cc = plot.MonoColorCycle()
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(str(ex)))


def test_MonoColorCycle_next_color():
    cc = plot.MonoColorCycle()
    assert cc.next_color(None, None) == "k"
    assert cc.next_color(None, None) == "k"


def test_HeightColorCycle___init__():
    try:
        cc = plot.HeightColorCycle()
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(str(ex)))


def test_HeightColorCycle_next_color():
    cc = plot.HeightColorCycle()
    assert cc.next_color(0, None) == "r"
    assert cc.next_color(6, None) == "#3399cc"
    assert cc.next_color(7, None) == "r"


def test_ColorCycleFactory_create_instance():
    s = plot.TrajectoryPlotSettings()

    s.color = s.Color.COLOR
    cc = plot.ColorCycleFactory.create_instance(s, 1)
    assert isinstance(cc, plot.ColorCycle)
    assert cc.max_colors == 3

    s.color = s.Color.COLOR
    cc = plot.ColorCycleFactory.create_instance(s, 2)
    assert isinstance(cc, plot.HeightColorCycle)
    assert cc.max_colors == 7

    s.color = s.Color.ITEMIZED
    cc = plot.ColorCycleFactory.create_instance(s, 2)
    assert isinstance(cc, plot.ItemizedColorCycle)

    s.color = s.Color.BLACK_AND_WHITE
    cc = plot.ColorCycleFactory.create_instance(s, 2)
    assert isinstance(cc, plot.MonoColorCycle)


def test_IntervalSymbolDrawer___init__():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()

    d = plot.IntervalSymbolDrawer(axes, s, 12)
    assert d.axes == axes
    assert d.settings == s
    assert d.interval == 12

    plt.close(axes.get_figure())


def test_IdleIntervalSymbolDrawer___init__():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()

    d = plot.IdleIntervalSymbolDrawer(axes, s, 12)
    assert d.axes == axes
    assert d.settings == s
    assert d.interval == 12

    plt.close(axes.get_figure())


def test_IdleIntervalSymbolDrawer_draw():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()

    d = plot.IdleIntervalSymbolDrawer(axes, s, 12)

    try:
        d.draw(None, None, None)
    except Exception as ex:
        pytest.fail("unexpected exception {0}".format(str(ex)))

    plt.close(axes.get_figure())


def test_TimeIntervalSymbolDrawer___init__():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()

    d = plot.TimeIntervalSymbolDrawer(axes, s, 12)
    assert d.axes == axes
    assert d.settings == s
    assert d.interval == 12

    plt.close(axes.get_figure())


def test_TimeIntervalSymbolDrawer_draw(plotData):
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    d = plot.TimeIntervalSymbolDrawer(axes, s, 12)

    t = plotData.trajectories[0]

    try:
        d.draw(t, t.collect_datetime(), t.collect_pressure())
    except Exception as ex:
        pytest.fail("unexpected exception {0}".format(str(ex)))

    plt.close(axes.get_figure())


def test_TimeIntervalSymbolDrawer__filter_datadraw(plotData):
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    d = plot.TimeIntervalSymbolDrawer(axes, s, 12)

    x24, y24, x12, y12 = d._filter_data(
        plotData.trajectories[0].collect_datetime(),
        plotData.trajectories[0].collect_longitude(),
        plotData.trajectories[0].collect_latitude(),
        12, False)

    assert len(x24) == 1
    assert x24[0] == -90.0

    assert len(y24) == 1
    assert y24[0] == 40.0

    assert len(x12) == 1
    assert x12[0] == -88.772

    assert len(y12) == 1
    assert y12[0] == 38.586


def test_AgeIntervalSymbolDrawer___init__():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()

    d = plot.AgeIntervalSymbolDrawer(axes, s, 12)
    assert d.axes == axes
    assert d.settings == s
    assert d.interval == 12

    plt.close(axes.get_figure())


def test_AgeIntervalSymbolDrawer_draw(plotData):
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    d = plot.AgeIntervalSymbolDrawer(axes, s, 12)

    t = plotData.trajectories[0]

    try:
        d.draw(t, t.collect_datetime(), t.collect_pressure())
    except Exception as ex:
        pytest.fail("unexpected exception {0}".format(str(ex)))

    plt.close(axes.get_figure())


def test_AgeIntervalSymbolDrawer__filter_datadraw(plotData):
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    d = plot.AgeIntervalSymbolDrawer(axes, s, 12)

    x24, y24, x12, y12 = d._filter_data(
        plotData.trajectories[0].collect_age(),
        plotData.trajectories[0].collect_longitude(),
        plotData.trajectories[0].collect_latitude(),
        12, False)

    assert len(x24) == 1
    assert x24[0] == -90.0

    assert len(y24) == 1
    assert y24[0] == 40.0

    assert len(x12) == 1
    assert x12[0] == -88.772

    assert len(y12) == 1
    assert y12[0] == 38.586


def test_IntervalSymbolDrawerFactory_create_instance():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()

    s.time_label_interval = 12
    d = plot.IntervalSymbolDrawerFactory.create_instance(axes, s)
    assert isinstance(d, plot.TimeIntervalSymbolDrawer)

    s.time_label_interval = -12
    d = plot.IntervalSymbolDrawerFactory.create_instance(axes, s)
    assert isinstance(d, plot.AgeIntervalSymbolDrawer)

    s.time_label_interval = 0
    d = plot.IntervalSymbolDrawerFactory.create_instance(axes, s)
    assert isinstance(d, plot.IdleIntervalSymbolDrawer)

    plt.close(axes.get_figure())


def test_AbstractVerticalPosition___init__():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = plot.AbstractVerticalProjection(axes, s, 6)
    assert o.axes == axes
    assert o.settings == s
    assert o.time_interval == 6
    plt.close(axes.get_figure())
    

def test_AbstractVerticalPosition_calc_xrange(plotData):
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = plot.AbstractVerticalProjection(axes, s, 6)
    assert o.calc_xrange(plotData) == None
    plt.close(axes.get_figure())
        

def test_AbstractVerticalPosition_create_xlabel_formatter():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = plot.AbstractVerticalProjection(axes, s, 6)
    assert o.create_xlabel_formatter() == None
    plt.close(axes.get_figure())
  

def test_AbstractVerticalPosition_select_xvalues(plotData):
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = plot.AbstractVerticalProjection(axes, s, 6)
    assert o.select_xvalues(plotData.trajectories[0]) == None
    plt.close(axes.get_figure())

    
def test_AbstractVerticalPosition_create_interval_symbol_drawer():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = plot.AbstractVerticalProjection(axes, s, 6)
    assert o.create_interval_symbol_drawer() is not None
    plt.close(axes.get_figure())
  

def test_AbstractVerticalPosition_create_instance():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    
    s.time_label_interval = 6
    o = plot.AbstractVerticalProjection.create_instance(axes, s)
    assert isinstance(o, plot.TimeVerticalProjection)
    
    s.time_label_interval = -6
    o = plot.AbstractVerticalProjection.create_instance(axes, s)
    assert isinstance(o, plot.AgeVerticalProjection)
    
    s.time_label_interval = 0
    o = plot.AbstractVerticalProjection.create_instance(axes, s)
    assert isinstance(o, plot.TimeVerticalProjection)


def test_TimeVerticalProjection___init__():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = plot.TimeVerticalProjection(axes, s, 6)
    assert o.axes == axes
    assert o.settings == s
    assert o.time_interval == 6
    plt.close(axes.get_figure())
    

def test_TimeVerticalProjection_calc_xrange(plotData):
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = plot.TimeVerticalProjection(axes, s, 6)
    r = o.calc_xrange(plotData)
    assert r[0] == datetime.datetime(95, 10, 16,  0, 0)
    assert r[1] == datetime.datetime(95, 10, 16, 12, 0)
    plt.close(axes.get_figure())
        

def test_TimeVerticalProjection_create_xlabel_formatter():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = plot.TimeVerticalProjection(axes, s, 6)
    f = o.create_xlabel_formatter()
    assert isinstance(f, plt.FuncFormatter)
    plt.close(axes.get_figure())


def test_TimeVerticalProjection__format_datetime():
    dt = matplotlib.dates.date2num(datetime.datetime(2019, 4, 18, 9, 0, 0))
    assert plot.TimeVerticalProjection._format_datetime(dt, None) == ""
    assert plot.TimeVerticalProjection._format_datetime(dt, 100) == "9"

    dt = matplotlib.dates.date2num(datetime.datetime(2019, 4, 18, 9, 30, 0))
    assert plot.TimeVerticalProjection._format_datetime(dt, 100) == ""

    dt = matplotlib.dates.date2num(datetime.datetime(2019, 4, 18, 0, 0, 0))
    assert plot.TimeVerticalProjection._format_datetime(dt, 100) == "0\n4/18"


def test_TimeVerticalProjection_select_xvalues(plotData):
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = plot.TimeVerticalProjection(axes, s, 6)
    x = o.select_xvalues(plotData.trajectories[0])
    assert len(x) > 0
    assert x[0] == datetime.datetime(95, 10, 16, 0, 0)
    plt.close(axes.get_figure())


def test_AgeVerticalProjection___init__():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = plot.AgeVerticalProjection(axes, s, 6)
    assert o.axes == axes
    assert o.settings == s
    assert o.time_interval == 6
    plt.close(axes.get_figure())
    

def test_AgeVerticalProjection_calc_xrange(plotData):
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = plot.AgeVerticalProjection(axes, s, 6)
    assert o.calc_xrange(plotData) == (0.0, 12.0)
    plt.close(axes.get_figure())


def test_AgeVerticalProjection_create_xlabel_formatter():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = plot.AgeVerticalProjection(axes, s, 6)
    f = o.create_xlabel_formatter()
    assert isinstance(f, plt.FuncFormatter)
    plt.close(axes.get_figure())


def test_AgeVerticalProjection__format_age():
    assert plot.AgeVerticalProjection._format_age(0.0, 100) == "0.0"
    assert plot.AgeVerticalProjection._format_age(12.0, 100) == "12.0"
    assert plot.AgeVerticalProjection._format_age(10.5, 100) == "10.5"


def test_AgeVerticalProjection_select_xvalues(plotData):
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = plot.AgeVerticalProjection(axes, s, 6)
    x = o.select_xvalues(plotData.trajectories[0])
    assert len(x) > 0
    assert x[0] == 0
    plt.close(axes.get_figure())
