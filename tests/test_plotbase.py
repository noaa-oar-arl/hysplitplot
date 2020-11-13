# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_plotbase.py
#
# Performs unit tests on functions and class methods declared in plotbase.py.
# ---------------------------------------------------------------------------

import datetime
import matplotlib.pyplot as plt
import pytest
import pytz

from hysplitdata.const import HeightUnit
from hysplitplot import const, datem, labels, mapbox, mapfile, mapproj, plotbase, streetmap
from hysplitplot.traj import plot


def blank_event_handler(event):
    # do nothing
    return


def cleanup_plot(p):
    if p.fig is not None:
        plt.close(p.fig)
        

class AbstractPlotTest(plotbase.AbstractPlot):
    
    def __init__(self):
        super(AbstractPlotTest, self).__init__()
        self.target_axes = None
        self.settings = plotbase.AbstractPlotSettings()
        
    def get_street_map_target_axes(self):
        return self.target_axes


def test_AbstractPlotSettings___init__():
    s = plotbase.AbstractPlotSettings()

    assert s.map_background == "../graphics/arlmap"
    assert s.noaa_logo == False
    assert s.output_filename == "output.ps"
    assert s.output_basename == "output"
    assert s.output_suffix == "ps"
    assert s.output_format == "ps"
    assert s.zoom_factor == 0.5
    assert s.interactive_mode == False
    assert len(s.additional_output_formats) == 0
    assert s.use_source_time_zone == False
    assert s.time_zone_str is None
    assert s.use_street_map == False
    assert s.street_map_type == 0
    assert s.map_projection == 0

    assert s.lat_lon_label_interval_option == 1
    assert s.lat_lon_label_interval == 1.0
    assert s.frames_per_file == 0
    assert s.map_color == "#1f77b4"
    assert s.station_marker != None
    assert s.station_marker_color != None
    assert s.station_marker_size > 0
    assert s.height_unit == HeightUnit.METERS
    assert s.street_map_update_delay > 0
    
    assert s.process_id_set == False
#         

def test_AbstractPlotSettings__process_cmdline_args():
    s = plotbase.AbstractPlotSettings()
    
    # test -j or -J
    s._process_cmdline_args(["-j../graphics/else"])
    assert s.map_background == "../graphics/else"
    
    s._process_cmdline_args(["-J../graphics/else_where"])
    assert s.map_background == "../graphics/else_where"

    # test +n
    s.noaa_logo = False
    s._process_cmdline_args(["+n"])
    assert s.noaa_logo == True

    # test +N
    s.noaa_logo = False
    s._process_cmdline_args(["+N"])
    assert s.noaa_logo == True

    # test -o or -O
    s.output_filename = None
    s.interactive_mode = True

    s._process_cmdline_args(["-otest"])
    assert s.output_filename == "test.ps"
    assert s.interactive_mode == True
    assert s.process_id_set == False
    
    s.output_filename = None
    s.interactive_mode = True
    
    s._process_cmdline_args(["-Oresult"])
    assert s.output_filename == "result.ps"
    assert s.interactive_mode == True
    
    # test -p or -P
    s.output_filename = "result"
    s.output_suffix = "ps"

    s._process_cmdline_args(["-ppdf"])
    assert s.output_suffix == "pdf"
    assert s.output_format == "pdf"
    assert s.process_id_set == True

    s.output_filename = "result"
    s.output_suffix = "ps"
    
    s._process_cmdline_args(["-Ppng"])
    assert s.output_suffix == "png"
    assert s.output_format == "png"
    
     # test -z or -Z
    s.zoom_factor = 0

    s._process_cmdline_args(["-z50"])
    assert s.zoom_factor == 0.5

    s._process_cmdline_args(["-Z70"])
    assert s.zoom_factor == 0.3

    # test --interactive
    s.interactive_mode = False
    s._process_cmdline_args(["--interactive"])
    assert s.interactive_mode == True
    
    # test --more-formats
    s.output_format = "ps"
    s.output_filename = "test.ps"
    s.additional_output_formats = []
    s._process_cmdline_args(["--more-formats=png,tif,pdf,jpg"])
    assert len(s.additional_output_formats) == 4
    
    # test --source-time-zone
    s.use_source_time_zone = False
    s._process_cmdline_args(["--source-time-zone"])
    assert s.use_source_time_zone == True

    # test --street-map=n or --street-map
    s.use_street_map = False
    s._process_cmdline_args(["--street-map"])
    assert s.use_street_map == True
    assert s.street_map_type == 0
    
    s.use_street_map = False
    s._process_cmdline_args(["--street-map=3"])
    assert s.use_street_map == True
    assert s.street_map_type == 3
    
    # test --time-zone option
    s.use_source_time_zone = True
    s._process_cmdline_args(["--time-zone=US/Eastern"])
    assert s.time_zone_str == "US/Eastern"
    assert s.use_source_time_zone == False


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


