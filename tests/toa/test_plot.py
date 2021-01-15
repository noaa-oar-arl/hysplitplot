# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_plot.py
#
# Performs unit tests on functions and class methods declared in toa/plot.py.
# ---------------------------------------------------------------------------

import datetime
import matplotlib.pyplot as plt
from matplotlib.contour import QuadContourSet
import numpy
import os
import pytest
import pytz
import xml.etree.ElementTree as ElementTree

from hysplitdata.const import HeightUnit
from hysplitdata.conc import model
from hysplitplot import const, labels, mapfile, mapproj, multipage, smooth, streetmap, util
from hysplitplot.conc import gisout, helper, plot as cplot 
from hysplitplot.toa import helper as thelper, plot


@pytest.fixture
def cdump():
    d = model.ConcentrationDump()
    r = model.ConcentrationDumpFileReader(d)
    r.read("data/cdump")
    return d


def blank_event_handler(event):
    # do nothing
    return


def cleanup_plot(p):
    if p.fig is not None:
        plt.close(p.fig)


def test_TimeOfArrivalPlotSettings___init__():
    s = plot.TimeOfArrivalPlotSettings()

    # test one option in the base class
    assert s.map_background == "../graphics/arlmap"
        
    assert s.input_file == "cdump"
    assert s.output_filename == "toaplot.ps"
    assert s.output_basename == "toaplot"
    
    assert s.pollutant_index == 1
    
    assert s.first_time_index == 1
    assert s.last_time_index == 9999
    assert s.time_index_step == 1
    assert s.contour_level_generator == const.ContourLevelGenerator.EXPONENTIAL_DYNAMIC
    assert s.QFILE == None
    assert s.source_label == "\u2606"
    assert s.this_is_test == 0
    assert s.LEVEL1 == 0
    assert s.LEVEL2 == 99999
    assert s.KMAP == const.ConcentrationMapType.TIME_OF_ARRIVAL
    assert s.KAVG == const.ConcentrationType.VERTICAL_AVERAGE
    assert s.NDEP == const.DepositionType.NONE
    assert s.show_max_conc == 0
    assert s.mass_unit == "mass"
    assert s.mass_unit_by_user == False
    assert s.CONADJ == 1.0 
    assert s.DEPADJ == 1.0
    assert s.IDYNC == 0
    assert s.KHEMIN == 0
    assert s.IZRO == 0
    assert s.NSSLBL == 0
    assert s.color == const.ConcentrationPlotColor.COLOR
    assert s.gis_alt_mode == const.GISOutputAltitude.CLAMPED_TO_GROUND
    assert s.KMLOUT == 0
    assert s.ring == False
    assert s.ring_number == -1
    assert s.ring_distance == 0.0
    assert s.center_loc == [0.0, 0.0]
    assert s.gis_output == const.GISOutput.NONE
    assert s.kml_option == const.KMLOption.NONE

    assert s.label_source == True
    assert s.source_label_color != None
    assert s.source_label_font_size > 0
    assert s.user_color == False
    assert s.user_label == False
    assert s.contour_levels is None
    assert s.contour_level_count == 4
    assert s.pollutant == ""
    assert s.SCALE == 1.0
    assert s.station_marker is not None
    assert s.station_marker_color != None
    assert s.station_marker_size > 0
    assert s.max_contour_legend_count == 5


