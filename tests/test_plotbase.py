import pytest
import matplotlib.pyplot as plt
from hysplit4 import plotbase, const, mapproj, mapfile, labels
from hysplit4.traj import plot


def blank_event_handler(event):
    # do nothing
    return


def cleanup_plot(p):
    if p.fig is not None:
        plt.close(p.fig)
        

def test_AbstractPlotSettings___init__():
    s = plotbase.AbstractPlotSettings()

    assert s.map_background == "../graphics/arlmap"
    assert s.map_projection == 0
    assert s.zoom_factor == 0.5
    assert s.ring == False
    assert s.ring_number == -1
    assert s.ring_distance == 0.0
    assert s.center_loc == [0.0, 0.0]
    assert s.output_postscript == "output.ps"
    assert s.output_suffix == "ps"
    assert s.output_basename == "output"
    assert s.noaa_logo == False
    assert s.lat_lon_label_interval_option == 1
    assert s.lat_lon_label_interval == 1.0
    assert s.frames_per_file == 0
    
    assert s.interactive_mode == True
    assert s.map_color == "#1f77b4"
    assert s.station_marker != None
    assert s.station_marker_color != None
    assert s.station_marker_size > 0
    

def test_AbstractPlotSettings__process_cmdline_args():
    s = plotbase.AbstractPlotSettings()

    # test +n
    s.noaa_logo = False
    s._process_cmdline_args(["+n"])
    assert s.noaa_logo == True

    # test +N
    s.noaa_logo = False
    s._process_cmdline_args(["+N"])
    assert s.noaa_logo == True

    # test -f or -F
    s.frames_per_file = 0
    s._process_cmdline_args(["-f2"])
    assert s.frames_per_file == 2

    s._process_cmdline_args(["-F5"])
    assert s.frames_per_file == 5

    # test -g or -G
    s.ring_number = 0
    s.ring_distance = 0.0

    s._process_cmdline_args(["-g"])
    assert s.ring_number == 4
    assert s.ring_distance == 0.0

    s._process_cmdline_args(["-G9"])
    assert s.ring_number == 9
    assert s.ring_distance == 0.0

    s._process_cmdline_args(["-G5:5.5"])
    assert s.ring_number == 5
    assert s.ring_distance == 5.5

    # test -h or -H
    s.center_loc = [0.0, 0.0]

    s._process_cmdline_args(["-h"])
    assert s.center_loc == [0.0, 0.0]

    s._process_cmdline_args(["-H12.3:45.6"])
    assert s.center_loc == [45.6, 12.3]

    s._process_cmdline_args(["-h-112.3:-195.6"])
    assert s.center_loc == [-180.0, -90.0]

    s._process_cmdline_args(["-H112.3:195.6"])
    assert s.center_loc == [180.0, 90.0]
    
    # test -j or -J
    s._process_cmdline_args(["-j../graphics/else"])
    assert s.map_background == "../graphics/else"
    
    s._process_cmdline_args(["-J../graphics/else_where"])
    assert s.map_background == "../graphics/else_where"

    # test -L
    s.lat_lon_label_interval_option = 0
    s.lat_lon_label_interval = 0

    s._process_cmdline_args(["-L1"])
    assert s.lat_lon_label_interval_option == 1

    s._process_cmdline_args(["-L2:50"])
    assert s.lat_lon_label_interval_option == 2
    assert s.lat_lon_label_interval == 5.0

    # test -m and -M
    s.map_projection = 0

    s._process_cmdline_args(["-m1"])
    assert s.map_projection == 1
    
    s._process_cmdline_args(["-M2"])
    assert s.map_projection == 2

    # test -o or -O
    s.output_postscript = None
    s.interactive_mode = True

    s._process_cmdline_args(["-otest"])
    assert s.output_postscript == "test.ps"
    assert s.interactive_mode == False
    
    s.output_postscript = None
    s.interactive_mode = True
    
    s._process_cmdline_args(["-Oresult"])
    assert s.output_postscript == "result.ps"
    assert s.interactive_mode == False
    
    # test -p or -P
    s.output_suffix = "ps"

    s._process_cmdline_args(["-ppdf"])
    assert s.output_suffix == "pdf"

    s._process_cmdline_args(["-Ppng"])
    assert s.output_suffix == "png"    
    
     # test -z or -Z
    s.zoom_factor = 0

    s._process_cmdline_args(["-z50"])
    assert s.zoom_factor == 0.5

    s._process_cmdline_args(["-Z70"])
    assert s.zoom_factor == 0.3
    

