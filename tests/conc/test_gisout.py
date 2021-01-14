# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_gisout.py
#
# Performs unit tests on functions and class methods declared in conc/gisout.py.
# ---------------------------------------------------------------------------

import datetime
import logging
import matplotlib.pyplot as plt
import os
import pytest
import pytz
import xml.etree.ElementTree as ET

from hysplitdata.conc import model
from hysplitplot import const, util
from hysplitplot.conc import gisout, plot, helper, cntr


logger = logging.getLogger(__name__)


@pytest.fixture
def cdump_two_pollutants():
    return model.ConcentrationDump().get_reader().read("data/cdump_two_pollutants")
    

# Concrete classes to test abstract classes
class AbstractWriterTest(gisout.AbstractWriter):
    
    def __init__(self, time_zone=None):
        super(AbstractWriterTest, self).__init__(time_zone)
    
    def write(self, basename, g, contour_set, lower_vert_level, upper_vert_level, distinguishable_vert_level):
        pass
    
    def make_output_basename(self, g, conc_type, depo_sum, upper_vert_level):
        pass
   
    
class AbstractKMLContourWriterTest(gisout.AbstractKMLContourWriter):
    
    def _get_name_cdata(self, dt):
        return ""
    
    def _get_description_cdata(self, lower_vert_level, upper_vert_level, dt):
        return "" 
    
    def _get_max_location_text(self):
        pass
    
    
def test_GISFileWriterFactory_create_instance():
    kml_option = 0
    tz = pytz.timezone("America/New_York")
    
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.GENERATE_POINTS, kml_option, tz)
    assert isinstance(w, gisout.PointsGenerateFileWriter)
    assert isinstance(w.formatter, gisout.PointsGenerateFileWriter.DecimalFormWriter)
    assert w.time_zone is tz
    assert w.formatter.time_zone is tz
    
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.GENERATE_POINTS_2, kml_option, tz)
    assert isinstance(w, gisout.PointsGenerateFileWriter)
    assert isinstance(w.formatter, gisout.PointsGenerateFileWriter.ExponentFormWriter)
    assert w.time_zone is tz
    assert w.formatter.time_zone is tz
     
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.GENERATE_POINTS_STR, kml_option, tz)
    assert isinstance(w, gisout.PointsGenerateFileWriter)
    assert isinstance(w.formatter, gisout.PointsGenerateFileWriter.StringFormWriter)
    assert w.time_zone is tz
    assert w.formatter.time_zone is tz
          
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.KML, 1, tz)
    assert isinstance(w, gisout.KMLWriter)
    assert w.kml_option == 1
    assert w.time_zone is tz
     
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.PARTIAL_KML, 1, tz)
    assert isinstance(w, gisout.PartialKMLWriter)
    assert w.kml_option == 1
    assert w.time_zone is tz
         
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.NONE, kml_option, tz)
    assert isinstance(w, gisout.NullWriter)
    assert w.time_zone is tz

    
    
def test_GISFileWriterFactory_create_instance__without_time_zone():
    kml_option = 0
    
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.GENERATE_POINTS, kml_option)
    assert isinstance(w, gisout.PointsGenerateFileWriter)
    assert isinstance(w.formatter, gisout.PointsGenerateFileWriter.DecimalFormWriter)
    assert w.time_zone is None
    assert w.formatter.time_zone is None
    
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.GENERATE_POINTS_2, kml_option)
    assert isinstance(w, gisout.PointsGenerateFileWriter)
    assert isinstance(w.formatter, gisout.PointsGenerateFileWriter.ExponentFormWriter)
    assert w.time_zone is None
    assert w.formatter.time_zone is None
       
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.KML, 1)
    assert isinstance(w, gisout.KMLWriter)
    assert w.kml_option == 1
    assert w.time_zone is None
     
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.PARTIAL_KML, 1)
    assert isinstance(w, gisout.PartialKMLWriter)
    assert w.kml_option == 1
    assert w.time_zone is None
         
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.NONE, kml_option)
    assert isinstance(w, gisout.NullWriter)
    assert w.time_zone is None


def test_AbstractWriter___init__():
    o = AbstractWriterTest()
    assert hasattr(o, 'alt_mode_str')
    assert hasattr(o, 'output_basename')
    assert hasattr(o, 'output_suffix')
    assert hasattr(o, 'KMAP')
    assert hasattr(o, 'NSSLBL')
    assert hasattr(o, 'show_max_conc')
    assert hasattr(o, 'NDEP')
    assert o.time_zone is None

    tz = pytz.timezone("America/New_York")
    o = AbstractWriterTest(tz)
    assert o.time_zone is tz
    

def test_AbstractWriter_initialize():
    o = AbstractWriterTest()
    o.initialize(0, "2", "3", 5, 6, 7, 8)
    assert o.alt_mode_str == "clampedToGround"
    assert o.output_basename == "2"
    assert o.output_suffix == "3"
    assert o.KMAP == 5
    assert o.NSSLBL == 6
    assert o.show_max_conc == 7
    assert o.NDEP == 8


def test_AbstractWriter_write():
    o = AbstractWriterTest()
    try:
        # a silly test
        o.write(1, 2, 3, 4, 5, False)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))


def test_AbstractWriter_finalize():
    o = AbstractWriterTest()
    try:
        # a silly test
        o.finalize()
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))


def test_AbstractWriter_make_output_basename():
    o = AbstractWriterTest()
    try:
        # a silly test
        o.make_output_basename(1, 2, 3, 4)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))


def test_AbstractWriter__reformat_color():
    assert gisout.AbstractWriter._reformat_color("#face01") == "C801CEFA"


def test_NullWriter___init__():
    try:
        o = gisout.NullWriter()
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))


def test_NullWriter_make_output_basename():
    o = gisout.NullWriter()
    try:
        # a silly test
        o.make_output_basename(1, 2, 3, 4)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
        