def test_TimeOfArrivalPlotSettings_process_command_line_arguments():
    s = plot.TimeOfArrivalPlotSettings()

    # test with few options processed by the base class.
    s.process_command_line_arguments(["-j../graphics/else", "-z10"])
    assert s.map_background == "../graphics/else"
    assert s.zoom_factor == 0.90

    # test -m and -M
    s.map_projection = 0

    s.process_command_line_arguments(["-m1"])
    assert s.map_projection == 1
    
    s.process_command_line_arguments(["-M2"])
    assert s.map_projection == 2
    
    # test -a
    s.gis_output = 0
    s.process_command_line_arguments(["-a2"])
    assert s.gis_output == 10  # 1 or 2 are mapped to 10.
    
    # test -A
    s.kml_option = 0
    s.process_command_line_arguments(["-A3"])
    assert s.kml_option == 3
    
    # test internal change for the -a1 or -a2 options
    s.gis_output = 0
    s.process_command_line_arguments(["-a1"])
    assert s.gis_output == 10

    s.gis_output = 0
    s.process_command_line_arguments(["-a2"])
    assert s.gis_output == 10
    
    s.gis_output = 0
    s.process_command_line_arguments(["-a3"])
    assert s.gis_output == 3
    
    # test +a or +A
    s.gis_alt_mode = 0
    s.process_command_line_arguments(["+a1"])
    assert s.gis_alt_mode == 1
    
    s.process_command_line_arguments(["+A0"])
    assert s.gis_alt_mode == 0
        
    # test -b or -B
    s.LEVEL1 = None
    s.process_command_line_arguments(["-b1"])
    assert s.LEVEL1 == 1
    
    s.process_command_line_arguments(["-B2"])
    assert s.LEVEL1 == 2   

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
    assert s.input_file == "INPUT"
    
    s.process_command_line_arguments(["-ITEST_INPUT"])
    assert s.input_file == "TEST_INPUT"

    # input file override.
    s.process_command_line_arguments(["-icdump", "cdump_two", "cdump_three"])
    assert s.input_file == "cdump_three"

    # test -k or -K
    s.color = 0
    s.process_command_line_arguments(["-k1"])
    assert s.color == 1
    
    s.process_command_line_arguments(["-K2"])
    assert s.color == 2
    
    # test -l
    s.source_label = None
    s.process_command_line_arguments(["-l72"])
    assert s.source_label == "*"

    # test -L
    s.lat_lon_label_interval_option = 0
    s.lat_lon_label_interval = 0

    s.process_command_line_arguments(["-L1"])
    assert s.lat_lon_label_interval_option == 1

    s.process_command_line_arguments(["-L2:50"])
    assert s.lat_lon_label_interval_option == 2
    assert s.lat_lon_label_interval == 5.0

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

    # test -t or -T
    s.LEVEL1 = 0
    s.LEVEL2 = None
    s.process_command_line_arguments(["-t1"])
    assert s.LEVEL2 == 1
    
    s.process_command_line_arguments(["-T2"])
    assert s.LEVEL2 == 2   
        
    # test -v
    s.process_command_line_arguments(["-v10E+2:USER1:100050200+10E+3:USER2:100070200"])
    assert len(s.contour_levels) == 2
    assert s.contour_level_count == 2
    assert s.contour_level_generator == const.ContourLevelGenerator.USER_SPECIFIED
    
    # test -5
    s.KMLOUT = 0
    s.process_command_line_arguments(["-51"])
    assert s.KMLOUT == 1
    
    # test -8
    s.process_command_line_arguments(["-87"])
    assert s.IZRO == 7


def test_TimeOfArrivalPlotSettings_parse_source_label():
    s = plot.TimeOfArrivalPlotSettings()
    assert s.parse_source_label("72") == "*"


def test_TimeOfArrivalPlotSettings_parse_time_indices():
    s = plot.TimeOfArrivalPlotSettings()
    assert s.first_time_index == 1
    assert s.last_time_index == 9999
    assert s.time_index_step == 1
    
    s = plot.TimeOfArrivalPlotSettings()
    s.parse_time_indices("2:5")
    assert s.first_time_index == 2
    assert s.last_time_index == 5
    assert s.time_index_step == 1
    
    s = plot.TimeOfArrivalPlotSettings()
    s.parse_time_indices("15")
    assert s.first_time_index == 1
    assert s.last_time_index == 15
    assert s.time_index_step == 1
    
    s = plot.TimeOfArrivalPlotSettings()
    s.parse_time_indices("-5")
    assert s.first_time_index == 1
    assert s.last_time_index == 9999
    assert s.time_index_step == 5
    

def test_TimeOfArrivalPlotSettings_setup_contour_styles():
    s = plot.TimeOfArrivalPlotSettings()
    assert s.contour_level_generator != const.ContourLevelGenerator.USER_SPECIFIED
    assert s.user_color != True
    assert s.contour_level_count == 4
    
    s.setup_contour_styles()
    assert s.contour_level_generator == const.ContourLevelGenerator.USER_SPECIFIED
    assert s.user_color == True
    assert s.contour_level_count == 5
    assert len(s.contour_levels) == 5
    
    
def test_TimeOfArrivalPlotSettings_parse_contour_levels():
    s = plot.TimeOfArrivalPlotSettings()
    s.parse_contour_levels("1E3+100+10")
    assert s.user_color == False
    assert s.user_colors is None
    assert s.user_label == False
    assert len(s.contour_levels) == 3
    assert s.contour_level_count == 3
    # sorted in the increasing level
    assert s.contour_levels[0].level == pytest.approx(10.0)
    assert s.contour_levels[1].level == pytest.approx(100.0)
    assert s.contour_levels[2].level == pytest.approx(1000.0)
    
    
    s = plot.TimeOfArrivalPlotSettings()
    s.parse_contour_levels("10E+2:USER1+10E+3:USER2")
    assert s.user_color == False
    assert s.user_colors is None
    assert s.user_label == True
    a = s.contour_levels
    assert len(a) == 2
    assert s.contour_level_count == 2
    k = 0
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(1000.0)
    assert a[k].label == "USER1"
    k += 1
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(10000.0)
    assert a[k].label == "USER2"


    s = plot.TimeOfArrivalPlotSettings()
    s.parse_contour_levels("10E+2:USER1:100050200+10E+3:USER2:100070200")
    assert s.user_color == True
    assert s.user_colors is not None
    assert s.user_label == True
    a = s.contour_levels
    c = s.user_colors
    assert len(a) == 2
    assert s.contour_level_count == 2
    k = 0
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(1000.0)
    assert a[k].label == "USER1"
    assert c[k] == pytest.approx((0.392157, 0.196078, 0.784314), 1.0e-5)
    k += 1
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(10000.0)
    assert a[k].label == "USER2"
    assert c[k] == pytest.approx((0.392157, 0.274510, 0.784314), 1.0e-5)

    # hysplitcameo test case
    s = plot.TimeOfArrivalPlotSettings()
    s.parse_contour_levels("::000255255+::000255000+::000000255+::255255000+::255000000")
    assert s.user_color == True
    assert s.user_colors is not None
    assert s.user_label == True
    a = s.contour_levels
    c = s.user_colors
    assert len(a) == 5
    assert s.contour_level_count == 5
    k = 0
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level is None
    assert a[k].label == ""
    assert c[k] == pytest.approx((0.0, 1.0, 1.0), 1.0e-5)
    k += 4
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level is None
    assert a[k].label == ""
    assert c[k] == pytest.approx((1.0, 0.0, 0.0), 1.0e-5)


