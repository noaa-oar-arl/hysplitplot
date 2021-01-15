# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_plot.py
#
# Performs unit tests on functions and class methods declared in conc/plot.py.
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
from hysplitplot.conc import gisout, helper, plot


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
    c.append(plot.LabelledContourLevel(10.0, "L1"))
    c.append(plot.LabelledContourLevel(15.0, "L2"))
    c.append(plot.LabelledContourLevel(20.0, "L3"))
    c.append(plot.LabelledContourLevel(25.0, "L4"))
    return c


@pytest.fixture
def userColors():
    c = []
    c.append((0.4, 0.4, 0.4))
    c.append((0.5, 0.5, 0.5))
    c.append((0.6, 0.6, 0.6))
    c.append((0.7, 0.7, 0.7))
    return c


def blank_event_handler(event):
    # do nothing
    return


def cleanup_plot(p):
    if p.fig is not None:
        plt.close(p.fig)

# declare concrete classes below to test their corresponding abstract class.

class AbstractContourLevelGeneratorTest(plot.AbstractContourLevelGenerator):
    
    def make_levels(self, min_conc, max_conc, max_levels):
        pass
    
    def compute_color_table_offset(self, levels):
        return 0
    

class AbstractColorTableTest(plot.AbstractColorTable):
    
    def __init__(self, ncolors, color_opacity=100):
        super(AbstractColorTableTest, self).__init__(ncolors, color_opacity)
        
    @property
    def raw_colors(self):
        pass
    
    @property
    def colors(self):
        pass
    
    
def test_ConcentrationPlotSettings___init__():
    s = plot.ConcentrationPlotSettings()

    assert s.input_file == "cdump"
    assert s.output_filename == "concplot.ps"
    assert s.output_basename == "concplot"
    
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
    assert s.exposure_unit == const.ExposureUnit.CONCENTRATION
    assert s.KMAP == const.ConcentrationMapType.CONCENTRATION
    assert s.KAVG == const.ConcentrationType.EACH_LEVEL
    assert s.NDEP == const.DepositionType.TIME
    assert s.show_max_conc == 1
    assert s.mass_unit == "mass"
    assert s.mass_unit_by_user == False
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
    assert s.max_contour_legend_count == 25
    

def test_ConcentrationPlotSettings_process_command_line_arguments():
    s = plot.ConcentrationPlotSettings()

    # test -m and -M
    s.map_projection = 0

    s.process_command_line_arguments(["-m1"])
    assert s.map_projection == 1
    
    s.process_command_line_arguments(["-M2"])
    assert s.map_projection == 2
    
    # test with few options processed by the base class.
    s.process_command_line_arguments(["-j../graphics/else", "-z10"])
    assert s.map_background == "../graphics/else"
    assert s.zoom_factor == 0.90

    # test -a
    s.gis_output = 0
    s.process_command_line_arguments(["-a2"])
    assert s.gis_output == 2
    
    # test -A
    s.kml_option = 0
    s.process_command_line_arguments(["-A3"])
    assert s.kml_option == 3

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

    # test -c or -C
    s.contour_level_generator = 0
    s.process_command_line_arguments(["-c1"])
    assert s.contour_level_generator == 1
    
    s.process_command_line_arguments(["-C2"])
    assert s.contour_level_generator == 2

    # test -d or -D
    s.KAVG = None
    s.process_command_line_arguments(["-d1"])
    assert s.KAVG == 1
    
    s.process_command_line_arguments(["-D2"])
    assert s.KAVG == 2
   
    # test -e or -E
    s.exposure_unit = None
    s.process_command_line_arguments(["-e1"])
    assert s.exposure_unit == 1
    
    s.process_command_line_arguments(["-E2"])
    assert s.exposure_unit == 2
 
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
    
    # test +l
    s.this_is_test = 0
    s.process_command_line_arguments(["+l1"])
    assert s.this_is_test == 1

    # test -L
    s.lat_lon_label_interval_option = 0
    s.lat_lon_label_interval = 0

    s.process_command_line_arguments(["-L1"])
    assert s.lat_lon_label_interval_option == 1

    s.process_command_line_arguments(["-L2:50"])
    assert s.lat_lon_label_interval_option == 2
    assert s.lat_lon_label_interval == 5.0
          
    # test +m or +M
    s.show_max_conc = None
    s.process_command_line_arguments(["+m1"])
    assert s.show_max_conc == 1
    
    s.process_command_line_arguments(["+M2"])
    assert s.show_max_conc == 2   

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
            
    # test -r or -R
    s.NDEP = None
    s.process_command_line_arguments(["-r1"])
    assert s.NDEP == 1
    
    s.process_command_line_arguments(["-R2"])
    assert s.NDEP == 2
  
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
   
    # test -u or -U
    s.mass_unit = None
    s.mass_unit_by_user = False
    s.process_command_line_arguments(["-ukg"])
    assert s.mass_unit == "kg"
    assert s.mass_unit_by_user == True
    
    s.mass_unit = None
    s.mass_unit_by_user = False
    s.process_command_line_arguments(["-Umg"])
    assert s.mass_unit == "mg"
    assert s.mass_unit_by_user == True
       
    # test -v
    s.process_command_line_arguments(["-v10E+2:USER1:100050200+10E+3:USER2:100070200"])
    assert len(s.contour_levels) == 2
    assert s.contour_level_count == 2
    assert s.contour_level_generator == const.ContourLevelGenerator.USER_SPECIFIED
 
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

    # test -5
    s.KMLOUT = 0
    s.process_command_line_arguments(["-51"])
    assert s.KMLOUT == 1


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
    assert s.user_colors is None
    assert s.user_label == False
    assert len(s.contour_levels) == 3
    assert s.contour_level_count == 3
    # sorted in the increasing level
    assert s.contour_levels[0].level == pytest.approx(10.0)
    assert s.contour_levels[1].level == pytest.approx(100.0)
    assert s.contour_levels[2].level == pytest.approx(1000.0)
    
    
    s = plot.ConcentrationPlotSettings()
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


    s = plot.ConcentrationPlotSettings()
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
    s = plot.ConcentrationPlotSettings()
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