def test_PointsGenerateFileWriter___init__():
    f = gisout.PointsGenerateFileWriter.DecimalFormWriter()
    o = gisout.PointsGenerateFileWriter( f )
    assert isinstance( o.formatter, gisout.PointsGenerateFileWriter.DecimalFormWriter )
    assert o.time_zone is None
    
    tz = pytz.timezone("America/New_York")
    o = gisout.PointsGenerateFileWriter( f, tz )
    assert isinstance( o.formatter, gisout.PointsGenerateFileWriter.DecimalFormWriter )
    assert o.time_zone is tz


def test_PointsGenerateFileWriter_make_output_basename(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    conc_type = helper.ConcentrationTypeFactory.create_instance( s.KAVG )
    depo_sum = helper.DepositSumFactory.create_instance(s.NDEP,
                                                        cdump_two_pollutants.has_ground_level_grid())

    o = gisout.PointsGenerateFileWriter( gisout.PointsGenerateFileWriter.DecimalFormWriter() )
    # Choose a concentration grid at 100 m.
    g = cdump_two_pollutants.grids[0]
    assert g.vert_level == 100
    basename = o.make_output_basename(g, conc_type, depo_sum, 500)
    assert basename == "GIS_00100_ps_01"
    # Choose a concentration grid at 300 m
    g = cdump_two_pollutants.grids[1]
    assert g.vert_level == 300
    basename = o.make_output_basename(g, conc_type, depo_sum, 500)
    assert basename == "GIS_00300_ps_01"
    # Recreate depo_sum with the flag for ground-level grid set to True.
    depo_sum = helper.DepositSumFactory.create_instance(s.NDEP,
                                                        True)
    # Change the height of the grid to zero.
    g.vert_level = 0
    basename = o.make_output_basename(g, conc_type, depo_sum, 500)
    assert basename == "GIS_DEP_ps_01"


def test_PointsGenerateFileWriter_write(cdump_two_pollutants):
    # delete files we are about to create
    if os.path.exists("GIS_00100_ps_01.att"):
        os.remove("GIS_00100_ps_01.att")
    if os.path.exists("GIS_00100_ps_01.txt"):
        os.remove("GIS_00100_ps_01.txt")
    
    o = gisout.PointsGenerateFileWriter( gisout.PointsGenerateFileWriter.DecimalFormWriter() )
    s = plot.ConcentrationPlotSettings()
    conc_type = helper.ConcentrationTypeFactory.create_instance( s.KAVG )
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    depo_type = helper.DepositSumFactory.create_instance(s.NDEP,
                                                         cdump_two_pollutants.has_ground_level_grid())
    g = cdump_two_pollutants.grids[0]
    
    o.initialize(s.gis_alt_mode,
                 s.KMLOUT,
                 s.output_suffix,
                 s.KMAP,
                 s.NSSLBL,
                 s.show_max_conc,
                 s.NDEP)

    ax = plt.axes()
    quad_contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                                   [1.0e-15, 1.0e-12],
                                   colors=["#ff0000", "#00ff00"],
                                   extend="max")
    plt.close(ax.figure)
    
    contour_set = cntr.convert_matplotlib_quadcontourset(quad_contour_set)
    contour_set.raw_colors = [(1.0, 1.0, 1.0), (1.0, 0.0, 0.0)]
    contour_set.colors = ["#ff0000", "#00ff00"]
    contour_set.levels = [1.0e-15, 1.0e-12]
    contour_set.levels_str = ["1.0e-15", "1.0e-12"]
    contour_set.labels = ["USER-2", "USER-1"]
    contour_set.concentration_unit = "mass/m^3"
    contour_set.min_concentration = 1.0e-16
    contour_set.max_concentration = 8.0e-12
    contour_set.min_concentration_str = "1.0e-16"
    contour_set.max_concentration_str = "8.0e-12"
    
    try:
        basename = "GIS_00100_ps_01"
        o.write(basename, g, contour_set, 100, 500)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
        
    assert os.path.exists("GIS_00100_ps_01.att")
    assert os.path.exists("GIS_00100_ps_01.txt")
    
    os.remove("GIS_00100_ps_01.att")
    os.remove("GIS_00100_ps_01.txt")


def test_DecimalFormWriter___init__():
    o = gisout.PointsGenerateFileWriter.DecimalFormWriter()
    assert o.time_zone is None
    
    tz = pytz.timezone("America/New_York")
    o = gisout.PointsGenerateFileWriter.DecimalFormWriter( tz )
    assert o.time_zone is tz
    
    
def test_DecimalFormWriter_write_boundary():
    o = gisout.PointsGenerateFileWriter.DecimalFormWriter()

    seg = cntr.Boundary(None)
    seg.latitudes = [1.2, 2.2, 3.2]
    seg.longitudes = [1.0, 2.0, 3.0]
    
    f = open("__decimalFormWriter.txt", "wt")
    o.write_boundary(f, seg, 1.0e-05)
    f.close()
    
    f = open("__decimalFormWriter.txt", "rt")
    lines = f.read().splitlines()
    f.close()
    
    assert lines[0] == "  -5.00000,    1.00000,    1.20000"
    assert lines[1] == "   2.00000,    2.20000"
    assert lines[3] == "END"
    
    os.remove("__decimalFormWriter.txt")
    
    
def test_DecimalFormWriter_write_attributes(cdump_two_pollutants):
    o = gisout.PointsGenerateFileWriter.DecimalFormWriter()
    g = cdump_two_pollutants.grids[0]
    
    f = open("__decimalFormWriter.txt", "wt")
    o.write_attributes(f, g, 100, 300, 1.0e-5, "#ff0000")
    f.close()
    
    f = open("__decimalFormWriter.txt", "rt")
    lines = f.read().splitlines()
    f.close()
    
    assert lines[0] == " -5.000,TEST,19830926,0500,00100,00300,#ff0000 "
    
    os.remove("__decimalFormWriter.txt")


def test_ExponentFormWriter___init__():
    o = gisout.PointsGenerateFileWriter.ExponentFormWriter()
    assert o.time_zone is None
    
    tz = pytz.timezone("America/New_York")
    o = gisout.PointsGenerateFileWriter.ExponentFormWriter( tz )
    assert o.time_zone is tz


