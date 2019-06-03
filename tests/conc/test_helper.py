import pytest
import logging
from hysplit4.conc import helper, model
from hysplit4 import const


logger = logging.getLogger(__name__)


@pytest.fixture
def cdump2():
    m = model.ConcentrationDump().get_reader().read("data/cdump_two_pollutants")
    return m
    
    
def test_sum_over_pollutants_per_level(cdump2):
    # check what we know
    assert cdump2.vert_levels == [100, 300]
    assert cdump2.grids[0].pollutant_index == 0
    assert cdump2.grids[1].pollutant_index == 0
    assert cdump2.grids[2].pollutant_index == 1
    assert cdump2.grids[3].pollutant_index == 1
    assert cdump2.grids[0].conc[300, 300] * 1.e+13 == pytest.approx(8.047535)
    assert cdump2.grids[1].conc[300, 300] * 1.e+13 == pytest.approx(7.963810)
    assert cdump2.grids[2].conc[300, 300] * 1.e+13 == pytest.approx(8.173024)
    assert cdump2.grids[3].conc[300, 300] * 1.e+13 == pytest.approx(7.608168)
    
    # pollutant 0, all levels
    ls = helper.VerticalLevelSelector(0, 10000)
    ps = helper.PollutantSelector(0)
    v_grids = helper.sum_over_pollutants_per_level(cdump2.grids, ls, ps)

    assert len(v_grids) == 2
    assert v_grids[0] is cdump2.grids[0]
    assert v_grids[1] is cdump2.grids[1]
    
    # pollutant 1, all levels
    ls = helper.VerticalLevelSelector(0, 10000)
    ps = helper.PollutantSelector(1)
    v_grids = helper.sum_over_pollutants_per_level(cdump2.grids, ls, ps)

    assert len(v_grids) == 2
    assert v_grids[0] is cdump2.grids[2]
    assert v_grids[1] is cdump2.grids[3]    
    
    # pollutant sums, all levels
    ls = helper.VerticalLevelSelector(0, 10000)
    ps = helper.PollutantSelector()
    v_grids = helper.sum_over_pollutants_per_level(cdump2.grids, ls, ps)
        
    assert len(v_grids) == 2
    assert v_grids[0].vert_level_index == 0
    assert v_grids[1].vert_level_index == 1
    assert v_grids[0].pollutant_index == -1
    assert v_grids[1].pollutant_index == -1
    assert v_grids[0].conc[300, 300] * 1.e+13 == pytest.approx(8.047535 + 8.173024)
    assert v_grids[1].conc[300, 300] * 1.e+13 == pytest.approx(7.963810 + 7.608168)
    

def test_sum_conc_grids_of_interest(cdump2):
    level_selector = helper.VerticalLevelSelector()
    pollutant_selector = helper.PollutantSelector()
    time_selector = helper.TimeIndexSelector()
    
    conc = helper.sum_conc_grids_of_interest(cdump2.grids,
                                             level_selector,
                                             pollutant_selector,
                                             time_selector)
    
    assert conc[300, 300] * 1.e+13 == pytest.approx(8.047535 + 8.173024 + 7.963810 + 7.608168)
    
     
def test_find_nonzero_min_max(cdump2):
    vmin, vmax = helper.find_nonzero_min_max(cdump2.grids[0].conc)
    assert vmin * 1.0e+15 == pytest.approx(1.871257)
    assert vmax * 1.0e+13 == pytest.approx(8.047535)
  

def test_TimeIndexSelector___init__():
    s = helper.TimeIndexSelector()
    assert s.first == 0
    assert s.last == 9999
    assert s.step == 1

    s = helper.TimeIndexSelector(1, 10, 2)
    assert s.first == 1
    assert s.last == 10
    assert s.step == 2
   

def test_TimeIndexSelector___iter__():
    s = helper.TimeIndexSelector(0, 4, 2)
    a = []
    for t_index in s:
        a.append(t_index)
    assert a == [0, 2, 4]    
    

def test_TimeIndexSelector___contains__():
    s = helper.TimeIndexSelector(0, 10)
    assert ( -1 in s) == False
    assert (  0 in s) == True
    assert (  5 in s) == True
    assert ( 10 in s) == True
    assert ( 11 in s) == False


