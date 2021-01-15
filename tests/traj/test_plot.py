# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_plot.py
#
# Performs unit tests on functions and class methods declared in traj/plot.py.
# ---------------------------------------------------------------------------

import cartopy.crs
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates
import os
import pytest
import pytz
import xml.etree.ElementTree as ElementTree

# Register a converter to avoid a warning message.
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

from hysplitdata.const import HeightUnit, VerticalCoordinate
from hysplitdata.traj import model
from hysplitplot import clist, const, labels, mapfile, mapproj, multipage, streetmap
from hysplitplot.traj import plot


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


def blank_event_handler(event):
    # do nothing
    return


def cleanup_plot(p):
    if p.fig is not None:
        plt.close(p.fig)


# concrete classes to test abstract classes

class AbstractFrameDataIteratorTest(plot.AbstractFrameDataIterator):
    
    def __init__(self, tdump_list):
        super(AbstractFrameDataIteratorTest, self).__init__(tdump_list)
        
    def __iter__(self):
        pass


class AbstractVerticalProjectionTest(plot.AbstractVerticalProjection):
    
    def calc_xrange(self, plot_data, time_zone=None):
        pass
    
    def create_xlabel_formatter(self):
        pass
    
    def select_xvalues(self, trajectory, time_zone=None):
        pass
    

def test_TrajectoryPlotSettings___init__():
    s = plot.TrajectoryPlotSettings()

    assert s.view == 1
    assert s.output_filename == "trajplot.ps"
    assert s.output_basename == "trajplot"
    assert s.time_label_interval == 6
    assert s.vertical_coordinate == VerticalCoordinate.NOT_SET
    assert s.label_source == True
    assert s.map_center == 0
    assert s.color == 1
    assert s.color_codes == None
    
    assert s.end_hour_duration == 0
    assert s.input_files == "tdump"
    assert s.ring == False
    assert s.ring_number == -1
    assert s.ring_distance == 0.0
    assert s.center_loc == [0.0, 0.0]
    assert s.gis_output == const.GISOutput.NONE
    assert s.kml_option == const.KMLOption.NONE

    assert len(s.marker_cycle) > 0
    assert s.marker_cycle_index == -1
    assert s.source_label != None
    assert s.source_marker != None
    assert s.source_marker_color != None
    assert s.source_marker_size > 0
    assert s.major_hour_marker_size > 0
    assert s.minor_hour_marker_size > 0
    assert s.terrain_line_color != None
    assert s.terrain_marker != None
    assert s.station_marker != None
    assert s.station_marker_color != None
    assert s.station_marker_size > 0
    assert s.color_cycle == None


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
    assert s.output_filename == "plot.ps"
    assert s.label_source == False
    assert s.vertical_coordinate == 1
    assert s.zoom_factor == 0.90
    
    # The -o option implies non-interactive mode
    assert s.interactive_mode == False

    # test -m and -M
    s.map_projection = 0

    s.process_command_line_arguments(["-m1"])
    assert s.map_projection == 1
    
    s.process_command_line_arguments(["-M2"])
    assert s.map_projection == 2
    
    # test -a
    s.gis_output = 0
    s.process_command_line_arguments(["-a2"])
    assert s.gis_output == 2
    
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

    # test -i or -I
    s.process_command_line_arguments(["-iINPUT"])
    assert s.input_files == "INPUT"
    
    s.process_command_line_arguments(["-ITEST_INPUT"])
    assert s.input_files == "TEST_INPUT"

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

    # test -l
    s.time_label_interval = 10
    s.process_command_line_arguments(["-l15"])
    assert s.time_label_interval == 15

    # test -L
    s.lat_lon_label_interval_option = 0
    s.lat_lon_label_interval = 0

    s.process_command_line_arguments(["-L1"])
    assert s.lat_lon_label_interval_option == 1

    s.process_command_line_arguments(["-L2:50"])
    assert s.lat_lon_label_interval_option == 2
    assert s.lat_lon_label_interval == 5.0
    
    # test -s or -S
    s.label_source = False
    s.process_command_line_arguments(["-s1"])
    assert s.label_source == True

    s.process_command_line_arguments(["-S0"])
    assert s.label_source == False
    
    # test -v or -V
    s.vertical_coordinate = -1
    s.process_command_line_arguments(["-v0"])
    assert s.vertical_coordinate == 0

    s.process_command_line_arguments(["-v4"])
    assert s.vertical_coordinate == 4

    # test +n or +N
    s.noaa_logo = False
    s.process_command_line_arguments(["+n"])
    assert s.noaa_logo == True

    s.noaa_logo = False
    s.process_command_line_arguments(["+N"])
    assert s.noaa_logo == True

    # test -p or -P
    s.output_suffix = "ps"

    s.process_command_line_arguments(["-ppdf"])
    assert s.output_suffix == "pdf"

    s.process_command_line_arguments(["-Ppng"])
    assert s.output_suffix == "png"