def test_ExponentFormWriter_write_boundary():
    o = gisout.PointsGenerateFileWriter.ExponentFormWriter()
    
    seg = cntr.Boundary(None)
    seg.latitudes = [1.2, 2.2, 3.2]
    seg.longitudes = [1.0, 2.0, 3.0]
    
    f = open("__exponentFormWriter.txt", "wt")
    o.write_boundary(f, seg, 1.0e-05)
    f.close()
    
    f = open("__exponentFormWriter.txt", "rt")
    lines = f.read().splitlines()
    f.close()
    
    assert lines[0] == " 1.000e-05,    1.00000,    1.20000"
    assert lines[1] == "   2.00000,    2.20000"
    assert lines[3] == "END"
    
    os.remove("__exponentFormWriter.txt")


def test_ExponentFormWriter_write_attributes(cdump_two_pollutants):
    o = gisout.PointsGenerateFileWriter.ExponentFormWriter()
    g = cdump_two_pollutants.grids[0]
    
    f = open("__exponentFormWriter.txt", "wt")
    o.write_attributes(f, g, 100, 300, 1.0e-5, "#ff0000")
    f.close()
    
    f = open("__exponentFormWriter.txt", "rt")
    lines = f.read().splitlines()
    f.close()
    
    assert lines[0] == " 1.000e-05,TEST,19830926,0500,00100,00300,#ff0000 "
    
    os.remove("__exponentFormWriter.txt")


def test_StringFormWriter___init__():
    o = gisout.PointsGenerateFileWriter.StringFormWriter()
    assert o.time_zone is None
    
    tz = pytz.timezone("America/New_York")
    o = gisout.PointsGenerateFileWriter.StringFormWriter( tz )
    assert o.time_zone is tz

    
def test_StringFormWriter_write_boundary():
    o = gisout.PointsGenerateFileWriter.StringFormWriter()

    seg = cntr.Boundary(None)
    seg.latitudes = [1.2, 2.2, 3.2]
    seg.longitudes = [1.0, 2.0, 3.0]
    
    f = open("__stringFormWriter.txt", "wt")
    o.write_boundary(f, seg, "0-6 hours")
    f.close()
    
    f = open("__stringFormWriter.txt", "rt")
    lines = f.read().splitlines()
    f.close()
    
    assert lines[0] ==  "0-6 hours,    1.00000,    1.20000"
    assert lines[1] == "   2.00000,    2.20000"
    assert lines[3] == "END"
    
    os.remove("__stringFormWriter.txt")


def test_StringFormWriter_write_attributes(cdump_two_pollutants):
    o = gisout.PointsGenerateFileWriter.StringFormWriter()
    g = cdump_two_pollutants.grids[0]
    
    f = open("__stringFormWriter.txt", "wt")
    o.write_attributes(f, g, 100, 300, "0-6 hours", "#ff0000")
    f.close()
    
    f = open("__stringFormWriter.txt", "rt")
    lines = f.read().splitlines()
    f.close()
    
    assert lines[0] == "0-6 hours,TEST,19830926,0500,00100,00300,#ff0000 "
    
    os.remove("__stringFormWriter.txt")


def test_KMLWriter___init__():
    kml_option = 1
    o = gisout.KMLWriter(kml_option)
    assert o.time_zone is None
    assert o.kml_option == 1
    assert hasattr(o, 'att_file')
    assert hasattr(o, 'contour_writer')
    assert hasattr(o, 'xml_root')
    assert hasattr(o, 'kml_filename')

    
    tz = pytz.timezone("America/New_York")
    o = gisout.KMLWriter(kml_option, tz)
    assert o.time_zone is tz


def test_KMLWriter_make_output_basename(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    conc_type = helper.ConcentrationTypeFactory.create_instance(s.KAVG)
    depo_sum = helper.DepositSumFactory.create_instance(
            s.NDEP, cdump_two_pollutants.has_ground_level_grid())

    o = gisout.KMLWriter(s.kml_option)
    g = cdump_two_pollutants.grids[0]
    basename = o.make_output_basename(g, conc_type, depo_sum, 500)
    assert basename == "HYSPLIT_ps" and s.KMLOUT == 0


def test_KMLWriter_initialize(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    o = gisout.KMLWriter(s.kml_option)

    assert s.show_max_conc != 0
    o.initialize(s.gis_alt_mode,
                 s.output_basename,
                 s.output_suffix,
                 s.KMAP,
                 s.NSSLBL,
                 s.show_max_conc,
                 s.NDEP)

    assert isinstance(o.contour_writer, gisout.AbstractKMLContourWriter)
    assert o.contour_writer.show_max_conc == True
    assert isinstance(o.deposition_contour_writer, gisout.AbstractKMLContourWriter)
    assert o.deposition_contour_writer.show_max_conc == True

    # test initialize() again with s.show_max_conc = 0.

    s.show_max_conc = 0
    
    o.initialize(s.gis_alt_mode,
                 s.output_basename,
                 s.output_suffix,
                 s.KMAP,
                 s.NSSLBL,
                 s.show_max_conc,
                 const.DepositionType.NONE)
    
    assert isinstance(o.contour_writer, gisout.AbstractKMLContourWriter)
    assert o.contour_writer.show_max_conc == False
    assert o.deposition_contour_writer is None

def test_KMLWriter_write(cdump_two_pollutants):
    # delete files we are about to create
    if os.path.exists("HYSPLIT_ps.kml"):
        os.remove("HYSPLIT_ps.kml")
    if os.path.exists("GELABEL_ps.txt"):
        os.remove("GELABEL_ps.txt")
        
    s = plot.ConcentrationPlotSettings()
    o = gisout.KMLWriter(s.kml_option)

    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
    
    o.initialize(s.gis_alt_mode,
                 s.output_basename,
                 s.output_suffix,
                 s.KMAP,
                 s.NSSLBL,
                 s.show_max_conc,
                 s.NDEP)
    
    ax = plt.axes()
    quad_contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                                    [1.0e-15, 1.0e-12],
                                    colors=["#ff0000", "#00ff00"],
                                    extend="max")
    plt.close(ax.figure)
    
    contour_set = cntr.convert_matplotlib_quadcontourset(quad_contour_set)
    contour_set.raw_colors = [(1.0, 1.0, 1.0), (1.0, 0.0, 0.0)]
    contour_set.colors = ["#ff0000", "#00ff00"]
    contour_set.levels = [1.0e-15, 1.0e-12]
    contour_set.levels_str = ["1.0e-15", "1.0e-12"]
    contour_set.labels = ["USER-2", "USER-1"]
    contour_set.concentration_unit = "mass/m^3"
    contour_set.min_concentration = 1.0e-16
    contour_set.max_concentration = 8.0e-12
    contour_set.min_concentration_str = "1.0e-16"
    contour_set.max_concentration_str = "8.0e-12"
    
    try:
        o.write("HYSPLIT_ps", g, contour_set, 100, 500)
        o.finalize()
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
        
    assert os.path.exists("HYSPLIT_ps.kml")
    assert os.path.exists("GELABEL_ps.txt")

    os.remove("HYSPLIT_ps.kml")
    os.remove("GELABEL_ps.txt")


def test_KMLWriter_finalize():
    s = plot.ConcentrationPlotSettings()
    o = gisout.KMLWriter(s.kml_option)
    
    try:
        o.finalize()
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))


