import pytest
import matplotlib.pyplot as plt
from hysplit4 import plotbase, const, mapproj, mapfile


def blank_event_handler(event):
    # do nothing
    return


def test_AbstractPlotSettings___init__():
    # TODO
    return


def test_AbstractPlotSettings__process_cmdline_args():
    # TODO
    return


def test_AbstractPlotSettings_parse_color_codes():
    codes = plotbase.AbstractPlotSettings.parse_color_codes("3:abc")

    assert len(codes) == 3
    assert codes[0] == "a"
    assert codes[1] == "b"
    assert codes[2] == "c"

    try:
        codes = plotbase.AbstractPlotSettings.parse_color_codes("3:ab")
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "FATAL ERROR: Mismatch in option (-kn:m) n=3 m=2"


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
    assert hasattr(p, "projection")
    assert hasattr(p, "crs")
    assert hasattr(p, "data_crs")
    assert hasattr(p, "background_maps")
    

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


def test_AbstractPlot__fix_map_color():
    p = plotbase.AbstractPlot()

    color_mode = const.Color.BLACK_AND_WHITE
    assert p._fix_map_color('#6699cc', color_mode) == 'k' # black

    color_mode = const.Color.COLOR
    assert p._fix_map_color('#6699cc', color_mode) == '#6699cc'

    color_mode = const.Color.ITEMIZED
    assert p._fix_map_color('#6699cc', color_mode) == '#6699cc'


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