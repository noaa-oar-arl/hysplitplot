import pytest
import logging
import datetime
import matplotlib.pyplot as plt
import os
from hysplit4.conc import gisout, model, plot, helper
from hysplit4 import const


logger = logging.getLogger(__name__)


@pytest.fixture
def cdump_two_pollutants():
    return model.ConcentrationDump().get_reader().read("data/cdump_two_pollutants")
    

# Concrete classes to test abstract classes
class AbstractKMLContourWriterTest(gisout.AbstractKMLContourWriter):
    
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
    o = gisout.AbstractWriter()
    assert o.gis_alt_mode == const.GISOutputAltitude.CLAMPED_TO_GROUND
    assert o.KMLOUT == 0
    assert o.output_basename == "output"
    assert o.output_suffix == "ps"
    assert o.conc_type is None
    assert o.depo_type is None
    assert o.KMAP == const.ConcentrationMapType.CONCENTRATION


def test_AbstractWriter_initialize():
    o = gisout.AbstractWriter()
    o.initialize(1, 2, "3", "4", 5, 6, 7, 8, 9, 10, ["11"])
    assert o.gis_alt_mode == 1
    assert o.KMLOUT == 2
    assert o.output_basename == "3"
    assert o.output_suffix == "4"
    assert o.conc_type == 5     # should have been an object
    assert o.conc_map == 6      # should have been an object
    assert o.depo_type == 7     # should have been an object
    assert o.KMAP == 8
    assert o.NSSLBL == 9
    assert o.show_max_conc == 10
    assert o.contour_labels == ["11"]


def test_AbstractWriter_write():
    o = gisout.AbstractWriter()
    try:
        # a silly test
        o.write(1, 2, 3, 4, 5, 6, 7, 8, 9)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))


def test_AbstractWriter_write():
    o = gisout.AbstractWriter()
    try:
        # a silly test
        o.finalize()
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


def test_PointsGenerateFileWriter___init__():
    o = gisout.PointsGenerateFileWriter( gisout.PointsGenerateFileWriter.DecimalFormWriter() )
    assert isinstance( o.formatter, gisout.PointsGenerateFileWriter.DecimalFormWriter )


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
    depo_type = helper.DepositFactory.create_instance(s.NDEP,
                                                      cdump_two_pollutants.has_ground_level_grid())
    g = cdump_two_pollutants.grids[0]
    
    o.initialize(s.gis_alt_mode,
                 s.KMLOUT,
                 s.output_basename,
                 s.output_suffix,
                 conc_type,
                 conc_map,
                 depo_type,
                 s.KMAP,
                 s.NSSLBL,
                 s.show_max_conc,
                 ["a", "b"])

    ax = plt.axes()
    contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                               [1.0e-15, 1.0e-12],
                               colors=["#ff0000", "#00ff00"],
                               extend="max")
    plt.close(ax.figure)
    
    raw_colors = [(1.0, 1.0, 1.0), (1.0, 0.0, 0.0)]
    
    try:
        o.write(g, 10, 100, 500, contour_set, 1.0e-15, 8.0e-12, "mass/m^3", raw_colors)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
        
    assert os.path.exists("GIS_00100_ps_01.att")
    assert os.path.exists("GIS_00100_ps_01.txt")
    
    os.remove("GIS_00100_ps_01.att")
    os.remove("GIS_00100_ps_01.txt")


def test_DecimalFormWriter_write_seg():
    o = gisout.PointsGenerateFileWriter.DecimalFormWriter()
    seg = [[1.0, 1.2], [2.0, 2.2], [3.0, 3.2]]
    
    f = open("__decimalFormWriter.txt", "wt")
    o.write_seg(f, seg, 1.0e-05)
    f.close()
    
    f = open("__decimalFormWriter.txt", "rt")
    lines = f.read().splitlines()
    f.close()
    
    assert lines[0] == "  -5.00000,    1.00000,    1.20000"
    assert lines[1] == "   2.00000,    2.20000"
    assert lines[3] == "END"
    
    os.remove("__decimalFormWriter.txt")