def test_KMLWriter__get_att_datetime_str():
    s = plot.ConcentrationPlotSettings()
    o = gisout.KMLWriter(s.kml_option)
    utc = pytz.utc
    
    dt = datetime.datetime(2019, 7, 2, 14, 50, 0, 0, utc)
    assert o._get_att_datetime_str(dt) == "1450 UTC Jul 02 2019&"


def test_KMLWriter__quote_if_space_present():
    s = plot.ConcentrationPlotSettings()
    o = gisout.KMLWriter(s.kml_option)
    
    assert o._quote_if_space_present("1.0e-12") == "1.0e-12"
    assert o._quote_if_space_present("0-6 hours") == "\"0-6 hours\""
    assert o._quote_if_space_present(12) == "12"
    assert o._quote_if_space_present(3.14) == "3.14"
    
    
def test_KMLWriter__write_attributes(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    o = gisout.KMLWriter(s.kml_option)

    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
    
    o.initialize(s.gis_alt_mode,
                 s.output_basename,
                 s.output_suffix,
                 s.KMAP,
                 s.NSSLBL,
                 s.show_max_conc,
                 s.NDEP)
    
    ax = plt.axes()
    quad_contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                                    [1.0e-15, 1.0e-12],
                                    colors=["#ff0000", "#00ff00"],
                                    extend="max")
    plt.close(ax.figure)
    
    contour_set = cntr.convert_matplotlib_quadcontourset(quad_contour_set)
    contour_set.raw_colors = [(1.0, 1.0, 1.0), (1.0, 0.0, 0.0)]
    contour_set.colors = ["#ff0000", "#00ff00"]
    contour_set.levels = [1.0e-15, 1.0e-12]
    contour_set.levels_str = ["1.0e-15", "1.0e-12"]
    contour_set.labels = ["USER-2", "USER-1"]
    contour_set.concentration_unit = "mass/m^3"
    contour_set.min_concentration = 1.0e-16
    contour_set.max_concentration = 8.0e-12
    contour_set.min_concentration_str = "1.0e-16"
    contour_set.max_concentration_str = "8.0e-12"
    
    f = open("__KMLWriter.txt", "wt")
    
    try:
        o._write_attributes(f, g, contour_set)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
        
    f.close()
    
    f = open("__KMLWriter.txt", "rt")
    lines = f.read().splitlines()
    f.close()
    
    assert lines[0] == "1"
    assert lines[1] == "mass/m^3&"
    assert lines[2] == "Integrated: 1700 UTC Sep 25 1983&"
    assert lines[3] == "        to: 0500 UTC Sep 26 1983&"
    assert lines[4] == "8.0e-12 1.0e-16  2"
    assert lines[5] == "1.0e-15 1.0e-12 "
    assert lines[6] == " 1.00 1.00 1.00"
    assert lines[7] == " 1.00 1.00 0.00"
    assert lines[8] == " 1.00 1.00 0.00"
    assert lines[9] == "USER-1   USER-2   "
    
    os.remove("__KMLWriter.txt")
    
    
def test_KMLWriter__write_attributes_case2(cdump_two_pollutants):
    # Test for chemical thresholds.
    s = plot.ConcentrationPlotSettings()
    o = gisout.KMLWriter(s.kml_option)

    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
    
    o.initialize(s.gis_alt_mode,
                 s.output_basename,
                 s.output_suffix,
                 const.ConcentrationMapType.THRESHOLD_LEVELS,
                 s.NSSLBL,
                 s.show_max_conc,
                 s.NDEP)
    
    ax = plt.axes()
    quad_contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                                    [1.0e-15, 1.0e-12],
                                    colors=["#ff0000", "#00ff00"],
                                    extend="max")
    plt.close(ax.figure)
    
    contour_set = cntr.convert_matplotlib_quadcontourset(quad_contour_set)
    contour_set.raw_colors = [(1.0, 1.0, 1.0), (1.0, 0.0, 0.0)]
    contour_set.colors = ["#ff0000", "#00ff00"]
    contour_set.levels = [1.0e-15, 1.0e-12]
    contour_set.levels_str = ["1.0e-15", "1.0e-12"]
    contour_set.labels = ["USER-2", "USER-1"]
    contour_set.concentration_unit = "mass/m^3"
    contour_set.min_concentration = 1.0e-16
    contour_set.max_concentration = 8.0e-12
    contour_set.min_concentration_str = "1.0e-16"
    contour_set.max_concentration_str = "8.0e-12"
    
    f = open("__KMLWriter.txt", "wt")
    
    try:
        o._write_attributes(f, g, contour_set)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
        
    f.close()
    
    f = open("__KMLWriter.txt", "rt")
    lines = f.read().splitlines()
    f.close()
    
    assert lines[0] == "4"
    assert lines[1] == "mass/m^3&"
    assert lines[2] == "Integrated: 1700 UTC Sep 25 1983&"
    assert lines[3] == "        to: 0500 UTC Sep 26 1983&"
    assert lines[4] == "8.0e-12 1.0e-16  4"
    assert lines[5] == "0       0       1.0e-15 1.0e-12 "
    assert lines[6] == " 1.00 1.00 1.00 1.00 1.00"
    assert lines[7] == " 1.00 1.00 1.00 1.00 0.00"
    assert lines[8] == " 1.00 1.00 1.00 1.00 0.00"
    assert lines[9] == "USER-1   USER-2                     "
    
    os.remove("__KMLWriter.txt")