def test_TimeOfArrivalPlotSettings_sort_contour_levels_and_colors():
    s = plot.TimeOfArrivalPlotSettings()
    # parse_contour_levels() calls sort_contour_levels_and_colors().
    s.parse_contour_levels("1::000255255+2::000255000+3::000000255+4::255255000+5::255000000")
    assert s.contour_levels[0].level == 1
    assert s.user_colors[0] == pytest.approx((0.0, 1.0, 1.0))
    assert s.contour_levels[4].level == 5
    assert s.user_colors[4] == pytest.approx((1.0, 0.0, 0.0))
    # reverse the order of contour levels.
    s.parse_contour_levels("5::000255255+4::000255000+3::000000255+2::255255000+1::255000000")
    assert s.contour_levels[0].level == 1
    assert s.user_colors[0] == pytest.approx((1.0, 0.0, 0.0))
    assert s.contour_levels[4].level == 5
    assert s.user_colors[4] == pytest.approx((0.0, 1.0, 1.0))
    # without colors
    s.parse_contour_levels("1E3+100+10")
    assert s.contour_levels[0].level == 10
    assert s.contour_levels[1].level == 100
    assert s.contour_levels[2].level == 1000
    # reverse the listing order
    s.parse_contour_levels("10+100+1E3")
    assert s.contour_levels[0].level == 10
    assert s.contour_levels[1].level == 100
    assert s.contour_levels[2].level == 1000


def test_TimeOfArrivalPlotSettings_validate_contour_levels():
    s = plot.TimeOfArrivalPlotSettings()
    # without contour levels
    s.parse_contour_levels("::000255255+::000255000+::000000255+::255255000+::255000000")
    assert s.validate_contour_levels(s.contour_levels) == False 
    # with contour levels
    s.parse_contour_levels("1E3+100+10")
    assert s.validate_contour_levels(s.contour_levels)


def test_TimeOfArrivalPlotSettings_parse_simple_contour_levels():
    a = plot.TimeOfArrivalPlotSettings.parse_simple_contour_levels("1E3+100+10")
    assert a == pytest.approx([1000.0, 100.0, 10.0])


def test_TimeOfArrivalPlotSettings_parse_labeled_contour_levels():
    a, clrs, clr_set = plot.TimeOfArrivalPlotSettings.parse_labeled_contour_levels("10E+2:USER1:100050200+10E+3:USER2:100070200")
    assert len(a) == 2
    assert len(clrs) == 2
    assert clr_set == True
    
    k = 0
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(1000.0)
    assert a[k].label == "USER1"
    assert clrs[k] == pytest.approx((0.392157, 0.196078, 0.784314), 1.0e-5)
    
    k += 1
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(10000.0)
    assert a[k].label == "USER2"
    assert clrs[k] == pytest.approx((0.392157, 0.274510, 0.784314), 1.0e-5)
    
    # without labels
    a, clrs, clr_set = plot.TimeOfArrivalPlotSettings.parse_labeled_contour_levels("10E+2::100050200+10E+3::100070200")
    assert len(a) == 2
    assert len(clrs) == 2
    assert clr_set == True
    
    k = 0
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(1000.0)
    assert a[k].label == ""
    assert clrs[k] == pytest.approx((0.392157, 0.196078, 0.784314), 1.0e-5)
    
    k += 1
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(10000.0)
    assert a[k].label == ""
    assert clrs[k] == pytest.approx((0.392157, 0.274510, 0.784314), 1.0e-5)
  
    #without colors
    a, clrs, clr_set = plot.TimeOfArrivalPlotSettings.parse_labeled_contour_levels("10E+2:USER1+10E+3:USER2")
    assert len(a) == 2
    assert len(clrs) == 0
    assert clr_set == False
    
    k = 0
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(1000.0)
    assert a[k].label == "USER1"
    
    k += 1
    assert isinstance(a[k], plot.LabelledContourLevel)
    assert a[k].level == pytest.approx(10000.0)
    assert a[k].label == "USER2"


