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
    assert hasattr(m, "conc_grids")
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
    
    
def test_ConcentrationDump_find_conc_grids_by_pollutant(cdump):
    list = cdump.find_conc_grids_by_pollutant("SO2")
    assert len(list) == 0
    
    # TEST at two release levels
    list = cdump.find_conc_grids_by_pollutant("TEST")
    assert len(list) == 2
    
    
def test_ConcentrationDump_find_conc_grids_by_pollutant_index(cdump):
    # two pollutants, 2 levels
    list = cdump.find_conc_grids_by_pollutant_index(-1)
    assert len(list) == 4
    
    # one pollutant, 2 levels
    list = cdump.find_conc_grids_by_pollutant_index(0)
    assert len(list) == 2
    
    
def test_ConcentrationDump_find_conc_grids_by_time_index(cdump):
    # none
    list = cdump.find_conc_grids_by_time_index(-1)
    assert len(list) == 0
    
    # two pollutants, 2 levels
    list = cdump.find_conc_grids_by_time_index(0)
    assert len(list) == 4
    
    
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


def test_ConcentrationGrid___init__():
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
    g = cdump.conc_grids[0]
    assert len(g.latitudes) == 601
   

def test_ConcentrationGrid_longitudes(cdump):
    g = cdump.conc_grids[0]
    assert len(g.longitudes) == 601
    

def test_ConcentrationGrid_copy_properties_except_conc(cdump):
    target = cdump.conc_grids[0]
    g = model.ConcentrationGrid(None)
    
    g.copy_properties_except_conc(target)
    
    assert g.parent is cdump
    assert g.time_index == 0
    assert g.pollutant_index == 0
    assert g.vert_level_index == 0
    assert g.pollutant == "TEST"
    assert g.vert_level == 100
    assert g.starting_datetime == datetime.datetime(83, 9, 25, 17, 0)
    assert g.ending_datetime == datetime.datetime(83, 9, 26, 5, 0)
    assert g.starting_forecast_hr == 0
    assert g.ending_forecast_hr == 0
    
    
def test_ConcentrationGrid_repair_pollutant(cdump):
    g = cdump.conc_grids[0]
    
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
    assert m.meteo_starting_datetime == datetime.datetime(83, 9, 25, 15, 0)
    assert m.meteo_forecast_hour == 0.0
    
    assert len(m.release_datetime) == 2
    assert len(m.release_locs) == 2
    assert len(m.release_heights) == 2
    assert m.release_datetime[0]== datetime.datetime(83, 9, 25, 17, 0)
    assert m.release_datetime[1]== datetime.datetime(83, 9, 25, 17, 0)
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
    
    assert len(m.conc_grids) == 4
    
    # grid 0
    
    g = m.conc_grids[0]
    assert g.time_index == 0
    assert g.starting_datetime == datetime.datetime(83, 9, 25, 17, 0)
    assert g.ending_datetime == datetime.datetime(83, 9, 26, 5, 0)
    assert g.starting_forecast_hr == 0
    assert g.ending_forecast_hr == 0
    
    assert g.pollutant == "TEST"
    assert g.vert_level == 100
    assert g.pollutant_index == 0
    assert g.vert_level_index == 0
    assert g.conc.shape == (601, 601)
    assert g.conc[300, 300] * 1.e+13 == pytest.approx(8.047535)
    
    # grid 1
    
    g = m.conc_grids[1]
    assert g.time_index == 0
    assert g.starting_datetime == datetime.datetime(83, 9, 25, 17, 0)
    assert g.ending_datetime == datetime.datetime(83, 9, 26, 5, 0)
    assert g.starting_forecast_hr == 0
    assert g.ending_forecast_hr == 0
    
    assert g.pollutant == "TEST"
    assert g.vert_level == 300
    assert g.pollutant_index == 0
    assert g.vert_level_index == 1
    assert g.conc.shape == (601, 601)
    assert g.conc[300, 300] * 1.e+13 == pytest.approx(7.963810)

    # grid 2
    
    g = m.conc_grids[2]
    assert g.time_index == 0
    assert g.starting_datetime == datetime.datetime(83, 9, 25, 17, 0)
    assert g.ending_datetime == datetime.datetime(83, 9, 26, 5, 0)
    assert g.starting_forecast_hr == 0
    assert g.ending_forecast_hr == 0
    
    assert g.pollutant == "MORE"
    assert g.vert_level == 100
    assert g.pollutant_index == 1
    assert g.vert_level_index == 0
    assert g.conc.shape == (601, 601)
    assert g.conc[300, 300] * 1.e+13 == pytest.approx(8.173024)  
    
    # grid 3
    
    g = m.conc_grids[3]
    assert g.time_index == 0
    assert g.starting_datetime == datetime.datetime(83, 9, 25, 17, 0)
    assert g.ending_datetime == datetime.datetime(83, 9, 26, 5, 0)
    assert g.starting_forecast_hr == 0
    assert g.ending_forecast_hr == 0
    
    assert g.pollutant == "MORE"
    assert g.vert_level == 300
    assert g.pollutant_index == 1
    assert g.vert_level_index == 1
    assert g.conc.shape == (601, 601)
    assert g.conc[300, 300] * 1.e+13 == pytest.approx(7.608168)    
    

def test_LazyGridFilter___init__(cdump):
    sel = model.PollutantSelector(-1)
    f = model.LazyGridFilter(cdump, 0, sel)
    assert f.cdump is cdump
    assert f.time_index == 0
    assert f.pollutant_selector is sel
    assert f.grids is None
        