def test_TrajectoryPlotSettings_parse_color_codes():
    codes = plot.TrajectoryPlotSettings.parse_color_codes("3:abc")

    assert len(codes) == 3
    assert codes[0] == "a"
    assert codes[1] == "b"
    assert codes[2] == "c"

    try:
        codes = plot.TrajectoryPlotSettings.parse_color_codes("3:ab")
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "FATAL ERROR: Mismatch in option (-kn:m) n=3 m=2"


def test_TrajectoryPlotSettings_get_reader():
    s = plot.TrajectoryPlotSettings()
    r = s.get_reader()

    assert isinstance(r, plot.TrajectoryPlotSettingsReader)
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



def test_TrajectoryPlotSettingsReader___init__():
    s = plot.TrajectoryPlotSettings()
    r = plot.TrajectoryPlotSettingsReader(s)

    assert r.settings is s


def test_TrajectoryPlotSettingsReader_read():
    s = plot.TrajectoryPlotSettings()
    r = plot.TrajectoryPlotSettingsReader(s)

    o = r.read("data/default_tplot")
    assert isinstance(o, plot.TrajectoryPlotSettings)

    assert s.gis_output == 0
    assert s.view == 1
    assert s.output_filename == "trajplot"
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


def test_TrapjectoyPlot___init__():
    p = plot.TrajectoryPlot()

    assert isinstance(p.labels, labels.LabelsConfig)    # from the base class
    assert hasattr(p, "settings")
    assert hasattr(p, "data_list")
    assert hasattr(p, "traj_axes")
    assert hasattr(p, "height_axes")
    assert hasattr(p, "height_axes_outer")
    assert hasattr(p, "cluster_list")
    assert hasattr(p, "plot_saver_list")
    assert hasattr(p, "current_frame")


def test_TrajectoryPlot_merge_plot_settings():
    p = plot.TrajectoryPlot()

    p.merge_plot_settings("data/default_tplot", ["-a1"])

    assert p.settings.gis_output == 1


def test_TrajectoryPlot_read_data_files():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "--source-time-zone"])

    p.read_data_files()

    assert len(p.data_list) == 1
    assert len(p.data_list[0].trajectories) == 3
    assert p.settings.color_cycle is not None
    assert p.plot_saver_list is not None
    assert p.time_zone is not None
    

def test_TrajectoryPlot_has_terrain_profile(plotData):
    assert plot.TrajectoryPlot.has_terrain_profile([plotData]) == False

    plotData.trajectories[0].others["TERR_MSL"] = []
    assert plot.TrajectoryPlot.has_terrain_profile([plotData]) == True

    plotData.trajectories[0].others["TERR_MSL"].append(0.0)
    assert plot.TrajectoryPlot.has_terrain_profile([plotData]) == True


def test_TrajectoryPlot_set_trajectory_color():
    p = plot.TrajectoryPlot()
    s = p.settings
    s.color = const.Color.ITEMIZED
    s.color_codes = ['2', '3']

    # add four trajectories
    pd = model.TrajectoryDump()
    pd.trajectories.append(model.Trajectory())
    pd.trajectories.append(model.Trajectory())
    pd.trajectories.append(model.Trajectory())
    pd.trajectories.append(model.Trajectory())
    
    p.set_trajectory_color(pd, s)
    
    assert pd.trajectories[0].color == '2'
    assert pd.trajectories[1].color == '3'
    assert pd.trajectories[2].color == '1'
    assert pd.trajectories[3].color == '1'