def test_ConcentrationPlotSettings_sort_contour_levels_and_colors():
    s = plot.ConcentrationPlotSettings()
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


def test_ConcentrationPlotSettings_validate_contour_levels():
    s = plot.ConcentrationPlotSettings()
    # without contour levels
    s.parse_contour_levels("::000255255+::000255000+::000000255+::255255000+::255000000")
    assert s.validate_contour_levels(s.contour_levels) == False 
    # with contour levels
    s.parse_contour_levels("1E3+100+10")
    assert s.validate_contour_levels(s.contour_levels)


def test_ConcentrationPlotSettings_parse_simple_contour_levels():
    a = plot.ConcentrationPlotSettings.parse_simple_contour_levels("1E3+100+10")
    assert a == pytest.approx([1000.0, 100.0, 10.0])


def test_ConcentrationPlotSettings_parse_labeled_contour_levels():
    a, clrs, clr_set = plot.ConcentrationPlotSettings.parse_labeled_contour_levels("10E+2:USER1:100050200+10E+3:USER2:100070200")
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
    a, clrs, clr_set = plot.ConcentrationPlotSettings.parse_labeled_contour_levels("10E+2::100050200+10E+3::100070200")
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
    a, clrs, clr_set = plot.ConcentrationPlotSettings.parse_labeled_contour_levels("10E+2:USER1+10E+3:USER2")
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
    assert hasattr(p, "time_selector")
    assert hasattr(p, "level_selector")
    assert hasattr(p, "pollutant_selector")
    assert hasattr(p, "smoothing_kernel")
    assert hasattr(p, "conc_type")
    assert hasattr(p, "conc_map")
    assert hasattr(p, "depo_map")
    assert hasattr(p, "prev_forecast_time")
    assert hasattr(p, "length_factory")

    assert hasattr(p, "fig")
    assert hasattr(p, "conc_outer")
    assert hasattr(p, "conc_axes")
    assert hasattr(p, "legends_axes")
    assert hasattr(p, "text_axes")
    assert hasattr(p, "plot_saver_list")
    assert p.color_opacity == 100
    assert hasattr(p, "color_table")

    assert hasattr(p, "TFACT")
    assert hasattr(p, "initial_time")
    assert hasattr(p, "contour_labels")
    assert p.current_frame == 1
    assert p.time_period_count == 0
    assert p.datem is None
    
    
def test_ConcentrationPlot_merge_plot_settings():
    p = plot.ConcentrationPlot()

    p.merge_plot_settings("data/default_cplot", ["-m4"])

    assert p.settings.map_projection == 4
    
    
def test_ConcentrationPlot_get_street_map_target_axes():
    p = plot.ConcentrationPlot()
    ax = plt.axes()
    p.conc_axes = ax
    assert p.get_street_map_target_axes() is ax
    plt.close(ax.get_figure())
    
    

def test_ConcentrationPlot_read_data_files():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump", "-w1", "-d2", "--source-time-zone", "-qdata/meas-t1.txt"])

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
    assert p.conc_type is not None
    assert isinstance(p.color_table, plot.AbstractColorTable)
    assert p.plot_saver_list is not None
    assert p.conc_map is not None
    assert p.depo_map is not None
    assert p.depo_sum is not None
    assert p.settings.smoothing_distance > 0 and p.smoothing_kernel is not None
    assert p.time_zone is not None
    assert p.datem is not None


def test_ConcentrationPlot__post_file_processing(cdump2):
    p = plot.ConcentrationPlot()
    
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
       
    p._post_file_processing(cdump2)
    
    assert p.conc_type.max_average * 1.e+13 == pytest.approx(7.991718)
    assert p.conc_type.min_average * 1.e+16 == pytest.approx(6.242119)
    

def test_ConcentrationPlot__normalize_settings(cdump2):
    p = plot.ConcentrationPlot()
    s = p.settings
    
    s.LEVEL1 = -10
    s.LEVEL2 = 1000000
    
    s.contour_level_generator = 5
    s.UCMIN = 1.0
    s.UDMIN = 2.0
    
    s.exposure_unit = 10
    
    p.contour_labels = None
    
    p._normalize_settings(cdump2)

    assert s.LEVEL1 == 100
    assert s.LEVEL2 == 300
    
    assert s.UCMIN == 0.0
    assert s.UDMIN == 0.0
    
    assert s.KMAP == 11
    
    assert p.contour_labels is not None
    assert p.contour_labels == ["", "", "", ""]
    
    # check with other exposure_unit values
    s.exposure_unit = const.ExposureUnit.CHEMICAL_THRESHOLDS
    p._normalize_settings(cdump2)
    assert s.KMAP == const.ConcentrationMapType.THRESHOLD_LEVELS #4
    
    s.exposure_unit = const.ExposureUnit.VOLCANIC_ASH
    p._normalize_settings(cdump2)
    assert s.KMAP == const.ConcentrationMapType.VOLCANIC_ERUPTION #5
    
    s.exposure_unit = const.ExposureUnit.MASS_LOADING
    p._normalize_settings(cdump2)
    assert s.KMAP == const.ConcentrationMapType.MASS_LOADING #

        
def test_ConcentrationPlot__fix_map_color():
    p = plot.ConcentrationPlot()

    color_mode = const.ConcentrationPlotColor.BLACK_AND_WHITE
    assert p._fix_map_color('#6699cc', color_mode) == 'k' # black

    color_mode = const.ConcentrationPlotColor.COLOR
    assert p._fix_map_color('#6699cc', color_mode) == '#6699cc'

    color_mode = const.ConcentrationPlotColor.BW_NO_LINES
    assert p._fix_map_color('#6699cc', color_mode) == 'k' # black

    color_mode = const.ConcentrationPlotColor.COLOR_NO_LINES
    assert p._fix_map_color('#6699cc', color_mode) == '#6699cc'


def test_ConcentrationPlot_layout():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump"])
    p.read_data_files()
    p._initialize_map_projection(p.cdump)

    p.layout( p.cdump.grids[0], {"resize_event" : blank_event_handler} )

    assert p.fig is not None
    assert p.conc_outer is not None
    assert p.conc_axes is not None
    assert p.legends_axes is not None
    assert p.text_axes is not None

    cleanup_plot(p)