def test_TimeOfArrivalPlotSettings_get_reader():
    s = plot.TimeOfArrivalPlotSettings()
    r = s.get_reader()

    assert isinstance(r, plot.TimeOfArrivalPlotSettingsReader)
    assert r.settings is s  


def test_TimeOfArrivalPlotSettingsReader___init__():
    s = plot.TimeOfArrivalPlotSettings()
    r = plot.TimeOfArrivalPlotSettingsReader(s)

    assert r.settings is s


def test_TimeOfArrivalPlotSettingsReader_read():
    s = plot.TimeOfArrivalPlotSettings()
    r = plot.TimeOfArrivalPlotSettingsReader(s)

    o = r.read("data/default_cplot")
    assert isinstance(o, plot.TimeOfArrivalPlotSettings)

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
    

def test_TimeOfArrivalPlot___init__():
    p = plot.TimeOfArrivalPlot()

    assert hasattr(p, "settings")
    assert hasattr(p, "cdump")
    assert hasattr(p, "time_selector")
    assert hasattr(p, "level_selector")
    assert hasattr(p, "pollutant_selector")
    assert hasattr(p, "conc_type")
    assert hasattr(p, "conc_map")
    assert hasattr(p, "depo_map")
    assert hasattr(p, "prev_forecast_time")
    assert hasattr(p, "length_factory")
    assert hasattr(p, "toa_generator")

    assert hasattr(p, "fig")
    assert hasattr(p, "conc_outer")
    assert hasattr(p, "conc_axes")
    assert hasattr(p, "legends_axes")
    assert hasattr(p, "text_axes")
    assert hasattr(p, "plot_saver_list")

    assert hasattr(p, "TFACT")
    assert hasattr(p, "initial_time")
    assert hasattr(p, "contour_labels")
    assert p.current_frame == 1
    assert p.time_period_count == 0
    assert p.datem is None
    
    
def test_TimeOfArrivalPlot_merge_plot_settings():
    p = plot.TimeOfArrivalPlot()
    assert p.settings.map_projection != 4
    
    p.merge_plot_settings("data/default_cplot", ["-m4"])
    assert p.settings.map_projection == 4
    
    
def test_TimeOfArrivalPlot_get_street_map_target_axes():
    p = plot.TimeOfArrivalPlot()
    ax = plt.axes()
    p.conc_axes = ax
    assert p.get_street_map_target_axes() is ax
    plt.close(ax.get_figure())
    

def test_TimeOfArrivalPlot_read_data_files():
    p = plot.TimeOfArrivalPlot()
    p.merge_plot_settings(None, ["-idata/rsmc.cdump2", "--source-time-zone", "-qdata/meas-t1.txt"])

    p.read_data_files()

    assert p.settings.KAVG == const.ConcentrationType.VERTICAL_AVERAGE
    
    assert p.cdump is not None
    assert p.time_selector is not None
    assert p.time_selector.first == 0
    assert p.time_selector.last == 23 # clipped at the last index in the data.
    assert p.time_selector.step == 1
    assert p.pollutant_selector is not None
    assert p.pollutant_selector.index == 0
    assert p.level_selector is not None
    assert p.level_selector.min == 0
    assert p.level_selector.max == 99999
    assert p.conc_type is not None
    assert p.plot_saver_list is not None
    assert p.conc_map is not None
    assert p.depo_map is not None
    assert p.depo_sum is not None
    assert p.time_zone is not None
    assert p.datem is not None
    assert p.toa_generator is not None
    

def test_TimeOfArrivalPlot__post_file_processing(cdump):
    p = plot.TimeOfArrivalPlot()
    
    p.settings.first_time_index = 0
    p.settings.last_time_index = 0
    p.settings.pollutant_index = 0
    p.settings.KAVG = const.ConcentrationType.VERTICAL_AVERAGE
    
    p.time_selector = helper.TimeIndexSelector(p.settings.first_time_index,
                                               p.settings.last_time_index,
                                               p.settings.time_index_step)
    p.pollutant_selector = helper.PollutantSelector(p.settings.pollutant_index)
    p.level_selector = helper.VerticalLevelSelector(p.settings.LEVEL1, p.settings.LEVEL2)
    p.conc_type = helper.ConcentrationTypeFactory.create_instance(p.settings.KAVG)
       
    p._post_file_processing(cdump)
    
    assert p.conc_type.max_average * 1.0e+12 == pytest.approx(2.152324)
    assert p.conc_type.min_average * 1.0e+16 == pytest.approx(9.429794)
    

