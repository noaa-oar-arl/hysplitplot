import pytest
import logging
import matplotlib.pyplot as plt
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
  

def test_get_lower_level():
    assert helper.get_lower_level(300.0, [100.0, 300.0]) == 100.0
    assert helper.get_lower_level(100.0, [100.0, 300.0]) == 0.0
    
    assert helper.get_lower_level(300.0, [300.0, 100.0]) == 100.0
    assert helper.get_lower_level(100.0, [300.0, 100.0]) == 0.0   
    
    assert helper.get_lower_level(100.0, [0.0, 100.0, 300.0]) == 0.0
    
    
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


def test_VerticalAverageCalculator___init__():
    cdump = model.ConcentrationDump()
    ls = helper.VerticalLevelSelector()
    o = helper.VerticalAverageCalculator(cdump, ls)
    
    assert len(o.selected_level_indices) == 0
    assert len(o.delta_z) == 0
    assert o.inverse_weight == 1.0

    
def test_VerticalAverageCalculator__prepare_weighted_averaging(cdump2):
    # check what we know
    assert cdump2.vert_levels == [100, 300]
    
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
    
    ls = helper.VerticalLevelSelector()
    grids = [cdump2.grids[0], cdump2.grids[1]]
    
    o = helper.VerticalAverageCalculator(cdump2, ls)
    result = o.average(grids)
    
    assert result.shape == (601, 601)
    assert result[300, 300] * 1.e+13 == pytest.approx(8.047535/3.0 + 7.963810*2.0/3.0 )
    assert result[300, 300] * 1.e+13 == pytest.approx(7.9917182)
    

def test_ConcentrationTypeFactory_create_instance():
    p = helper.ConcentrationTypeFactory.create_instance(const.ConcentrationType.EACH_LEVEL)
    assert isinstance(p, helper.LevelConcentration)
    
    p = helper.ConcentrationTypeFactory.create_instance(const.ConcentrationType.VERTICAL_AVERAGE)
    assert isinstance(p, helper.VerticalAverageConcentration) 

    try:
        # try with an unknown type
        p = helper.ConcentrationTypeFactory.create_instance(999999)
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "unknown concentration type 999999" 
        

def test_ConcentrationType___init__():
    p = helper.ConcentrationType()
    assert hasattr(p, "cdump")
    assert hasattr(p, "level_selector")
    assert hasattr(p, "pollutant_selector")
       

def test_ConcentrationType_initialize():
    p = helper.ConcentrationType()
    cdump = model.ConcentrationDump()
    ls = helper.VerticalLevelSelector()
    ps = helper.PollutantSelector()
    
    p.initialize(cdump, ls, ps)
    
    assert p.cdump is cdump
    assert p.level_selector is ls
    assert p.pollutant_selector is ps
    
    
def test_VerticalAverageConcentration___init__():
    p = helper.VerticalAverageConcentration()
    
    assert p.cdump is None
    assert p.level_selector is None
    assert p.pollutant_selector is None
    
    assert p.average_calc is None
    assert p.min_average == 1.0e+25
    assert p.max_average == 0.0


def test_VerticalAverageConcentration_initialize(cdump2):
    p = helper.VerticalAverageConcentration()
    ls = helper.VerticalLevelSelector()
    ps = helper.PollutantSelector()
    
    p.initialize(cdump2, ls, ps)
    
    assert p.average_calc is not None
    assert p.cdump is cdump2
    assert p.level_selector is ls
    assert p.pollutant_selector is ps


def test_VerticalAverageConcentration_prepare_grids_for_plotting(cdump2):
    p = helper.VerticalAverageConcentration()
    ls = helper.VerticalLevelSelector()
    ps = helper.PollutantSelector()
    p.initialize(cdump2, ls, ps)
    
    # should result in one conc grid: vertical average of concs after summing over pollutants
    grids = p.prepare_grids_for_plotting(cdump2.grids)
    assert len(grids) == 1
    
    g = grids[0]
    assert g.time_index == 0
    assert g.pollutant_index == -1
    assert g.vert_level_index == -1
    assert g.conc.shape == (601, 601)
    assert g.conc[300, 300] * 1.0e+13 == pytest.approx( \
                                                        8.047535/3.0 + 7.963810*2.0/3.0 + \
                                                        8.173024/3.0 + 7.608168*2.0/3.0 )
    
    
