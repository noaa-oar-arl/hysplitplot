import pytest
import matplotlib.pyplot as plt
import numpy
from hysplit4.conc import plot, model, prop
from hysplit4 import const, mapfile, mapproj, labels, smooth


@pytest.fixture
def cdump():
    s = plot.ConcentrationPlotSettings()
    d = model.ConcentrationDump()
    r = model.ConcentrationDumpFileReader(d)
    r.read("data/cdump")
    return d


@pytest.fixture
def cdump2():
    s = plot.ConcentrationPlotSettings()
    d = model.ConcentrationDump()
    r = model.ConcentrationDumpFileReader(d)
    r.read("data/cdump_two_pollutants")
    return d


@pytest.fixture
def contourLevels():
    c = []
    c.append(plot.LabelledContourLevel(10.0, "L1", 0.4, 0.4, 0.4))
    c.append(plot.LabelledContourLevel(15.0, "L2", 0.6, 0.6, 0.6))
    c.append(plot.LabelledContourLevel(20.0, "L3", 0.8, 0.8, 0.8))
    c.append(plot.LabelledContourLevel(25.0, "L4", 1.0, 1.0, 1.0))
    return c
    
    
def blank_event_handler(event):
    # do nothing
    return


def cleanup_plot(p):
    if p.fig is not None:
        plt.close(p.fig)
        

def test_ConcentrationPlotSettings___init__():
    s = plot.ConcentrationPlotSettings()

    # base class
    assert s.map_background == "../graphics/arlmap"
    assert s.map_projection == 0
    assert s.zoom_factor == 0.5
    assert s.ring == False
    assert s.ring_number == -1
    assert s.ring_distance == 0.0
    assert s.center_loc == [0.0, 0.0]
    #assert s.output_postscript == "trajplot.ps"
    assert s.output_suffix == "ps"
    #assert s.output_basename == "trajplot"
    assert s.noaa_logo == False
    assert s.lat_lon_label_interval_option == 1
    assert s.lat_lon_label_interval == 1.0
    assert s.frames_per_file == 0
    assert s.interactive_mode == True
    assert s.map_color == "#1f77b4"
    assert s.station_marker != None
    assert s.station_marker_color != None
    assert s.station_marker_size > 0
        
    assert s.input_file == "cdump"
    assert s.output_postscript == "concplot.ps"
    assert s.output_basename == "concplot"
    
    assert s.pollutant_index == 1
    assert s.first_time_index == 1
    assert s.last_time_index == 9999
    assert s.time_index_step == 1
    assert s.contour_level_generator == const.ContourLevelGenerator.EXPONENTIAL_DYNAMIC
    assert s.QFILE == "undefined"
    assert s.source_label == "\u2606"
    assert s.this_is_test == 0
    assert s.LEVEL1 == 0
    assert s.LEVEL2 == 99999
    assert s.exposure_unit == const.ExposureUnit.CONC
    assert s.KAVG == const.ConcentrationType.EACH_LEVEL
    assert s.NDEP == const.DepositionSum.TIME
    assert s.show_max_conc == 1
    assert s.default_mass_unit == "mass"
    assert s.smoothing_distance == 0
    assert s.CONADJ == 1.0 
    assert s.DEPADJ == 1.0
    assert s.UCMIN == 0.0
    assert s.UDMIN == 0.0
    assert s.IDYNC == 0
    assert s.KHEMIN == 0
    assert s.IZRO == 0
    assert s.NSSLBL == 0
    assert s.color == const.ConcentrationPlotColor.COLOR
    
    assert s.label_source == False
    assert s.source_marker != None
    assert s.source_marker_color != None
    assert s.source_marker_size > 0
    assert s.user_color == False
    assert s.user_label == False
    assert s.contour_levels is None
    assert s.contour_level_count == 4
    assert s.pollutant == ""
    assert s.SCALE == 1.0