def test_TimeOfArrivalPlot__normalize_settings(cdump):
    p = plot.TimeOfArrivalPlot()
    s = p.settings
     
    s.LEVEL1 = -10
    s.LEVEL2 = 1000000
       
    assert s.height_unit == HeightUnit.METERS
    p.labels.cfg["ALTTD"] = "feet"

    p.contour_labels = None
    
    p._normalize_settings(cdump)

    assert s.LEVEL1 == 100
    assert s.LEVEL2 == 100
    
    assert s.height_unit == HeightUnit.FEET
    
    assert p.contour_labels is not None
    assert p.contour_labels == ["", "", "", ""]

    # check again with proper settings.contour_levels.
    p.contour_labels = None
    s.setup_contour_styles()
    assert s.contour_levels is not None
    
    p._normalize_settings(cdump)
    
    assert p.contour_labels is not None
    assert p.contour_labels == ["NONE", "NONE", "NONE", "NONE", "NONE"]

        
def test_TimeOfArrivalPlot__fix_map_color():
    p = plot.TimeOfArrivalPlot()

    color_mode = const.ConcentrationPlotColor.BLACK_AND_WHITE
    assert p._fix_map_color('#6699cc', color_mode) == 'k' # black

    color_mode = const.ConcentrationPlotColor.COLOR
    assert p._fix_map_color('#6699cc', color_mode) == '#6699cc'

    color_mode = const.ConcentrationPlotColor.BW_NO_LINES
    assert p._fix_map_color('#6699cc', color_mode) == 'k' # black

    color_mode = const.ConcentrationPlotColor.COLOR_NO_LINES
    assert p._fix_map_color('#6699cc', color_mode) == '#6699cc'


def test_TimeOfArrivalPlot_layout():
    p = plot.TimeOfArrivalPlot()
    p.merge_plot_settings(None, ["-idata/rsmc.cdump2"])
    p.read_data_files()
    p._initialize_map_projection(p.cdump)

    p.layout( p.cdump.grids[0], {"resize_event" : blank_event_handler} )

    assert p.fig is not None
    assert p.conc_outer is not None
    assert p.conc_axes is not None
    assert p.legends_axes is not None
    assert p.text_axes is not None

    cleanup_plot(p)


def test_TimeOfArrivalPlot_make_plot_title(cdump):
    g = cdump.grids[0]
    p = plot.TimeOfArrivalPlot()
    p.labels = labels.LabelsConfig()
    toa = thelper.PlumeTimeOfArrival(g)
    toa.starting_datetime = g.starting_datetime
    toa.ending_datetime = g.ending_datetime
    level1 = util.LengthInMeters(1.0)
    level2 = util.LengthInMeters(2.0)
    
    title = p.make_plot_title(toa, g, level1, level2)
    assert title == "NOAA HYSPLIT MODEL\n" + \
            "Time of arrival (h) averaged between 1 m and 2 m\n" + \
            "Integrated from 1700 25 Sep to 0500 26 Sep 1983 (UTC)\n" + \
            "TEST Release started at 1700 25 Sep 1983 (UTC)"

    # swap start and end datetimes
    toa.starting_datetime, toa.ending_datetime = toa.ending_datetime, toa.starting_datetime
    g.starting_datetime, g.ending_datetime = g.ending_datetime, g.starting_datetime
   
    title = p.make_plot_title(toa, g, level1, level2)
    assert title == "NOAA HYSPLIT MODEL\n" + \
            "Time of arrival (h) averaged between 1 m and 2 m\n" + \
            "Integrated from 0500 26 Sep to 1700 25 Sep 1983 (UTC) [backward]\n" + \
            "TEST Calculation started at 1700 25 Sep 1983 (UTC)"

    # set the time zone
    p.time_zone = pytz.timezone("EST")
    title = p.make_plot_title(toa, g, level1, level2)
    assert title == "NOAA HYSPLIT MODEL\n" + \
            "Time of arrival (h) averaged between 1 m and 2 m\n" + \
            "Integrated from 0000 26 Sep to 1200 25 Sep 1983 (EST) [backward]\n" + \
            "TEST Calculation started at 1200 25 Sep 1983 (EST)"   


def test_TimeOfArrivalPlot_make_ylabel(cdump):
    p = plot.TimeOfArrivalPlot()
    p.length_factory = util.LengthInMetersFactory()
    plotData = cdump
    
    # with one release location
    plotData.release_locs = [(30.00, 20.00)]
    label = p.make_ylabel(plotData, "*")
    assert label == "Source * at  20.00 N   30.00 E      from 10 m"

    # more than one release location
    plotData.release_locs = [(30.00, 20.00), (31.00, 21.00)]
    label = p.make_ylabel(plotData, "*")
    assert label == "Source * at multiple locations      from 10 m"

    # add release heights
    plotData.release_heights = [10, 500]
    label = p.make_ylabel(plotData, "*")
    assert label == "Source * at multiple locations      from 10 m to 500 m"


def test_TimeOfArrivalPlot_make_xlabel(cdump):
    p = plot.TimeOfArrivalPlot()
    p.cdump = cdump
    g = cdump.grids[0]
    
    assert p.make_xlabel(g) == "NARR METEOROLOGICAL DATA"

    g.ending_forecast_hr = 24
    p.prev_forecast_time = None
    assert p.make_xlabel(g) == "0500 25 Sep 1983 NARR FORECAST INITIALIZATION"
    
    g.ending_forecast_hr = 23
    assert p.make_xlabel(g) == "NARR METEOROLOGICAL DATA"

    assert p.make_xlabel(g) == "0600 25 Sep 1983 NARR FORECAST INITIALIZATION"
    

