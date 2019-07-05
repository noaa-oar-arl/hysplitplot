import pytest
import logging
import datetime
import matplotlib.pyplot as plt
import os
from hysplit4.conc import gisout, model, plot, helper, cntr
from hysplit4 import const


logger = logging.getLogger(__name__)


@pytest.fixture
def cdump_two_pollutants():
    return model.ConcentrationDump().get_reader().read("data/cdump_two_pollutants")
    

# Concrete classes to test abstract classes
class AbstractWriterTest(gisout.AbstractWriter):
    
    def make_output_basename(self, g, conc_type, depo_sum, output_basename, output_suffix, KMLOUT, upper_vert_level):
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
    
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.GENERATE_POINTS, kml_option)
    assert isinstance(w, gisout.PointsGenerateFileWriter)
    assert isinstance(w.formatter, gisout.PointsGenerateFileWriter.DecimalFormWriter)
    
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.GENERATE_POINTS_2, kml_option)
    assert isinstance(w, gisout.PointsGenerateFileWriter)
    assert isinstance(w.formatter, gisout.PointsGenerateFileWriter.ExponentFormWriter)
    
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.KML, 1)
    assert isinstance(w, gisout.KMLWriter)
    assert w.kml_option == 1
     
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.PARTIAL_KML, 1)
    assert isinstance(w, gisout.PartialKMLWriter)
    assert w.kml_option == 1
     
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.NONE, kml_option)
    assert isinstance(w, gisout.IdleWriter)


def test_AbstractWriter___init__():
    o = AbstractWriterTest()
    assert o.alt_mode_str == "clampedToGround"
    assert o.KMLOUT == 0
    assert o.output_suffix == "ps"
    assert o.KMAP == const.ConcentrationMapType.CONCENTRATION


def test_AbstractWriter_initialize():
    o = AbstractWriterTest()
    o.initialize(0, 2, "3", 5, 6, 7)
    assert o.alt_mode_str == "clampedToGround"
    assert o.KMLOUT == 2
    assert o.output_suffix == "3"
    assert o.KMAP == 5
    assert o.NSSLBL == 6
    assert o.show_max_conc == 7


def test_AbstractWriter_write():
    o = AbstractWriterTest()
    try:
        # a silly test
        o.write(1, 2, 3, 4, 5)
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
        o.make_output_basename(1, 2, 3, 4, 5, 6, 7)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))


def test_AbstractWriter__reformat_color():
    assert gisout.AbstractWriter._reformat_color("#face01") == "C801CEFA"


def test_AbstractWriter__get_iso_8601_str():
    dt = datetime.datetime(19, 7, 2, 13, 28, 5)
    assert gisout.AbstractWriter._get_iso_8601_str(dt) == "2019-07-02T13:28:05Z"


def test_IdleWriter___init__():
    try:
        o = gisout.IdleWriter()
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))


def test_IdleWriter_make_output_basename():
    o = gisout.IdleWriter()
    try:
        # a silly test
        o.make_output_basename(1, 2, 3, 4, 5, 6, 7)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
        

def test_PointsGenerateFileWriter___init__():
    o = gisout.PointsGenerateFileWriter( gisout.PointsGenerateFileWriter.DecimalFormWriter() )
    assert isinstance( o.formatter, gisout.PointsGenerateFileWriter.DecimalFormWriter )


def test_PointsGenerateFileWriter_make_output_basename(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    conc_type = helper.ConcentrationTypeFactory.create_instance( s.KAVG )
    depo_sum = helper.DepositSumFactory.create_instance(s.NDEP,
                                                     cdump_two_pollutants.has_ground_level_grid())
    
    o = gisout.PointsGenerateFileWriter( gisout.PointsGenerateFileWriter.DecimalFormWriter() )
    g = cdump_two_pollutants.grids[0]
    basename = o.make_output_basename(g, conc_type, depo_sum, "output", "ps", s.KMLOUT, 500)
    assert basename == "GIS_00100_ps_01"
        

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
                 s.show_max_conc)

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


def test_KMLWriter___init__():
    kml_option = 1
    o = gisout.KMLWriter(kml_option)
    assert o.kml_option == 1
    assert o.kml_file is None
    assert o.att_file is None
    assert o.contour_writer is None