def test_TrajectoryPlot__make_clusterlist_filename():
    p = plot.TrajectoryPlot()
    
    # create a test file
    with open("CLUSLIST_4", "wt") as f:
        f.write("line")
    
    fn, start_index, candidates = p._make_clusterlist_filename(4)
    assert fn == "CLUSLIST_4"
    assert start_index == 1
    
    os.remove("CLUSLIST_4")
    
    # create another test file
    with open("CLUSLIST_3", "wt") as f:
        f.write("line")
    
    fn, start_index, candidates = p._make_clusterlist_filename(4)
    assert fn == "CLUSLIST_3"
    assert start_index == 0
    
    os.remove("CLUSLIST_3")

    # otherwise
    fn, start_index, candidates = p._make_clusterlist_filename(4)
    assert fn is None
    assert start_index == 1
    assert candidates[0] == "CLUSLIST_4"
    assert candidates[1] == "CLUSLIST_3"

    
def test_TrajecotryPlot__read_cluster_info_if_exists():
    p = plot.TrajectoryPlot()
    pd = model.TrajectoryDump()
    pd.IDLBL = "MERGMEAN"
    # need four trajectories to match the contents of CLUSLIST_4
    pd.trajectories.append(model.Trajectory())
    pd.trajectories.append(model.Trajectory())
    pd.trajectories.append(model.Trajectory())
    pd.trajectories.append(model.Trajectory())
    p.data_list = [pd]
    
    # when CLUSLIST_4 does not exist
    try:
        p._read_cluster_info_if_exists(p.data_list)
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "file not found CLUSLIST_4 or CLUSLIST_3"
    
    # create CLUSLIST_4
    with open("CLUSLIST_4", "wt") as f:
        f.write("1 1\n")
        f.write("2 1\n")
        f.write("3 1\n")
        f.write("4 1\n")
    
    try:
        p._read_cluster_info_if_exists(p.data_list)
        assert p.cluster_list is not None
        assert p.cluster_list.total_traj == 4
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))

    os.remove("CLUSLIST_4")


def test_TrajectoryPlot__initialize_map_projection():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump"])
    p.read_data_files()

    assert p.street_map is None
    
    p._initialize_map_projection(p.data_list)

    assert isinstance(p.projection, mapproj.AbstractMapProjection)
    assert isinstance(p.street_map, streetmap.AbstractMapBackground)
    assert p.street_map.fix_map_color_fn is None
    assert p.initial_corners_xy == pytest.approx((-171532.0, 573785.0, -421432.0, 151889.0))
    assert p.initial_corners_lonlat == pytest.approx((-91.92366, -83.13186, 36.15948, 41.16591))


def test_TrajectoryPlot__determine_map_limits(plotData):
    p = plot.TrajectoryPlot()

    mb = p._determine_map_limits(plotData, 2)

    assert mb.grid_corner == [0.0, -90.0]
    assert mb.grid_delta == 1.0
    assert mb.sz == [360, 181]
    assert mb.plume_sz == [6.0, 4.0]
    assert mb.plume_loc == [270, 127]

    nil_plot_data = model.TrajectoryDump()

    try:
        mb2 = p._determine_map_limits(nil_plot_data, 2)
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "no trajectories to plot"


def test_TrajectoryPlot__determine_vertical_limit(plotData):
    p = plot.TrajectoryPlot()

    # ensure vertical coordinates are pressures
    plotData.fix_vertical_coordinates(VerticalCoordinate.PRESSURE, p.settings.height_unit)
    low, high = p._determine_vertical_limit(plotData, VerticalCoordinate.PRESSURE)
    assert low == 1001.1
    assert high == 879.8

    # ensure vertical coordinates are heights
    plotData.fix_vertical_coordinates(VerticalCoordinate.ABOVE_GROUND_LEVEL, p.settings.height_unit)
    low, high = p._determine_vertical_limit(plotData, VerticalCoordinate.ABOVE_GROUND_LEVEL)
    assert low == 0.0
    assert high == 1000.0

    pd = model.TrajectoryDump()
    traj = model.Trajectory()
    traj.vertical_coord = model.BlankVerticalCoordinate(traj)
    pd.trajectories.append(traj)
    low, high = p._determine_vertical_limit(pd, VerticalCoordinate.ABOVE_GROUND_LEVEL)
    assert low is None
    assert high is None
    