def test_TimeIndexSelector_first():
    s = helper.TimeIndexSelector(0, 4, 2)
    assert s.first == 0
    
    
def test_TimeIndexSelector_last():
    s = helper.TimeIndexSelector(0, 4, 2)
    assert s.last == 4
    
    
def test_TimeIndexSelector_normalize():
    s = helper.TimeIndexSelector(-50, 99999)
    
    s.normalize(10)
    assert s.first == 0
    assert s.last == 10
    
    
def test_PollutantSelector___init__():
    s = helper.PollutantSelector()
    assert s.index == -1
    
    s = helper.PollutantSelector(0)
    assert s.index == 0
    
    
def test_PollutantSelector___contains__():
    s = helper.PollutantSelector(-1)
    # -1 indicates any pollutant
    assert (-1 in s) == True
    assert ( 0 in s) == True
    assert ( 1 in s) == True
    
    s = helper.PollutantSelector(0)
    assert (-1 in s) == False
    assert ( 0 in s) == True
    assert ( 1 in s) == False
    

def test_PollutantSelector_index():
    s = helper.PollutantSelector(1)
    assert s.index == 1
    
    
def test_PollutantSelector_normalize():
    s = helper.PollutantSelector(-2)
    s.normalize(2)
    assert s.index == -1
    
    s = helper.PollutantSelector(50)
    s.normalize(1)
    assert s.index == 1
   

def test_VerticalLevelSelector___init__():
    s = helper.VerticalLevelSelector(500, 1000)
    assert s.min == 500
    assert s.max == 1000


def test_VerticalLevelSelector___contains__():
    s = helper.VerticalLevelSelector(500, 1000)
    assert ( 250 in s) == False
    assert ( 500 in s) == True
    assert ( 750 in s) == True
    assert (1000 in s) == True
    assert (1100 in s) == False
   

def test_VerticalLevelSelector_min():
    s = helper.VerticalLevelSelector(500, 1000)
    assert s.min == 500
   

def test_VerticalLevelSelector_max():
    s = helper.VerticalLevelSelector(500, 1000)
    assert s.max == 1000

    
def test_AbstractGridFilter___init__():
    f = helper.AbstractGridFilter()
    assert f.grids is None


def test_AbstractGridFilter___iter__():
    f = helper.AbstractGridFilter()
    f.grids = [2, 4, 8]
    try:
        it = iter(f)
    except Exception as ex:
        pytest.fail("unexpectged exception: {0}".format(ex))


def test_AbstractGridFilter___getitem__():
    f = helper.AbstractGridFilter()
    f.grids = [2, 4, 8]
    try:
        assert f[1] == 4
    except Exception as ex:
        pytest.fail("unexpectged exception: {0}".format(ex))
        

def test_AbstractGridFilter__filter():
    f = helper.AbstractGridFilter()
    r = f._filter([2, 4, 8], lambda v: v == 4)
    assert len(r) == 1
    assert r[0] == 4


def test_TimeIndexGridFilter___init__(cdump2):
    ts = helper.TimeIndexSelector(0, 0)
    f = helper.TimeIndexGridFilter(cdump2.grids, ts)
    assert f.grids is not None
    assert len(f.grids) == 4


def test_TimeIndexGridFilter__filter(cdump2):
    ts = helper.TimeIndexSelector(0, 0)
    grids = helper.TimeIndexGridFilter._filter(cdump2.grids, ts)
    assert grids is not None
    assert len(grids) == 4


def test_VerticalLevelGridFilter___init__(cdump2):
    ls = helper.VerticalLevelSelector(0, 150)
    f = helper.VerticalLevelGridFilter(cdump2.grids, ls)
    assert f.grids is not None
    assert len(f.grids) == 2
    assert f.grids[0].vert_level == 100
    assert f.grids[1].vert_level == 100


def test_VerticalLevelGridFilter__filter(cdump2):
    ls = helper.VerticalLevelSelector(0, 150)
    grids = helper.VerticalLevelGridFilter._filter(cdump2.grids, ls)
    assert grids is not None
    assert len(grids) == 2
    assert grids[0].vert_level == 100
    assert grids[1].vert_level == 100    