def test_KMLWriter_make_output_basename(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    conc_type = helper.ConcentrationTypeFactory.create_instance( s.KAVG )
    depo_sum = helper.DepositSumFactory.create_instance(s.NDEP,
                                                     cdump_two_pollutants.has_ground_level_grid())
    
    o = gisout.KMLWriter(s.kml_option)
    g = cdump_two_pollutants.grids[0]
    basename = o.make_output_basename(g, conc_type, depo_sum, "output", "ps", s.KMLOUT, 500)
    assert basename == "HYSPLIT_ps" and s.KMLOUT == 0
        

def test_KMLWriter_initialize(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    o = gisout.KMLWriter(s.kml_option)

    o.initialize(s.gis_alt_mode,
                 s.KMLOUT,
                 s.output_suffix,
                 s.KMAP,
                 s.NSSLBL,
                 s.show_max_conc)
    
    assert isinstance(o.contour_writer, gisout.AbstractKMLContourWriter)


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
                 s.KMLOUT,
                 s.output_suffix,
                 s.KMAP,
                 s.NSSLBL,
                 s.show_max_conc)
    
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
    dt = datetime.datetime(19, 7, 2, 14, 50)
    assert gisout.KMLWriter._get_att_datetime_str(dt) == "1450 UTC Jul 02 2019&"


def test_KMLWriter__write_attributes(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    o = gisout.KMLWriter(s.kml_option)

    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
    
    o.initialize(s.gis_alt_mode,
                 s.KMLOUT,
                 s.output_suffix,
                 s.KMAP,
                 s.NSSLBL,
                 s.show_max_conc)
    
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
    assert lines[4] == "8.0e-12 1.0e-16 2"
    assert lines[5] == "1.0e-15 1.0e-12 "
    assert lines[6] == "1.00 1.00 "
    assert lines[7] == "1.00 0.00 "
    assert lines[8] == "1.00 0.00 "
    assert lines[9] == "USER-2 USER-1 "
    
    os.remove("__KMLWriter.txt")


def test_PartialKMLWriter___init__():
    kml_option = 1
    o = gisout.PartialKMLWriter(kml_option)
    assert o.kml_option == 1
    assert o.kml_file is None
    assert o.att_file is None
    assert o.contour_writer is None


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
                 s.KMLOUT,
                 s.output_suffix,
                 s.KMAP,
                 s.NSSLBL,
                 s.show_max_conc)
    
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
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
        
    assert os.path.exists("HYSPLIT_ps.txt")
    assert os.path.exists("GELABEL_ps.txt")
        
    os.remove("HYSPLIT_ps.txt")
    os.remove("GELABEL_ps.txt")


def test_PartialKMLWriter__write_attributes(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    o = gisout.PartialKMLWriter(s.kml_option)
    
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)

    contour_set = None
                  
    f = open("__PartialKMLWriter.txt", "wt")
    
    try:
        o._write_attributes(f, g, contour_set)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
    
    f.close()
    
    os.remove("__PartialKMLWriter.txt")

   
def test_KMLContourWriterFactory_create_instance():
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
    
    
def test_AbstractKMLContourWriter___init__():
    o = AbstractKMLContourWriterTest("relativeToGround")
    assert o.frame_count == 0
    assert o.alt_mode_str == "relativeToGround"


def test_AbstractKMLContourWriter__get_begin_end_timestamps(cdump_two_pollutants):
    g = cdump_two_pollutants.grids[0]
    
    a = gisout.AbstractKMLContourWriter._get_begin_end_timestamps(g)
    assert a[0] == "1983-09-25T17:00:00Z"
    assert a[1] == "1983-09-26T05:00:00Z"
    
    
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
    
    f = open("__AbstractKMLContourWriter.txt", "wt")
    
    try:
        o.write(f, g, contour_set, 100, 500, "ps")
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))

    f.close()
    
    assert o.frame_count == 1
    
    os.remove("__AbstractKMLContourWriter.txt")


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
    
    f = open("__AbstractKMLContourWriter.txt", "wt")
    
    # just see if there is any exception
    try:
        o._write_contour(f, g, contour_set, 100)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
        
    f.close()
    
    os.remove("__AbstractKMLContourWriter.txt")


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
    
    f = open("__AbstractKMLContourWriter.txt", "wt")
    
    # just see if there is any exception
    try:
        o._write_polygon(f, contour_set.contours[0].polygons[0], 100)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
            
    f.close()
    
    os.remove("__AbstractKMLContourWriter.txt")


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
    
    f = open("__AbstractKMLContourWriter.txt", "wt")
    
    # just see if there is any exception
    try:
        o._write_boundary(f, contour_set.contours[0].polygons[0].boundaries[0], 100)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
            
    f.close()
    
    os.remove("__AbstractKMLContourWriter.txt")


def test_AbstractKMLContourWriter__write_max_location(cdump_two_pollutants):
    o = AbstractKMLContourWriterTest("relativeToGround")
    
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
   
    cntr_labels = ["AEGL-1", "AEGL-2"]
    
    f = open("__AbstractKMLContourWriter.txt", "wt")
    
    # just see if there is any exception
    try:
        o._write_max_location(f, g, 8.0e-12, 300, cntr_labels[0])
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
            
    f.close()
    
    os.remove("__AbstractKMLContourWriter.txt")


def test_AbstractKMLContourWriter__get_timestamp_str():
    dt = datetime.datetime(19, 7, 3, 8, 11)
    assert gisout.AbstractKMLContourWriter._get_timestamp_str(dt) == "20190703 0811 UTC"
    