def test_PartialKMLWriter___init__():
    kml_option = 1
    o = gisout.PartialKMLWriter(kml_option)
    assert o.kml_option == 1
    assert hasattr(o, 'att_file')
    assert hasattr(o, 'contour_writer')
    assert hasattr(o, 'xml_root')
    assert hasattr(o, 'kml_filename')

    tz = pytz.timezone("America/New_York")
    o = gisout.PartialKMLWriter(kml_option, tz)
    assert o.time_zone is tz


def test_PartialKMLWriter_write(cdump_two_pollutants):
    # delete files we are about to create
    if os.path.exists("HYSPLIT_ps.txt"):
        os.remove("HYSPLIT_ps.txt")
    if os.path.exists("GELABEL_ps.txt"):
        os.remove("GELABEL_ps.txt")
        
    s = plot.ConcentrationPlotSettings()
    o = gisout.PartialKMLWriter(s.kml_option)

    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
    
    o.initialize(s.gis_alt_mode,
                 s.output_basename,
                 s.output_suffix,
                 s.KMAP,
                 s.NSSLBL,
                 s.show_max_conc,
                 s.NDEP)
    
    ax = plt.axes()
    quad_contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                                    [1.0e-15, 1.0e-12],
                                    colors=["#ff0000", "#00ff00"],
                                    extend="max")
    plt.close(ax.figure)
    
    contour_set = cntr.convert_matplotlib_quadcontourset(quad_contour_set)
    contour_set.raw_colors = [(1.0, 1.0, 1.0), (1.0, 0.0, 0.0)]
    contour_set.colors = ["#ff0000", "#00ff00"]
    contour_set.levels = [1.0e-15, 1.0e-12]
    contour_set.levels_str = ["1.0e-15", "1.0e-12"]
    contour_set.labels = ["USER-2", "USER-1"]
    contour_set.concentration_unit = "mass/m^3"
    contour_set.min_concentration = 1.0e-16
    contour_set.max_concentration = 8.0e-12
    contour_set.min_concentration_str = "1.0e-16"
    contour_set.max_concentration_str = "8.0e-12"
    
    try:
        o.write("HYSPLIT_ps", g, contour_set, 100, 500)
        o.finalize()
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
        
    assert os.path.exists("HYSPLIT_ps.txt")
    assert os.path.exists("GELABEL_ps.txt")
        
    os.remove("HYSPLIT_ps.txt")
    os.remove("GELABEL_ps.txt")


def test_PartialKMLWriter_finalize():
    s = plot.ConcentrationPlotSettings()
    o = gisout.PartialKMLWriter(s.kml_option)
    
    try:
        o.finalize()
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))


def test_PartialKMLWriter__write_attributes(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    o = gisout.PartialKMLWriter(s.kml_option)
    
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
    
    o.initialize(s.gis_alt_mode,
                 s.output_basename,
                 s.output_suffix,
                 s.KMAP,
                 s.NSSLBL,
                 s.show_max_conc,
                 s.NDEP)
    
    ax = plt.axes()
    quad_contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                                    [1.0e-15, 1.0e-12],
                                    colors=["#ff0000", "#00ff00"],
                                    extend="max")
    plt.close(ax.figure)
    
    contour_set = cntr.convert_matplotlib_quadcontourset(quad_contour_set)
    contour_set.raw_colors = [(1.0, 1.0, 1.0), (1.0, 0.0, 0.0)]
    contour_set.colors = ["#ff0000", "#00ff00"]
    contour_set.levels = [1.0e-15, 1.0e-12]
    contour_set.levels_str = ["1.0e-15", "1.0e-12"]
    contour_set.labels = ["USER-2", "USER-1"]
    contour_set.concentration_unit = "mass/m^3"
    contour_set.min_concentration = 1.0e-16
    contour_set.max_concentration = 8.0e-12
    contour_set.min_concentration_str = "1.0e-16"
    contour_set.max_concentration_str = "8.0e-12"
    
    f = open("__PartialKMLWriter.txt", "wt")
    
    try:
        o._write_attributes(f, g, contour_set)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
    
    f.close()
    
    os.remove("__PartialKMLWriter.txt")

   
def test_KMLContourWriterFactory_create_instance():
    gis_alt_mode = 0
    tz = pytz.timezone("America/New_York")
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.CONCENTRATION, gis_alt_mode, tz)
    assert isinstance(w, gisout.KMLConcentrationWriter)
    assert w.time_zone is tz
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.EXPOSURE, gis_alt_mode, tz)
    assert isinstance(w, gisout.KMLConcentrationWriter)
    assert w.time_zone is tz
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.DEPOSITION, gis_alt_mode, tz)
    assert isinstance(w, gisout.KMLDepositionWriter)
    assert w.time_zone is tz
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.THRESHOLD_LEVELS, gis_alt_mode, tz)
    assert isinstance(w, gisout.KMLChemicalThresholdWriter)
    assert w.time_zone is tz
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.VOLCANIC_ERUPTION, gis_alt_mode, tz)
    assert isinstance(w, gisout.KMLDepositionWriter)
    assert w.time_zone is tz
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.DEPOSITION_6, gis_alt_mode, tz)
    assert isinstance(w, gisout.KMLDepositionWriter)
    assert w.time_zone is tz
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.MASS_LOADING, gis_alt_mode, tz)
    assert isinstance(w, gisout.KMLMassLoadingWriter)
    assert w.time_zone is tz
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.TIME_OF_ARRIVAL, gis_alt_mode, tz)
    assert isinstance(w, gisout.KMLTimeOfArrivalWriter)
    assert w.time_zone is tz
        
   