def test_ConcentrationDumpProperty___init__(cdump2):
    p = helper.ConcentrationDumpProperty(cdump2)
    assert p.cdump is cdump2
    assert p.min_average == 1.0e+25
    assert p.max_average == 0.0
    assert p.min_concs == [1.0e+25, 1.0e+25]
    assert p.max_concs == [0.0, 0.0]
    
    
def test_ConcentrationDumpProperty_update_average_min_max(cdump2):
    p = helper.ConcentrationDumpProperty(cdump2)
    p.min_average = 0.25
    p.max_average = 1.25
    
    p.update_average_min_max(None, None)
    assert p.min_average == 0.25
    assert p.max_average == 1.25

    p.update_average_min_max(0.35, 0.90)
    assert p.min_average == 0.25
    assert p.max_average == 1.25

    p.update_average_min_max(0.125, 1.50)
    assert p.min_average == 0.125
    assert p.max_average == 1.50
    
       
def test_ConcentrationDumpProperty_update_level_min_max(cdump2):
    p = helper.ConcentrationDumpProperty(cdump2)
    k = 1;
    p.min_concs[k] = 0.25
    p.max_concs[k] = 1.25
    
    p.update_min_max_at_level(None, None, k)
    assert p.min_concs[k] == 0.25
    assert p.max_concs[k] == 1.25

    p.update_min_max_at_level(0.35, 0.90, k)
    assert p.min_concs[k] == 0.25
    assert p.max_concs[k] == 1.25

    p.update_min_max_at_level(0.125, 1.50, k)
    assert p.min_concs[k] == 0.125
    assert p.max_concs[k] == 1.50
    
    
def test_ConcentrationDumpProperty_scale_conc():
    cdump2 = model.ConcentrationDump()
    p = helper.ConcentrationDumpProperty(cdump2)
    
    # when the first vertical level is zero.
    cdump2.vert_levels = [0, 100, 200]
    
    p.min_average = 0.25
    p.max_average = 0.75
    p.min_concs = [0.4, 0.5, 0.6]
    p.max_concs = [0.6, 0.7, 0.8]
    
    p.scale_conc(const.ConcentrationType.EACH_LEVEL, 3, 4)
    assert p.min_concs == pytest.approx((4*0.4, 3*0.5, 3*0.6))
    assert p.max_concs == pytest.approx((4*0.6, 3*0.7, 3*0.8))
    assert p.min_average == 0.25
    assert p.max_average == 0.75
    
    p.min_average = 0.25
    p.max_average = 0.75
    p.min_concs = [0.4, 0.5, 0.6]
    p.max_concs = [0.6, 0.7, 0.8]
    
    p.scale_conc(const.ConcentrationType.VERTICAL_AVERAGE, 3, 4)
    assert p.min_concs == pytest.approx((4*0.4, 0.5, 0.6))
    assert p.max_concs == pytest.approx((4*0.6, 0.7, 0.8))
    assert p.min_average == pytest.approx(3*0.25)
    assert p.max_average == pytest.approx(3*0.75)

    # when the first vertical level is not zero.
    cdump2.vert_levels = [10, 100, 200]
    
    p.min_average = 0.25
    p.max_average = 0.75
    p.min_concs = [0.4, 0.5, 0.6]
    p.max_concs = [0.6, 0.7, 0.8]
    
    p.scale_conc(const.ConcentrationType.EACH_LEVEL, 3, 4)
    assert p.min_concs == pytest.approx((3*0.4, 3*0.5, 3*0.6))
    assert p.max_concs == pytest.approx((3*0.6, 3*0.7, 3*0.8))
    assert p.min_average == 0.25
    assert p.max_average == 0.75
    
    p.min_average = 0.25
    p.max_average = 0.75
    p.min_concs = [0.4, 0.5, 0.6]
    p.max_concs = [0.6, 0.7, 0.8]
    
    p.scale_conc(const.ConcentrationType.VERTICAL_AVERAGE, 3, 4)
    assert p.min_concs == pytest.approx((0.4, 0.5, 0.6))
    assert p.max_concs == pytest.approx((0.6, 0.7, 0.8))
    assert p.min_average == pytest.approx(3*0.25)
    assert p.max_average == pytest.approx(3*0.75)

    