def test_TimeOfArrivalPlot__initialize_map_projection():
    p = plot.TimeOfArrivalPlot()
    p.merge_plot_settings(None, ["-idata/rsmc.cdump2"])
    p.read_data_files()

    assert p.street_map is None
    
    p._initialize_map_projection( p.cdump )

    assert isinstance(p.projection, mapproj.AbstractMapProjection)
    assert p.settings.center_loc == pytest.approx((150.98, -34.05))
    assert isinstance(p.street_map, streetmap.AbstractMapBackground)
    assert p.street_map.fix_map_color_fn is not None
    assert p.initial_corners_xy == pytest.approx((-754041.0, 3502343.0, -3111461.0, 1144922.0))
    assert p.initial_corners_lonlat == pytest.approx((138.7327, -176.2121, -60.67622, -18.70194))
    

def test_TimeOfArrivalPlot__create_map_box_instance():
    p = plot.TimeOfArrivalPlot()
    cdump = model.ConcentrationDump()
    cdump.grid_loc = [-84.0, 34.0]
    
    # case 1 - 5 degrees by 3 degress
    cdump.grid_sz = [10, 6]
    cdump.grid_deltas = [0.05, 0.05]
    mb = p._create_map_box_instance(cdump);
    assert mb.grid_delta == 0.1
    assert mb.grid_corner == [-84.0, 34.0]
    assert mb.sz == [5, 3]
    
    # case 2 - 4 degrees x 3 degrees
    cdump.grid_sz = [8, 6]
    cdump.grid_deltas = [0.5, 0.5]
    mb = p._create_map_box_instance(cdump);
    assert mb.grid_delta == 0.2
    assert mb.grid_corner == [-84.0, 34.0]
    assert mb.sz == [20, 15]

    # case 3 - 25 degrees x 20 degrees
    cdump.grid_sz = [50, 40]
    cdump.grid_deltas = [0.5, 0.5]
    mb = p._create_map_box_instance(cdump);
    assert mb.grid_delta == 1.0
    assert mb.grid_corner == [0.0, -90.0]
    assert mb.sz == [360, 181]
    

def test_TimeOfArrivalPlot__determine_map_limits(cdump):
    p = plot.TimeOfArrivalPlot()
    p.time_selector = helper.TimeIndexSelector()
    p.pollutant_selector = helper.PollutantSelector()
    p.level_selector = helper.VerticalLevelSelector()    
    
    mb = p._determine_map_limits(cdump, 2)

    assert mb.grid_corner== [0.0, -90.0]
    assert mb.grid_delta == 1.0
    assert mb.sz == [360, 181]
    assert mb.plume_sz == [4.0, 4.0]
    assert mb.plume_loc == [276, 130]

    nil_plot_data = model.ConcentrationDump()
    nil_plot_data.grid_deltas = (1.0, 1.0)
    nil_plot_data.grid_loc = (-84.0, 22.0)
    nil_plot_data.grid_sz = (2, 2)
    g = model.ConcentrationGrid(nil_plot_data)
    g.time_index = 0
    g.pollutant_index = 0
    g.vert_level_index = 0
    g.conc = numpy.zeros((2, 2))
    nil_plot_data.grids.append(g)
    try:
        mb2 = p._determine_map_limits(nil_plot_data, 2)
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "ALL concentrations are ZERO - no maps"


def test_TimeOfArrivalPlot_draw_toa_contour_plot():
    p = plot.TimeOfArrivalPlot()
    p.merge_plot_settings(None, ["-idata/rsmc.cdump2", "-jdata/arlmap_truncated"])
    p.read_data_files()
    
    # See if no exception is thrown.
    try:
        p._initialize_map_projection(p.cdump)
        p.layout(p.cdump.grids[0], {"resize_event" : blank_event_handler})
        color_table = cplot.ColorTableFactory.create_instance(p.settings)
        toa_data = p.toa_generator.make_plume_data(thelper.TimeOfArrival.DAY_0,
                                                   color_table.colors)
        
        contour_set = p.draw_toa_contour_plot(toa_data)
        
        assert isinstance(contour_set, QuadContourSet)
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_TimeOfArrivalPlot_get_conc_unit():
    p = plot.TimeOfArrivalPlot()
    p.labels = labels.LabelsConfig()
    p.conc_map = helper.ThresholdLevelsMap(1)
    s = p.settings
    
    # when both mass units and volume are specified in the labels.cfg
    p.labels.cfg["UNITS"] = "pg"
    p.labels.cfg["VOLUM"] = "/cm^3"
    s.mass_unit_by_user = False
    assert p.get_conc_unit(p.conc_map, s) == "pg/cm^3"
    
    # when the mass unit is specified by the user
    s.mass_unit = "kg"
    s.mass_unit_by_user = True
    assert p.get_conc_unit(p.conc_map, s) == "kg/cm^3"
    
    # no labels params.
    p.labels.cfg.clear()
    s.mass_unit = "ppm"
    s.mass_unit_by_user = False
    assert p.get_conc_unit(p.conc_map, s) == "ppm"
    
    
