# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_gisout.py
#
# Performs unit tests on functions and class methods declared in traj/gisout.py.
# ---------------------------------------------------------------------------

import datetime
import numpy
import os
import pytest
import pytz

from hysplitdata.const import HeightUnit
from hysplitdata.traj import model
from hysplitplot import const
from hysplitplot.traj import plot, gisout


@pytest.fixture
def plotData():
    s = plot.TrajectoryPlotSettings()
    d = model.TrajectoryDump()
    r = model.TrajectoryDumpFileReader(d)
    r.set_end_hour_duration(s.end_hour_duration)
    r.set_vertical_coordinate(s.vertical_coordinate, s.height_unit)
    r.read("data/tdump")
    s.vertical_coordinate = r.vertical_coordinate
    return d


# concrete classes for testing abstract classes
class AbstractGISFileWriterTest(gisout.AbstractGISFileWriter):
    
    def __init__(self, time_zone=None):
        super(AbstractGISFileWriterTest, self).__init__(time_zone)
        
    def write(self, file_no, plot_data):
        pass


def test_GISFileWriterFactory_create_instance():
    tz = pytz.utc
    
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.GENERATE_POINTS, HeightUnit.FEET, tz)
    assert isinstance(w, gisout.PointsGenerateFileWriter)
    assert w.time_zone is tz
    
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.GENERATE_LINES, HeightUnit.FEET, tz)
    assert isinstance(w, gisout.LinesGenerateFileWriter)
    assert w.time_zone is tz
    
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.KML, HeightUnit.FEET, tz)
    assert isinstance(w, gisout.KMLWriter)
    assert w.height_unit == HeightUnit.FEET
    assert w.time_zone is tz
    
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.PARTIAL_KML, HeightUnit.FEET, tz)
    assert isinstance(w, gisout.PartialKMLWriter)
    assert w.height_unit == HeightUnit.FEET
    assert w.time_zone is tz
    
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.NONE, HeightUnit.FEET, tz)
    assert isinstance(w, gisout.NullGISFileWriter)
    assert w.time_zone is tz
    

def test_GISFileWriterFactory_create_instance__without_time_zone():
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.GENERATE_POINTS)
    assert isinstance(w, gisout.PointsGenerateFileWriter)
    assert w.time_zone is None
    
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.GENERATE_LINES)
    assert isinstance(w, gisout.LinesGenerateFileWriter)
    assert w.time_zone is None
    
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.KML)
    assert isinstance(w, gisout.KMLWriter)
    assert w.height_unit == HeightUnit.METERS
    assert w.time_zone is None
     
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.KML, HeightUnit.FEET)
    assert isinstance(w, gisout.KMLWriter)
    assert w.height_unit == HeightUnit.FEET
    assert w.time_zone is None
    
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.PARTIAL_KML)
    assert isinstance(w, gisout.PartialKMLWriter)
    assert w.height_unit == HeightUnit.METERS
    assert w.time_zone is None
     
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.PARTIAL_KML, HeightUnit.FEET)
    assert isinstance(w, gisout.PartialKMLWriter)
    assert w.height_unit == HeightUnit.FEET
    assert w.time_zone is None
    
    w = gisout.GISFileWriterFactory.create_instance(const.GISOutput.NONE)
    assert isinstance(w, gisout.NullGISFileWriter)
    assert w.time_zone is None


def test_AbstractGISFileWriter___init__():
    w = AbstractGISFileWriterTest()
    
    assert w.output_suffix == "ps"
    assert w.output_name == "trajplot.ps"
    assert w.kml_option == const.KMLOption.NONE
    assert w.time_zone is None

    tz = pytz.utc
    w = AbstractGISFileWriterTest(tz)
    assert w.time_zone is tz
    

def test_AbstractGISFileWriter_write(plotData):
    # just see if no error occurs
    try:
        w = AbstractGISFileWriterTest()
        w.write(1, plotData)
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))

    
def test_NullGISFileWriter___init__():
    w = gisout.NullGISFileWriter()
    assert w.time_zone is None

    tz = pytz.utc
    w = gisout.NullGISFileWriter(tz)
    assert w.time_zone is tz
    