def test_KMLContourWriterFactory_create_instance__without_time_zone():
    gis_alt_mode = 0
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.CONCENTRATION, gis_alt_mode)
    assert isinstance(w, gisout.KMLConcentrationWriter)
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.EXPOSURE, gis_alt_mode)
    assert isinstance(w, gisout.KMLConcentrationWriter)
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.DEPOSITION, gis_alt_mode)
    assert isinstance(w, gisout.KMLDepositionWriter)
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.THRESHOLD_LEVELS, gis_alt_mode)
    assert isinstance(w, gisout.KMLChemicalThresholdWriter)
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.VOLCANIC_ERUPTION, gis_alt_mode)
    assert isinstance(w, gisout.KMLDepositionWriter)
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.DEPOSITION_6, gis_alt_mode)
    assert isinstance(w, gisout.KMLDepositionWriter)
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.MASS_LOADING, gis_alt_mode)
    assert isinstance(w, gisout.KMLMassLoadingWriter)
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.TIME_OF_ARRIVAL, gis_alt_mode)
    assert isinstance(w, gisout.KMLTimeOfArrivalWriter)
        
    
def test_AbstractKMLContourWriter___init__():
    o = AbstractKMLContourWriterTest("relativeToGround")
    assert o.frame_count == 0
    assert o.alt_mode_str == "relativeToGround"
    assert o.time_zone is None
    assert o.show_max_conc == True

    tz = pytz.timezone("America/New_York")
    o = AbstractKMLContourWriterTest("relativeToGround", tz)
    assert o.time_zone is tz


def test_AbstractKMLContourWriter_set_show_max_conc():
    o = AbstractKMLContourWriterTest("relativeToGround")
    
    o.set_show_max_conc( 0 )
    assert o.show_max_conc == False
    
    o.set_show_max_conc( 1 )
    assert o.show_max_conc == True


def test_AbstractKMLContourWriter__get_begin_end_timestamps(cdump_two_pollutants):
    o = AbstractKMLContourWriterTest("relativeToGround")
    g = cdump_two_pollutants.grids[0]
    
    a = o._get_begin_end_timestamps(g)
    assert a[0] == "1983-09-25T17:00:00Z"
    assert a[1] == "1983-09-26T05:00:00Z"
    
    o.time_zone = pytz.timezone("EST")
    a = o._get_begin_end_timestamps(g)
    assert a[0] == "1983-09-25T12:00:00-0500"
    assert a[1] == "1983-09-26T00:00:00-0500"


def test_AbstractKMLContourWriter__get_contour_name(cdump_two_pollutants):
    o = AbstractKMLContourWriterTest("relativeToGround")
    assert o._get_contour_name("300", "ppm") == "Contour Level: 300 ppm"

    
def test_AbstractKMLContourWriter_write(cdump_two_pollutants):
    o = AbstractKMLContourWriterTest("relativeToGround")
    
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
   
    ax = plt.axes()
    quad_contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                                    [1.0e-15, 1.0e-12],
                                    colors=["#ff0000", "#00ff00"],
                                    extend="max")
    plt.close(ax.figure)
    
    contour_set = cntr.convert_matplotlib_quadcontourset(quad_contour_set)
    contour_set.raw_colors = [(1.0, 1.0, 1.0), (1.0, 0.0, 0.0)]
    contour_set.colors = ["#ff0000", "#00ff00"]
    contour_set.levels = [1.0e-15, 1.0e-12]
    contour_set.levels_str = ["1.0e-15", "1.0e-12"]
    contour_set.labels = ["USER-2", "USER-1"]
    contour_set.concentration_unit = "mass/m^3"
    contour_set.min_concentration = 1.0e-16
    contour_set.max_concentration = 8.0e-12
    contour_set.min_concentration_str = "1.0e-16"
    contour_set.max_concentration_str = "8.0e-12"
    
    xml_root = ET.Element('kml')
    doc = ET.SubElement(xml_root, 'Document')
    
    try:
        o.write(xml_root, g, contour_set, 100, 500, "ps")
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))

    assert o.frame_count == 1


def test_AbstractKMLContourWriter__get_contour_height_at():
    o = AbstractKMLContourWriterTest("relativeToGround")
    
    assert o._get_contour_height_at(0, 100.0) == 100
    assert o._get_contour_height_at(1, 100.0) == 300
    assert o._get_contour_height_at(2, 100.0) == 500


def test_AbstractKMLContourWriter__write_contour(cdump_two_pollutants):
    o = AbstractKMLContourWriterTest("relativeToGround")
    
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
   
    ax = plt.axes()
    quad_contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                                    [1.0e-15, 1.0e-12],
                                    colors=["#ff0000", "#00ff00"],
                                    extend="max")
    plt.close(ax.figure)
    
    contour_set = cntr.convert_matplotlib_quadcontourset(quad_contour_set)
    contour_set.raw_colors = [(1.0, 1.0, 1.0), (1.0, 0.0, 0.0)]
    contour_set.colors = ["#ff0000", "#00ff00"]
    contour_set.levels = [1.0e-15, 1.0e-12]
    contour_set.levels_str = ["1.0e-15", "1.0e-12"]
    contour_set.labels = ["USER-2", "USER-1"]
    contour_set.concentration_unit = "mass/m^3"
    contour_set.min_concentration = 1.0e-16
    contour_set.max_concentration = 8.0e-12
    contour_set.min_concentration_str = "1.0e-16"
    contour_set.max_concentration_str = "8.0e-12"
    
    xml_root = ET.Element('kml')
    
    # just see if there is any exception
    try:
        o._write_contour(xml_root, g, contour_set, 100, True)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))