def test_ConcentrationPlotSettings_process_command_line_arguments():
    s = plot.ConcentrationPlotSettings()

    # test with few options processed by the base class.
    s.process_command_line_arguments(["-j../graphics/else", "-z10"])
    assert s.map_background == "../graphics/else"
    assert s.zoom_factor == 0.90
    
    # test -c or -C
    s.contour_level_generator = 0
    s.process_command_line_arguments(["-c1"])
    assert s.contour_level_generator == 1
    
    s.process_command_line_arguments(["-C2"])
    assert s.contour_level_generator == 2

    # test -i or -I
    s.process_command_line_arguments(["-iINPUT"])
    assert s.input_file == "INPUT"
    
    s.process_command_line_arguments(["-ITEST_INPUT"])
    assert s.input_file == "TEST_INPUT"

    # test -l
    s.source_label = None
    s.process_command_line_arguments(["-l72"])
    assert s.source_label == "*"

    # test -k or -K
    s.color = 0
    s.process_command_line_arguments(["-k1"])
    assert s.color == 1
    
    s.process_command_line_arguments(["-K2"])
    assert s.color == 2
    
    # test +l
    s.this_is_test = 0
    s.process_command_line_arguments(["+l1"])
    assert s.this_is_test == 1

    # test -n or -N
    s.first_time_index = None
    s.last_time_index = None
    s.process_command_line_arguments(["-n1:2"])
    assert s.first_time_index == 0
    assert s.last_time_index == 1

    s.process_command_line_arguments(["-N2:3"])
    assert s.first_time_index == 1
    assert s.last_time_index == 2

    # test -q or -Q
    s.QFILE = None
    s.process_command_line_arguments(["-qNAME"])
    assert s.QFILE == "NAME"
    
    s.process_command_line_arguments(["-QNAME2"])
    assert s.QFILE == "NAME2"
    
    # test -s or -S
    s.pollutant_index = None
    s.process_command_line_arguments(["-s1"])
    assert s.pollutant_index == 0
    
    s.process_command_line_arguments(["-s2"])
    assert s.pollutant_index == 1
    
    # test -b or -B
    s.LEVEL1 = None
    s.process_command_line_arguments(["-b1"])
    assert s.LEVEL1 == 1
    
    s.process_command_line_arguments(["-B2"])
    assert s.LEVEL1 == 2   

    # test -t or -T
    s.LEVEL1 = 0
    s.LEVEL2 = None
    s.process_command_line_arguments(["-t1"])
    assert s.LEVEL2 == 1
    
    s.process_command_line_arguments(["-T2"])
    assert s.LEVEL2 == 2   
    
    # test -e or -E
    s.exposure_unit = None
    s.process_command_line_arguments(["-e1"])
    assert s.exposure_unit == 1
    
    s.process_command_line_arguments(["-E2"])
    assert s.exposure_unit == 2
        
    # test -d or -D
    s.KAVG = None
    s.process_command_line_arguments(["-d1"])
    assert s.KAVG == 1
    
    s.process_command_line_arguments(["-D2"])
    assert s.KAVG == 2
         
    # test -r or -R
    s.NDEP = None
    s.process_command_line_arguments(["-r1"])
    assert s.NDEP == 1
    
    s.process_command_line_arguments(["-R2"])
    assert s.NDEP == 2
          
    # test +m or +M
    s.show_max_conc = None
    s.process_command_line_arguments(["+m1"])
    assert s.show_max_conc == 1
    
    s.process_command_line_arguments(["+M2"])
    assert s.show_max_conc == 2   
    
    # test -u or -U
    s.default_mass_unit = None
    s.process_command_line_arguments(["-ukg"])
    assert s.default_mass_unit == "kg"
    
    s.process_command_line_arguments(["-Umg"])
    assert s.default_mass_unit == "mg"
    
    # test -w or -W
    s.smoothing_distance = None
    s.process_command_line_arguments(["-w1"])
    assert s.smoothing_distance == 1
    
    s.process_command_line_arguments(["-W2"])
    assert s.smoothing_distance == 2
    
    # test -x or -X
    s.CONADJ = None
    s.process_command_line_arguments(["-x1"])
    assert s.CONADJ == 1
    
    s.process_command_line_arguments(["-X2"])
    assert s.CONADJ == 2
     
    # test -y or -Y
    s.DEPADJ = None
    s.process_command_line_arguments(["-y1"])
    assert s.DEPADJ == 1
    
    s.process_command_line_arguments(["-Y2"])
    assert s.DEPADJ == 2
    
    # test -1, -2, -3, -4, -8, -9
    s.process_command_line_arguments(["-13.1", "-24.2", "-35", "-46", "-87", "-98"])
    assert s.UCMIN == 3.1
    assert s.UDMIN == 4.2
    assert s.IDYNC == 5
    assert s.KHEMIN == 6
    assert s.IZRO == 7
    assert s.NSSLBL == 8
    
    # test -v
    s.process_command_line_arguments(["-v10E+2:USER1:100050200+10E+3:USER2:100070200"])
    assert len(s.contour_levels) == 2
    assert s.contour_level_count == 2
    assert s.contour_level_generator == const.ContourLevelGenerator.USER_SPECIFIED