def test_AbstractPlotSettings_parse_lat_lon_label_interval():
    mapdel = plotbase.AbstractPlotSettings.parse_lat_lon_label_interval("2:50")
    assert mapdel == 5.0


def test_AbstractPlotSettings_parse_ring_option():
    count, distance = plotbase.AbstractPlotSettings.parse_ring_option("2:50")
    assert count == 2
    assert distance == 50.0


def test_AbstractPlotSettings_parse_map_center():
    loc = plotbase.AbstractPlotSettings.parse_map_center("45.0:-120.0")
    assert loc == [-120.0, 45.0]


def test_AbstractPlotSettings_parse_zoom_factor():
    assert plotbase.AbstractPlotSettings.parse_zoom_factor("-10") == 1.0
    assert plotbase.AbstractPlotSettings.parse_zoom_factor("10") == .90
    assert plotbase.AbstractPlotSettings.parse_zoom_factor("90") == .10
    assert plotbase.AbstractPlotSettings.parse_zoom_factor("120") == 0.0


def test_AbstractPlot___init__():
    p = plotbase.AbstractPlot()

    assert p._GRIDLINE_DENSITY == 0.25
    assert hasattr(p, "fig")
    assert hasattr(p, "projection")
    assert hasattr(p, "crs")
    assert hasattr(p, "data_crs")
    assert hasattr(p, "background_maps")
    assert hasattr(p, "labels")
    assert isinstance(p.labels, labels.LabelsConfig)


def test_AbstractPlot__connect_event_handlers():
    p = plotbase.AbstractPlot()
    axes = plt.axes()
    p.fig = axes.figure

    try:
        p._connect_event_handlers({"resize_event" : blank_event_handler})
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_AbstractPlot_compute_pixel_aspect_ratio():
    axes = plt.axes()
    assert plotbase.AbstractPlot.compute_pixel_aspect_ratio(axes) == pytest.approx(1.39909)
    plt.close(axes.figure)
  

def test_AbstractPlot__turn_off_spines():
    p = plotbase.AbstractPlot()
    axes = plt.axes()

    # See if no exception is thrown.
    try:
        p._turn_off_spines(axes)
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_AbstractPlot__turn_off_ticks():
    p = plotbase.AbstractPlot()
    axes = plt.axes()

    # See if no exception is thrown.
    try:
        p._turn_off_ticks(axes)
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_AbstractPlot__update_gridlines():
    p = plotbase.AbstractPlot()
    p.projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    p.projection.corners_xy = [1.0, 1.0, 500.0, 500.0]
    p.projection.corners_lonlat = [-95.0, -75.0, 25.0, 45.0]
    p.crs = p.projection.create_crs()
    axes = plt.axes(projection=p.crs)

    try:
        p._update_gridlines(axes, 'k', const.LatLonLabel.AUTO, 1.0)
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))
     

def test_AbstractPlot__collect_tick_values():
    t = plotbase.AbstractPlot._collect_tick_values(-1800, 1800, 100, 0.1, (-120, -80))
    assert t == pytest.approx((-130, -120, -110, -100, -90, -80, -70))


def test_AbstractPlot__get_gridline_spacing():
    p = plotbase.AbstractPlot()
    assert p._get_gridline_spacing([-130.0, -110.0, 45.0, 55.0], const.LatLonLabel.NONE, 1.0) == 0.0
    assert p._get_gridline_spacing([-130.0, -110.0, 45.0, 55.0], const.LatLonLabel.SET, 3.14) == 3.14
    assert p._get_gridline_spacing([-130.0, -110.0, 45.0, 55.0], const.LatLonLabel.AUTO, 1.0) == 5.0
    
    