def test_TrajectoryPlot_layout():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump"])
    p.read_data_files()

    p.layout(p.data_list)

    assert p.fig is not None
    assert p.traj_axes is not None
    assert p.height_axes is not None
    assert p.height_axes_outer is not None
    assert p.text_axes is not None

    cleanup_plot(p)


def test_TrajectoryPlot_make_plot_title(plotData):
    p = plot.TrajectoryPlot()
    p.labels = labels.LabelsConfig()
    p.cluster_list = clist.ClusterList(1)
    
    title = p.make_plot_title(plotData)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "Forward trajectories starting at 0000 UTC 16 Oct 1995\n" + \
           "NGM  Meteorological Data"

    # Change the model name

    plotData.grids[0].model = " TEST "
    title = p.make_plot_title(plotData)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "Forward trajectories starting at 0000 UTC 16 Oct 1995\n" + \
           "TEST  Meteorological Data"

    # Add a grid

    g = model.MeteorologicalGrid()
    g.model = "TEST"
    plotData.grids.append(g)
    title = p.make_plot_title(plotData)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "Forward trajectories starting at 0000 UTC 16 Oct 1995\n" + \
           "TEST  Meteorological Data"

    # Add time zone
    p.time_zone = pytz.timezone("EST")
    title = p.make_plot_title(plotData)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "Forward trajectories starting at 1900 EST 15 Oct 1995\n" + \
           "TEST  Meteorological Data"
    p.time_zone = None
    
    # Change the starting time of a trajectory

    t = plotData.trajectories[2]
    t.starting_datetime = datetime.datetime(1993, 10, 16, 1, 0)
    title = p.make_plot_title(plotData)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "Forward trajectories starting at various times\n" + \
           "TEST  Meteorological Data"

    # Change direction

    plotData.trajectory_direction = "BACKWARD"
    title = p.make_plot_title(plotData)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "Backward trajectories ending at various times\n" + \
           "TEST  Meteorological Data"

    # With one trajectory

    plotData.trajectories.pop()
    plotData.trajectories.pop()
    title = p.make_plot_title(plotData)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "Backward trajectory ending at 0000 UTC 16 Oct 1995\n" + \
           "TEST  Meteorological Data"

    # Change direction

    plotData.trajectory_direction = "FORWARD"
    title = p.make_plot_title(plotData)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "Forward trajectory starting at 0000 UTC 16 Oct 1995\n" + \
           "TEST  Meteorological Data"

    # IDLBL = "MERGMEAN"
    
    plotData.IDLBL = "MERGMEAN"
    p.cluster_list.total_traj = 112
    title = p.make_plot_title(plotData)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "112 forward trajectories\n" + \
           "TEST  Meteorological Data"
           
    # change direction
    
    plotData.trajectory_direction = "BACKWARD"
    title = p.make_plot_title(plotData)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "112 backward trajectories\n" + \
           "TEST  Meteorological Data"

    # Forecast
    
    plotData.trajectories[0].forecast_hours[0] = 13.0 # > 12
    title = p.make_plot_title(plotData)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "112 backward trajectories\n" + \
           "11 UTC 15 Oct  TEST  Forecast Initialization"

    # Time zone
    p.time_zone = pytz.timezone("EST")
    
    title = p.make_plot_title(plotData)
    assert title == "NOAA HYSPLIT MODEL\n" + \
           "112 backward trajectories\n" + \
           "06 EST 15 Oct  TEST  Forecast Initialization"


def test_TrajectoryPlot_make_ylabel():
    plotData = model.TrajectoryDump()
    t = model.Trajectory()
    t.starting_loc = (30.0, 20.0)
    plotData.trajectories.append(t)

    label = plot.TrajectoryPlot.make_ylabel(plotData, "*", 6)
    assert label == "Source * at  20.00 N   30.00 E"

    # no marker when the time label interval is negative
    label = plot.TrajectoryPlot.make_ylabel(plotData, "*", -6)
    assert label == "Source at  20.00 N   30.00 E"

    # negative longitude

    t.starting_loc = (-30.0, 20.0)

    label = plot.TrajectoryPlot.make_ylabel(plotData, "*", 6)
    assert label == "Source * at  20.00 N   30.00 W"

    # negative latitude

    t.starting_loc = (-30.0, -20.0)

    label = plot.TrajectoryPlot.make_ylabel(plotData, "*", 6)
    assert label == "Source * at  20.00 S   30.00 W"

    # add a trajectory with a different starting location

    t = model.Trajectory()
    t.starting_loc = (30.0, 25.0)
    plotData.trajectories.append(t)

    label = plot.TrajectoryPlot.make_ylabel(plotData, "*", 6)
    assert label == "Source * at multiple locations"
    
    