def test_AbstractKMLContourWriter__write_polygon(cdump_two_pollutants):
    o = AbstractKMLContourWriterTest("relativeToGround")
    
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
   
    ax = plt.axes()
    quad_contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                                    [1.0e-15, 1.0e-12],
                                    colors=["#ff0000", "#00ff00"],
                                    extend="max")
    plt.close(ax.figure)
    
    contour_set = cntr.convert_matplotlib_quadcontourset(quad_contour_set)
    contour_set.raw_colors = [(1.0, 1.0, 1.0), (1.0, 0.0, 0.0)]
    contour_set.colors = ["#ff0000", "#00ff00"]
    contour_set.levels = [1.0e-15, 1.0e-12]
    contour_set.levels_str = ["1.0e-15", "1.0e-12"]
    contour_set.labels = ["USER-2", "USER-1"]
    contour_set.concentration_unit = "mass/m^3"
    contour_set.min_concentration = 1.0e-16
    contour_set.max_concentration = 8.0e-12
    contour_set.min_concentration_str = "1.0e-16"
    contour_set.max_concentration_str = "8.0e-12"
    
    xml_root = ET.Element('kml')
    
    # just see if there is any exception
    try:
        o._write_polygon(xml_root, contour_set.contours[0].polygons[0], 100)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))


def test_AbstractKMLContourWriter__write_boundary(cdump_two_pollutants):
    o = AbstractKMLContourWriterTest("relativeToGround")
    
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
   
    ax = plt.axes()
    quad_contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                                    [1.0e-15, 1.0e-12],
                                    colors=["#ff0000", "#00ff00"],
                                    extend="max")
    plt.close(ax.figure)
    
    contour_set = cntr.convert_matplotlib_quadcontourset(quad_contour_set)
    contour_set.raw_colors = [(1.0, 1.0, 1.0), (1.0, 0.0, 0.0)]
    contour_set.colors = ["#ff0000", "#00ff00"]
    contour_set.levels = [1.0e-15, 1.0e-12]
    contour_set.levels_str = ["1.0e-15", "1.0e-12"]
    contour_set.labels = ["USER-2", "USER-1"]
    contour_set.concentration_unit = "mass/m^3"
    contour_set.min_concentration = 1.0e-16
    contour_set.max_concentration = 8.0e-12
    contour_set.min_concentration_str = "1.0e-16"
    contour_set.max_concentration_str = "8.0e-12"
    
    xml_root = ET.Element('kml')
    
    # just see if there is any exception
    try:
        o._write_boundary(xml_root, contour_set.contours[0].polygons[0].boundaries[0], 100)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))


def test_AbstractKMLContourWriter__write_max_location(cdump_two_pollutants):
    o = AbstractKMLContourWriterTest("relativeToGround")
    
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
   
    cntr_labels = ["AEGL-1", "AEGL-2"]
    
    xml_root = ET.Element('kml')
    
    # just see if there is any exception
    try:
        o._write_max_location(xml_root, g, 8.0e-12, 300, cntr_labels[0])
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))


def test_AbstractKMLContourWriter__get_timestamp_str():
    o = AbstractKMLContourWriterTest("relativeToGround")
    utc = pytz.utc
    
    dt = datetime.datetime(2019, 7, 3, 8, 11, 0, 0, utc)
    assert o._get_timestamp_str(dt) == "20190703 0811 UTC"
    
    o.time_zone = pytz.timezone("EST")
    assert o._get_timestamp_str(dt) == "20190703 0311 EST"
    

def test_KMLConcentrationWriter___init__():
    o = gisout.KMLConcentrationWriter("relativeToGround")

    assert o.alt_mode_str == "relativeToGround"
    assert o.time_zone is None
    
    tz = pytz.timezone("America/New_York")
    o = gisout.KMLConcentrationWriter("relativeToGround", tz)

    assert o.alt_mode_str == "relativeToGround"
    assert o.time_zone is tz 


def test_KMLConcentrationWriter__get_name_cdata():
    o = gisout.KMLConcentrationWriter("relativeToGround")
    utc = pytz.utc
    
    dt = datetime.datetime(2019, 7, 5, 7, 42, 0, 0, utc)    
    assert o._get_name_cdata(dt) == """<pre>Concentration
(Valid:20190705 0742 UTC)</pre>"""


def test_KMLConcentrationWriter__get_description_cdata():
    o = gisout.KMLConcentrationWriter("relativeToGround")
    utc = pytz.utc
    
    dt = datetime.datetime(2019, 7, 5, 7, 42, 0, 0, utc)
    lower_level = util.LengthInMeters(100)
    upper_level = util.LengthInMeters(500)    
    assert o._get_description_cdata(lower_level, upper_level, dt) == """<pre>
Averaged from 100 m to 500 m
Valid:20190705 0742 UTC</pre>"""


def test_KMLConcentrationWriter__get_max_location_text():
    o = gisout.KMLConcentrationWriter("relativeToGround")
    
    assert o._get_max_location_text().strip().startswith("The square represents")


def test_KMLChemicalThresholdWriter___init__():
    o = gisout.KMLChemicalThresholdWriter("relativeToGround")

    assert o.alt_mode_str == "relativeToGround"
    assert o.time_zone is None
    
    tz = pytz.timezone("America/New_York")
    o = gisout.KMLChemicalThresholdWriter("relativeToGround", tz)

    assert o.alt_mode_str == "relativeToGround"
    assert o.time_zone is tz 


def test_KMLChemicalThresholdWriter__get_contour_height_at():
    o = gisout.KMLChemicalThresholdWriter("relativeToGround")
    
    assert o._get_contour_height_at(0, 100.0) == 100
    assert o._get_contour_height_at(1, 100.0) == 100
    assert o._get_contour_height_at(2, 100.0) == 500    