def test_DecimalFormWriter_write_att(cdump_two_pollutants):
    o = gisout.PointsGenerateFileWriter.DecimalFormWriter()
    g = cdump_two_pollutants.grids[0]
    
    f = open("__decimalFormWriter.txt", "wt")
    o.write_att(f, g, 100, 300, 1.0e-5, "#ff0000")
    f.close()
    
    f = open("__decimalFormWriter.txt", "rt")
    lines = f.read().splitlines()
    f.close()
    
    assert lines[0] == " -5.000,TEST,19830926,0500,00100,00300,#ff0000 "
    
    os.remove("__decimalFormWriter.txt")


def test_ExponentFormWriter_write_seg():
    o = gisout.PointsGenerateFileWriter.ExponentFormWriter()
    seg = [[1.0, 1.2], [2.0, 2.2], [3.0, 3.2]]
    
    f = open("__exponentFormWriter.txt", "wt")
    o.write_seg(f, seg, 1.0e-05)
    f.close()
    
    f = open("__exponentFormWriter.txt", "rt")
    lines = f.read().splitlines()
    f.close()
    
    assert lines[0] == " 1.000e-05,    1.00000,    1.20000"
    assert lines[1] == "   2.00000,    2.20000"
    assert lines[3] == "END"
    
    os.remove("__exponentFormWriter.txt")


def test_ExponentFormWriter_write_att(cdump_two_pollutants):
    o = gisout.PointsGenerateFileWriter.ExponentFormWriter()
    g = cdump_two_pollutants.grids[0]
    
    f = open("__exponentFormWriter.txt", "wt")
    o.write_att(f, g, 100, 300, 1.0e-5, "#ff0000")
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
    assert o.cntr_writer is None


def test_KMLWriter_initialize(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    o = gisout.KMLWriter(s.kml_option)
    conc_type = helper.ConcentrationTypeFactory.create_instance( s.KAVG )
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    depo_type = helper.DepositFactory.create_instance(s.NDEP,
                                                      cdump_two_pollutants.has_ground_level_grid())
    o.initialize(s.gis_alt_mode,
                 s.KMLOUT,
                 s.output_basename,
                 s.output_suffix,
                 conc_type,
                 conc_map,
                 depo_type,
                 s.KMAP,
                 s.NSSLBL,
                 s.show_max_conc,
                 ["a", "b"])
    
    assert isinstance(o.cntr_writer, gisout.AbstractKMLContourWriter)


def test_KMLWriter_write(cdump_two_pollutants):
    # delete files we are about to create
    if os.path.exists("HYSPLIT_ps.kml"):
        os.remove("HYSPLIT_ps.kml")
    if os.path.exists("GELABEL_ps.txt"):
        os.remove("GELABEL_ps.txt")
        
    s = plot.ConcentrationPlotSettings()
    o = gisout.KMLWriter(s.kml_option)
    conc_type = helper.ConcentrationTypeFactory.create_instance( s.KAVG )
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    depo_type = helper.DepositFactory.create_instance(s.NDEP,
                                                      cdump_two_pollutants.has_ground_level_grid())
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
    
    o.initialize(s.gis_alt_mode,
                 s.KMLOUT,
                 s.output_basename,
                 s.output_suffix,
                 conc_type,
                 conc_map,
                 depo_type,
                 s.KMAP,
                 s.NSSLBL,
                 s.show_max_conc,
                 ["a", "b"])
    
    ax = plt.axes()
    contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                               [1.0e-15, 1.0e-12],
                               colors=["#ff0000", "#00ff00"],
                               extend="max")
    plt.close(ax.figure)
    
    raw_colors = [(1.0, 1.0, 1.0), (1.0, 0.0, 0.0)]
    
    try:
        o.write(g, 10, 100, 500, contour_set, 1.0e-15, 8.0e-12, "mass/m^3", raw_colors)
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
    conc_type = helper.ConcentrationTypeFactory.create_instance( s.KAVG )
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    depo_type = helper.DepositFactory.create_instance(s.NDEP,
                                                      cdump_two_pollutants.has_ground_level_grid())
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
    
    o.initialize(s.gis_alt_mode,
                 s.KMLOUT,
                 s.output_basename,
                 s.output_suffix,
                 conc_type,
                 conc_map,
                 depo_type,
                 s.KMAP,
                 s.NSSLBL,
                 s.show_max_conc,
                 ["a", "b"])
    
    f = open("__KMLWriter.txt", "wt")
    raw_colors = [(1.0, 1.0, 1.0), (1.0, 0.0, 0.0)]
    
    try:
        o._write_attributes(f, g, 1.0e-15, 8.0e-12, "mass/m^3", [1.0e-15, 1.0e-12], raw_colors)
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
    assert lines[4] == "8.0e-12 1.0e-15 2"
    assert lines[5] == "1.0e-15 1.0e-12 "
    assert lines[6] == "1.00 1.00 "
    assert lines[7] == "1.00 0.00 "
    assert lines[8] == "1.00 0.00 "
    assert lines[9] == "a b "
    
    os.remove("__KMLWriter.txt")