def test_AbstractPlotSettings_parse_output_formats():
    a = plotbase.AbstractPlotSettings.parse_output_formats("png")
    assert len(a) == 1
    assert a[0] == "png"
    
    a = plotbase.AbstractPlotSettings.parse_output_formats("png,jpg")
    assert len(a) == 2
    assert a[0] == "png"
    assert a[1] == "jpg"
    
    a = plotbase.AbstractPlotSettings.parse_output_formats(None)
    assert len(a) == 0
    
    a = plotbase.AbstractPlotSettings.parse_output_formats("png,jpg,,jpg,,,unknown,")
    assert len(a) == 2
    assert a[0] == "png"
    assert a[1] == "jpg"
        
    a = plotbase.AbstractPlotSettings.parse_output_formats("png,jpg,pdf,tif")
    assert len(a) == 4
    assert a[0] == "png"
    assert a[1] == "jpg"
    assert a[2] == "pdf"
    assert a[3] == "tif"
    

def test_AbstractPlotSettings_normalzie_output_suffix():
    s = plotbase.AbstractPlotSettings()
    
    s.process_id_set = True
    s.output_suffix = "12345"
    assert s.normalize_output_suffix("pdf") == "12345.pdf"
    
    s.process_id_set = False
    assert s.normalize_output_suffix("pdf") == "pdf"
        

def test_AbstractPlot___init__():
    p = AbstractPlotTest()

    assert hasattr(p, "fig")
    assert hasattr(p, "projection")
    assert hasattr(p, "data_crs")
    assert hasattr(p, "background_maps")
    assert hasattr(p, "labels") and isinstance(p.labels, labels.LabelsConfig)
    assert hasattr(p, "time_zone")
    assert hasattr(p, "street_map") and p.street_map is None
    assert hasattr(p, "logo_drawer")
    assert hasattr(p, "settings")
    assert hasattr(p, "initial_corners_xy") and p.initial_corners_xy is None
    assert hasattr(p, "initial_corners_lonlat") and p.initial_corners_lonlat is None


def test_AbstractPlot__connect_event_handlers():
    p = AbstractPlotTest()
    axes = plt.axes()
    p.fig = axes.figure

    try:
        p._connect_event_handlers({"resize_event" : blank_event_handler})
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_AbstractPlot_compute_pixel_aspect_ratio():
    p = AbstractPlotTest()
    axes = plt.axes()
    p.settings.interactive_mode = True
    assert p.compute_pixel_aspect_ratio(axes) == pytest.approx(1.39909)
    p.settings.interactive_mode = False
    assert p.compute_pixel_aspect_ratio(axes) == pytest.approx(1.0)
    plt.close(axes.figure)
  