def test_AbstractPlot__calc_gridline_spacing():
    p = plotbase.AbstractPlot()
    assert p._calc_gridline_spacing([-130.0, -110.0, 45.0, 55.0]) == 5.0
    assert p._calc_gridline_spacing([-120.0, -110.0, 35.0, 55.0]) == 5.0
    # across the dateline
    assert p._calc_gridline_spacing([+350.0, -10.0, 35.0, 55.0]) == 5.0
    # test min.
    assert p._calc_gridline_spacing([0.0, 0.1, 0.0, 0.1]) == 0.2


def test_AbstractPlot__fix_arlmap_filename():
    assert plotbase.AbstractPlot._fix_arlmap_filename("data/arlmap_truncated") == "data/arlmap_truncated"
    assert plotbase.AbstractPlot._fix_arlmap_filename("data/nonexistent") == None

 
def test_AbstractPlot_load_background_map():
    p = plotbase.AbstractPlot()
    maps = p.load_background_map("data/arlmap_truncated")

    assert maps is not None
    assert len(maps) > 0
    assert isinstance(maps[0], mapfile.DrawableBackgroundMap)
    assert maps[0].map.crs == mapproj.MapProjection._WGS84
    
    
def test_AbstractPlot__make_labels_filename():
    assert plotbase.AbstractPlot._make_labels_filename("ps") == "LABELS.CFG"
    assert plotbase.AbstractPlot._make_labels_filename("pdf") == "LABELS.pdf"


def test_AbstractPlot_read_custom_labels_if_exists():
    p = plot.TrajectoryPlot() # need a concrete class
    assert p.labels.get("TITLE") == "NOAA HYSPLIT MODEL"

    # Without the filename argument, it will try to read LABELS.CFG.
    p.read_custom_labels_if_exists()
    assert p.labels.get("TITLE") == "NOAA HYSPLIT MODEL"
    
    p.read_custom_labels_if_exists("data/nonexistent")
    assert p.labels.get("TITLE") == "NOAA HYSPLIT MODEL"

    p.read_custom_labels_if_exists("data/LABELS.CFG")
    assert p.labels.get("TITLE") == "Sagebrush Exp #5"


def test_AbstractPlot__draw_latlon_labels():
    p = plotbase.AbstractPlot()
    p.projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    p.projection.corners_xy = [1.0, 1.0, 500.0, 500.0]
    p.crs = p.projection.create_crs()
    axes = plt.axes()
    
    try:
        p._draw_latlon_labels(axes, [], 1.0, 1.0, 'k')
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))
    


def test_AbstractPlot__make_stationplot_filename():
    assert plotbase.AbstractPlot._make_stationplot_filename("ps") == "STATIONPLOT.CFG"
    assert plotbase.AbstractPlot._make_stationplot_filename("pdf") == "STATIONPLOT.pdf"


def test_AbstractPlot__draw_stations_if_exists():
    p = plotbase.AbstractPlot()
    p.projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    p.projection.corners_xy = [1.0, 1.0, 500.0, 500.0]
    p.crs = p.projection.create_crs()
    axes = plt.axes(projection=p.crs)

    s = plotbase.AbstractPlotSettings()
    
    # See if no exception is thrown.
    try:
        p._draw_stations_if_exists(axes, s, "data/STATIONPLOT.CFG")
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_AbstractPlot__draw_concentric_circles():
    p = plotbase.AbstractPlot()
    p.projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    p.projection.corners_xy = [1.0, 1.0, 500.0, 500.0]
    p.crs = p.projection.create_crs()
    axes = plt.axes(projection=p.crs)

    try:
        p._draw_concentric_circles(axes, [-84.0, 35.0], 4, 100.0)
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))

    
def test_AbstractPlot__draw_noaa_logo():
    p = plotbase.AbstractPlot()
    axes = plt.axes()
    
    try:
        p._draw_noaa_logo(axes)
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))
    
    
def test_AbstractPlot_make_plot_filename():
    s = plotbase.AbstractPlotSettings()
    p = plotbase.AbstractPlot()
    
    s.output_postscript= "output.ps"
    s.output_basename = "output"
    s.output_suffix = "ps"
    
    s.frames_per_file = const.Frames.ALL_FILES_ON_ONE
    assert p.make_plot_filename(s) == "output.ps"
    
    s.frames_per_file = const.Frames.ONE_PER_FILE
    assert p.make_plot_filename(s) == "output0001.ps"
    assert p.make_plot_filename(s, 2) == "output0002.ps"
    
    