def test_VerticalAverageConcentration_update_min_max(cdump2):
    p = helper.VerticalAverageConcentration()
    ls = helper.VerticalLevelSelector()
    ps = helper.PollutantSelector(0)
    p.initialize(cdump2, ls, ps)

    p.update_min_max(cdump2.grids)
    
    assert p.max_average * 1.e+13 == pytest.approx(8.047535/3.0 + 7.963810*2.0/3.0)
    assert p.min_average * 1.e+15 == pytest.approx(0.6242119)
    
    
def test_VerticalAverageConcentration_update_average_min_max():
    p = helper.VerticalAverageConcentration()
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


def test_VerticalAverageConcentration_scale_conc():
    p = helper.VerticalAverageConcentration()
    p.cdump = model.ConcentrationDump()
    
    # when the first vertical level is zero.
    p.cdump.vert_levels = [0, 100, 200]
    
    p.min_average = 0.25
    p.max_average = 0.75
    
    p.scale_conc(3, 4)
    
    assert p.min_average == pytest.approx(3*0.25)
    assert p.max_average == pytest.approx(3*0.75)

    # when the first vertical level is not zero.
    
    p.cdump.vert_levels = [10, 100, 200]
    
    p.min_average = 0.25
    p.max_average = 0.75
    
    p.scale_conc(3, 4)
    
    assert p.min_average == pytest.approx(3*0.25)
    assert p.max_average == pytest.approx(3*0.75)


def test_VerticalAverageConcentration_scale_exposure():
    p = helper.VerticalAverageConcentration()
    
    p.min_average = 0.25
    p.max_average = 0.75
    
    p.scale_exposure(3)
    assert p.min_average == pytest.approx(3*0.25)
    assert p.max_average == pytest.approx(3*0.75)


def test_VerticalAverageConcentration_contour_min_conc():
    p = helper.VerticalAverageConcentration()
    p.min_average = 0.25
    assert p.contour_min_conc == 0.25
    
    
def test_VerticalAverageConcentration_contour_max_conc():
    p = helper.VerticalAverageConcentration()
    p.max_average = 0.75
    assert p.contour_max_conc == 0.75  
     
    
def test_VerticalAverageConcentration_get_plot_conc_range():
    p = helper.VerticalAverageConcentration()
    p.min_average = 0.25
    p.max_average = 0.75
    assert p.get_plot_conc_range(0) == pytest.approx((0.25, 0.75))     


def test_LevelConcentration___init__():
    p = helper.LevelConcentration()
    
    assert p.cdump is None
    assert p.level_selector is None
    assert p.pollutant_selector is None
    
    assert p.min_concs is None
    assert p.max_concs is None
    

def test_LevelConcentration_initialize(cdump2):
    p = helper.LevelConcentration()
    ls = helper.VerticalLevelSelector()
    ps = helper.PollutantSelector()
    
    p.initialize(cdump2, ls, ps)
    assert p.min_concs == [1.0e+25, 1.0e+25]
    assert p.max_concs == [0.0, 0.0]

    assert p.cdump is cdump2
    assert p.level_selector is ls
    assert p.pollutant_selector is ps
    

def test_LevelConcentration_update_min_max(cdump2):
    p = helper.LevelConcentration()
    p.initialize(cdump2, None, None)
    p.update_min_max(cdump2.grids)
    
    assert p.min_concs[0] * 1.0e+15 == pytest.approx(1.39594131)
    assert p.min_concs[1] * 1.0e+15 == pytest.approx(0.935228347)
    assert p.max_concs[0] * 1.0e+13 == pytest.approx(8.173024)
    assert p.max_concs[1] * 1.0e+13 == pytest.approx(7.963810)