def test_LazyGridFilter__fetch(cdump):
    sel = model.PollutantSelector(0)
    f = model.LazyGridFilter(cdump, 0, sel)
    g = f._fetch()
    assert len(g) == 2
    assert g[0].time_index == 0
    assert g[0].pollutant_index == 0
    assert g[0].pollutant == "TEST"


def test_LazyGridFilter___iter__(cdump):
    sel = model.PollutantSelector(0)
    f = model.LazyGridFilter(cdump, 0, sel)
    try:
        for g in f:
            assert g.time_index == 0
            assert g.pollutant_index == 0
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))


def test_LazyGridFilter___getitem__(cdump):
    sel = model.PollutantSelector(0)
    f = model.LazyGridFilter(cdump, 0, sel)
    try:
        g = f[0]
        assert g.time_index == 0
        assert g.pollutant_index == 0
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))    
        

def test_LazyGridFilter_filter_grids(cdump):
    sel = model.PollutantSelector(0)
    g = model.LazyGridFilter.filter_grids(cdump, 0, sel)
    assert len(g) == 2
    assert g[0].time_index == 0
    assert g[0].pollutant_index == 0
    
    # all pollutants
    sel = model.PollutantSelector(-1)
    g = model.LazyGridFilter.filter_grids(cdump, 0, sel)
    assert len(g) == 2 # averaged
    assert g[0].time_index == 0
    assert g[0].pollutant_index == -1


def test_GridSelector___init__():
    try:
        o = model.GridSelector()
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(x))
        

def test_GridSelector_is_selected():
    o = model.GridSelector()
    assert o.is_selected(None) == True
    

def test_VerticalLevelSelector___init__(cdump):
    s = model.VerticalLevelSelector(500, 1000)
    assert s.min == 500
    assert s.max == 1000


def test_VerticalLevelSelector___contains__():
    s = model.VerticalLevelSelector(500, 1000)
    assert ( 250 in s) == False
    assert ( 500 in s) == True
    assert ( 750 in s) == True
    assert (1000 in s) == True
    assert (1100 in s) == False


def test_VerticalLevelSelector_is_selected(cdump):
    s = model.VerticalLevelSelector(500, 1000)
    g = cdump.conc_grids[0]
    
    g.vert_level = 0
    assert s.is_selected(g) == False
    
    g.vert_level = 500
    assert s.is_selected(g) == True
    
    g.vert_level = 1000
    assert s.is_selected(g) == True
    
    g.vert_level = 1500
    assert s.is_selected(g) == False
  

def test_TimeIndexSelector___init__(cdump):
    s = model.TimeIndexSelector()
    assert s.first == 0
    assert s.last == 99999
    assert s.step == 1

    s = model.TimeIndexSelector(1, 10, 2)
    assert s.first == 1
    assert s.last == 10
    assert s.step == 2
   

def test_TimeIndexSelector___iter__():
    s = model.TimeIndexSelector(0, 4, 2)
    a = []
    for t_index in s:
        a.append(t_index)
    assert a == [0, 2, 4]    
    

def test_TimeIndexSelector___contains__():
    s = model.TimeIndexSelector(0, 10)
    assert ( -1 in s) == False
    assert (  0 in s) == True
    assert (  5 in s) == True
    assert ( 10 in s) == True
    assert ( 11 in s) == False


def test_TimeIndexSelector_is_selected(cdump):
    s = model.TimeIndexSelector(0, 10)
    g = cdump.conc_grids[0]
    
    g.time_index = -1
    assert s.is_selected(g) == False
    
    g.time_index = 0
    assert s.is_selected(g) == True
    
    g.time_index = 10
    assert s.is_selected(g) == True
    
    g.time_index = 15
    assert s.is_selected(g) == False


def test_TimeIndexSelector_first():
    s = model.TimeIndexSelector(0, 4, 2)
    assert s.first == 0
    
    
def test_TimeIndexSelector_last():
    s = model.TimeIndexSelector(0, 4, 2)
    assert s.last == 4
    
    
def test_TimeIndexSelector_normalize():
    s = model.TimeIndexSelector(-50, 99999)
    
    s.normalize(10)
    assert s.first == 0
    assert s.last == 10
    
    
def test_PollutantSelector___init__():
    s = model.PollutantSelector()
    assert s.index == -1
    
    s = model.PollutantSelector(0)
    assert s.index == 0
    
    
def test_PollutantSelector___contains__():
    s = model.PollutantSelector(-1)
    # -1 indicates any pollutant
    assert (-1 in s) == True
    assert ( 0 in s) == True
    assert ( 1 in s) == True
    
    s = model.PollutantSelector(0)
    assert (-1 in s) == False
    assert ( 0 in s) == True
    assert ( 1 in s) == False
    

def test_TimeIndexSelector_is_selected(cdump):
    s = model.PollutantSelector(-1)
    g = cdump.conc_grids[0]
    
    g.pollutant_index = -1
    assert s.is_selected(g) == True
    
    g.pollutant_index = 0
    assert s.is_selected(g) == True
    
    g.pollutant_index = 10
    assert s.is_selected(g) == True
    
    # with pollutant index = 0
    s = model.PollutantSelector(0)

    g.pollutant_index = -1
    assert s.is_selected(g) == False
    
    g.pollutant_index = 0
    assert s.is_selected(g) == True
    
    g.pollutant_index = 10
    assert s.is_selected(g) == False
    
    
def test_PollutantSelector_index():
    s = model.PollutantSelector(1)
    assert s.index == 1
    
    
def test_PollutantSelector_normalize():
    s = model.PollutantSelector(-2)
    s.normalize(2)
    assert s.index == -1
    
    s = model.PollutantSelector(50)
    s.normalize(1)
    assert s.index == 1
    
    
    
    
