import pytest
import datetime
from hysplit4 import util
from hysplit4.conc import model


@pytest.fixture
def cdump():
    m = model.ConcentrationDump().get_reader().read("data/cdump_two_pollutants")
    return m


def test_ConcentrationDump___init__():
    m = model.ConcentrationDump()
    
    assert hasattr(m, "meteo_model")
    assert hasattr(m, "meteo_starting_datetime")
    assert hasattr(m, "meteo_forecast_hour")
    assert hasattr(m, "release_datetime")
    assert hasattr(m, "release_locs")
    assert hasattr(m, "release_heights")
    assert hasattr(m, "grid_deltas")
    assert hasattr(m, "grid_loc")
    assert hasattr(m, "grid_sz")
    assert hasattr(m, "vert_levels")
    assert hasattr(m, "pollutants")
    assert hasattr(m, "grids")
    assert hasattr(m, "pollutants")
    assert hasattr(m, "latitudes")
    assert hasattr(m, "longitudes")
    
    
def test_ConcentrationDump_get_reader():
    m = model.ConcentrationDump()
    r = m.get_reader()
    
    assert isinstance(r, model.ConcentrationDumpFileReader)
    assert r.conc_dump is m
    
    
def test_ConcentrationDump_get_unique_start_locations():
    m = model.ConcentrationDump()
    m.release_locs = [(-85.0, 35.0), (-85.0, 35.0)]
    
    locs = m.get_unique_start_locations()
    assert len(locs) == 1
    assert locs[0] == pytest.approx((-85.0, 35.0))
    

def test_ConcentrationDump_get_unique_start_levels():
    m = model.ConcentrationDump()
    m.release_heights = [0.0, 10.0, 10.0]
    
    levels = m.get_unique_start_levels()
    assert len(levels) == 2
    assert levels == pytest.approx((0.0, 10.0))


def test_ConcentrationDump_get_pollutant():
    m = model.ConcentrationDump()
    m.pollutants = ["TEST", "TRCR"]
    
    assert m.get_pollutant(-1) == "SUM"
    assert m.get_pollutant( 0) == "TEST"
    assert m.get_pollutant( 1) == "TRCR"

    
def test_ConcentrationDump_latitudes(cdump):
    assert len(cdump.latitudes) == 601
    assert cdump.latitudes[  0] == pytest.approx(24.9000)
    assert cdump.latitudes[600] == pytest.approx(54.9000)

    try:
        cdump.latitudes = [0, 1, 2, 3]
        assert len(cdump.latitudes) == 4
    except Exception as ex:
        pytest.fail("unexpected exception {0}".format(ex))
    
    
def test_ConcentrationDump_longitudes(cdump):
    assert len(cdump.longitudes) == 601
    assert cdump.longitudes[  0] == pytest.approx(-99.2200)
    assert cdump.longitudes[600] == pytest.approx(-69.2200)

    try:
        cdump.longitudes = [0, 1, 2, 3]
        assert len(cdump.longitudes) == 4
    except Exception as ex:
        pytest.fail("unexpected exception {0}".format(ex))


def test_ConcentrationDump_has_ground_level_grid(cdump):
    assert cdump.has_ground_level_grid() == False
    
    cdump.vert_levels = [500, 100, 0]
    assert cdump.has_ground_level_grid() == True


def test_ConcentrationGrid___init__():
    m = model.ConcentrationDump()
    g = model.ConcentrationGrid(m)
    
    assert g.parent is m
    assert g.time_index == -1
    assert g.pollutant_index == -1
    assert g.vert_level_index == -1
    assert hasattr(g, "pollutant")
    assert g.vert_level == 0
    assert hasattr(g, "starting_datetime")
    assert hasattr(g, "ending_datetime")
    assert g.starting_forecast_hr == 0
    assert g.ending_forecast_hr == 0
    assert hasattr(g, "conc")
    assert g.nonzero_conc_count == None
    assert g.extension == None


def test_ConcentrationGrid_is_forward_calculation():
    m = model.ConcentrationDump()
    g = model.ConcentrationGrid(m)
    
    g.starting_datetime = datetime.datetime(2019, 5, 28, 8, 0) # 2019/5/28 8:00
    g.ending_datetime = datetime.datetime(2019, 5, 28, 9, 0)   # 2019/5/28 9:00
    assert g.is_forward_calculation() == True
       
    g.starting_datetime = datetime.datetime(2019, 5, 28, 8, 0)
    g.ending_datetime = datetime.datetime(2019, 5, 25, 9, 0)
    assert g.is_forward_calculation() == False 
    

def test_ConcentrationGrid_conc():
    m = model.ConcentrationDump()
    g = model.ConcentrationGrid(m)
    
    g.conc = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert g.conc[0] == pytest.approx((0.1, 0.2, 0.3))
   

def test_ConcentrationGrid_latitudes(cdump):
    g = cdump.grids[0]
    assert len(g.latitudes) == 601
   

def test_ConcentrationGrid_longitudes(cdump):
    g = cdump.grids[0]
    assert len(g.longitudes) == 601
    

def test_ConcentrationGrid_clone(cdump):
    target = cdump.grids[0]
    g = target.clone()
    
    assert g.parent is cdump
    assert g.time_index == 0
    assert g.pollutant_index == 0
    assert g.vert_level_index == 0
    assert g.pollutant == "TEST"
    assert g.vert_level == 100
    assert g.starting_datetime == datetime.datetime(1983, 9, 25, 17, 0)
    assert g.ending_datetime == datetime.datetime(1983, 9, 26, 5, 0)
    assert g.starting_forecast_hr == 0
    assert g.ending_forecast_hr == 0
    assert g.nonzero_conc_count == 854
    assert g.extension == None
    
    