def test_ConcentrationPlotSettings_parse_source_label():
    s = plot.ConcentrationPlotSettings()
    assert s.parse_source_label("72") == "*"


def test_ConcentrationPlotSettings_parse_time_indices():
    s = plot.ConcentrationPlotSettings()
    assert s.first_time_index == 1
    assert s.last_time_index == 9999
    assert s.time_index_step == 1
    
    s = plot.ConcentrationPlotSettings()
    s.parse_time_indices("2:5")
    assert s.first_time_index == 2
    assert s.last_time_index == 5
    assert s.time_index_step == 1
    
    s = plot.ConcentrationPlotSettings()
    s.parse_time_indices("15")
    assert s.first_time_index == 1
    assert s.last_time_index == 15
    assert s.time_index_step == 1
    
    s = plot.ConcentrationPlotSettings()
    s.parse_time_indices("-5")
    assert s.first_time_index == 1
    assert s.last_time_index == 9999
    assert s.time_index_step == 5
    
    
def test_ConcentrationPlotSettings_parse_contour_levels():
    s = plot.ConcentrationPlotSettings()
    
    s.parse_contour_levels("1E3+100+10")
    assert s.user_color == False
    assert s.user_label == False
    assert len(s.contour_levels) == 3
    assert s.contour_level_count == 3
    assert s.contour_levels[0].level == pytest.approx(1000.0)
    assert s.contour_levels[1].level == pytest.approx(100.0)
    assert s.contour_levels[2].level == pytest.approx(10.0)
    
    s.parse_contour_levels("10E+2:USER1:100050200+10E+3:USER2:100070200")
    a = s.contour_levels
    assert len(a) == 2
    assert s.contour_level_count == 2
    k = 0
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(1000.0)
    assert a[k].label == "USER1"
    assert (a[k].r, a[k].g, a[k].b) == pytest.approx((0.392157, 0.196078, 0.784314), 1.0e-5)
    k += 1
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(10000.0)
    assert a[k].label == "USER2"
    assert (a[k].r, a[k].g, a[k].b) == pytest.approx((0.392157, 0.274510, 0.784314), 1.0e-5)


def test_ConcentrationPlotSettings_parse_simple_contour_levels():
    a = plot.ConcentrationPlotSettings.parse_simple_contour_levels("1E3+100+10")
    assert a == pytest.approx([1000.0, 100.0, 10.0])