def test_KMLConcentrationWriter___init__():
    o = gisout.KMLConcentrationWriter("relativeToGround")

    assert o.alt_mode_str == "relativeToGround"


def test_KMLDepositionWriter__get_name_cdata():
    o = gisout.KMLConcentrationWriter("relativeToGround")
    
    dt = datetime.datetime(19, 7, 5, 7, 42)
    assert o._get_name_cdata(dt) == """<pre>Concentration
(Valid:20190705 0742 UTC)</pre>"""


def test_KMLDepositionWriter__get_description_cdata():
    o = gisout.KMLConcentrationWriter("relativeToGround")
    
    dt = datetime.datetime(19, 7, 5, 7, 42)
    assert o._get_description_cdata(100, 500, dt) == """<pre>
Averaged from 100 to 500 m
Valid:20190705 0742 UTC</pre>"""


def test_KMLConcentrationWriter__get_max_location_text():
    o = gisout.KMLConcentrationWriter("relativeToGround")
    
    assert o._get_max_location_text().strip().startswith("The square represents")


def test_KMLChemicalThresholdWriter___init__():
    o = gisout.KMLChemicalThresholdWriter("relativeToGround")

    assert o.alt_mode_str == "relativeToGround"


def test_KMLChemicalThresholdWriter__get_contour_height_at():
    o = gisout.KMLChemicalThresholdWriter("relativeToGround")
    
    assert o._get_contour_height_at(0, 100.0) == 100
    assert o._get_contour_height_at(1, 100.0) == 100
    assert o._get_contour_height_at(2, 100.0) == 500    


def test_KMLDepositionWriter___init__():
    o = gisout.KMLMassLoadingWriter("relativeToGround")

    assert o.alt_mode_str == "relativeToGround"


def test_KMLDepositionWriter__get_name_cdata():
    o = gisout.KMLDepositionWriter("relativeToGround")
    
    dt = datetime.datetime(19, 7, 5, 7, 42)
    assert o._get_name_cdata(dt) == """<pre>Deposition
(Valid:20190705 0742 UTC)</pre>"""


def test_KMLDepositionWriter__get_description_cdata():
    o = gisout.KMLDepositionWriter("relativeToGround")
    
    dt = datetime.datetime(19, 7, 5, 7, 42)
    assert o._get_description_cdata(100, 500, dt) == """<pre>
Valid:20190705 0742 UTC</pre>"""

    
def test_KMLDepositionWriter__get_max_location_text():
    o = gisout.KMLDepositionWriter("relativeToGround")
    
    assert o._get_max_location_text().strip().startswith("The square represents")

    
def test_KMLDepositionWriter__write_placemark_visibility():
    o = gisout.KMLDepositionWriter("relativeToGround")
    
    f = open("__KMLDepositionWriter.txt", "wt")
    o.frame_count = 2
    o._write_placemark_visibility(f)
    f.close()

    f = open("__KMLDepositionWriter.txt", "rt")
    lines = f.read().splitlines()
    f.close()
    
    assert lines[0].strip() == "<visibility>0</visibility>"

    os.remove("__KMLDepositionWriter.txt")


def test_KMLMassLoadingWriter___init__():
    o = gisout.KMLMassLoadingWriter("relativeToGround")

    assert o.alt_mode_str == "relativeToGround"


def test_KMLMassLoadingWriter__get_name_cdata():
    o = gisout.KMLMassLoadingWriter("relativeToGround")
    
    dt = datetime.datetime(19, 7, 5, 7, 42)
    assert o._get_name_cdata(dt) == """<pre>Mass_loading
(Valid:20190705 0742 UTC)</pre>"""


def test_KMLMassLoadingWriter__get_description_cdata():
    o = gisout.KMLMassLoadingWriter("relativeToGround")
    
    dt = datetime.datetime(19, 7, 5, 7, 42)
    assert o._get_description_cdata(100, 500, dt) == """<pre>
From 100 to 500 m
Valid:20190705 0742 UTC</pre>"""

    
def test_KMLMassLoadingWriter__get_max_location_text():
    o = gisout.KMLMassLoadingWriter("relativeToGround")
    
    assert o._get_max_location_text().strip().startswith("The square represents")

    
def test_KMLMassLoadingWriter__write_placemark_visibility():
    o = gisout.KMLMassLoadingWriter("relativeToGround")
    
    f = open("__KMLMassLoadingWriter.txt", "wt")
    o.frame_count = 2
    o._write_placemark_visibility(f)
    f.close()

    f = open("__KMLMassLoadingWriter.txt", "rt")
    lines = f.read().splitlines()
    f.close()
    
    assert lines[0].strip() == "<visibility>0</visibility>"

    os.remove("__KMLMassLoadingWriter.txt")