def test_PartialKMLWriter___init__():
    kml_option = 1
    o = gisout.PartialKMLWriter(kml_option)
    assert o.kml_option == 1
    assert o.kml_file is None
    assert o.att_file is None
    assert o.cntr_writer is None


def test_PartialKMLWriter_write(cdump_two_pollutants):
    # delete files we are about to create
    if os.path.exists("HYSPLIT_ps.txt"):
        os.remove("HYSPLIT_ps.txt")
    if os.path.exists("GELABEL_ps.txt"):
        os.remove("GELABEL_ps.txt")
        
    s = plot.ConcentrationPlotSettings()
    o = gisout.PartialKMLWriter(s.kml_option)
    conc_type = helper.ConcentrationTypeFactory.create_instance( s.KAVG )
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    depo_type = helper.DepositFactory.create_instance(s.NDEP,
                                                      cdump_two_pollutants.has_ground_level_grid())
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
    
    o.initialize(s.gis_alt_mode,
                 s.KMLOUT,
                 s.output_basename,
                 s.output_suffix,
                 conc_type,
                 conc_map,
                 depo_type,
                 s.KMAP,
                 s.NSSLBL,
                 s.show_max_conc,
                 ["a", "b"])
    
    ax = plt.axes()
    contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                               [1.0e-15, 1.0e-12],
                               colors=["#ff0000", "#00ff00"],
                               extend="max")
    plt.close(ax.figure)
    
    raw_colors = [(1.0, 1.0, 1.0), (1.0, 0.0, 0.0)]
    
    try:
        o.write(g, 10, 100, 500, contour_set, 1.0e-15, 8.0e-12, "mass/m^3", raw_colors)
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
              
    f = open("__PartialKMLWriter.txt", "wt")
    raw_colors = [(1.0, 1.0, 1.0), (1.0, 0.0, 0.0)]
    
    try:
        o._write_attributes(f, g, 1.0e-15, 8.0e-12, "mass/m^3", [1.0e-15, 1.0e-12], raw_colors)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
    
    f.close()
    
    os.remove("__PartialKMLWriter.txt")

   
def test_KMLContourWriterFactory_create_instance():
    conc_map = None
    gis_alt_mode = 0
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.CONCENTRATION, conc_map, gis_alt_mode)
    assert isinstance(w, gisout.KMLConcentrationWriter)
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.EXPOSURE, conc_map, gis_alt_mode)
    assert isinstance(w, gisout.KMLConcentrationWriter)
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.DEPOSITION, conc_map, gis_alt_mode)
    assert isinstance(w, gisout.KMLDepositionWriter)
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.THRESHOLD_LEVELS, conc_map, gis_alt_mode)
    assert isinstance(w, gisout.KMLChemicalThresholdWriter)
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.VOLCANIC_ERUPTION, conc_map, gis_alt_mode)
    assert isinstance(w, gisout.KMLDepositionWriter)
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.DEPOSITION_6, conc_map, gis_alt_mode)
    assert isinstance(w, gisout.KMLDepositionWriter)
    
    w = gisout.KMLContourWriterFactory.create_instance(const.ConcentrationMapType.MASS_LOADING, conc_map, gis_alt_mode)
    assert isinstance(w, gisout.KMLMassLoadingWriter)
    
    