def test_ConcentrationPlotSettings_parse_labeled_contour_levels():
    a = plot.ConcentrationPlotSettings.parse_labeled_contour_levels("10E+2:USER1:100050200+10E+3:USER2:100070200")
    assert len(a) == 2
    
    k = 0
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(1000.0)
    assert a[k].label == "USER1"
    assert (a[k].r, a[k].g, a[k].b) == pytest.approx((0.392157, 0.196078, 0.784314), 1.0e-5)
    
    k += 1
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(10000.0)
    assert a[k].label == "USER2"
    assert (a[k].r, a[k].g, a[k].b) == pytest.approx((0.392157, 0.274510, 0.784314), 1.0e-5)
    
    # without labels
    a = plot.ConcentrationPlotSettings.parse_labeled_contour_levels("10E+2::100050200+10E+3::100070200")
    assert len(a) == 2
    
    k = 0
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(1000.0)
    assert a[k].label == ""
    assert (a[k].r, a[k].g, a[k].b) == pytest.approx((0.392157, 0.196078, 0.784314), 1.0e-5)
    
    k += 1
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(10000.0)
    assert a[k].label == ""
    assert (a[k].r, a[k].g, a[k].b) == pytest.approx((0.392157, 0.274510, 0.784314), 1.0e-5)
  
    #without colors
    a = plot.ConcentrationPlotSettings.parse_labeled_contour_levels("10E+2:USER1+10E+3:USER2")
    assert len(a) == 2
    
    k = 0
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(1000.0)
    assert a[k].label == "USER1"
    assert (a[k].r, a[k].g, a[k].b) == pytest.approx((1.0, 1.0, 1.0), 1.0e-5)
    
    k += 1
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(10000.0)
    assert a[k].label == "USER2"
    assert (a[k].r, a[k].g, a[k].b) == pytest.approx((1.0, 1.0, 1.0), 1.0e-5)


def test_ConcentrationPlotSettings_get_reader():
    s = plot.ConcentrationPlotSettings()
    r = s.get_reader()

    assert isinstance(r, plot.ConcentrationPlotSettingsReader)
    assert r.settings is s  


def test_ConcentrationPlotSettingsReader___init__():
    s = plot.ConcentrationPlotSettings()
    r = plot.ConcentrationPlotSettingsReader(s)

    assert r.settings is s


def test_ConcentrationPlotSettingsReader_read():
    s = plot.ConcentrationPlotSettings()
    r = plot.ConcentrationPlotSettingsReader(s)

    o = r.read("data/default_cplot")
    assert isinstance(o, plot.ConcentrationPlotSettings)

    assert s.map_background == "../graphics/arlmap"
    assert s.map_projection == 0
    # num_polid, l 3
    assert s.zoom_factor == 0.50
    assert s.color == 1
    # cval, l 6
    # fixed, l 7
    # cscale, l 8
    # dscale, l 9
    # smooth, l 10
    # remove, l 11
    # expose, l 12
    # frame, l 13
    # mass, l 14
    assert s.ring == False
    assert s.map_center == 0
    assert s.ring_number == 4
    assert s.ring_distance == 100.0
    # qpnt, l 19
    assert s.center_loc == [-84.22, 39.90]
    

def test_ConcentrationPlot___init__():
    p = plot.ConcentrationPlot()

    assert p.MAX_CONTOUR_LEVELS == 32
    
    assert hasattr(p, "settings")
    assert hasattr(p, "cdump")
    assert hasattr(p, "data_properties")
    assert hasattr(p, "time_selector")
    assert hasattr(p, "level_selector")
    assert hasattr(p, "pollutant_selector")
    assert hasattr(p, "smoothing_kernel")

    assert hasattr(p, "fig")
    assert hasattr(p, "conc_outer")
    assert hasattr(p, "conc_axes")
    assert hasattr(p, "legends_axes")
    assert hasattr(p, "text_axes")

def test_ConcentrationPlot_merge_plot_settings():
    p = plot.ConcentrationPlot()

    p.merge_plot_settings("data/default_cplot", ["-m4"])

    assert p.settings.map_projection == 4

    
def test_ConcentrationPlot_update_gridlines():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.read_background_map()
    p.layout()

    # See if no exception is thrown.
    try:
        p.update_gridlines()
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_ConcentrationPlot_read_data_files():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump", "-w1", "-d2"])

    p.read_data_files()

    # -d2 should be changed to -d1
    assert p.settings.KAVG == const.ConcentrationType.EACH_LEVEL
    
    assert p.cdump is not None
    assert p.time_selector is not None
    assert p.time_selector.first == 0
    assert p.time_selector.last == 0 # clipped at the last index in the data.
    assert p.time_selector.step == 1
    assert p.pollutant_selector is not None
    assert p.pollutant_selector.index == 0
    assert p.level_selector is not None
    assert p.level_selector.min == 0
    assert p.level_selector.max == 99999
    assert p.data_properties is not None
    assert p.data_properties.max_average == 0.0 # not set for -d1
    assert p.data_properties.min_average == 1.0e+25 # not set for -d1
    assert p.data_properties.max_concs[0] * 1.e+12 == pytest.approx(2.152324)
    assert p.data_properties.min_concs[0] * 1.e+16 == pytest.approx(9.429794)
    assert p.smoothing_kernel is not None