def test_TrajectoryPlot_get_street_map_target_axes():
    p = plot.TrajectoryPlot()
    ax = plt.axes()
    p.traj_axes = ax
    assert p.get_street_map_target_axes() is ax
    plt.close(ax.get_figure())
    

def test_TrajectoryPlot_draw_height_profile():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.layout(p.data_list)

    # See if no exception is thrown.
    try:
        p.draw_height_profile(p.data_list, False)
        p.draw_height_profile(p.data_list, True)
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_TrajectoryPlot_draw_trajectory_plot():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.layout(p.data_list)

    # See if no exception is thrown.
    try:
        p.draw_trajectory_plot(p.data_list)
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_TrajectoryPlot_draw_trajectories():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.layout(p.data_list)

    # See if no exception is thrown.
    try:
        p.draw_trajectories(p.traj_axes, p.data_list)
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_TrajectoryPlot_draw_source_markers():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.layout(p.data_list)

    # See if no exception is thrown.
    try:
        p.draw_source_markers(p.traj_axes, p.data_list)
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_TrajectoryPlot_draw_trajectory_uncertainty():
    p = plot.TrajectoryPlot()
    ax = plt.axes()
    p.traj_axes = ax

    # See if no exception is thrown.
    try:
        lons = (-84.815, -84.395)
        lats = ( 39.908,  39.690)
        sigmas = ((0.1, 0.1), (0.1, 0.2))
        p.draw_trajectory_uncertainty(lons, lats, sigmas, "r")
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))
    
    plt.close(ax.get_figure())


def test_TrajectoryPlot_draw_bottom_plot():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.layout(p.data_list)

    # See if no exception is thrown.
    try:
        p.draw_bottom_plot(p.data_list)
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_TrajectoryPlot_draw_bottom_text():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.layout(p.data_list)

    # See if no exception is thrown.
    try:
        p.draw_bottom_text()
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_TrajectoryPlot_draw():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()

    # See if no exception is thrown.
    try:
        p.draw(block=False)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))

    assert os.path.exists("trajplot.ps")
    os.remove("trajplot.ps")
    
    # Save to a file
    p.settings.interactive_mode = False
    plot_saver = multipage.PlotFileWriterFactory.create_instance(p.settings.frames_per_file,
                                                                   "__traj",
                                                                   "png",
                                                                   "png")
    p.plot_saver_list = [ plot_saver ]
    p.draw()
    assert os.path.exists("__traj0002.png")
    os.remove("__traj0002.png")

    cleanup_plot(p)
    

def test_TrajectoryPlot_write_gis_files():
    p = plot.TrajectoryPlot()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated", "-a3", "+a0", "-A0"])
    p.read_data_files()
    
    if os.path.exists("HYSPLITtraj_ps_01.kml"):
        os.remove("HYSPLITtraj_ps_01.kml")
        
    p.write_gis_files()
    
    assert os.path.exists("HYSPLITtraj_ps_01.kml")
    
    # parse the XML document and check some elements.
    tree = ElementTree.parse("HYSPLITtraj_ps_01.kml")
    root = tree.getroot()
    name = root.find("./{http://www.opengis.net/kml/2.2}Document/{http://www.opengis.net/kml/2.2}name")
    assert name.text == "NOAA HYSPLIT Trajectory ps"
    
    os.remove("HYSPLITtraj_ps_01.kml")


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
        pytest.fail("unexpected exception: {0}".format(ex))


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
        pytest.fail("unexpected exception: {0}".format(ex))


def test_MonoColorCycle_next_color():
    cc = plot.MonoColorCycle()
    assert cc.next_color(None, None) == "k"
    assert cc.next_color(None, None) == "k"


def test_HeightColorCycle___init__():
    try:
        cc = plot.HeightColorCycle()
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))