def test_ConcentrationPlot_make_plot_title(cdump):
    g = cdump.grids[0]
    p = plot.ConcentrationPlot()
    p.labels = labels.LabelsConfig()
    p.conc_type = helper.LevelConcentration()
    p.conc_map = helper.ThresholdLevelsMap(4)
    level1 = util.LengthInMeters(1.0)
    level2 = util.LengthInMeters(2.0)
    
    title = p.make_plot_title(g, p.conc_map, level1, level2, g.starting_datetime)
    assert title == "NOAA HYSPLIT MODEL\n" + \
            "Concentration ($mass/m^3$) at level 2 m\n" + \
            "Integrated from 1700 25 Sep to 0500 26 Sep 1983 (UTC)\n" + \
            "TEST Release started at 1700 25 Sep 1983 (UTC)"

    # use the release start time for the integration start time.
    p.settings.NSSLBL = 1
    saved = g.parent.release_datetimes[0]
    g.parent.release_datetimes[0] = datetime.datetime(1983, 9, 25, 21, 13, 0, 0, pytz.utc)
    title = p.make_plot_title(g, p.conc_map, level1, level2, g.starting_datetime)
    assert title == "NOAA HYSPLIT MODEL\n" + \
            "Concentration ($mass/m^3$) at level 2 m\n" + \
            "Integrated from 2113 25 Sep to 0500 26 Sep 1983 (UTC)\n" + \
            "TEST Release started at 2113 25 Sep 1983 (UTC)"
    g.parent.release_datetimes[0] = saved
    p.settings.NSSLBL = 0
        
    # swap start and end datetimes
    g.starting_datetime, g.ending_datetime = g.ending_datetime, g.starting_datetime
    
    title = p.make_plot_title(g, p.conc_map, level1, level2, g.starting_datetime)
    assert title == "NOAA HYSPLIT MODEL\n" + \
            "Concentration ($mass/m^3$) at level 2 m\n" + \
            "Integrated from 0500 26 Sep to 1700 25 Sep 1983 (UTC) [backward]\n" + \
            "TEST Calculation started at 1700 25 Sep 1983 (UTC)"

    # set the time zone
    p.time_zone = pytz.timezone("EST")
    title = p.make_plot_title(g, p.conc_map, level1, level2, g.starting_datetime)
    assert title == "NOAA HYSPLIT MODEL\n" + \
            "Concentration ($mass/m^3$) at level 2 m\n" + \
            "Integrated from 0000 26 Sep to 1200 25 Sep 1983 (EST) [backward]\n" + \
            "TEST Calculation started at 1200 25 Sep 1983 (EST)"   


def test_ConcentrationPlot_make_ylabel(cdump):
    p = plot.ConcentrationPlot()
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


def test_ConcentrationPlot_make_xlabel(cdump):
    p = plot.ConcentrationPlot()
    p.cdump = cdump
    g = cdump.grids[0]
    
    assert p.make_xlabel(g) == "NARR METEOROLOGICAL DATA"

    g.ending_forecast_hr = 24
    p.prev_forecast_time = None
    assert p.make_xlabel(g) == "0500 25 Sep 1983 NARR FORECAST INITIALIZATION"
    
    g.ending_forecast_hr = 23
    assert p.make_xlabel(g) == "NARR METEOROLOGICAL DATA"

    assert p.make_xlabel(g) == "0600 25 Sep 1983 NARR FORECAST INITIALIZATION"
    

def test_ConcentrationPlot__initialize_map_projection():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump"])
    p.read_data_files()

    assert p.street_map is None
    
    p._initialize_map_projection( p.cdump )

    assert isinstance(p.projection, mapproj.AbstractMapProjection)
    assert p.settings.center_loc == pytest.approx((-84.22, 39.90))
    assert isinstance(p.street_map, streetmap.AbstractMapBackground)
    assert p.street_map.fix_map_color_fn is not None
    assert p.initial_corners_xy == pytest.approx((-189489.0, 414083.0, -154687.0, 448885.0))
    assert p.initial_corners_lonlat == pytest.approx((-86.41419, -79.06401, 38.46890, 43.84349))
    

def test_ConcentrationPlot__create_map_box_instance():
    p = plot.ConcentrationPlot()
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
    

def test_ConcentrationPlot__determine_map_limits(cdump):
    p = plot.ConcentrationPlot()
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


def test_ConcentrationPlot_draw_concentration_plot():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    
    # See if no exception is thrown.
    try:
        p._initialize_map_projection(p.cdump)
        p.layout(p.cdump.grids[0], {"resize_event" : blank_event_handler})
        contour_set = p.draw_concentration_plot(p.cdump.grids[0],
                                                p.cdump.grids[0].conc,
                                                p.conc_map,
                                                [1.0e-16, 1.0e-15, 1.0e-14],
                                                ["g", "b", "r"])
        assert isinstance(contour_set, QuadContourSet)
        
        # no contour levels
        contour_set = p.draw_concentration_plot(p.cdump.grids[0],
                                                p.cdump.grids[0].conc,
                                                p.conc_map,
                                                [],
                                                [])
                
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_ConcentrationPlot_get_conc_unit():
    p = plot.ConcentrationPlot()
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
    
    
def test_ConcentrationPlot__limit_contour_levels_for_legends():
    p = plot.ConcentrationPlot()
    c = [0, 1, 3, 4, 5] # any list will do
    l = p._limit_contour_levels_for_legends(c, 3)
    assert len(l) == 3
    assert l[0] == 0
    assert l[2] == 3
    
    