def test_AbstractKMLContourWriter___init__():
    o = AbstractKMLContourWriterTest(None, 1)
    assert o.frame_count == 0
    assert o.conc_map is None
    assert o.gis_alt_mode == 1    


def test_AbstractKMLContourWriter_write(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = AbstractKMLContourWriterTest(conc_map, s.gis_alt_mode)
    
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
   
    ax = plt.axes()
    contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                               [1.0e-15, 1.0e-12],
                               colors=["#ff0000", "#00ff00"],
                               extend="max")
    plt.close(ax.figure)
    
    cntr_labels = ["AEGL-1", "AEGL-2"]
    
    f = open("__AbstractKMLContourWriter.txt", "wt")
    
    try:
        o.write(f, g, contour_set, 100, 500, "ps", 8.0e-12, "mass/m^3", cntr_labels)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))

    f.close()
    
    assert o.frame_count == 1
    
    os.remove("__AbstractKMLContourWriter.txt")


def test_AbstractKMLContourWriter__get_contour_height_at():
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = AbstractKMLContourWriterTest(conc_map, s.gis_alt_mode)
    
    assert o._get_contour_height_at(0, 100.0) == 100
    assert o._get_contour_height_at(1, 100.0) == 300
    assert o._get_contour_height_at(2, 100.0) == 500


def test_AbstractKMLContourWriter__write_contour(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = AbstractKMLContourWriterTest(conc_map, s.gis_alt_mode)
    
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
   
    ax = plt.axes()
    contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                               [1.0e-15, 1.0e-12],
                               colors=["#ff0000", "#00ff00"],
                               extend="max")
    plt.close(ax.figure)
    
    cntr_labels = ["AEGL-1", "AEGL-2"]
    
    f = open("__AbstractKMLContourWriter.txt", "wt")
    
    # just see if there is any exception
    try:
        o._write_contour(f, g, contour_set, "mass/m^3", 100, cntr_labels)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
        
    f.close()
    
    os.remove("__AbstractKMLContourWriter.txt")


def test_AbstractKMLContourWriter__write_seg(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = AbstractKMLContourWriterTest(conc_map, s.gis_alt_mode)
    
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
   
    ax = plt.axes()
    contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                               [1.0e-15, 1.0e-12],
                               colors=["#ff0000", "#00ff00"],
                               extend="max")
    plt.close(ax.figure)
    
    cntr_labels = ["AEGL-1", "AEGL-2"]
    
    f = open("__AbstractKMLContourWriter.txt", "wt")
    
    # just see if there is any exception
    try:
        o._write_seg(f, g, contour_set.allsegs[0][0], contour_set.allkinds[0][0], 100)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
            
    f.close()
    
    os.remove("__AbstractKMLContourWriter.txt")


def test_AbstractKMLContourWriter__separate_paths():
    path_codes = [1, 2, 2, 79]
    seg = [(0,0), (1,1), (2,2), (0,0)]
    
    paths = AbstractKMLContourWriterTest._separate_paths(seg, path_codes, 1)

    assert paths == [ [(0,0), (1,1), (2,2), (0,0)] ]
    
    path_codes = [1, 2, 2, 79, 1, 2, 2, 79]
    seg = [(0,0), (1,1), (2,2), (0,0), (5,5), (6,6), (7,7), (5,5)]
    
    paths = AbstractKMLContourWriterTest._separate_paths(seg, path_codes, 1)

    assert paths == [ [(0,0), (1,1), (2,2), (0,0)], [(5,5), (6,6), (7,7), (5,5)] ]