def test_LevelConcentration_update_min_max_at_level(cdump2):
    p = helper.LevelConcentration()
    ls = helper.VerticalLevelSelector()
    ps = helper.PollutantSelector()
    p.initialize(cdump2, ls, ps)
    
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
    
    
def test_LevelConcentration_prepare_grids_for_plotting(cdump2):
    p = helper.LevelConcentration()
    # limit to one pollutant and one vertical level
    ls = helper.VerticalLevelSelector(300, 1000)
    ps = helper.PollutantSelector(1)
    p.initialize(cdump2, ls, ps)

    grids = p.prepare_grids_for_plotting(cdump2.grids)
    
    assert len(grids) == 1
    assert grids[0].conc[300, 300] * 1.0e+13 == pytest.approx(7.608168)
    
    
def test_LevelConcentration_scale_conc():
    p = helper.LevelConcentration()
    
    # when the first vertical level is zero.
    
    p.cdump = model.ConcentrationDump()
    p.cdump.vert_levels = [0, 100, 200]
    
    p.min_concs = [0.4, 0.5, 0.6]
    p.max_concs = [0.6, 0.7, 0.8]
    
    p.scale_conc(3, 4)
    
    assert p.min_concs == pytest.approx((4*0.4, 3*0.5, 3*0.6))
    assert p.max_concs == pytest.approx((4*0.6, 3*0.7, 3*0.8))
    
    # when the first vertical level is not zero.
    
    p.cdump.vert_levels = [10, 100, 200]
    
    p.min_concs = [0.4, 0.5, 0.6]
    p.max_concs = [0.6, 0.7, 0.8]
    
    p.scale_conc(3, 4)
    
    assert p.min_concs == pytest.approx((3*0.4, 3*0.5, 3*0.6))
    assert p.max_concs == pytest.approx((3*0.6, 3*0.7, 3*0.8))


def test_LevelConcentration_scale_exposure():
    p = helper.LevelConcentration()
    
    p.min_concs = [0.4, 0.5, 0.6]
    p.max_concs = [0.6, 0.7, 0.8]
    
    p.scale_exposure(3)
    assert p.min_concs == pytest.approx((3*0.4, 3*0.5, 3*0.6))
    assert p.max_concs == pytest.approx((3*0.6, 3*0.7, 3*0.8))


def test_LevelConcentration_contour_min_conc():
    p = helper.LevelConcentration()
    p.min_concs = [0.1, 0.2, 0.4]
    assert p.contour_min_conc == 0.4
    
    
def test_LevelConcentration_contour_max_conc():
    p = helper.LevelConcentration()
    p.max_concs = [0.2, 0.4, 0.75]
    assert p.contour_max_conc == 0.75  
     
    
def test_LevelConcentration_get_plot_conc_range():
    p = helper.LevelConcentration()
    p.min_concs = [0.1, 0.2, 0.4]
    p.max_concs = [0.2, 0.4, 0.75]
    assert p.get_plot_conc_range(0) == pytest.approx((0.1, 0.20))
    assert p.get_plot_conc_range(2) == pytest.approx((0.4, 0.75))


def test_ConcentrationMapFactory_create_instance():
    p = helper.ConcentrationMapFactory.create_instance(const.ConcentrationMapType.THRESHOLD_LEVELS, 1)
    assert isinstance(p, helper.ThresholdLevelsMap)
    assert p.KHEMIN == 1
    
    p = helper.ConcentrationMapFactory.create_instance(const.ConcentrationMapType.VOLCANIC_ERUPTION, 1)
    assert isinstance(p, helper.VolcanicEruptionMap)
    assert p.KHEMIN == 1
    
    p = helper.ConcentrationMapFactory.create_instance(99999, 1)
    assert isinstance(p, helper.ConcentrationMap)
    assert p.KHEMIN == 1
    
    