def test_ConcentrationPlot__post_file_processing(cdump2):
    p = plot.ConcentrationPlot()
    
    p.settings.first_time_index = 0
    p.settings.last_time_index = 0
    p.settings.pollutant_index = 0
    p.settings.KAVG = const.ConcentrationType.VERTICAL_AVERAGE
    
    p.time_selector = prop.TimeIndexSelector(p.settings.first_time_index,
                                             p.settings.last_time_index,
                                             p.settings.time_index_step)
    p.pollutant_selector = prop.PollutantSelector(p.settings.pollutant_index)
    p.level_selector = prop.VerticalLevelSelector(p.settings.LEVEL1, p.settings.LEVEL2)

    q = p._post_file_processing(cdump2)
    
    assert q.max_average * 1.e+13 == pytest.approx(7.991718)
    assert q.min_average * 1.e+16 == pytest.approx(6.242119)
    
    assert q.min_concs[0] * 1.e+16 == pytest.approx(13.959413)
    assert q.max_concs[0] * 1.e+13 == pytest.approx( 8.173024)


def test_ConcentrationPlot__normalize_settings(cdump2):
    p = plot.ConcentrationPlot()
    s = p.settings
    
    s.LEVEL1 = -10
    s.LEVEL2 = 1000000
    
    s.contour_level_generator = 5
    s.UCMIN = 1.0
    s.UDMIN = 2.0
    
    s.exposure_unit = 10
    
    p._normalize_settings(cdump2)

    assert s.LEVEL1 == 100
    assert s.LEVEL2 == 300
    
    assert s.UCMIN == 0.0
    assert s.UDMIN == 0.0
    
    assert s.KMAP == 11
    
    # check with other exposure_unit values
    s.exposure_unit = const.ExposureUnit.CHEM_THRESHOLDS
    p._normalize_settings(cdump2)
    assert s.KMAP == const.ConcentrationMapType.THRESHOLD_LEVELS #4
    
    s.exposure_unit = const.ExposureUnit.VA
    p._normalize_settings(cdump2)
    assert s.KMAP == const.ConcentrationMapType.VOCANIC_ERUPTION #5
    
    s.exposure_unit = const.ExposureUnit.VAL_4
    p._normalize_settings(cdump2)
    assert s.KMAP == const.ConcentrationMapType.MASS_LOADING #


def test_ConcentrationPlot__fix_map_color():
    p = plot.ConcentrationPlot()

    color_mode = const.ConcentrationPlotColor.BLACK_AND_WHITE
    assert p._fix_map_color('#6699cc', color_mode) == 'k' # black

    color_mode = const.ConcentrationPlotColor.COLOR
    assert p._fix_map_color('#6699cc', color_mode) == '#6699cc'


def test_ConcentrationPlot_read_background_map():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-jdata/arlmap_truncated"])

    crs = p.read_background_map()

    assert p.background_maps is not None
    assert len(p.background_maps) > 0
    assert isinstance(p.background_maps[0], mapfile.DrawableBackgroundMap)
    assert p.background_maps[0].map.crs == mapproj.MapProjection._WGS84


def test_ConcentrationPlot_layout():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump"])
    p.read_data_files()

    p.layout( {"resize_event" : blank_event_handler} )

    assert p.fig is not None
    assert p.conc_outer is not None
    assert p.conc_axes is not None
    assert p.legends_axes is not None
    assert p.text_axes is not None

    cleanup_plot(p)