def test_AbstractPlot__turn_off_spines():
    p = AbstractPlotTest()
    axes = plt.axes()

    # See if no exception is thrown.
    try:
        p._turn_off_spines(axes)
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_AbstractPlot__turn_off_ticks():
    p = AbstractPlotTest()
    axes = plt.axes()

    # See if no exception is thrown.
    try:
        p._turn_off_ticks(axes)
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_AbstractPlot_create_street_map():
    p = AbstractPlotTest()
    # Supplement setting parameters that are not declared by the AbstractPlotSettings class.
    p.settings.color = const.Color.COLOR
    p.settings.map_background = "data/arlmap_truncated"

    projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    projection.corners_xy = [1.0, 500.0, 1.0, 500.0]
    projection.corners_lonlat = [-95.0, -75.0, 25.0, 45.0]
    street_map = p.create_street_map(projection, False, const.StreetMap.STAMEN_TERRAIN)

    assert street_map.fix_map_color_fn is None
    assert street_map.projection is projection
    #
    assert street_map.background_maps is not None
    assert len(street_map.background_maps) > 0
    assert isinstance(street_map.background_maps[0], mapfile.DrawableBackgroundMap)
    assert street_map.background_maps[0].map.crs == mapproj.AbstractMapProjection._WGS84
    

def test_AbstractPlot_update_plot_extents():
    p = AbstractPlotTest()
    p.projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    p.projection.corners_xy = [-645202.80, 248127.59, -499632.13, 248127.59]
    p.projection.corners_lonlat = [-132.6424, -121.7551, 40.2331, 47.1785]
    
    p.target_axes = plt.axes(projection=p.projection.crs)
    p.target_axes.axis( (-642202.80, 245127.59, -496632.13, 246127.59) )
    
    p.update_plot_extents(p.target_axes)

    assert p.projection.corners_xy == pytest.approx((-642202.80, 245127.59, -496632.13, 246127.59))
    assert p.projection.corners_lonlat == pytest.approx((-132.5834, -121.7633, 40.22826, 47.17279))

    plt.close(p.target_axes.get_figure())
    

def test_AbstractPlot_on_update_plot_extent():
    p = AbstractPlotTest()
    p.projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    p.projection.corners_xy = [-645202.80, 248127.59, -499632.13, 248127.59]
    p.projection.corners_lonlat = [-132.6424, -121.7551, 40.2331, 47.1785]
    p.target_axes = plt.axes(projection=p.projection.crs)
    p.street_map = streetmap.HYSPLITMapBackground(p.projection)

    # See if no exception is thrown.
    try:
        p.on_update_plot_extent()
        plt.close(p.target_axes.get_figure())
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))
    pass

    
def test_AbstractPlot__make_labels_filename():
    p = AbstractPlotTest()
    assert p._make_labels_filename("ps") == "LABELS.CFG"
    assert p._make_labels_filename("pdf") == "LABELS.CFG"

    p.settings.process_id_set = True
    assert p._make_labels_filename("ps") == "LABELS.ps"
    assert p._make_labels_filename("pdf") == "LABELS.pdf"


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
  

def test_AbstractPlot_update_height_unit():
    p = AbstractPlotTest()
    o = labels.LabelsConfig()
    
    # check the default
    assert p.settings.height_unit == HeightUnit.METERS
    
    # test with "feet"
    o.cfg["ALTTD"] = "feet"
    p.update_height_unit(o)
    assert p.settings.height_unit == HeightUnit.FEET
    
    # test with "ft"
    o.cfg["ALTTD"] = "ft"
    p.update_height_unit(o)
    assert p.settings.height_unit == HeightUnit.FEET
    
    # test with "meters"
    o.cfg["ALTTD"] = "meters"
    p.update_height_unit(o)
    assert p.settings.height_unit == HeightUnit.METERS
    
    # test with "m"
    o.cfg["ALTTD"] = "m"
    p.update_height_unit(o)
    assert p.settings.height_unit == HeightUnit.METERS

    # test with "kg"
    o.cfg["ALTTD"] = "kg"
    try:
        p.update_height_unit(o)
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex).startswith("ALTTD units must be meters or feet")


def test_AbstractPlot__make_stationplot_filename():
    p = AbstractPlotTest()
    assert p._make_stationplot_filename("ps") == "STATIONPLOT.CFG"
    assert p._make_stationplot_filename("pdf") == "STATIONPLOT.CFG"

    p.settings.process_id_set = True
    assert p._make_stationplot_filename("ps") == "STATIONPLOT.ps"
    assert p._make_stationplot_filename("pdf") == "STATIONPLOT.pdf"