def test_AbstractKMLContourWriter__write_boundary(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = AbstractKMLContourWriterTest(conc_map, s.gis_alt_mode)
    
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
   
    ax = plt.axes()
    contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                               [1.0e-15, 1.0e-12],
                               colors=["#ff0000", "#00ff00"],
                               extend="max")
    plt.close(ax.figure)
    
    cntr_labels = ["AEGL-1", "AEGL-2"]
    
    f = open("__AbstractKMLContourWriter.txt", "wt")
    
    # just see if there is any exception
    try:
        paths = AbstractKMLContourWriterTest._separate_paths(contour_set.allsegs[0][0], contour_set.allkinds[0][0], 1)
        o._write_boundary(f, g, paths[0], 100)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
            
    f.close()
    
    os.remove("__AbstractKMLContourWriter.txt")


def test_AbstractKMLContourWriter__crossing_date_line():
    lons = [170, 175, -185, -190]
    assert AbstractKMLContourWriterTest._crossing_date_line(lons) == True
    
    lons = [170, 175, 177, 178]
    assert AbstractKMLContourWriterTest._crossing_date_line(lons) == False
   
    
def test_AbstractKMLContourWriter__compute_polygon_area():
    # clockwise, area < 0
    x = [0, 0, 1, 1, 0]
    y = [0, 1, 1, 0, 0]
    area = gisout.AbstractKMLContourWriter._compute_polygon_area(x, y)
    assert area == pytest.approx(-1.0)
    
    # counterclockwise, area > 0
    x = [0, 1, 1, 0, 0]
    y = [0, 0, 1, 1, 0]
    area = gisout.AbstractKMLContourWriter._compute_polygon_area(x, y)
    assert area == pytest.approx(1.0)


def test_AbstractKMLContourWriter__write_max_location(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = AbstractKMLContourWriterTest(conc_map, s.gis_alt_mode)
    
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
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = gisout.KMLConcentrationWriter(conc_map, s.gis_alt_mode)

    assert o.conc_map is conc_map
    assert o.gis_alt_mode == s.gis_alt_mode
    

def test_KMLConcentrationWriter_write(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = gisout.KMLConcentrationWriter(conc_map, s.gis_alt_mode)
    
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
   
    ax = plt.axes()
    contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                               [1.0e-15, 1.0e-12],
                               colors=["#ff0000", "#00ff00"],
                               extend="max")
    plt.close(ax.figure)
    
    cntr_labels = ["AEGL-1", "AEGL-2"]
    
    f = open("__KMLConcentrationWriter.txt", "wt")
    
    # just see if no exception occurs
    try:
        o.write(f, g, contour_set, 100, 500, "ps", 8.0e-12, "mass/m^3", cntr_labels)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))

    f.close()
    
    os.remove("__KMLConcentrationWriter.txt")

    
def test_KMLConcentrationWriter__get_max_location_text():
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = gisout.KMLConcentrationWriter(conc_map, s.gis_alt_mode)
    
    assert o._get_max_location_text().strip().startswith("The square represents")


def test_KMLChemicalThresholdWriter___init__():
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = gisout.KMLChemicalThresholdWriter(conc_map, s.gis_alt_mode)

    assert o.conc_map is conc_map
    assert o.gis_alt_mode == s.gis_alt_mode


def test_KMLChemicalThresholdWriter__get_contour_height_at():
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = gisout.KMLChemicalThresholdWriter(conc_map, s.gis_alt_mode)
    
    assert o._get_contour_height_at(0, 100.0) == 100
    assert o._get_contour_height_at(1, 100.0) == 100
    assert o._get_contour_height_at(2, 100.0) == 500    