def test_KMLDepositionWriter___init__():
    o = gisout.KMLDepositionWriter("relativeToGround")

    assert o.alt_mode_str == "relativeToGround"
    assert o.time_zone is None
    
    tz = pytz.timezone("America/New_York")
    o = gisout.KMLDepositionWriter("relativeToGround", tz)

    assert o.alt_mode_str == "relativeToGround"
    assert o.time_zone is tz
    

def test_KMLDepositionWriter__get_name_cdata():
    o = gisout.KMLDepositionWriter("relativeToGround")
    utc = pytz.utc
    
    dt = datetime.datetime(2019, 7, 5, 7, 42, 0, 0, utc)
    assert o._get_name_cdata(dt) == """<pre>Deposition
(Valid:20190705 0742 UTC)</pre>"""


def test_KMLDepositionWriter__get_description_cdata():
    o = gisout.KMLDepositionWriter("relativeToGround")
    utc = pytz.utc
    
    dt = datetime.datetime(2019, 7, 5, 7, 42, 0, 0, utc)
    assert o._get_description_cdata(100, 500, dt) == """<pre>
Valid:20190705 0742 UTC</pre>"""

    
def test_KMLDepositionWriter__get_max_location_text():
    o = gisout.KMLDepositionWriter("relativeToGround")
    
    assert o._get_max_location_text().strip().startswith("The square represents")

    
def test_KMLDepositionWriter__write_placemark_visibility():
    o = gisout.KMLDepositionWriter("relativeToGround")
    
    xml_root = ET.Element('kml')
    o.frame_count = 2
    o._write_placemark_visibility(xml_root)
    tree = ET.ElementTree(xml_root)
    tree.write("__KMLDepositionWriter.txt")
    
    f = open("__KMLDepositionWriter.txt", "rt")
    lines = f.read().splitlines()
    f.close()
    
    assert lines[0].strip() == "<kml><visibility>0</visibility></kml>"

    os.remove("__KMLDepositionWriter.txt")


def test_KMLMassLoadingWriter___init__():
    o = gisout.KMLMassLoadingWriter("relativeToGround")

    assert o.alt_mode_str == "relativeToGround"
    assert o.time_zone is None
    
    tz = pytz.timezone("America/New_York")
    o = gisout.KMLMassLoadingWriter("relativeToGround", tz)

    assert o.alt_mode_str == "relativeToGround"
    assert o.time_zone is tz
    

def test_KMLMassLoadingWriter__get_name_cdata():
    o = gisout.KMLMassLoadingWriter("relativeToGround")
    utc = pytz.utc
    
    dt = datetime.datetime(2019, 7, 5, 7, 42, 0, 0, utc)
    assert o._get_name_cdata(dt) == """<pre>Mass_loading
(Valid:20190705 0742 UTC)</pre>"""


def test_KMLMassLoadingWriter__get_description_cdata():
    o = gisout.KMLMassLoadingWriter("relativeToGround")
    utc = pytz.utc
    
    dt = datetime.datetime(2019, 7, 5, 7, 42, 0, 0, utc)
    lower_level = util.LengthInMeters(100)
    upper_level = util.LengthInMeters(500)
    assert o._get_description_cdata(lower_level, upper_level, dt) == """<pre>
From 100 m to 500 m
Valid:20190705 0742 UTC</pre>"""

    
def test_KMLMassLoadingWriter__get_max_location_text():
    o = gisout.KMLMassLoadingWriter("relativeToGround")
    
    assert o._get_max_location_text().strip().startswith("The square represents")

    
def test_KMLMassLoadingWriter__write_placemark_visibility():
    o = gisout.KMLMassLoadingWriter("relativeToGround")
    
    xml_root = ET.Element('kml');
    o.frame_count = 2
    o._write_placemark_visibility(xml_root)
    tree = ET.ElementTree(xml_root)
    tree.write("__KMLMassLoadingWriter.txt")

    f = open("__KMLMassLoadingWriter.txt", "rt")
    lines = f.read().splitlines()
    f.close()
    
    assert lines[0].strip() == "<kml><visibility>0</visibility></kml>"

    os.remove("__KMLMassLoadingWriter.txt")


def test_KMLTimeOfArrivalWriter___init__():
    o = gisout.KMLTimeOfArrivalWriter("relativeToGround")

    assert o.alt_mode_str == "relativeToGround"
    assert o.time_zone is None
    
    tz = pytz.timezone("America/New_York")
    o = gisout.KMLTimeOfArrivalWriter("relativeToGround", tz)

    assert o.alt_mode_str == "relativeToGround"
    assert o.time_zone is tz
    

def test_KMLTimeOfArrivalWriter__get_name_cdata():
    o = gisout.KMLTimeOfArrivalWriter("relativeToGround")
    utc = pytz.utc
    
    dt = datetime.datetime(2019, 7, 5, 7, 42, 0, 0, utc)
    assert o._get_name_cdata(dt) == """<pre>Time of arrival (h)
(Valid:20190705 0742 UTC)</pre>"""


def test_KMLTimeOfArrivalWriter__get_description_cdata():
    o = gisout.KMLTimeOfArrivalWriter("relativeToGround")
    utc = pytz.utc
    
    dt = datetime.datetime(2019, 7, 5, 7, 42, 0, 0, utc)
    lower_level = util.LengthInMeters(100)
    upper_level = util.LengthInMeters(500)
    assert o._get_description_cdata(lower_level, upper_level, dt) == """<pre>
Averaged from 100 m to 500 m
Valid:20190705 0742 UTC</pre>"""

    lower_level = util.LengthInMeters(0)
    upper_level = util.LengthInMeters(0)
    assert o._get_description_cdata(lower_level, upper_level, dt) == """<pre>
At ground-level
Valid:20190705 0742 UTC</pre>"""


def test_KMLTimeOfArrivalWriter__get_contour_name():
    o = gisout.KMLTimeOfArrivalWriter("relativeToGround")
    assert o._get_contour_name("0-6 hours", "Bq") == "Time of arrival: 0-6 hours"