def test_NullGISFileWriter_write(plotData):
    # just see if no error occurs
    try:
        w = gisout.NullGISFileWriter()
        w.write(1, plotData)
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))    


def test_GenerateAttributeFileWriter_write(plotData):
    # just see if no error occurs
    try:
        gisout.GenerateAttributeFileWriter.write("__gis.att", plotData)
        os.remove("__gis.att")

        tz = pytz.timezone("EST")        
        gisout.GenerateAttributeFileWriter.write("__gis.att", plotData, tz)
        os.remove("__gis.att")
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))

    
def test_PointsGenerateFileWriter___init__():
    w = gisout.PointsGenerateFileWriter()
    assert w.time_zone is None
    assert w.att_writer is not None 
    
    tz = pytz.timezone("EST")      
    w = gisout.PointsGenerateFileWriter( tz )
    assert w.time_zone is tz
        

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
    w = gisout.LinesGenerateFileWriter()
    assert w.time_zone is None
    assert w.att_writer is not None 

    tz = pytz.timezone("EST")
    w = gisout.LinesGenerateFileWriter(tz)
    assert w.time_zone is tz
    

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
        assert w.height_unit == HeightUnit.METERS
        assert w.time_zone is None
        
        w = gisout.KMLWriter(HeightUnit.FEET)
        assert w.height_unit == HeightUnit.FEET
        assert w.time_zone is None
            
        tz = pytz.timezone("EST")
        w = gisout.KMLWriter(HeightUnit.FEET, tz)
        assert w.height_unit == HeightUnit.FEET
        assert w.time_zone is tz
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
        

def test_KMLWriter_make_filename():
    assert gisout.KMLWriter.make_filename("trajplot.ps", "ps", 1) == "HYSPLITtraj_ps_01.kml"
    assert gisout.KMLWriter.make_filename("trajplot ps", "ps", 1) == "HYSPLITtraj_ps_01.kml"
    assert gisout.KMLWriter.make_filename("sample", "ps", 1) == "sample_01.kml"
    assert gisout.KMLWriter.make_filename("sample.pdf", "ps", 1) == "sample_01.kml"
    assert gisout.KMLWriter.make_filename("sample pdf", "ps", 1) == "sample_01.kml"
   

def test_KMLWriter__get_timestamp_str():
    dt = datetime.datetime(1983, 10, 13, 0, 15, 0, 0, pytz.utc)
    assert gisout.KMLWriter._get_timestamp_str(dt) == "10/13/1983 0015 UTC"


def test_KMLWriter__get_alt_mode(plotData):
    t = plotData.trajectories[0]
    assert gisout.KMLWriter._get_alt_mode(t) == "relativeToGround"
    
    # now add TERR_MSL
    t.diagnostic_names.append("TERR_MSL")
    t.others["TERR_MSL"] = numpy.zeros(len(t.latitudes))
    
    assert gisout.KMLWriter._get_alt_mode(t) == "absolute"
    

def test_KMLWriter__get_level_type(plotData):
    t = plotData.trajectories[0]
    
    w = gisout.KMLWriter(HeightUnit.METERS)
    assert w._get_level_type(t) == "m AGL"
    
    w = gisout.KMLWriter(HeightUnit.FEET)
    assert w._get_level_type(t) == "ft AGL"
    
    # now add TERR_MSL
    t.diagnostic_names.append("TERR_MSL")
    t.others["TERR_MSL"] = numpy.zeros(len(t.latitudes))
   
    w = gisout.KMLWriter(HeightUnit.METERS)
    assert w._get_level_type(t) == "m AMSL"
    
    w = gisout.KMLWriter(HeightUnit.FEET)
    assert w._get_level_type(t) == "ft AMSL"


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
        assert w.height_unit == HeightUnit.METERS
        assert w.time_zone is None
        
        w = gisout.PartialKMLWriter(HeightUnit.FEET)
        assert w.height_unit == HeightUnit.FEET
        assert w.time_zone is None
        
        tz = pytz.timezone("EST")
        w = gisout.PartialKMLWriter(HeightUnit.FEET, tz)
        assert w.height_unit == HeightUnit.FEET
        assert w.time_zone is tz
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