def test_ConcentrationPlot_make_plot_title(cdump):
    plotData = cdump.conc_grids[0]
    p = plot.ConcentrationPlot()
    p.labels = labels.LabelsConfig()
    
    title = p.make_plot_title(plotData)
    assert title == "NOAA HYSPLIT MODEL\n" + \
            "TODO\n" + \
            "Integrated from 1700 25 Sep to 0500 26 Sep 83 (UTC)\n" + \
            "TEST Release started at 1700 25 Sep 83 (UTC)"

    # swap start and end datetimes
    plotData.starting_datetime, plotData.ending_datetime = plotData.ending_datetime, plotData.starting_datetime
    
    title = p.make_plot_title(plotData)
    assert title == "NOAA HYSPLIT MODEL\n" + \
            "TODO\n" + \
            "Integrated from 0500 26 Sep to 1700 25 Sep 83 (UTC) [backward]\n" + \
            "TEST Calculation started at 1700 25 Sep 83 (UTC)"


def test_ConcentrationPlot_make_ylabel(cdump):
    p = plot.ConcentrationPlot()
    plotData = cdump
    
    # with one release location
    plotData.release_locs = [(30.00, 20.00)]
    label = plot.ConcentrationPlot.make_ylabel(plotData, "*")
    assert label == "Source * at  20.00 N   30.00 E      from 10 m"

    # more than one release location
    plotData.release_locs = [(30.00, 20.00), (31.00, 21.00)]
    label = plot.ConcentrationPlot.make_ylabel(plotData, "*")
    assert label == "Source * at multiple locations      from 10 m"

    # add release heights
    plotData.release_heights = [10, 500]
    label = plot.ConcentrationPlot.make_ylabel(plotData, "*")
    assert label == "Source * at multiple locations      from 10 to 500 m"


def test_ConcentrationPlot__initialize_map_projection():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump"])
    p.read_data_files()

    p._initialize_map_projection()

    assert isinstance(p.projection, mapproj.MapProjection)
    assert p.crs is not None


def test_ConcentrationPlot__determine_map_limits(cdump):
    p = plot.ConcentrationPlot()

    mb = p._determine_map_limits(cdump, 2)

    assert mb.grid_corner== [0.0, -90.0]
    assert mb.grid_delta == 1.0
    assert mb.sz == [360, 181]
    assert mb.plume_sz == [4.0, 5.0]
    assert mb.plume_loc == [275, 129]

    nil_plot_data = model.ConcentrationDump()

    try:
        mb2 = p._determine_map_limits(nil_plot_data, 2)
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "no concentration data to plot"


def test_ConcentrationPlot_draw_concentration_plot():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.read_background_map()
    
    # See if no exception is thrown.
    try:
        p.layout({"resize_event" : blank_event_handler})
        p.draw_concentration_plot(p.cdump.conc_grids[0],
                                  p.cdump.conc_grids[0].conc,
                                  [1.0e-16, 1.0e-15, 1.0e-14],
                                  ["g", "b", "r"])
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_ConcentrationPlot_draw_contour_legends():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.read_background_map()

    # See if no exception is thrown.
    try:
        p.layout({"resize_event" : blank_event_handler})
        p.draw_contour_legends()
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_ConcentrationPlot_draw_bottom_text():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.read_background_map()

    # See if no exception is thrown.
    try:
        p.layout({"resize_event" : blank_event_handler})
        p.draw_bottom_text()
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_ConcentrationPlot_draw():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    p.read_background_map()
    
    # See if no exception is thrown.
    try:
        p.layout({"resize_event" : blank_event_handler})
        p.draw(block=False)
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_LabelledContourLevel___init__():
    o = plot.LabelledContourLevel(10.0, "USER1", 0.5, 0.6, 0.7)
    assert o.level == 10.0
    assert o.label == "USER1"
    assert o.r == 0.5
    assert o.g == 0.6
    assert o.b == 0.7


def test_ContourLevelGeneratorFactory_create_instance(contourLevels):
    o = plot.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.EXPONENTIAL_DYNAMIC, None, None)
    assert isinstance(o, plot.ExponentialDynamicLevelGenerator)
    
    o = plot.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.EXPONENTIAL_FIXED, None, None)
    assert isinstance(o, plot.ExponentialFixedLevelGenerator)
    
    o = plot.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.LINEAR_DYNAMIC, None, None)
    assert isinstance(o, plot.LinearDynamicLevelGenerator)
    
    o = plot.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.LINEAR_FIXED, None, None)
    assert isinstance(o, plot.LinearFixedLevelGenerator)
    
    o = plot.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.USER_SPECIFIED, contourLevels, None)
    assert isinstance(o, plot.UserSpecifiedLevelGenerator)
    
    try:
        o = plot.ContourLevelGeneratorFactory.create_instance(100000, None, None)
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "unknown method 100000 for contour level generation"