def test_ConcentrationMap___init__():
    p = helper.ConcentrationMap(2, 4)
    assert p.KMAP == 2
    assert p.KHEMIN == 4
    
    
def test_ConcentrationMap_has_banner():
    p = helper.ConcentrationMap(2, 4)
    assert p.has_banner() == False

    
def test_ConcentrationMap_format_conc():
    p = helper.ConcentrationMap(2, 4)
    assert p.format_conc(2.56789e+5) == "2.6e+05"
    assert p.format_conc(2.56789e+4) == "25678"
    assert p.format_conc(2.56789e+3) == "2567"
    assert p.format_conc(2.56789e+2) == "256"
    assert p.format_conc(2.56789e+1) == "25"
    assert p.format_conc(2.56789) == "2"
    assert p.format_conc(0.256789) == "0.3"
    assert p.format_conc(0.0256789) == "0.03"
    assert p.format_conc(0.00256789) == "0.003"
    assert p.format_conc(0.000256789) == "2.6e-04"
    assert p.format_conc(0.0) == " "
    assert p.format_conc(-0.1) == " "

    
def test_ConcentrationMap_draw_explanation_text():
    p = helper.ConcentrationMap(2, 4)
    assert p.draw_explanation_text(None, 0, 1.25, None, None, None) == 1.25
   
    
def test_ThresholdLevelsMap___init__():
    p = helper.ThresholdLevelsMap(2, 4)
    assert p.KMAP == 2
    assert p.KHEMIN == 4
    
    
def test_ThresholdLevelsMap_has_banner():
    p = helper.ThresholdLevelsMap(2, 4)
    assert p.has_banner() == True
    
    
def test_ThresholdLevelsMap_get_banner():
    p = helper.ThresholdLevelsMap(2, 4)
    assert p.get_banner() == "Not for Public Dissemination"
    

def test_ThresholdLevelsMap_format_conc():
    p = helper.ThresholdLevelsMap(2, 4)
    assert p.format_conc(2.56789e+5) == "2.6e+05"
    assert p.format_conc(2.56789e+4) == "25678"
    assert p.format_conc(2.56789e+3) == "2567"
    assert p.format_conc(2.56789e+2) == "256"
    assert p.format_conc(2.56789e+1) == "25.7"
    assert p.format_conc(2.56789) == "2.6"
    assert p.format_conc(0.256789) == "0.3"
    assert p.format_conc(0.0256789) == "0.03"
    assert p.format_conc(0.00256789) == "0.003"
    assert p.format_conc(0.000256789) == "2.6e-04"
    assert p.format_conc(0.0) == " "
    assert p.format_conc(-0.1) == " "

    
def test_ThresholdLevelsMap_draw_explanation_text():
    p = helper.ThresholdLevelsMap(2, 4)
    axes = plt.axes()
    
    try:
        y = p.draw_explanation_text(axes, 0, 1.25, 12.0, 14.0, ["USER"])
        assert y == 1.25
        
        y = p.draw_explanation_text(axes, 0, 1.25, 12.0, 14.0, ["AEGL-1"])
        assert y < 1.25
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))

    plt.close(axes.get_figure())
   
    
def test_VolcanicEruptionMap___init__():
    p = helper.VolcanicEruptionMap(2, 4)
    assert p.KMAP == 2
    assert p.KHEMIN == 4
    
    
def test_VolcanicEruptionMap_has_banner():
    p = helper.VolcanicEruptionMap(2, 4)
    assert p.has_banner() == True
    
    
def test_VolcanicEruptionMap_has_banner():
    p = helper.VolcanicEruptionMap(2, 4)
    assert p.get_banner() == "*** Hypothetical eruption ***"
    
    
def test_VolcanicEruptionMap_draw_explanation_text():
    p = helper.VolcanicEruptionMap(2, 4)
    axes = plt.axes()
    
    try:
        y = p.draw_explanation_text(axes, 0, 1.25, 12.0, 14.0, ["AGEL"]) == 1.25
        assert y < 1.25
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))

    plt.close(axes.get_figure())