def test_ConcentrationPlot_draw_contour_legends():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    
    # See if no exception is thrown.
    try:
        p._initialize_map_projection(p.cdump)
        p.layout(p.cdump.grids[0], {"resize_event" : blank_event_handler})
        p.draw_contour_legends(
            p.cdump.grids[0],
            p.conc_map,
            ["AEGL-1", "AEGL-2", "AEGL-3"],
            [1.0-16, 1.0e-15, 1.0e-14],
            ["g", "b", "y"],
            1.0)
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_ConcentrationPlot_draw_bottom_text():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump", "-jdata/arlmap_truncated"])
    p.read_data_files()

    # See if no exception is thrown.
    try:
        p._initialize_map_projection(p.cdump)
        p.layout(p.cdump.grids[0], {"resize_event" : blank_event_handler})
        p.draw_bottom_text()
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_ConcentrationPlot__write_gisout():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings("data/default_cplot", ["-idata/cdump", "-jdata/arlmap_truncated", "-a3", "+a0", "-A0"])
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
                          p.settings.NDEP)
    g = p.cdump.grids[0]
    lower_vert_level = util.LengthInMeters(0)
    upper_vert_level = util.LengthInMeters(100)
    contour_levels = [1.0e-15, 1.0e-14, 1.0e-13, 1.0e-12]
    fill_colors = ["b", "g", "y", "r"]
    scaling_factor = 1.0
    quad_contour_set = axes.contourf(g.longitudes, g.latitudes, g.conc,
                                     contour_levels,
                                     colors=fill_colors, extend="max",
                                     transform=p.data_crs)
    
    if os.path.exists("HYSPLIT_ps.kml"):
        os.remove("HYSPLIT_ps.kml")
    if os.path.exists("GELABEL_ps.txt"):
        os.remove("GELABEL_ps.txt")
    
    p._write_gisout([gis_writer], g,
                     lower_vert_level, upper_vert_level,
                     quad_contour_set, contour_levels,
                     color_table, scaling_factor)
    
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


def test_ConcentrationPlot_draw_conc_above_ground():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump_deposit", "-jdata/arlmap_truncated", "-d1"])
    p.read_data_files()
    
    lgen = plot.ContourLevelGeneratorFactory.create_instance(p.settings.contour_level_generator,
                                                             p.settings.contour_levels,
                                                             p.settings.UCMIN,
                                                             p.settings.user_color)
    ctbl = plot.ColorTableFactory.create_instance(p.settings)
    
    gis_writer = gisout.GISFileWriterFactory.create_instance(p.settings.gis_output,
                                                             p.settings.kml_option)
                                                             
    gis_writer.initialize(p.settings.gis_alt_mode,
                          p.settings.KMLOUT,
                          p.settings.output_suffix,
                          p.settings.KMAP,
                          p.settings.NSSLBL,
                          p.settings.show_max_conc,
                          p.settings.NDEP)
        
    # See if no exception is thrown.
    try:
        p._initialize_map_projection(p.cdump)
        p.depo_sum.initialize(p.cdump.grids, p.time_selector, p.pollutant_selector)
        p.contour_labels = [""] * p.settings.contour_level_count
        p.draw_conc_above_ground(p.cdump.grids[0],
                                 {"resize_event" : blank_event_handler},
                                 lgen,
                                 ctbl,
                                 block=False)
        
        # with a gis writer
        p.draw_conc_above_ground(p.cdump.grids[0],
                                 {"resize_event" : blank_event_handler},
                                 lgen,
                                 ctbl,
                                 gis_writer,
                                 block=False)       
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_ConcentrationPlot_draw_conc_on_ground():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump_deposit", "-jdata/arlmap_truncated", "-d1"])
    p.read_data_files()
    
    lgen = plot.ContourLevelGeneratorFactory.create_instance(p.settings.contour_level_generator,
                                                             p.settings.contour_levels,
                                                             p.settings.UCMIN,
                                                             p.settings.user_color)
    ctbl = plot.ColorTableFactory.create_instance(p.settings)

    gis_writer = gisout.GISFileWriterFactory.create_instance(p.settings.gis_output,
                                                             p.settings.kml_option)

    gis_writer.initialize(p.settings.gis_alt_mode,
                          p.settings.KMLOUT,
                          p.settings.output_suffix,
                          p.settings.KMAP,
                          p.settings.NSSLBL,
                          p.settings.show_max_conc,
                          p.settings.NDEP)

    # See if no exception is thrown.
    try:
        p._initialize_map_projection(p.cdump)
        p.depo_sum.initialize(p.cdump.grids, p.time_selector, p.pollutant_selector)
        p.contour_labels = [""] * p.settings.contour_level_count
        p.draw_conc_on_ground(p.cdump.grids[0],
                              {"resize_event" : blank_event_handler},
                              lgen,
                              ctbl,
                              block=False)
        
        # with a gis writer
        p.draw_conc_on_ground(p.cdump.grids[0],
                              {"resize_event" : blank_event_handler},
                              lgen,
                              ctbl,
                              gis_writer,
                              block=False)
        cleanup_plot(p)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))
    
    
def test_ConcentrationPlot_draw():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump", "-jdata/arlmap_truncated"])
    p.read_data_files()
    
    # See if no exception is thrown.
    try:
        p._initialize_map_projection(p.cdump)
        p.contour_labels = [""] * p.settings.contour_level_count
        p.draw({"resize_event" : blank_event_handler}, block=False)
        assert p.time_period_count == 1
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))

    assert os.path.exists("concplot.ps")
    os.remove("concplot.ps")

    # Save to a file
    p.settings.interactive_mode = False
    plot_saver = multipage.PlotFileWriterFactory.create_instance(p.settings.frames_per_file,
                                                                 "__conc",
                                                                 "png",
                                                                 "png")
    p.plot_saver_list = [ plot_saver ]
    
    p.draw()
    assert os.path.exists("__conc0002.png")
    os.remove("__conc0002.png")
    
    cleanup_plot(p)    


def test_ConcentrationPlot_get_plot_count_str():
    p = plot.ConcentrationPlot()
    
    plot_saver = multipage.SinglePlotFileWriter("test", "png", "png")
    p.plot_saver_list = [ plot_saver ]
    
    plot_saver.file_count = 7
    assert p.get_plot_count_str() == "7 output files"
    
    plot_saver.file_count = 1
    p.time_period_count = 1
    assert p.get_plot_count_str() == "1 time period"
    
    p.time_period_count = 2
    assert p.get_plot_count_str() == "2 time periods"
    

def test_LabelledContourLevel___init__():
    o = plot.LabelledContourLevel(10.0, "USER1")
    assert o.level == 10.0
    assert o.label == "USER1"
    
    o = plot.LabelledContourLevel()
    assert o.level == 0.0
    assert o.label == ""