def test_HeightColorCycle_next_color():
    cc = plot.HeightColorCycle()
    assert cc.next_color(0, None) == "r"
    assert cc.next_color(6, None) == "#3399cc"
    assert cc.next_color(7, None) == "r"


def test_ColorCycleFactory_create_instance():
    s = plot.TrajectoryPlotSettings()

    s.color = const.Color.COLOR
    cc = plot.ColorCycleFactory.create_instance(s, 1)
    assert isinstance(cc, plot.ColorCycle)
    assert cc.max_colors == 3

    s.color = const.Color.COLOR
    cc = plot.ColorCycleFactory.create_instance(s, 2)
    assert isinstance(cc, plot.HeightColorCycle)
    assert cc.max_colors == 7

    s.color = const.Color.ITEMIZED
    cc = plot.ColorCycleFactory.create_instance(s, 2)
    assert isinstance(cc, plot.ItemizedColorCycle)

    s.color = const.Color.BLACK_AND_WHITE
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


def test_NullIntervalSymbolDrawer___init__():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()

    d = plot.NullIntervalSymbolDrawer(axes, s, 12)
    assert d.axes == axes
    assert d.settings == s
    assert d.interval == 12

    plt.close(axes.get_figure())


def test_NullIntervalSymbolDrawer_draw():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()

    d = plot.NullIntervalSymbolDrawer(axes, s, 12)

    try:
        d.draw(None, None, None)
    except Exception as ex:
        pytest.fail("unexpected exception {0}".format(ex))

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
        d.draw(t, t.datetimes, t.pressures)
    except Exception as ex:
        pytest.fail("unexpected exception {0}".format(ex))

    plt.close(axes.get_figure())


def test_TimeIntervalSymbolDrawer__filter_datadraw(plotData):
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    d = plot.TimeIntervalSymbolDrawer(axes, s, 12)

    x24, y24, x12, y12 = d._filter_data(
        plotData.trajectories[0].datetimes,
        plotData.trajectories[0].longitudes,
        plotData.trajectories[0].latitudes,
        12, False)

    assert len(x24) == 1
    assert x24[0] == -90.0

    assert len(y24) == 1
    assert y24[0] == 40.0

    assert len(x12) == 1
    assert x12[0] == -88.772

    assert len(y12) == 1
    assert y12[0] == 38.586

    plt.close(axes.get_figure())
    

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
        d.draw(t, t.datetimes, t.pressures)
    except Exception as ex:
        pytest.fail("unexpected exception {0}".format(ex))

    plt.close(axes.get_figure())


def test_AgeIntervalSymbolDrawer__filter_data(plotData):
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    d = plot.AgeIntervalSymbolDrawer(axes, s, 12)

    x24, y24, x12, y12 = d._filter_data(
        plotData.trajectories[0].ages,
        plotData.trajectories[0].longitudes,
        plotData.trajectories[0].latitudes,
        12, False)

    assert len(x24) == 1
    assert x24[0] == -90.0

    assert len(y24) == 1
    assert y24[0] == 40.0

    assert len(x12) == 1
    assert x12[0] == -88.772

    assert len(y12) == 1
    assert y12[0] == 38.586

    plt.close(axes.get_figure())
    
    
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
    assert isinstance(d, plot.NullIntervalSymbolDrawer)

    plt.close(axes.get_figure())
 

def test_AbstractVerticalProjection___init__():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = AbstractVerticalProjectionTest(axes, s, 6)
    assert o.axes == axes
    assert o.settings == s
    assert o.time_interval == 6
    plt.close(axes.get_figure())
    

def test_AbstractVerticalProjection_calc_xrange(plotData):
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = AbstractVerticalProjectionTest(axes, s, 6)
    assert o.calc_xrange(plotData) == None
    plt.close(axes.get_figure())
        

def test_AbstractVerticalProjection_create_xlabel_formatter():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = AbstractVerticalProjectionTest(axes, s, 6)
    assert o.create_xlabel_formatter() == None
    plt.close(axes.get_figure())
  

def test_AbstractVerticalProjection_select_xvalues(plotData):
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = AbstractVerticalProjectionTest(axes, s, 6)
    assert o.select_xvalues(plotData.trajectories[0]) == None
    plt.close(axes.get_figure())

    