def test_ConcentrationGrid_repair_pollutant(cdump):
    g = cdump.grids[0]
    
    # test before repair
    assert g.pollutant_index == 0
    assert g.pollutant == "TEST"
    
    g.repair_pollutant(1)
    assert g.pollutant_index == 1
    assert g.pollutant == "MORE"
    
    # average across pollutants
    g.repair_pollutant(-1)
    assert g.pollutant_index == -1
    assert g.pollutant == "SUM"
    g = model.ConcentrationGrid(None)
    
    
def test_ConcentrationGrid_get_duration_in_sec():
    g = model.ConcentrationGrid(None)
    
    g.starting_datetime = datetime.datetime(2019, 5, 28, 14, 0)
    g.ending_datetime = datetime.datetime(2019, 5, 28, 14, 30)
    assert g.get_duration_in_sec() == 1800
    

def test_ConcentrationDumpFileReader___init__():
    m = model.ConcentrationDump()
    r = model.ConcentrationDumpFileReader(m)
    
    assert r.conc_dump is m
    
    
def test_ConcentrationDumpFileReader_read():
    m = model.ConcentrationDump()
    r = model.ConcentrationDumpFileReader(m)
    
    r.read("data/cdump_two_pollutants")
    
    assert m.meteo_model == "NARR"
    assert m.meteo_starting_datetime == datetime.datetime(1983, 9, 25, 15, 0)
    assert m.meteo_forecast_hour == 0.0
    
    assert len(m.release_datetime) == 2
    assert len(m.release_locs) == 2
    assert len(m.release_heights) == 2
    assert m.release_datetime[0]== datetime.datetime(1983, 9, 25, 17, 0)
    assert m.release_datetime[1]== datetime.datetime(1983, 9, 25, 17, 0)
    assert m.release_locs[0] == pytest.approx((-84.22, 39.90))
    assert m.release_locs[1] == pytest.approx((-84.22, 39.90))
    assert m.release_heights[0] == pytest.approx( 10.0)
    assert m.release_heights[1] == pytest.approx(500.0)
    
    assert m.grid_sz == (601, 601)
    assert m.grid_deltas == pytest.approx((0.05, 0.05))
    assert m.grid_loc == pytest.approx((-99.22, 24.90))
    assert len(m.longitudes) == 601
    assert len(m.latitudes) == 601
    assert m.longitudes[0] == pytest.approx(-99.22)
    assert m.latitudes[0] == pytest.approx(24.90)

    assert m.vert_levels == pytest.approx((100, 300))
    assert m.pollutants == ["TEST", "MORE"]
    
    assert len(m.grids) == 4
    
    # grid 0
    
    g = m.grids[0]
    assert g.time_index == 0
    assert g.starting_datetime == datetime.datetime(1983, 9, 25, 17, 0)
    assert g.ending_datetime == datetime.datetime(1983, 9, 26, 5, 0)
    assert g.starting_forecast_hr == 0
    assert g.ending_forecast_hr == 0
    
    assert g.pollutant == "TEST"
    assert g.vert_level == 100
    assert g.pollutant_index == 0
    assert g.vert_level_index == 0
    assert g.conc.shape == (601, 601)
    assert g.conc[300, 300] * 1.e+13 == pytest.approx(8.047535)
    
    # grid 1
    
    g = m.grids[1]
    assert g.time_index == 0
    assert g.starting_datetime == datetime.datetime(1983, 9, 25, 17, 0)
    assert g.ending_datetime == datetime.datetime(1983, 9, 26, 5, 0)
    assert g.starting_forecast_hr == 0
    assert g.ending_forecast_hr == 0
    
    assert g.pollutant == "TEST"
    assert g.vert_level == 300
    assert g.pollutant_index == 0
    assert g.vert_level_index == 1
    assert g.conc.shape == (601, 601)
    assert g.conc[300, 300] * 1.e+13 == pytest.approx(7.963810)

    # grid 2
    
    g = m.grids[2]
    assert g.time_index == 0
    assert g.starting_datetime == datetime.datetime(1983, 9, 25, 17, 0)
    assert g.ending_datetime == datetime.datetime(1983, 9, 26, 5, 0)
    assert g.starting_forecast_hr == 0
    assert g.ending_forecast_hr == 0
    
    assert g.pollutant == "MORE"
    assert g.vert_level == 100
    assert g.pollutant_index == 1
    assert g.vert_level_index == 0
    assert g.conc.shape == (601, 601)
    assert g.conc[300, 300] * 1.e+13 == pytest.approx(8.173024)  
    
    # grid 3
    
    g = m.grids[3]
    assert g.time_index == 0
    assert g.starting_datetime == datetime.datetime(1983, 9, 25, 17, 0)
    assert g.ending_datetime == datetime.datetime(1983, 9, 26, 5, 0)
    assert g.starting_forecast_hr == 0
    assert g.ending_forecast_hr == 0
    
    assert g.pollutant == "MORE"
    assert g.vert_level == 300
    assert g.pollutant_index == 1
    assert g.vert_level_index == 1
    assert g.conc.shape == (601, 601)
    assert g.conc[300, 300] * 1.e+13 == pytest.approx(7.608168)    