def test_LabelledContourLevel___repr__():
    o = plot.LabelledContourLevel(10.0, "USER1")
    assert str(o) == "LabelledContourLevel(USER1, 10.0)"


def test_ContourLevelGeneratorFactory_create_instance(contourLevels):
    cntr_levels = None
    cutoff = 3.14e-15
    user_color = None
    
    o = plot.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.EXPONENTIAL_DYNAMIC,
                                                          cntr_levels,
                                                          cutoff,
                                                          user_color)
    assert isinstance(o, plot.ExponentialDynamicLevelGenerator)
    
    o = plot.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.EXPONENTIAL_FIXED,
                                                          cntr_levels,
                                                          cutoff,
                                                          user_color)
    assert isinstance(o, plot.ExponentialFixedLevelGenerator)
    
    o = plot.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.LINEAR_DYNAMIC,
                                                          cntr_levels,
                                                          cutoff,
                                                          user_color)
    assert isinstance(o, plot.LinearDynamicLevelGenerator)
    
    o = plot.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.LINEAR_FIXED,
                                                          cntr_levels,
                                                          cutoff,
                                                          user_color)
    assert isinstance(o, plot.LinearFixedLevelGenerator)
    
    o = plot.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.USER_SPECIFIED,
                                                          contourLevels,
                                                          cutoff,
                                                          None)
    assert isinstance(o, plot.UserSpecifiedLevelGenerator)
    
    try:
        o = plot.ContourLevelGeneratorFactory.create_instance(100000,
                                                              None,
                                                              cutoff,
                                                              None)
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "unknown method 100000 for contour level generation"


def test_AbstractContourLevelGenerator___init__():
    o = AbstractContourLevelGeneratorTest()
    assert o is not None
    assert hasattr(o, "global_min")
    assert hasattr(o, "global_max")
 

def test_AbstractContourLevelGenerator_set_global_min_max():
    o = AbstractContourLevelGeneratorTest()
    o.set_global_min_max(0.25, 0.75)
    assert o.global_min == pytest.approx(0.25)
    assert o.global_max == pytest.approx(0.75)
       

def test_ExponentialDynamicLevelGenerator___init__():
    cutoff = 3.14e-15
    o = plot.ExponentialDynamicLevelGenerator(cutoff, force_base_10=True)
    assert o is not None
    assert o.cutoff == pytest.approx(3.14e-15)
    assert o.force_base_10 == True  


def test_ExponentialDynamicLevelGenerator__compute_interval():
    o = plot.ExponentialDynamicLevelGenerator(0)

    cint, cint_inverse = o._compute_interval(1.39594e-15, 8.17302e-13)
    assert cint == pytest.approx( 10.0 )
    assert cint_inverse == pytest.approx( 0.1 )

    cint, cint_inverse = o._compute_interval(1.39594e-15, 8.17302e-6)
    assert cint == pytest.approx( 100.0 )
    assert cint_inverse == pytest.approx( 0.01 )
    
    o.force_base_10 = True

    cint, cint_inverse = o._compute_interval(1.39594e-15, 8.17302e-6)
    assert cint == pytest.approx( 10.0 )
    assert cint_inverse == pytest.approx( 0.1 )
    

def test_ExponentialDynamicLevelGenerator_make_levels():
    o = plot.ExponentialDynamicLevelGenerator(3.14e-19)
    
    # base 10.0
    
    levels = o.make_levels(1.39594e-15, 8.17302e-13, 4)
    
    levels *= 1.e+16
    assert levels == pytest.approx((1.0, 10.0, 100.0, 1000.0))
    
    # base 100.0
    
    levels = o.make_levels(1.39594e-15, 8.17302e-07, 4)
    
    levels *= 1.e+13
    assert levels == pytest.approx((1.0, 100.0, 10000.0, 1000000.0))

    # force base 10
    
    o.force_base_10 = True
    levels = o.make_levels(1.39594e-15, 8.17302e-7, 4)
    
    levels *= 1.e+10
    assert levels == pytest.approx((1.0, 10.0, 100.0, 1000.0))

    # when cmax is zero
    levels = o.make_levels(0, 0, 4)
    assert levels == pytest.approx((0.001, 0.01, 0.1, 1.0))
    
    # When the cutoff exceeds the min and max values.
    o = plot.ExponentialDynamicLevelGenerator( 1.0 )
    levels = o.make_levels(1.0e-16, 1.0e-12, 4)
    assert levels == pytest.approx((1.0))
    
    # When the cutoff is between the min and max values
    o = plot.ExponentialDynamicLevelGenerator( 1.0e-14 )
    levels = o.make_levels(1.0e-16, 1.0e-12, 4)
    levels *= 1.0e+16
    assert levels == pytest.approx((100.0, 1000.0))
    
    
def test_ExponentialDynamicLevelGenerator_compute_color_table_offset():
    o = plot.ExponentialDynamicLevelGenerator( 0 )
    o.set_global_min_max(1.39594e-15, 8.17302e-13)
    levels = o.make_levels(1.39594e-15, 8.17302e-13, 4)
    
    assert o.compute_color_table_offset( levels ) == 0
    
    o.set_global_min_max(1.39594e-15, 8.17302e-12)
    
    assert o.compute_color_table_offset( levels ) == 1
    
    assert o.compute_color_table_offset( [1.0e-13] ) == 1
    
    
def test_ExponentialFixedLevelGenerator___init__():
    cutoff = 3.14e-15
    o = plot.ExponentialFixedLevelGenerator(cutoff, force_base_10=True)
    assert o is not None
    assert o.cutoff == pytest.approx(3.14e-15)
    assert o.force_base_10 == True  


