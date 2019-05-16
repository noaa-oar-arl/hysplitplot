import pytest
import os
import datetime
from hysplit4 import gisout, const
from hysplit4.traj import plot, model


@pytest.fixture
def plotData():
    s = plot.TrajectoryPlotSettings()
    d = model.TrajectoryPlotData()
    r = model.TrajectoryDataFileReader(d)
    r.set_end_hour_duration(s.end_hour_duration)
    r.set_vertical_coordinate(s.vertical_coordinate, s.height_unit)
    r.read("data/tdump")
    s.vertical_coordinate = r.vertical_coordinate
    return d


def test_AbstractGISFileWriter___init__():
    w = gisout.AbstractGISFileWriter()
    
    assert w.output_suffix == "ps"
    assert w.output_name == "trajplot.ps"
    assert w.kml_option == const.KMLOption.NONE


def test_AbstractGISFileWriter_create_instance():
    w = gisout.AbstractGISFileWriter.create_instance(const.GISOutput.GENERATE_POINTS)
    assert isinstance(w, gisout.PointsGenerateFileWriter)
    
    w = gisout.AbstractGISFileWriter.create_instance(const.GISOutput.GENERATE_LINES)
    assert isinstance(w, gisout.LinesGenerateFileWriter)
    
    w = gisout.AbstractGISFileWriter.create_instance(const.GISOutput.KML)
    assert isinstance(w, gisout.KMLWriter)
    
    w = gisout.AbstractGISFileWriter.create_instance(const.GISOutput.PARTIAL_KML)
    assert isinstance(w, gisout.PartialKMLWriter)
  
    w = gisout.AbstractGISFileWriter.create_instance(const.GISOutput.NONE)
    assert w is None


def test_GenerateAttributeFileWriter_write(plotData):
    # just see if no error occurs
    try:
        gisout.GenerateAttributeFileWriter.write("__gis.att", plotData)
        os.remove("__gis.att")
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))

    
def test_PointsGenerateFileWriter___init__():
    try:
        w = gisout.PointsGenerateFileWriter()
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
        

def test_PointsGenerateFileWriter_write(plotData):
    # just see if no error occurs
    try:
        w = gisout.PointsGenerateFileWriter()
        w.write(1, plotData)
        os.remove("GIS_traj_ps_01.txt")
        os.remove("GIS_traj_ps_01.att")
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))

    
def test_LinesGenerateFileWriter___init__():
    try:
        w = gisout.LinesGenerateFileWriter()
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
        

def test_LinesGenerateFileWriter_write(plotData):
    # just see if no error occurs
    try:
        w = gisout.LinesGenerateFileWriter()
        w.write(1, plotData)
        os.remove("GIS_traj_ps_01.txt")
        os.remove("GIS_traj_ps_01.att")
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))

    
def test_KMLWriter___init__():
    try:
        w = gisout.KMLWriter()
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
        

def test_KMLWriter_make_filename():
    assert gisout.KMLWriter.make_filename("trajplot.ps", "ps", 1) == "HYSPLITtraj_ps_01.kml"
    assert gisout.KMLWriter.make_filename("trajplot ps", "ps", 1) == "HYSPLITtraj_ps_01.kml"
    assert gisout.KMLWriter.make_filename("sample", "ps", 1) == "sample_01.kml"
    assert gisout.KMLWriter.make_filename("sample.pdf", "ps", 1) == "sample_01.kml"
    assert gisout.KMLWriter.make_filename("sample pdf", "ps", 1) == "sample_01.kml"
        

def test_KMLWriter__get_iso_8601_str():
    dt = datetime.datetime(83, 10, 13, 0, 15)
    assert gisout.KMLWriter._get_iso_8601_str(dt) == "1983-10-13T00:15:00Z"
    

def test_KMLWriter__get_timestamp_str(plotData):
    dt = datetime.datetime(83, 10, 13, 0, 15)
    assert gisout.KMLWriter._get_timestamp_str(dt) == "10/13/1983 0015 UTC"


def test_KMLWriter_write(plotData):
    w = gisout.KMLWriter()
    
    # KML option - NONE (0)
    try:
        w.kml_option = const.KMLOption.NONE
        w.write(1, plotData)
        os.remove("HYSPLITtraj_ps_01.kml")
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
        
    # KML option - NO_EXTRA_OVERLAYS (1)
    try:
        w.kml_option = const.KMLOption.NO_EXTRA_OVERLAYS
        w.write(1, plotData)
        os.remove("HYSPLITtraj_ps_01.kml")
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
        
    # KML option - NO_ENDPOINTS (2)
    try:
        w.kml_option = const.KMLOption.NO_ENDPOINTS
        w.write(1, plotData)
        os.remove("HYSPLITtraj_ps_01.kml")
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
        
    # KML option - BOTH_1_AND_2 (3)
    try:
        w.kml_option = const.KMLOption.BOTH_1_AND_2
        w.write(1, plotData)
        os.remove("HYSPLITtraj_ps_01.kml")
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))

    
def test_PartialKMLWriter___init__():
    try:
        w = gisout.PartialKMLWriter()
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
        

def test_PartialKMLWriter_make_filename():
    assert gisout.PartialKMLWriter.make_filename("trajplot.ps", "ps", 1) == "HYSPLITtraj_ps_01.txt"
    assert gisout.PartialKMLWriter.make_filename("trajplot ps", "ps", 1) == "HYSPLITtraj_ps_01.txt"
    assert gisout.PartialKMLWriter.make_filename("sample", "ps", 1) == "sample_01.txt"
    assert gisout.PartialKMLWriter.make_filename("sample.pdf", "ps", 1) == "sample_01.txt"
    assert gisout.PartialKMLWriter.make_filename("sample pdf", "ps", 1) == "sample_01.txt"
        

def test_PartialKMLWriter_write(plotData):
    w = gisout.PartialKMLWriter()
    
    # KML option - NONE (0)
    try:
        w.kml_option = const.KMLOption.NONE
        w.write(1, plotData)
        os.remove("HYSPLITtraj_ps_01.txt")
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
        
    # KML option - NO_EXTRA_OVERLAYS (1)
    try:
        w.kml_option = const.KMLOption.NO_EXTRA_OVERLAYS
        w.write(1, plotData)
        os.remove("HYSPLITtraj_ps_01.txt")
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
        
    # KML option - NO_ENDPOINTS (2)
    try:
        w.kml_option = const.KMLOption.NO_ENDPOINTS
        w.write(1, plotData)
        os.remove("HYSPLITtraj_ps_01.txt")
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
        
    # KML option - BOTH_1_AND_2 (3)
    try:
        w.kml_option = const.KMLOption.BOTH_1_AND_2
        w.write(1, plotData)
        os.remove("HYSPLITtraj_ps_01.txt")
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