def test_TimeOfArrivalPlot__limit_contour_levels_for_legends():
    p = plot.TimeOfArrivalPlot()
    c = [0, 1, 3, 4, 5] # any list will do
    l = p._limit_contour_levels_for_legends(c, 3)
    assert len(l) == 3
    assert l[0] == 0
    assert l[2] == 3
    
    
def test_TimeOfArrivalPlot_draw_contour_legends():
    p = plot.TimeOfArrivalPlot()
    p.merge_plot_settings(None, ["-idata/rsmc.cdump2", "-jdata/arlmap_truncated"])
    p.read_data_files()
    
    # See if no exception is thrown.
    try:
        p._initialize_map_projection(p.cdump)
        p.layout(p.cdump.grids[0], {"resize_event" : blank_event_handler})
        p.draw_contour_legends(
            p.cdump.grids[0],
            p.conc_map,
            ["66-72 hours", "60-66 hours", "54-60 hours", "48-54 hours", "0-48 hours"],
            [1.0e-7, 40, 60, 80, 100, 120],
            ["b", "g", "y", "r", "k"])
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_TimeOfArrivalPlot_draw_bottom_text():
    p = plot.TimeOfArrivalPlot()
    p.merge_plot_settings(None, ["-idata/rsmc.cdump2", "-jdata/arlmap_truncated"])
    p.read_data_files()

    # See if no exception is thrown.
    try:
        p._initialize_map_projection(p.cdump)
        p.layout(p.cdump.grids[0], {"resize_event" : blank_event_handler})
        p.draw_bottom_text()
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_TimeOfArrivalPlot__write_gisout():
    p = plot.TimeOfArrivalPlot()
    p.merge_plot_settings(None, ["-idata/rsmc.cdump2", "-jdata/arlmap_truncated", "-a3", "+a0", "-A0"])
    p.read_data_files()
    
    p._initialize_map_projection(p.cdump)
    axes = plt.axes(projection=p.projection.crs)
    axes.axis(p.initial_corners_xy)
    
    color_table = plot.ColorTableFactory.create_instance(p.settings)
    gis_writer = gisout.GISFileWriterFactory.create_instance(p.settings.gis_output,
                                                             p.settings.kml_option)
    gis_writer.initialize(p.settings.gis_alt_mode,
                          p.settings.KMLOUT,
                          p.settings.output_suffix,
                          p.settings.KMAP,
                          p.settings.NSSLBL,
                          p.settings.show_max_conc,
                          const.DepositionType.NONE)
 
    toa_data = p.toa_generator.make_plume_data(thelper.TimeOfArrival.DAY_0, color_table.colors)
    lower_vert_level = util.LengthInMeters(0)
    upper_vert_level = util.LengthInMeters(500)
    scaling_factor = 1.0
    quad_contour_set = axes.contourf(toa_data.longitudes, toa_data.latitudes, toa_data.data,
                                     toa_data.contour_levels,
                                     colors=toa_data.fill_colors, extend="max",
                                     transform=p.data_crs)
    time_of_arrivals = [(18, 24), (12, 18), (6, 12), (0, 6)]
    
    if os.path.exists("HYSPLIT_ps.kml"):
        os.remove("HYSPLIT_ps.kml")
    if os.path.exists("GELABEL_ps.txt"):
        os.remove("GELABEL_ps.txt")
    
    p._write_gisout(gis_writer, toa_data.grid, lower_vert_level, upper_vert_level,
                    quad_contour_set, toa_data.contour_levels, color_table,
                    scaling_factor, time_of_arrivals)
    
    gis_writer.finalize()
    plt.close(axes.figure)
    
    assert os.path.exists("HYSPLIT_ps.kml")
    assert os.path.exists("GELABEL_ps.txt")
    
    # parse the XML document and check some elements.
    tree = ElementTree.parse("HYSPLIT_ps.kml")
    root = tree.getroot()
    name = root.find("./{http://www.opengis.net/kml/2.2}Document/{http://www.opengis.net/kml/2.2}name")
    assert name.text == "NOAA HYSPLIT RESULTS"
    
    os.remove("HYSPLIT_ps.kml")
    os.remove("GELABEL_ps.txt")