def test_ExponentialFixedLevelGenerator_make_levels():
    o = plot.ExponentialFixedLevelGenerator(3.14e-19)
    o.set_global_min_max(1.39594e-15, 8.17302e-13)

    levels = o.make_levels(1.39594e-16, 8.17302e-12, 4)
    
    # levels should be generated using the global min and max.
    levels *= 1.e+16
    assert levels == pytest.approx((1.0, 10.0, 100.0, 1000.0))
    
    # when cmax is zero
    o.set_global_min_max(0, 0)
    levels = o.make_levels(1.39594e-16, 8.17302e-12, 4)
    assert levels == pytest.approx((0.001, 0.01, 0.1, 1.0))

    # When the cutoff exceeds the min and max values.
    o = plot.ExponentialFixedLevelGenerator( 1.0 )
    o.set_global_min_max(1.0e-16, 1.0e-12)
    levels = o.make_levels(1.0e-16, 1.0e-12, 4)
    assert levels == pytest.approx((1.0))
    
    # When the cutoff is between the min and max values
    o = plot.ExponentialFixedLevelGenerator( 1.0e-14 )
    o.set_global_min_max(1.0e-16, 1.0e-12)
    levels = o.make_levels(1.0e-16, 1.0e-12, 4)
    levels *= 1.0e+16
    assert levels == pytest.approx((100.0, 1000.0))
    
    
def test_ExponentialFixedLevelGenerator_compute_color_table_offset():
    o = plot.ExponentialFixedLevelGenerator( 0 )
    o.set_global_min_max(1.39594e-15, 8.17302)
    levels = o.make_levels(1.39594e-15, 8.17302e-13, 4)
    assert o.compute_color_table_offset( levels ) == 0


def test_LinearDynamicLevelGenerator___init__():
    o = plot.LinearDynamicLevelGenerator()
    assert o is not None


def test_LinearDynamicLevelGenerator__compute_interval():
    o = plot.LinearDynamicLevelGenerator()
    assert o._compute_interval(1.0, 10.0) == pytest.approx( (2.0, 0.5) )
    assert o._compute_interval(0.0,  0.0) == pytest.approx( (1.0, 1.0) )


def test_LinearDynamicLevelGenerator_make_levels():
    o = plot.LinearDynamicLevelGenerator()
    
    levels = o.make_levels(1.0, 10.0, 4)
    
    assert levels == pytest.approx((2., 4., 6., 8.))
    
    # when cmax is zero
    levels = o.make_levels(0.0, 0.0, 4)
    assert levels == pytest.approx((1., 2., 3., 4.))
    
    
def test_LinearDynamicLevelGenerator_compute_color_table_offset():
    o = plot.LinearDynamicLevelGenerator()
    o.set_global_min_max(0, 10.0)
    levels = o.make_levels(1.0, 10.0, 4)
    
    # levels[-1] = 8.0
    assert o.compute_color_table_offset( levels ) == 1
    
    o.set_global_min_max(0, 9.0)
    
    assert o.compute_color_table_offset( levels ) == 0
    
    assert o.compute_color_table_offset( [4.0] ) == 2
    

def test_LinearFixedLevelGenerator___init__():
    o = plot.LinearFixedLevelGenerator()
    assert o is not None


def test_LinearFixedLevelGenerator_make_levels():
    o = plot.LinearFixedLevelGenerator()
    o.set_global_min_max(1.0, 10.0)
    
    levels = o.make_levels(1.0, 50.0, 4)
    
    # levels should be generated using the global min and max.
    assert levels == pytest.approx((2., 4., 6., 8.))
    
    # when cmax is zero
    o.set_global_min_max(0.0, 0.0)
    levels = o.make_levels(1.0, 50.0, 4)
    assert levels == pytest.approx((1., 2., 3., 4.))

    
def test_LinearFixedLevelGenerator_compute_color_table_offset():
    o = plot.LinearFixedLevelGenerator()
    o.set_global_min_max(0, 10.0)
    levels = o.make_levels(1.0, 10.0, 4)
    
    assert o.compute_color_table_offset( levels ) == 0
    
    o.set_global_min_max(0, 12.0)
    
    assert o.compute_color_table_offset( levels ) == 0
    
    
def test_UserSpecifiedLevelGenerator___init__(contourLevels):
    o = plot.UserSpecifiedLevelGenerator(contourLevels)
    assert o is not None
    assert len(contourLevels) == 4
    assert len(o.contour_levels) == 4

    o = plot.UserSpecifiedLevelGenerator(None)
    assert o is not None
    assert len(o.contour_levels) == 0
    

def test_UserSpecifiedLevelGenerator_make_levels(contourLevels):
    o = plot.UserSpecifiedLevelGenerator(contourLevels)
    
    levels = o.make_levels(1.0, 10.0, 4)
    
    assert levels == pytest.approx((10., 15., 20., 25.))
    

def test_UserSpecifiedLevelGenerator_compute_color_table_offset(contourLevels):
    o = plot.UserSpecifiedLevelGenerator(contourLevels)
    
    levels = o.make_levels(1.0, 10.0, 4)
    
    assert levels == pytest.approx((10., 15., 20., 25.))
    
    o.set_global_min_max(0, 100.0)
    assert o.compute_color_table_offset( levels ) == 0
        

def test_ColorTableFactory():
    p = plot.ColorTableFactory()
    assert len(p.COLOR_TABLE_FILE_NAMES) == 2


def test_ColorTableFactory_create_instance():
    p = plot.ConcentrationPlot()
    s = p.settings
    
    saved = plot.ColorTableFactory.COLOR_TABLE_FILE_NAMES
    plot.ColorTableFactory.COLOR_TABLE_FILE_NAMES = ["data/CLRTBL.CFG"]

    # DefaultChemicalThresholdColorTable
    s.KMAP = const.ConcentrationMapType.THRESHOLD_LEVELS
    s.KHEMIN = 1
    ct = plot.ColorTableFactory.create_instance(s)
    assert isinstance(ct, plot.DefaultChemicalThresholdColorTable)
    assert ct.scaled_opacity == pytest.approx(1.0)
    # repeat with the color opacity specified
    ct = plot.ColorTableFactory.create_instance(s, 50)
    assert isinstance(ct, plot.DefaultChemicalThresholdColorTable)
    assert ct.scaled_opacity == pytest.approx(0.5)

    # UserColorTable
    s.KMAP = const.ConcentrationMapType.CONCENTRATION
    s.user_color = True
    s.parse_contour_levels("10E+2:USER1:100050200+10E+3:USER2:100070200")
    ct = plot.ColorTableFactory.create_instance(s)
    assert isinstance(ct, plot.UserColorTable)
    assert ct.scaled_opacity == pytest.approx(1.0)
    # repeat with the color opacity specified
    ct = plot.ColorTableFactory.create_instance(s, 50)
    assert isinstance(ct, plot.UserColorTable)
    assert ct.scaled_opacity == pytest.approx(0.5)

    # DefaultColorTable
    s.user_color = False
    ct = plot.ColorTableFactory.create_instance(s)
    assert isinstance(ct, plot.DefaultColorTable)
    assert ct.scaled_opacity == pytest.approx(1.0)
    # repeat with the color opacity specified
    ct = plot.ColorTableFactory.create_instance(s, 50)
    assert isinstance(ct, plot.DefaultColorTable)
    assert ct.scaled_opacity == pytest.approx(0.5)

    # check conversion to grayscale table
    s.color = const.ConcentrationPlotColor.BLACK_AND_WHITE
    ct = plot.ColorTableFactory.create_instance(s)
    assert isinstance(ct, plot.DefaultColorTable)
    for rgb in ct.rgbs:
        r, g, b, a = rgb
        assert r == g and g == b
        assert a == pytest.approx(1.0)

    plot.ColorTableFactory.COLOR_TABLE_FILE_NAMES = saved