def test_AbstractContourLevelGenerator___init__():
    o = plot.AbstractContourLevelGenerator()
    assert o is not None
    

def test_ExponentialDynamicLevelGenerator___init__():
    o = plot.ExponentialDynamicLevelGenerator()
    assert o is not None


def test_ExponentialDynamicLevelGenerator_make_levels():
    o = plot.ExponentialDynamicLevelGenerator()
    
    levels = o.make_levels(1.0e-16, 1.0e-13, 4)
    
    levels *= 1.e+16
    assert levels == pytest.approx((0.01, 1.0, 100.0, 1000.0))
    

def test_EExponentialFixedLevelGenerator___init__():
    o = plot.ExponentialFixedLevelGenerator()
    assert o is not None


def test_ExponentialFixedLevelGenerator_make_levels():
    o = plot.ExponentialFixedLevelGenerator()
    
    levels = o.make_levels(1.0e-16, 1.0e-13, 4)
    
    levels *= 1.e+16
    assert levels == pytest.approx((0.01, 1.0, 100.0, 1000.0))
    

def test_LinearDynamicLevelGenerator___init__():
    o = plot.LinearDynamicLevelGenerator()
    assert o is not None


def test_LinearDynamicLevelGenerator_make_levels():
    o = plot.LinearDynamicLevelGenerator()
    
    levels = o.make_levels(1.0, 10.0, 4)
    
    assert levels == pytest.approx((2., 4., 6., 8.))
    

def test_LinearFixedLevelGenerator___init__():
    o = plot.LinearFixedLevelGenerator()
    assert o is not None


def test_LinearFixedLevelGenerator_make_levels():
    o = plot.LinearFixedLevelGenerator()
    
    levels = o.make_levels(1.0, 10.0, 4)
    
    assert levels == pytest.approx((2., 4., 6., 8.))
    
    
def test_UserSpecifiedLevelGenerator___init__(contourLevels):
    o = plot.UserSpecifiedLevelGenerator(contourLevels)
    assert o is not None
    assert len(contourLevels) == 4
    assert len(o.contour_levels) == 4


def test_UserSpecifiedLevelGenerator_make_levels(contourLevels):
    o = plot.UserSpecifiedLevelGenerator(contourLevels)
    
    levels = o.make_levels(1.0, 10.0, 4)
    
    assert levels == pytest.approx((10., 15., 20., 25.))
    

def test_ColorTableFactory():
    p = plot.ColorTableFactory()
    assert len(p.COLOR_TABLE_FILE_NAMES) == 2


def test_ColorTableFactory_create_instance():
    p = plot.ConcentrationPlot()
    s = p.settings
    
    saved = plot.ColorTableFactory.COLOR_TABLE_FILE_NAMES
    plot.ColorTableFactory.COLOR_TABLE_FILE_NAMES = ["data/CLRTBL.CFG"]

    s.KMAP = const.ConcentrationMapType.THRESHOLD_LEVELS
    s.KHEMIN = 1
    ct = plot.ColorTableFactory.create_instance(s)
    assert isinstance(ct, plot.DefaultChemicalThresholdColorTable)
    
    s.KMAP = const.ConcentrationMapType.CONCENTRATION
    s.user_color = True
    s.parse_contour_levels("10E+2:USER1:100050200+10E+3:USER2:100070200")
    ct = plot.ColorTableFactory.create_instance(s)
    assert isinstance(ct, plot.UserColorTable)
    
    s.user_color = False
    ct = plot.ColorTableFactory.create_instance(s)
    assert isinstance(ct, plot.DefaultColorTable)
    
    # check conversion to grayscale table
    s.color = const.ConcentrationPlotColor.BLACK_AND_WHITE
    ct = plot.ColorTableFactory.create_instance(s)
    assert isinstance(ct, plot.DefaultColorTable)
    for rgb in ct.rgbs:
        r, g, b = rgb
        assert r == g and g == b

    plot.ColorTableFactory.COLOR_TABLE_FILE_NAMES = saved