def test_AbstractPlot__draw_stations_if_exists():
    p = AbstractPlotTest()
    p.projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    p.projection.corners_xy = [1.0, 500.0, 1.0, 500.0]
    axes = plt.axes(projection=p.projection.crs)

    s = plotbase.AbstractPlotSettings()
    
    # See if no exception is thrown.
    try:
        p._draw_stations_if_exists(axes, s, "data/STATIONPLOT.CFG")
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))

    plt.close(axes.get_figure())
    

def test_AbstractPlot__draw_datem():
    p = AbstractPlotTest()
    p.projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    p.projection.corners_xy = [1.0, 500.0, 1.0, 500.0]
    axes = plt.axes(projection=p.projection.crs)

    s = plotbase.AbstractPlotSettings()
    
    d = datem.Datem().get_reader().read("data/meas-t1.txt")
    
    utc = pytz.utc
    dt1 = datetime.datetime(1983, 9, 18, 18, 0, 0, 0, utc)
    dt2 = datetime.datetime(1983, 9, 18, 21, 0, 0, 0, utc)

    # See if no exception is thrown.
    try:
        p._draw_datem(axes, s, d, dt1, dt2)
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))
      
    plt.close(axes.get_figure())


def test_AbstractPlot_make_maptext_filename():
    p = AbstractPlotTest()
    assert p._make_maptext_filename("ps") == "MAPTEXT.CFG"
    assert p._make_maptext_filename("pdf") == "MAPTEXT.CFG"

    p.settings.process_id_set = True
    assert p._make_maptext_filename("ps") == "MAPTEXT.ps"
    assert p._make_maptext_filename("pdf") == "MAPTEXT.pdf"


def test_AbstractPlot__draw_maptext_if_exists():
    p = plot.TrajectoryPlot() # need a concrete class
    #p = AbstractPlotTest()
    p.merge_plot_settings("data/default_tplot", ["-idata/tdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.layout(p.data_list)

    # See if no exception is thrown.
    try:
        p._draw_maptext_if_exists(p.text_axes, "data/MAPTEXT.CFG")
        p._draw_maptext_if_exists(p.text_axes, "data/MAPTEXT.CFG", lambda s, idx: True)
        p._draw_maptext_if_exists(p.text_axes, "data/MAPTEXT.CFG", lambda s, idx: True, vskip=0.100)
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))
 

def test_AbstractPlot__draw_alt_text_boxes():
    p = AbstractPlotTest()
    p.projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    p.projection.corners_xy = [1.0, 500.0, 1.0, 500.0]
    axes = plt.axes(projection=p.projection.crs)

    # See if no exception is thrown.
    try:
        p._draw_alt_text_boxes(axes, ["line 1", "line 2"])
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))
 

def test_AbstractPlot__draw_concentric_circles():
    p = AbstractPlotTest()
    p.projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    p.projection.corners_xy = [1.0, 500.0, 1.0, 500.0]
    axes = plt.axes(projection=p.projection.crs)

    try:
        p._draw_concentric_circles(axes, [-84.0, 35.0], 4, 100.0)
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))

    
def test_AbstractPlot__draw_noaa_logo():
    p = AbstractPlotTest()
    axes = plt.axes()
    
    try:
        p._draw_noaa_logo(axes)
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_AbstractPlot_adjust_for_time_zone():
    p = AbstractPlotTest()
    assert p.time_zone is None
    
    dt = datetime.datetime(2019, 7, 10, 14, 3, 0, 0, pytz.utc)
    
    p.time_zone = pytz.timezone("America/New_York")
    t = p.adjust_for_time_zone(dt)
    assert t.year        == 2019
    assert t.month       == 7
    assert t.day         == 10
    assert t.hour        == 10
    assert t.minute      == 3
    assert t.second      == 0
    assert t.tzinfo.zone == "America/New_York"


def test_AbstractPlot__create_plot_saver_list():
    p = AbstractPlotTest()
    
    p.settings.additional_output_formats = ["png", "tif"]
    
    plot_saver_list = p._create_plot_saver_list( p.settings )

    assert len(plot_saver_list) == 3