def test_KMLChemicalThresholdWriter_write(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = gisout.KMLChemicalThresholdWriter(conc_map, s.gis_alt_mode)
    
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
   
    ax = plt.axes()
    contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                               [1.0e-15, 1.0e-12],
                               colors=["#ff0000", "#00ff00"],
                               extend="max")
    plt.close(ax.figure)
    
    cntr_labels = ["AEGL-1", "AEGL-2"]
    
    f = open("__KMLChemicalThresholdWriter.txt", "wt")
    
    # just see if no exception occurs
    try:
        o.write(f, g, contour_set, 100, 500, "ps", 8.0e-12, "mass/m^3", cntr_labels)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))

    f.close()
    
    os.remove("__KMLChemicalThresholdWriter.txt")


def test_KMLDepositionWriter___init__():
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = gisout.KMLDepositionWriter(conc_map, s.gis_alt_mode)

    assert o.conc_map is conc_map
    assert o.gis_alt_mode == s.gis_alt_mode


def test_KMLDepositionWriter_write(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = gisout.KMLDepositionWriter(conc_map, s.gis_alt_mode)
    
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
   
    ax = plt.axes()
    contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                               [1.0e-15, 1.0e-12],
                               colors=["#ff0000", "#00ff00"],
                               extend="max")
    plt.close(ax.figure)
    
    cntr_labels = ["AEGL-1", "AEGL-2"]
    
    f = open("__KMLDepositionWriter.txt", "wt")
    
    # just see if no exception occurs
    try:
        o.write(f, g, contour_set, 100, 500, "ps", 8.0e-12, "mass/m^3", cntr_labels)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))

    f.close()
    
    os.remove("__KMLDepositionWriter.txt")

    
def test_KMLDepositionWriter__get_max_location_text():
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = gisout.KMLDepositionWriter(conc_map, s.gis_alt_mode)
    
    assert o._get_max_location_text().strip().startswith("The square represents")

    
def test_KMLDepositionWriter__write_placemark_visibility():
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = gisout.KMLDepositionWriter(conc_map, s.gis_alt_mode)
    
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
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = gisout.KMLMassLoadingWriter(conc_map, s.gis_alt_mode)

    assert o.conc_map is conc_map
    assert o.gis_alt_mode == s.gis_alt_mode


def test_KMLMassLoadingWriter_write(cdump_two_pollutants):
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = gisout.KMLMassLoadingWriter(conc_map, s.gis_alt_mode)
    
    g = cdump_two_pollutants.grids[0]
    g.extension = helper.GridProperties()
    g.extension.max_locs = helper.find_max_locs(g)
   
    ax = plt.axes()
    contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                               [1.0e-15, 1.0e-12],
                               colors=["#ff0000", "#00ff00"],
                               extend="max")
    plt.close(ax.figure)
    
    cntr_labels = ["AEGL-1", "AEGL-2"]
    
    f = open("__KMLMassLoadingWriter.txt", "wt")
    
    # just see if no exception occurs
    try:
        o.write(f, g, contour_set, 100, 500, "ps", 8.0e-12, "mass/m^3", cntr_labels)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))

    f.close()
    
    os.remove("__KMLMassLoadingWriter.txt")

    
def test_KMLMassLoadingWriter__get_max_location_text():
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = gisout.KMLMassLoadingWriter(conc_map, s.gis_alt_mode)
    
    assert o._get_max_location_text().strip().startswith("The square represents")

    
def test_KMLMassLoadingWriter__write_placemark_visibility():
    s = plot.ConcentrationPlotSettings()
    conc_map = helper.ConcentrationMapFactory.create_instance( s.KMAP, s.KHEMIN )
    
    o = gisout.KMLMassLoadingWriter(conc_map, s.gis_alt_mode)
    
    f = open("__KMLMassLoadingWriter.txt", "wt")
    o.frame_count = 2
    o._write_placemark_visibility(f)
    f.close()

    f = open("__KMLMassLoadingWriter.txt", "rt")
    lines = f.read().splitlines()
    f.close()
    
    assert lines[0].strip() == "<visibility>0</visibility>"

    os.remove("__KMLMassLoadingWriter.txt")