def test_ColorTableFactory__get_color_table_filename():
    p = plot.ColorTableFactory()
    assert p._get_color_table_filename() == None

    saved = plot.ColorTableFactory.COLOR_TABLE_FILE_NAMES
    plot.ColorTableFactory.COLOR_TABLE_FILE_NAMES = ["data/CLRTBL.CFG"]
    assert p._get_color_table_filename() == "data/CLRTBL.CFG"
    plot.ColorTableFactory.COLOR_TABLE_FILE_NAMES = saved

    
def test_AbstractColorTable___init__():
    o = AbstractColorTableTest(4, 50)
    assert hasattr(o, "ncolors")
    assert hasattr(o, "rgbs")
    assert hasattr(o, "offset")
    assert o.ncolors == 4
    assert o.scaled_opacity == pytest.approx(0.5)
    assert o.offset == 0
    assert o.use_offset == False


def test_AbstractColorTable_get_reader():
    o = AbstractColorTableTest(4)
    r = o.get_reader()
    assert isinstance(r, plot.ColorTableReader)
    assert r.color_table is o


def test_AbstractColorTable_set_rgb():
    o = AbstractColorTableTest(2)
    o.rgbs = [(0,0,0), (.5, .5, .5)]

    o.set_rgb(0, (.2, .2, .2))
    assert o.rgbs[0] == pytest.approx((0.2, 0.2, 0.2, 1.0))

    # repeat with an alpha value specified
    o.set_rgb(0, (.1, .2, .2, 0.75))
    assert o.rgbs[0] == pytest.approx((0.1, 0.2, 0.2, 0.75))


def test_AbstractColorTable_change_to_grayscale():
    o = AbstractColorTableTest(2)
    o.rgbs = [(0,0,0), (.5, .6, .7)]
    
    o.change_to_grayscale()
    
    assert o.rgbs[0] == pytest.approx((0.0, 0.0, 0.0, 1.0))
    assert o.rgbs[1] == pytest.approx((0.5815, 0.5815, 0.5815, 1.0))
    
    # repeat with an alpha value specified
    o.scaled_opacity = 0.50
    o.rgbs = [(0,0,0), (.5, .6, .7)]
    o.change_to_grayscale()
    assert o.rgbs[0] == pytest.approx((0.0, 0.0, 0.0, 0.5))
    assert o.rgbs[1] == pytest.approx((0.5815, 0.5815, 0.5815, 0.5))


def test_AbstractColorTable_get_luminance():
    assert AbstractColorTableTest.get_luminance((0.5, 0.6, 0.7)) == pytest.approx(0.5815)
    assert AbstractColorTableTest.get_luminance((0.5, 0.6, 0.7, 0.8)) == pytest.approx(0.5815)


def test_AbstractColorTable_create_plot_colors():
    clrs = AbstractColorTableTest.create_plot_colors([(.5, .5, .5), (1., 1., 1.)])
    assert len(clrs) == 2
    assert clrs[0] == "#808080"
    assert clrs[1] == "#ffffff"

    # include alpha
    clrs = AbstractColorTableTest.create_plot_colors([(.5, .5, .5, 0.0), (1., 1., 1., 0.5)])
    assert len(clrs) == 2
    assert clrs[0] == "#80808000"
    assert clrs[1] == "#ffffff80"


def test_AbstractColorTable_set_offset():
    o = AbstractColorTableTest(4)
    
    o.enable_offset( True )
    
    o.set_offset( 1 )
    assert o.offset == 1
    
    o.set_offset( 2 )
    assert o.offset == 2
        
    o.enable_offset( False )
    
    o.set_offset( 1 )
    assert o.offset == 0
    
    o.set_offset( 2 )
    assert o.offset == 0
    
    
def test_AbstractColorTable_enable_offset():
    o = AbstractColorTableTest(4)
    
    o.enable_offset()
    assert o.use_offset == True
    
    o.enable_offset( False )
    assert o.use_offset == False
    
    o.enable_offset( True )
    assert o.use_offset == True
    
    
def test_DefaultColorTable___init__():
    o = plot.DefaultColorTable(3, False)
    assert o.ncolors == 3
    assert o.scaled_opacity == pytest.approx(1.0)
    assert o.skip_std_colors == False
    assert len(o.rgbs) == 32
    assert o.rgbs[3] == pytest.approx((0.0, 1.0, 0.0, 1.0))
    assert hasattr(o, "colors")
    assert hasattr(o, "raw_colors")
    assert o._DefaultColorTable__current_offset == 0
    
    # repeat with an alpha value
    o = plot.DefaultColorTable(3, False, 50)
    assert o.scaled_opacity == pytest.approx(0.5)