def test_TimeOfArrivalPlot_draw_toa_plot_above_ground():
    p = plot.TimeOfArrivalPlot()
    p.merge_plot_settings(None, ["-idata/rsmc.cdump2", "-jdata/arlmap_truncated", "-d1"])
    p.read_data_files()
    
    ctbl = cplot.ColorTableFactory.create_instance(p.settings)
    
    gis_writer = gisout.GISFileWriterFactory.create_instance(p.settings.gis_output,
                                                             p.settings.kml_option)
                                                             
    gis_writer.initialize(p.settings.gis_alt_mode,
                          p.settings.KMLOUT,
                          p.settings.output_suffix,
                          p.settings.KMAP,
                          p.settings.NSSLBL,
                          p.settings.show_max_conc,
                          const.DepositionType.NONE)
    
    toa_data = p.toa_generator.make_plume_data(thelper.TimeOfArrival.DAY_0,
                                               ctbl.colors)
        
    # See if no exception is thrown.
    try:
        p._initialize_map_projection(p.cdump)
        p.depo_sum.initialize(p.cdump.grids, p.time_selector, p.pollutant_selector)
        p.contour_labels = [""] * p.settings.contour_level_count
        p.draw_toa_plot_above_ground(toa_data,
                        {"resize_event" : blank_event_handler},
                        ctbl,
                        block=False)
        
        # with a gis writer
        p.draw_toa_plot_above_ground(toa_data,
                        {"resize_event" : blank_event_handler},
                        ctbl,
                        gis_writer,
                        block=False)       
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_TimeOfArrivalPlot_draw_toa_plot_on_ground():
    p = plot.TimeOfArrivalPlot()
    p.merge_plot_settings(None, ["-idata/rsmc.cdump2", "-jdata/arlmap_truncated", "-d1"])
    p.read_data_files()
    
    ctbl = cplot.ColorTableFactory.create_instance(p.settings)
    
    gis_writer = gisout.GISFileWriterFactory.create_instance(p.settings.gis_output,
                                                             p.settings.kml_option)
                                                             
    gis_writer.initialize(p.settings.gis_alt_mode,
                          p.settings.KMLOUT,
                          p.settings.output_suffix,
                          p.settings.KMAP,
                          p.settings.NSSLBL,
                          p.settings.show_max_conc,
                          const.DepositionType.NONE)
    
    toa_data = p.toa_generator.make_deposition_data(thelper.TimeOfArrival.DAY_0,
                                               ctbl.colors)
        
    # See if no exception is thrown.
    try:
        p._initialize_map_projection(p.cdump)
        p.depo_sum.initialize(p.cdump.grids, p.time_selector, p.pollutant_selector)
        p.contour_labels = [""] * p.settings.contour_level_count
        p.draw_toa_plot_on_ground(toa_data,
                        {"resize_event" : blank_event_handler},
                        ctbl,
                        block=False)
        
        # with a gis writer
        p.draw_toa_plot_on_ground(toa_data,
                        {"resize_event" : blank_event_handler},
                        ctbl,
                        gis_writer,
                        block=False)       
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_TimeOfArrivalPlot_draw():
    p = plot.TimeOfArrivalPlot()
    p.merge_plot_settings(None, ["-idata/rsmc.cdump2", "-jdata/arlmap_truncated"])
    p.read_data_files()
    
    # See if no exception is thrown.
    try:
        p._initialize_map_projection(p.cdump)
        p.contour_labels = [""] * p.settings.contour_level_count
        p.draw({"resize_event" : blank_event_handler}, block=False)
        assert p.time_period_count == 24
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))

    assert os.path.exists("toaplot.ps")
    os.remove("toaplot.ps")

    # Save to a file
    p.settings.interactive_mode = False
    plot_saver = multipage.PlotFileWriterFactory.create_instance(p.settings.frames_per_file,
                                                                 "__conc",
                                                                 "png",
                                                                 "png")
    p.plot_saver_list = [ plot_saver ]
    p.draw()
    # A previous call to draw() increased the current_frame value to 7.
    assert os.path.exists("__conc0007.png")
    assert os.path.exists("__conc0008.png")
    assert os.path.exists("__conc0009.png")
    assert os.path.exists("__conc0010.png")
    assert os.path.exists("__conc0011.png")
    assert os.path.exists("__conc0012.png")
    os.remove("__conc0007.png")
    os.remove("__conc0008.png")
    os.remove("__conc0009.png")
    os.remove("__conc0010.png")
    os.remove("__conc0011.png")
    os.remove("__conc0012.png")
    
    cleanup_plot(p)    


def test_TimeOfArrivalPlot_get_plot_count_str():
    p = plot.TimeOfArrivalPlot()
    p.toa_generator = thelper.TimeOfArrivalGenerator(None, None)
    
    plot_saver = multipage.SinglePlotFileWriter("test", "png", "png")
    p.plot_saver_list = [ plot_saver ]
    
    plot_saver.file_count = 7
    assert p.get_plot_count_str() == "7 output files"
    
    plot_saver.file_count = 1
    
    p.toa_generator.time_period_count = 1
    assert p.get_plot_count_str() == "1 time period"
    
    p.toa_generator.time_period_count = 2
    assert p.get_plot_count_str() == "2 time periods"