def test_AbstractVerticalProjection_create_interval_symbol_drawer():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    o = AbstractVerticalProjectionTest(axes, s, 6)
    assert o.create_interval_symbol_drawer() is not None
    plt.close(axes.get_figure())


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
    utc = pytz.utc
    assert r[0] == datetime.datetime(1995, 10, 16,  0, 0, 0, 0, utc)
    assert r[1] == datetime.datetime(1995, 10, 16, 12, 0, 0, 0, utc)
    
    est = pytz.timezone("EST")
    r = o.calc_xrange(plotData, est)
    assert r[0] == datetime.datetime(1995, 10, 15, 19, 0, 0, 0)
    assert r[1] == datetime.datetime(1995, 10, 16,  7, 0, 0, 0)
    
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
    utc = pytz.utc
    assert len(x) > 0
    assert x[0] == datetime.datetime(1995, 10, 16, 0, 0, 0, 0, utc)

    est = pytz.timezone("EST")    
    x = o.select_xvalues(plotData.trajectories[0], est)
    utc = pytz.utc
    assert len(x) > 0
    assert x[0] == datetime.datetime(1995, 10, 15, 19, 0, 0, 0)
    
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
    assert o.calc_xrange(plotData, pytz.utc) == (0.0, 12.0)
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
    
    est = pytz.timezone("EST")
    x = o.select_xvalues(plotData.trajectories[0], est)
    assert len(x) > 0
    assert x[0] == 0
    
    plt.close(axes.get_figure())
 

def test_VerticalProjectionFactory_create_instance():
    s = plot.TrajectoryPlotSettings()
    axes = plt.axes()
    
    s.time_label_interval = 6
    o = plot.VerticalProjectionFactory.create_instance(axes, s)
    assert isinstance(o, plot.TimeVerticalProjection)
    
    s.time_label_interval = -6
    o = plot.VerticalProjectionFactory.create_instance(axes, s)
    assert isinstance(o, plot.AgeVerticalProjection)
    
    s.time_label_interval = 0
    o = plot.VerticalProjectionFactory.create_instance(axes, s)
    assert isinstance(o, plot.TimeVerticalProjection)
    
    plt.close(axes.get_figure())
    
    
def test_FrameDataIteratorFactory_create_instance(plotData):
    tdump_list = [plotData]
    
    o = plot.FrameDataIteratorFactory.create_instance(const.Frames.ALL_FILES_ON_ONE, tdump_list)
    assert isinstance(o, plot.AllAtOnceFrameDataIterator)
        
    o = plot.FrameDataIteratorFactory.create_instance(const.Frames.ONE_PER_FILE, tdump_list)
    assert isinstance(o, plot.OneByOneFrameDataIterator)


def test_AbstractFrameDataIterator___init__(plotData):
    tdump_list = [plotData]
        
    # Since an object cannot be created from an abstract class, instantiate a concrete test class.
    o = AbstractFrameDataIteratorTest(tdump_list)
    assert len(o.tdump_list) == 1
    assert o.tdump_list[0] is plotData


def test_AllAtOnceFrameDataIterator___init__(plotData):
    tdump_list = [plotData]
    
    o = plot.AllAtOnceFrameDataIterator(tdump_list)
    assert len(o.tdump_list) == 1
    assert o.tdump_list[0] is plotData
    
    
def test_AllAtOnceFrameDataIterator___iter__(plotData):
    tdump_list = [plotData, plotData]
    a = []
    
    o = plot.AllAtOnceFrameDataIterator(tdump_list)
    for data_list in o:
        a.append(data_list)
        
    assert len(a) == 1
    assert len(a[0]) == 2
    assert a[0] == [plotData, plotData]


def test_OneByOneFrameDataIterator___init__(plotData):
    tdump_list = [plotData]
    
    o = plot.OneByOneFrameDataIterator(tdump_list)
    assert len(o.tdump_list) == 1
    assert o.tdump_list[0] is plotData
    
    
def test_OneByOneFrameDataIterator___iter__(plotData):
    tdump_list = [plotData, plotData]
    a = []
    
    o = plot.OneByOneFrameDataIterator(tdump_list)
    for data_list in o:
        a.append(data_list)
        
    assert len(a) == 2
    assert a == [[plotData], [plotData]]