def test_DefaultColorTable_raw_colors():
    o = plot.DefaultColorTable(3, False)
    clrs = o.raw_colors
    assert len(clrs) == 3
    assert clrs[0] == pytest.approx((0.0, 1.0, 0.0, 1.0))
    assert clrs[1] == pytest.approx((0.0, 0.0, 1.0, 1.0))
    assert clrs[2] == pytest.approx((1.0, 1.0, 0.0, 1.0))

    o = plot.DefaultColorTable(3, True)
    clrs = o.raw_colors
    assert len(clrs) == 3
    assert clrs[0] == pytest.approx((1.0, 1.0, 0.0, 1.0))
    assert clrs[1] == pytest.approx((1.0, 0.6, 0.0, 1.0))
    assert clrs[2] == pytest.approx((1.0, 0.0, 0.0, 1.0)) 
    
    o.enable_offset( True )
    o.set_offset(1)
    
    clrs = o.raw_colors
    assert len(clrs) == 3
    assert clrs[0] == pytest.approx((0.8, 1.0, 0.0, 1.0))
    assert clrs[1] == pytest.approx((1.0, 1.0, 0.0, 1.0))
    assert clrs[2] == pytest.approx((1.0, 0.6, 0.0, 1.0))
    

def test_DefaultColorTable_colors():
    o = plot.DefaultColorTable(3, False)
    clrs = o.colors
    assert len(clrs) == 3
    assert clrs[0] == "#00ff00"
    assert clrs[1] == "#0000ff"
    assert clrs[2] == "#ffff00"

    o = plot.DefaultColorTable(3, True)
    clrs = o.colors
    assert len(clrs) == 3
    assert clrs[0] == "#ffff00"
    assert clrs[1] == "#ff9900"
    assert clrs[2] == "#ff0000"
    
    o.enable_offset( True )
    o.set_offset( 1 )
    
    clrs = o.colors
    assert len(clrs) == 3
    assert clrs[0] == "#ccff00"
    assert clrs[1] == "#ffff00"
    assert clrs[2] == "#ff9900"


def test_DefaultChemicalThresholdColorTable___init__():
    o = plot.DefaultChemicalThresholdColorTable(3, False)
    assert o.ncolors == 3
    assert o.scaled_opacity == pytest.approx(1.0)
    assert o.skip_std_colors == False
    assert len(o.rgbs) == 32
    assert o.rgbs[3] == pytest.approx((1.0, 0.5, 0.0, 1.0))
    assert hasattr(o, "colors")
    assert hasattr(o, "raw_colors")
    assert o._DefaultChemicalThresholdColorTable__current_offset == 0

    # repeat with an alpha value
    o = plot.DefaultChemicalThresholdColorTable(3, False, 50)
    assert o.scaled_opacity == pytest.approx(0.5)


def test_DefaultChemicalThresholdColorTable_raw_colors():
    o = plot.DefaultChemicalThresholdColorTable(3, False)
    clrs = o.raw_colors
    assert len(clrs) == 3
    assert clrs[2] == pytest.approx((1.0, 0.5, 0.0, 1.0))
    assert clrs[1] == pytest.approx((1.0, 1.0, 0.0, 1.0))
    assert clrs[0] == pytest.approx((0.8, 0.8, 0.8, 1.0))

    o.enable_offset( True )
    o.set_offset( 1 )
    
    clrs = o.raw_colors
    assert len(clrs) == 3
    assert clrs[2] == pytest.approx((1.0, 0.0, 0.0, 1.0))
    assert clrs[1] == pytest.approx((1.0, 0.5, 0.0, 1.0))
    assert clrs[0] == pytest.approx((1.0, 1.0, 0.0, 1.0))
    
    o = plot.DefaultChemicalThresholdColorTable(3, True)
    clrs = o.raw_colors
    assert len(clrs) == 3
    assert clrs[2] == pytest.approx((1.0, 1.0, 1.0, 1.0))
    assert clrs[1] == pytest.approx((1.0, 1.0, 1.0, 1.0))
    assert clrs[0] == pytest.approx((1.0, 1.0, 1.0, 1.0)) 


def test_DefaultChemicalThresholdColorTable_colors():
    o = plot.DefaultChemicalThresholdColorTable(3, False)
    clrs = o.colors
    assert len(clrs) == 3
    assert clrs[2] == "#ff8000"
    assert clrs[1] == "#ffff00"
    assert clrs[0] == "#cccccc"

    o.enable_offset( True )
    o.set_offset( 1 )
    
    clrs = o.colors
    assert len(clrs) == 3
    assert clrs[2] == "#ff0000"
    assert clrs[1] == "#ff8000"
    assert clrs[0] == "#ffff00"
    
    o = plot.DefaultChemicalThresholdColorTable(3, True)
    clrs = o.colors
    assert len(clrs) == 3
    assert clrs[2] == "#ffffff"
    assert clrs[1] == "#ffffff"
    assert clrs[0] == "#ffffff"   


def test_UserColorTable___init__(userColors):
    o = plot.UserColorTable(userColors)
    assert o.scaled_opacity == pytest.approx(1.0)
    assert len(o.rgbs) == 4
    assert o.rgbs[0] == pytest.approx((0.4, 0.4, 0.4, 1.0))

    # repeat with an alpha value.
    o = plot.UserColorTable(userColors, 50)
    assert o.scaled_opacity == pytest.approx(0.5)


def test_UserColorTable_raw_colors(userColors):
    o = plot.UserColorTable(userColors)
    clrs = o.raw_colors
    assert len(clrs) == 4
    

def test_UserColorTable_colors(userColors):
    o = plot.UserColorTable(userColors)
    clrs = o.colors
    assert len(clrs) == 4
    

def test_ColorTableReader___init__():
    tbl = plot.DefaultColorTable(4, False)
    o = plot.ColorTableReader(tbl)
    assert o.color_table is tbl
    

def test_ColorTableReader_read():
    tbl = plot.DefaultColorTable(4, False)
    o = plot.ColorTableReader(tbl)
    tbl2 = o.read("data/CLRTBL.CFG")
    assert tbl2 is tbl
    assert tbl2.rgbs[20] == pytest.approx((153.0/255.0, 0, 0, 1.0))

    # repeat with an alpha value specified
    tbl = plot.DefaultColorTable(4, False, 50)
    o = plot.ColorTableReader(tbl)
    tbl2 = o.read("data/CLRTBL.CFG")
    assert tbl2 is tbl
    assert tbl2.rgbs[20] == pytest.approx((153.0/255.0, 0, 0, 0.5))