def test_ConcentrationPlot__get_color_table_filename():
    p = plot.ColorTableFactory()
    assert p._get_color_table_filename() == None

    saved = plot.ColorTableFactory.COLOR_TABLE_FILE_NAMES
    plot.ColorTableFactory.COLOR_TABLE_FILE_NAMES = ["data/CLRTBL.CFG"]
    assert p._get_color_table_filename() == "data/CLRTBL.CFG"
    plot.ColorTableFactory.COLOR_TABLE_FILE_NAMES = saved

    
def test_ColorTable___init__():
    o = plot.ColorTable()
    assert hasattr(o, "colors")
    assert hasattr(o, "rgbs")


def test_ColorTable_get_reader():
    o = plot.ColorTable()
    r = o.get_reader()
    assert isinstance(r, plot.ColorTableReader)
    assert r.color_table is o


def test_ColorTable_set_rgb():
    o = plot.ColorTable()
    o.rgbs = [(0,0,0), (.5, .5, .5)]
    
    o.set_rgb(0, (.2, .2, .2))
    assert o.rgbs[0] == pytest.approx((0.2, 0.2, 0.2))
    

def test_ColorTable_change_to_grayscale():
    o = plot.ColorTable()
    o.rgbs = [(0,0,0), (.5, .6, .7)]
    
    o.change_to_grayscale()
    
    assert o.rgbs[0] == pytest.approx((0.0, 0.0, 0.0))
    assert o.rgbs[1] == pytest.approx((0.6402, 0.6402, 0.6402))
    

def test_ColorTable_get_luminance():
    o = plot.ColorTable()
    
    assert o.get_luminance((0.5, 0.6, 0.7)) == pytest.approx(0.6402)


def test_ColorTable_colors():
    o = plot.ColorTable()
    o.rgbs = [(0,0,0), (.5, .5, .5)]
    
    assert o.colors == ["#000000", "#808080"]


def test_ColorTable_create_plot_colors():
    clrs = plot.ColorTable.create_plot_colors([(.5, .5, .5), (1., 1., 1.)])
    assert len(clrs) == 2
    assert clrs[0] == "#808080"
    assert clrs[1] == "#ffffff"
    

def test_DefaultColorTable_colors___init__():
    o = plot.DefaultColorTable()
    assert len(o.rgbs) == 32
    assert o.rgbs[3] == pytest.approx((0.0, 1.0, 0.0))
    

def test_DefaultChemicalThresholdColorTable___init__():
    o = plot.DefaultChemicalThresholdColorTable()
    assert len(o.rgbs) == 32
    assert o.rgbs[3] == pytest.approx((1.0, 0.5, 0.0))
    

def test_UserColorTable___init__(contourLevels):
    o = plot.UserColorTable(contourLevels)
    assert len(o.rgbs) == 4
    assert o.rgbs[0] == pytest.approx((0.4, 0.4, 0.4))


def test_ColorTableReader___init__():
    tbl = plot.DefaultColorTable()
    o = plot.ColorTableReader(tbl)
    assert o.color_table is tbl
    

def test_ColorTableReader_read():
    tbl = plot.DefaultColorTable()
    o = plot.ColorTableReader(tbl)
    tbl2 = o.read("data/CLRTBL.CFG")
    assert tbl2 is tbl
    assert tbl2.rgbs[20] == pytest.approx((153.0/255.0, 0, 0))
    

def test_ContourColorFactory_create_instance():
    tbl = plot.ColorTable().get_reader().read("data/CLRTBL.CFG")
    o = plot.ContourColorFactory.create_instance(tbl)
    assert isinstance(o, plot.ContourColor)
    assert len(o.colors) == 4


def test_ContourColor___init__():
    tbl = plot.ColorTable().get_reader().read("data/CLRTBL.CFG")

    o = plot.ContourColor(tbl)    
    assert len(o.colors) == 4