def test_ConcentrationDumpProperty_scale_exposure():
    cdump = model.ConcentrationDump()
    p = helper.ConcentrationDumpProperty(cdump)
    
    # EACH_LEVEL
    
    p.min_average = 0.25
    p.max_average = 0.75
    p.min_concs = [0.4, 0.5, 0.6]
    p.max_concs = [0.6, 0.7, 0.8]
    
    p.scale_exposure(const.ConcentrationType.EACH_LEVEL, 3)
    assert p.min_concs == pytest.approx((3*0.4, 3*0.5, 3*0.6))
    assert p.max_concs == pytest.approx((3*0.6, 3*0.7, 3*0.8))
    assert p.min_average == pytest.approx(0.25)
    assert p.max_average == pytest.approx(0.75)
    
    # VERTICAL AVERAGE
    
    p.min_average = 0.25
    p.max_average = 0.75
    p.min_concs = [0.4, 0.5, 0.6]
    p.max_concs = [0.6, 0.7, 0.8]
    
    p.scale_exposure(const.ConcentrationType.VERTICAL_AVERAGE, 3)
    assert p.min_concs == pytest.approx((0.4, 0.5, 0.6))
    assert p.max_concs == pytest.approx((0.6, 0.7, 0.8))
    assert p.min_average == pytest.approx(3*0.25)
    assert p.max_average == pytest.approx(3*0.75)


def test_VerticalAverageCalculator___init__():
    cdump = model.ConcentrationDump()
    p = helper.ConcentrationDumpProperty(cdump)
    ls = helper.VerticalLevelSelector()
    o = helper.VerticalAverageCalculator(cdump, ls)
    
    assert len(o.selected_level_indices) == 0
    assert len(o.delta_z) == 0
    assert o.inverse_weight == 1.0

    
def test_VerticalAverageCalculator__prepare_weighted_averaging(cdump2):
    # check what we know
    assert cdump2.vert_levels == [100, 300]
    
    p = helper.ConcentrationDumpProperty(cdump2)
    ls = helper.VerticalLevelSelector(0, 10000)
    o = helper.VerticalAverageCalculator(cdump2, ls)
    
    result = o._prepare_weighted_averaging(cdump2, ls)
    assert result == True
    assert o.selected_level_indices == [0, 1]
    assert o.delta_z[0] == 100
    assert o.delta_z[1] == 200
    assert o.inverse_weight == pytest.approx(0.003333333)
    
    # include 0 and see if the results are the same except for select_level_indices
    
    cdump2.vert_levels = [0, 100, 300]
    
    ls = helper.VerticalLevelSelector(0, 10000)
    result = o._prepare_weighted_averaging(cdump2, ls)
    assert result == True
    assert o.selected_level_indices == [1, 2]
    assert o.delta_z[1] == 100
    assert o.delta_z[2] == 200
    assert o.inverse_weight == pytest.approx(0.003333333)
    
    
def test_VerticalAverageCalculator_average(cdump2):
   
    # check what we know values
    assert cdump2.vert_levels == [100, 300]
    assert cdump2.grids[0].pollutant_index == 0
    assert cdump2.grids[1].pollutant_index == 0
    assert cdump2.grids[2].pollutant_index == 1
    assert cdump2.grids[3].pollutant_index == 1
    assert cdump2.grids[0].conc[300, 300] * 1.e+13 == pytest.approx(8.047535)
    assert cdump2.grids[1].conc[300, 300] * 1.e+13 == pytest.approx(7.963810)
    assert cdump2.grids[2].conc[300, 300] * 1.e+13 == pytest.approx(8.173024)
    assert cdump2.grids[3].conc[300, 300] * 1.e+13 == pytest.approx(7.608168)
    
    # vertical average of pollutant 0
    
    p = helper.ConcentrationDumpProperty(cdump2)
    ls = helper.VerticalLevelSelector()
    grids = [cdump2.grids[0], cdump2.grids[1]]
    
    o = helper.VerticalAverageCalculator(cdump2, ls)
    result = o.average(grids)
    
    assert result.shape == (601, 601)
    assert result[300, 300] * 1.e+13 == pytest.approx(8.047535/3.0 + 7.963810*2.0/3.0 )
    assert result[300, 300] * 1.e+13 == pytest.approx(7.9917182)
    