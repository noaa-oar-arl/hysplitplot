import pytest
import logging
from hysplit4.conc import prop, model
from hysplit4 import const


logger = logging.getLogger(__name__)


@pytest.fixture
def cdump():
    m = model.ConcentrationDump().get_reader().read("data/cdump_two_pollutants")
    return m


def test_ConcentrationDumpProperty___init__(cdump):
    p = prop.ConcentrationDumpProperty(cdump)
    assert p.cdump is cdump
    assert p.min_average == 0.0
    assert p.max_average == 0.0
    assert len(p.min_concs) == 0
    assert len(p.max_concs) == 0
    
    
def test_ConcentrationDumpProperty_get_vertical_average_analyzer(cdump):
    p = prop.ConcentrationDumpProperty(cdump)
    a = p.get_vertical_average_analyzer()
    assert isinstance(a, prop.VerticalAverageAnalyzer)
    
    
def test_ConcentrationDumpProperty_get_vertical_level_analyzer(cdump):
    p = prop.ConcentrationDumpProperty(cdump)
    a = p.get_vertical_level_analyzer()
    assert isinstance(a, prop.VerticalLevelAnalyzer)
    
    
def test_ConcentrationDumpProperty_scale_conc():
    cdump = model.ConcentrationDump()
    p = prop.ConcentrationDumpProperty(cdump)
    
    # when the first vertical level is zero.
    cdump.vert_levels = [0, 100, 200]
    
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
    cdump.vert_levels = [10, 100, 200]
    
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
    p = prop.ConcentrationDumpProperty(cdump)
    
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


def test_VerticalAverageAnalayzer___init__():
    cdump = model.ConcentrationDump()
    p = prop.ConcentrationDumpProperty(cdump)
    o = prop.VerticalAverageAnalyzer(p)
    
    assert o.cdump_prop is p
    assert len(o.selected_level_indices) == 0
    assert len(o.delta_z) == 0
    assert o.inverse_weight == 1.0
    
    
def test_VerticalAverageAnalyzer_analyze(cdump):
    p = prop.ConcentrationDumpProperty(cdump)
    o = prop.VerticalAverageAnalyzer(p)
    
    # two pollutants are expected
    assert len(cdump.pollutants) == 2
    
    assert len(cdump.conc_grids) == 4
    
    # pollutant 0
    
    ts = model.TimeIndexSelector(0, 0)
    ps = model.PollutantSelector(0)
    ls = model.VerticalLevelSelector(0, 10000)
    result = o.analyze(ts, ps, ls)
    assert result is p
    assert result.max_average * 1.e+13 == pytest.approx(7.991718)
    assert result.min_average * 1.e+16 == pytest.approx(6.242119)
    
    # all pollutants
    
    ts = model.TimeIndexSelector(0, 0)
    ps = model.PollutantSelector(-1)
    ls = model.VerticalLevelSelector(0, 10000)
    result = o.analyze(ts, ps, ls)
    assert result is p
    assert result.max_average * 1.e+12 == pytest.approx(1.578817)
    assert result.min_average * 1.e+16 == pytest.approx(6.235384) 
       
    
def test_VerticalAverageAnalyzer__prepare_weighted_averaging(cdump):
    p = prop.ConcentrationDumpProperty(cdump)
    o = prop.VerticalAverageAnalyzer(p)
    
    # check the levels
    assert cdump.vert_levels == [100, 300]
    
    ls = model.VerticalLevelSelector(0, 10000)
    result = o._prepare_weighted_averaging(cdump, ls)
    assert result == True
    assert o.selected_level_indices == [0, 1]
    assert o.delta_z == [100, 200]
    assert o.inverse_weight == pytest.approx(0.003333333)
    
    # include 0 and see if the results are the same except for select_level_indices
    
    cdump.vert_levels = [0, 100, 300]
    
    ls = model.VerticalLevelSelector(0, 10000)
    result = o._prepare_weighted_averaging(cdump, ls)
    assert result == True
    assert o.selected_level_indices == [1, 2]
    assert o.delta_z == [100, 200]
    assert o.inverse_weight == pytest.approx(0.003333333)
    
    
def test_VerticalAverageAnalyzer__average_vertically(cdump):
    p = prop.ConcentrationDumpProperty(cdump)
    o = prop.VerticalAverageAnalyzer(p)
    
    # check values
    assert cdump.vert_levels == [100, 300]
    assert cdump.conc_grids[0].pollutant_index == 0
    assert cdump.conc_grids[1].pollutant_index == 0
    assert cdump.conc_grids[2].pollutant_index == 1
    assert cdump.conc_grids[3].pollutant_index == 1
    assert cdump.conc_grids[0].conc[300, 300] * 1.e+13 == pytest.approx(8.047535)
    assert cdump.conc_grids[1].conc[300, 300] * 1.e+13 == pytest.approx(7.963810)
    assert cdump.conc_grids[2].conc[300, 300] * 1.e+13 == pytest.approx(8.173024)
    assert cdump.conc_grids[3].conc[300, 300] * 1.e+13 == pytest.approx(7.608168)
    
    ls = model.VerticalLevelSelector(0, 10000)
    o._prepare_weighted_averaging(cdump, ls)
    
    # vertical average of pollutant 0
    
    ps = model.PollutantSelector(0)
    result = o._average_vertically(0, ps)
    
    assert result.shape == (601, 601)
    assert result[300, 300] * 1.e+13 == pytest.approx( \
                                              8.047535/3.0 + \
                                              7.963810*2.0/3.0 )
    assert result[300, 300] * 1.e+13 == pytest.approx(7.9917182)
    
    # vertical average of all pollutants
    
    ps = model.PollutantSelector(-1)
    result = o._average_vertically(0, ps)
    
    assert result.shape == (601, 601)
    assert result[300, 300] * 1.e+13 == pytest.approx( \
                                              8.047535/3.0 + \
                                              7.963810*2.0/3.0 + \
                                              8.173024/3.0 + \
                                              7.608168*2.0/3.0 )
    assert result[300,300] * 1.e+12 == pytest.approx(1.5788172)


def test_VerticalLevelAnalyzer___init__():
    cdump = model.ConcentrationDump()
    p = prop.ConcentrationDumpProperty(cdump)
    o = prop.VerticalLevelAnalyzer(p)
    
    assert o.cdump_prop is p


def test_VerticalLevelAnalyzer_analyze(cdump):
    p = prop.ConcentrationDumpProperty(cdump)
    o = prop.VerticalLevelAnalyzer(p)
    
    ts = model.TimeIndexSelector(0, 0)
    ps = model.PollutantSelector(-1)
    
    q = o.analyze(ts, ps)
    
    assert len(cdump.vert_levels) == 2
    assert len(q.min_concs) == 2
    assert len(q.max_concs) == 2
    assert q.max_concs[0] * 1.0e+13 == pytest.approx(8.1730244)
    assert q.max_concs[1] * 1.0e+13 == pytest.approx(7.9638097)
    assert q.min_concs[0] * 1.0e+15 == pytest.approx(1.3959413)
    assert q.min_concs[1] * 1.0e+16 == pytest.approx(9.352283)




    