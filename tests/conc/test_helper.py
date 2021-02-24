# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_helper.py
#
# Performs unit tests on functions and class methods declared in conc/helper.py.
# ---------------------------------------------------------------------------

import datetime
import logging
import matplotlib.pyplot as plt
import numpy
import pytest
import pytz

from hysplitdata.conc import model
from hysplitplot import const, util
from hysplitplot.conc import helper


logger = logging.getLogger(__name__)


@pytest.fixture
def cdump2():
    m = model.ConcentrationDump().get_reader().read("data/cdump_two_pollutants")
    return m


@pytest.fixture
def cdump3():
    m = model.ConcentrationDump().get_reader().read("data/cdump_deposit")
    return m    
        

# Declare a concrete class needed for testing an abstract class.
class ConcentrationTypeTest(helper.ConcentrationType):
    
    def prepare_grids_for_plotting(self, t_grids):
        pass
    
    def update_min_max(self, t_grids):
        pass
    
    def scale_conc(self, CONADJ, DEPADJ):
        pass
    
    def scale_exposure(self, factor):
        pass
    
    def undo_scale_exposure(self):
        pass    
   
    def normalize_min_max(self):
        pass
    
    @property
    def contour_min_conc(self):
        pass
    
    @property
    def contour_max_conc(self):
        pass
    
    def get_plot_conc_range(self, grid):
        pass
    
    def get_level_range_str(self, level1, level2):
        pass
    
    def get_upper_level(self, grid_level, settings_level):
        pass


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
    
    # set min and max values
    for g in cdump2.grids:
        g.extension = helper.GridProperties()
        g.extension.update(g.conc)
        
    # pollutant 0, all levels
    ls = helper.VerticalLevelSelector(0, 10000)
    ps = helper.PollutantSelector(0)
    v_grids = helper.sum_over_pollutants_per_level(cdump2.grids, ls, ps)

    assert len(v_grids) == 2
    assert v_grids[0] is cdump2.grids[0]
    assert v_grids[1] is cdump2.grids[1]
    assert v_grids[0].extension.min_conc * 1.e+13 == pytest.approx(0.01871257)
    assert v_grids[0].extension.max_conc * 1.e+13 == pytest.approx(8.047535)
    assert v_grids[1].extension.min_conc * 1.e+13 == pytest.approx(0.009363178)
    assert v_grids[1].extension.max_conc * 1.e+13 == pytest.approx(7.963810)
    
    # pollutant 1, all levels
    ls = helper.VerticalLevelSelector(0, 10000)
    ps = helper.PollutantSelector(1)
    v_grids = helper.sum_over_pollutants_per_level(cdump2.grids, ls, ps)

    assert len(v_grids) == 2
    assert v_grids[0] is cdump2.grids[2]
    assert v_grids[1] is cdump2.grids[3]    
    assert v_grids[0].extension.min_conc * 1.e+13 == pytest.approx(0.01395941)
    assert v_grids[0].extension.max_conc * 1.e+13 == pytest.approx(8.173024)
    assert v_grids[1].extension.min_conc * 1.e+13 == pytest.approx(0.00935228)
    assert v_grids[1].extension.max_conc * 1.e+13 == pytest.approx(7.608169)
#        
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
    assert v_grids[0].extension.min_conc * 1.e+13 == pytest.approx( 0.01873180)
    assert v_grids[0].extension.max_conc * 1.e+13 == pytest.approx(16.22056)
    assert v_grids[1].extension.min_conc * 1.e+13 == pytest.approx( 0.009353077)
    assert v_grids[1].extension.max_conc * 1.e+13 == pytest.approx(15.57198)


def test_sum_conc_grids_of_interest(cdump2):
    level_selector = helper.VerticalLevelSelector()
    pollutant_selector = helper.PollutantSelector()
    time_selector = helper.TimeIndexSelector()
    
    conc = helper.sum_conc_grids_of_interest(cdump2.grids,
                                             level_selector,
                                             pollutant_selector,
                                             time_selector)
    
    assert conc[300, 300] * 1.e+13 == pytest.approx(8.047535 + 8.173024 + 7.963810 + 7.608168)
    
    # when no grid can be selected
    level_selector = helper.VerticalLevelSelector(50000, 90000)
    try:
        conc = helper.sum_conc_grids_of_interest(cdump2.grids,
                                                 level_selector,
                                                 pollutant_selector,
                                                 time_selector)
    except Exception as ex:
        pytest.fail("unexpected exception: {}".format(ex))
        
    assert conc is None


def test_find_nonzero_min_max(cdump2):
    vmin, vmax = helper.find_nonzero_min_max(cdump2.grids[0].conc)
    assert vmin * 1.0e+15 == pytest.approx(1.871257)
    assert vmax * 1.0e+13 == pytest.approx(8.047535)


def test_find_max_locs(cdump2):
    g = cdump2.grids[0]
    
    loc = helper.find_max_locs(g)
    
    assert len(loc) == 1
    assert loc[0] == pytest.approx((-84.22, 39.90))
    assert loc[0][0] == g.longitudes[300]
    assert loc[0][1] == g.latitudes[300]
    
    # max at another location
    g.conc[0, 1] = g.conc[300, 300]
    
    loc = helper.find_max_locs(g)
    
    assert len(loc) == 2
    assert loc[0] == pytest.approx((-99.17, 24.90))
    assert loc[0][0] == g.longitudes[1]
    assert loc[0][1] == g.latitudes[0]
    assert loc[1] == pytest.approx((-84.22, 39.90))
    assert loc[1][0] == g.longitudes[300]
    assert loc[1][1] == g.latitudes[300]
    
    
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
    assert a == [1, 3]    
    
    s = helper.TimeIndexSelector(6-1, 8-1, 1)
    a = []
    for t_index in s:
        a.append(t_index)
    assert a == [5, 6, 7]    
    
    
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


def test_GridProperties___init__():
    p = helper.GridProperties()
    assert p.min_conc is None
    assert p.max_conc is None
    assert p.min_vert_avg_conc is None
    assert p.max_vert_avg_conc is None
    assert p.max_locs is None


def test_GridProperties_clone():
    p = helper.GridProperties()
    p.min_conc = 0.4
    p.max_conc = 0.6
    p.min_vert_avg_conc = 0.2
    p.max_vert_avg_conc = 0.8
    
    o = p.clone()
    assert o.min_conc == 0.4
    assert o.max_conc == 0.6
    assert o.min_vert_avg_conc == 0.2
    assert o.max_vert_avg_conc == 0.8


def test_GridProperties_update():
    p = helper.GridProperties()
    c = numpy.zeros((3, 2))
    c[0, 0] = 10.0
    c[0, 1] =  1.0
    
    p.update(c)
    
    assert p.min_conc == 1.0
    assert p.max_conc == 10.0
    
    # Test with a concentration grid with zero values.
    c = numpy.zeros((3, 2))
    p.update(c)
    assert p.min_conc == 0.0
    assert p.max_conc == 0.0
    
    # Another test.
    c[0, 1] = 10.0
    p.update(c)
    assert p.min_conc == 10.0  # because zeros are ignored.
    assert p.max_conc == 10.0


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


def test_GisOutputFilenameForVerticalAverageConc_get_basename():
    o = helper.GisOutputFilenameForVerticalAverageConc()
    assert o.get_basename(1, 'ps') == 'GIS_00000-99999_ps_01'
    assert o.get_basename(2, 'jobid', 50, 100) == 'GIS_00050-00100_jobid_02'


def test_GisOutputFilenameForLevelConc_get_basename():
    o = helper.GisOutputFilenameForLevelConc()
    assert o.get_basename(1, 'ps') == 'GIS_00000_ps_01'
    assert o.get_basename(2, 'jobid', 50) == 'GIS_00050_jobid_02'


def test_GisOutputFilenameForDeposit_get_basename():
    o = helper.GisOutputFilenameForDeposit()
    assert o.get_basename(1, 'ps') == 'GIS_DEP_ps_01'
    assert o.get_basename(2, 'jobid', 50) == 'GIS_DEP_jobid_02'


def test_KmlOutputFilename_get_basename():
    o = helper.KmlOutputFilename()
    assert o.get_basename(1, 'ps') == 'HYSPLIT_ps'
    assert o.get_basename(2, 'jobid', 50) == 'HYSPLIT_jobid'
    # with the output_basename set
    o = helper.KmlOutputFilename('plot')
    assert o.get_basename(1, 'ps') == 'plot_ps'
    assert o.get_basename(2, 'jobid', 50) == 'plot_jobid'


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
    p = ConcentrationTypeTest()
    assert hasattr(p, "cdump")
    assert hasattr(p, "level_selector")
    assert hasattr(p, "pollutant_selector")
    assert hasattr(p, "custom_layer_str") and p.custom_layer_str == None
    assert hasattr(p, "gis_filename_maker")
    assert hasattr(p, "kml_filename_maker")


def test_ConcentrationType_initialize():
    p = ConcentrationTypeTest()
    cdump = model.ConcentrationDump()
    ls = helper.VerticalLevelSelector()
    ps = helper.PollutantSelector()
    
    p.initialize(cdump, ls, ps)
    
    assert p.cdump is cdump
    assert p.level_selector is ls
    assert p.pollutant_selector is ps


def test_ConcentrationType_set_custom_layer_str():
    p = ConcentrationTypeTest()
    p.set_custom_layer_str("  AVERAGED BETWEEN ") # spaces will be trimmed.
    assert p.custom_layer_str == "AVERAGED BETWEEN"
    
    p.set_custom_layer_str(None)
    assert p.custom_layer_str is None
    
    
def test_ConcentrationType_get_lower_level():
    p = ConcentrationTypeTest()
    
    assert p.get_lower_level(300.0, [100.0, 300.0]) == 100.0
    assert p.get_lower_level(100.0, [100.0, 300.0]) == 0.0
    
    assert p.get_lower_level(300.0, [300.0, 100.0]) == 100.0
    assert p.get_lower_level(100.0, [300.0, 100.0]) == 0.0   
    
    assert p.get_lower_level(100.0, [0.0, 100.0, 300.0]) == 0.0
    
    
def test_ConcentrationType_make_gis_basename():
    # use a concrete class object
    o = helper.VerticalAverageConcentration()
    assert o.make_gis_basename(2, "ps", 100.0, 5000.0) == "GIS_00100-05000_ps_02"


def test_ConcentrationType_make_kml_basename():
    # use a concrete class object
    o = helper.VerticalAverageConcentration()
    assert o.make_kml_basename(2, "ps", 100.0, 5000.0) == "HYSPLIT_ps"


def test_VerticalAverageConcentration___init__():
    p = helper.VerticalAverageConcentration()
    # member variables declared in the super class.
    assert p.cdump is None
    assert p.level_selector is None
    assert p.pollutant_selector is None
    #
    assert p.average_calc is None
    assert p.min_average == 1.0e+25
    assert p.max_average == 0.0
    assert p.gis_filename_maker is not None
    assert p.kml_filename_maker is not None


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
    grids, grids_gnd = p.prepare_grids_for_plotting(cdump2.grids)
    assert len(grids) == 1
    assert len(grids_gnd) == 0
    
    g = grids[0]
    assert g.time_index == 0
    assert g.pollutant_index == -1
    assert g.vert_level_index == -1
    assert g.conc.shape == (601, 601)
    assert g.conc[300, 300] * 1.0e+13 == pytest.approx( \
                                                        8.047535/3.0 + 7.963810*2.0/3.0 + \
                                                        8.173024/3.0 + 7.608168*2.0/3.0 )
    assert g.nonzero_conc_count == 1351


def test_VerticalAverageConcentration_prepare_grids_for_plotting_case2(cdump3):
    p = helper.VerticalAverageConcentration()
    ls = helper.VerticalLevelSelector()
    ps = helper.PollutantSelector()
    p.initialize(cdump3, ls, ps)

    t_grids = list(filter(lambda g: g.time_index == 0, cdump3.grids))
    assert len(t_grids) == 2
        
    grids, grids_gnd = p.prepare_grids_for_plotting(t_grids)
    assert len(grids) == 1
    assert len(grids_gnd) == 1
    assert grids[0].nonzero_conc_count == 15
    assert grids_gnd[0].nonzero_conc_count == 14
    
    
def test_VerticalAverageConcentration_update_min_max(cdump2):
    p = helper.VerticalAverageConcentration()
    ls = helper.VerticalLevelSelector()
    ps = helper.PollutantSelector(0)
    p.initialize(cdump2, ls, ps)

    p.update_min_max(cdump2.grids)
    
    assert p.max_average * 1.e+13 == pytest.approx(8.047535/3.0 + 7.963810*2.0/3.0)
    assert p.min_average * 1.e+15 == pytest.approx(0.6242119)
    
    # check extended properties
    ext = cdump2.grids[0].extension
    assert ext is not None
    assert ext.max_vert_avg_conc * 1.e+13 == pytest.approx(8.047535/3.0 + 7.963810*2.0/3.0)
    assert ext.min_vert_avg_conc * 1.e+15 == pytest.approx(0.6242119)
    
    ext2 = cdump2.grids[1].extension
    assert ext2.max_vert_avg_conc == ext.max_vert_avg_conc
    assert ext2.min_vert_avg_conc == ext.min_vert_avg_conc
    
    ext2 = cdump2.grids[3].extension
    assert ext2.max_vert_avg_conc == ext.max_vert_avg_conc
    assert ext2.min_vert_avg_conc == ext.min_vert_avg_conc


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


def test_VerticalAverageConcentration_normalize_min_max():
    p = helper.VerticalAverageConcentration()
    assert p.min_average == 1.0e+25
    assert p.max_average == 0.0
    
    p.normalize_min_max()
    
    assert p.min_average == 0.0
    assert p.max_average == 1.0e+25
    

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


def test_VerticalAverageConcentration_undo_scale_exposure():
    p = helper.VerticalAverageConcentration()
    
    p.min_average = 0.25
    p.max_average = 0.75
    
    p.scale_exposure(3)
    assert p.min_average == pytest.approx(3*0.25)
    assert p.max_average == pytest.approx(3*0.75)

    p.undo_scale_exposure()
    assert p.min_average == pytest.approx(0.25)
    assert p.max_average == pytest.approx(0.75)


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
    
    g = model.ConcentrationGrid(None)
    g.extension = helper.GridProperties()
    g.extension.min_vert_avg_conc = 0.4
    g.extension.max_vert_avg_conc = 0.6
    
    assert p.get_plot_conc_range(g, 2.0) == pytest.approx((0.80, 1.20))     
     
    
def test_VerticalAverageConcentration_get_level_range_str():
    p = helper.VerticalAverageConcentration()
    level1 = util.LengthInMeters(1.0)
    level2 = util.LengthInMeters(2.0)
    
    assert p.get_level_range_str(level1, level2) == "averaged between 1 m and 2 m"
    
    p.set_custom_layer_str("  AVERAGED BETWEEN ")
    assert p.get_level_range_str(level1, level2) == "AVERAGED BETWEEN 1 m and 2 m"
    
    
def test_VerticalAverageConcentration_get_upper_level():
    p = helper.VerticalAverageConcentration()

    # should return the settings_level
    grid_level = 100.0
    settings_level = 500.0    
    assert p.get_upper_level(grid_level, settings_level) == pytest.approx(500.0)
    
    
def test_LevelConcentration___init__():
    p = helper.LevelConcentration()
    # those declared in the super class.
    assert p.cdump is None
    assert p.level_selector is None
    assert p.pollutant_selector is None
    #
    assert p.min_concs is None
    assert p.max_concs is None
    assert p.KAVG == 1
    assert p.alt_KAVG == 1
    assert p.ground_index is None
    assert p.gis_filename_maker is not None
    assert p.kml_filename_maker is not None


def test_LevelConcentration_set_alt_KAVG():
    p = helper.LevelConcentration()
    p.set_alt_KAVG(13)
    assert p.alt_KAVG == 13
    assert p.KAVG == 1
        

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
    assert p.ground_index == None


def test_LevelConcentration_prepare_grids_for_plotting(cdump2):
    p = helper.LevelConcentration()
    # limit to one pollutant and one vertical level
    ls = helper.VerticalLevelSelector(300, 1000)
    ps = helper.PollutantSelector(1)
    p.initialize(cdump2, ls, ps)

    grids, grids_gnd = p.prepare_grids_for_plotting(cdump2.grids)
    
    assert len(grids) == 1
    assert len(grids_gnd) == 0
    assert grids[0].conc[300, 300] * 1.0e+13 == pytest.approx(7.608168)
    

def test_LevelConcentration_prepare_grids_for_plotting__case2(cdump3):
    p = helper.LevelConcentration()
    ls = helper.VerticalLevelSelector(10, 500) # choose one-level
    ps = helper.PollutantSelector()
    p.initialize(cdump3, ls, ps)

    # take the grids at zero time index.
    t_grids = list(filter(lambda g: g.time_index == 0, cdump3.grids))
    assert len(t_grids) == 2

    # expect one grid above the ground and another on the ground.
    grids, grids_gnd = p.prepare_grids_for_plotting(t_grids)

    assert len(grids) == 1
    assert len(grids_gnd) == 1
    assert grids[0].vert_level == 100
    assert grids_gnd[0].vert_level == 0
        

def test_LevelConcentration_update_min_max(cdump2):
    p = helper.LevelConcentration()
    p.initialize(cdump2, None, None)
    p.update_min_max(cdump2.grids)
    
    assert p.min_concs[0] * 1.0e+15 == pytest.approx(1.39594131)
    assert p.min_concs[1] * 1.0e+15 == pytest.approx(0.935228347)
    assert p.max_concs[0] * 1.0e+13 == pytest.approx(8.173024)
    assert p.max_concs[1] * 1.0e+13 == pytest.approx(7.963810)
   
    # check extended properties
    ext = cdump2.grids[0].extension
    assert ext is not None
    assert ext.max_conc * 1.e+13 == pytest.approx(8.047535)
    assert ext.min_conc * 1.e+15 == pytest.approx(1.871257)
    
    ext = cdump2.grids[1].extension
    assert ext.max_conc * 1.e+13 == pytest.approx(7.9638097)
    assert ext.min_conc * 1.e+15 == pytest.approx(0.93631784)
    
    ext = cdump2.grids[3].extension
    assert ext.max_conc * 1.e+13 == pytest.approx(7.6081687)
    assert ext.min_conc * 1.e+15 == pytest.approx(0.93522835)


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
    
    
def test_LevelConcentration_normalize_min_max():
    p = helper.LevelConcentration()
    
    # The min and max values at the last level are not set properly.
    p.min_concs = [1.0, 10.0, 1.0e+15]
    p.max_concs = [5.0, 15.0, 0.0    ]

    p.normalize_min_max()
    
    assert p.min_concs == pytest.approx((1.0, 10.0, 10.0))
    assert p.max_concs == pytest.approx((5.0, 15.0, 15.0))
           
    # None of the min and max values are properly set.
    p.min_concs = [1.0e+25, 1.0e+25, 1.0e+25]
    p.max_concs = [0.0    , 0.0    , 0.0    ]

    p.normalize_min_max()
    
    assert p.min_concs == pytest.approx((0.0, 0.0, 0.0))
    assert p.max_concs == pytest.approx((1.0e+25, 1.0e+25, 1.0e+25))


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


def test_LevelConcentration_undo_scale_exposure():
    p = helper.LevelConcentration()
    
    p.min_concs = [0.4, 0.5, 0.6]
    p.max_concs = [0.6, 0.7, 0.8]
    
    p.scale_exposure(3)
    assert p.min_concs == pytest.approx((3*0.4, 3*0.5, 3*0.6))
    assert p.max_concs == pytest.approx((3*0.6, 3*0.7, 3*0.8))
    
    p.undo_scale_exposure()
    assert p.min_concs == pytest.approx((0.4, 0.5, 0.6))
    assert p.max_concs == pytest.approx((0.6, 0.7, 0.8))
    

def test_LevelConcentration_contour_min_conc():
    p = helper.LevelConcentration()
    p.min_concs = [0.1, 0.2, 0.4]
    assert p.contour_min_conc == 0.4
    
    
def test_LevelConcentration_contour_max_conc():
    p = helper.LevelConcentration()
    p.max_concs = [0.2, 0.4, 0.75]
    assert p.contour_max_conc == 0.75  


def test_LevelConcentration_ground_min_conc():
    p = helper.LevelConcentration()
    p.ground_index = 0
    p.min_concs = [0.1, 0.2, 0.4]
    assert p.ground_min_conc == 0.1
    
    
def test_LevelConcentration_ground_max_conc():
    p = helper.LevelConcentration()
    p.ground_index = 0
    p.max_concs = [0.2, 0.4, 0.75]
    assert p.ground_max_conc == 0.2
    
    
def test_LevelConcentration_get_plot_conc_range():
    p = helper.LevelConcentration()
    p.min_concs = [0.1, 0.2, 0.4]
    p.max_concs = [0.2, 0.4, 0.75]
    
    g = model.ConcentrationGrid(None)
    g.vert_level = 10.0
    g.vert_level_index = 0
    g.extension = helper.GridProperties()
    g.extension.min_conc = 0.13
    g.extension.max_conc = 0.14
    
    assert p.get_plot_conc_range(g, 2.0) == pytest.approx((0.26, 0.28))


def test_LevelConcentration_get_level_range_str():
    p = helper.LevelConcentration()
    level1 = util.LengthInMeters(1.0)
    level2 = util.LengthInMeters(2.0)
    
    assert p.get_level_range_str(level1, level2) == "at level 2 m"
    
    p.set_custom_layer_str("AT LEVEL")
    assert p.get_level_range_str(level1, level2) == "AT LEVEL 2 m"
    p.set_custom_layer_str(None)
    
    p.alt_KAVG = 3
    assert p.get_level_range_str(level1, level2) == "averaged between 1 m and 2 m"
    
    p.set_custom_layer_str("BETWEEN")
    assert p.get_level_range_str(level1, level2) == "BETWEEN 1 m and 2 m"


def test_LevelConcentration_get_upper_level():
    p = helper.LevelConcentration()

    # should return the grid
    grid_level = 100.0
    settings_level = 500.0    
    assert p.get_upper_level(grid_level, settings_level) == pytest.approx(100.0)


def test_LevelConcentration_make_gis_basename():
    o = helper.LevelConcentration()
    assert o.make_gis_basename(2, "ps", 100.0, 5000.0) == "GIS_00100_ps_02"


def test_ConcentrationMapFactory_create_instance():
    p = helper.ConcentrationMapFactory.create_instance(const.ConcentrationMapType.CONCENTRATION, 1)
    assert isinstance(p, helper.ConcentrationMap)
    assert p.KHEMIN == 1
    
    p = helper.ConcentrationMapFactory.create_instance(const.ConcentrationMapType.EXPOSURE, 1)
    assert isinstance(p, helper.ExposureMap)
    assert p.KHEMIN == 1
    
    p = helper.ConcentrationMapFactory.create_instance(const.ConcentrationMapType.DEPOSITION, 1)
    assert isinstance(p, helper.DepositionMap)
    assert p.KHEMIN == 1
    
    p = helper.ConcentrationMapFactory.create_instance(const.ConcentrationMapType.THRESHOLD_LEVELS, 1)
    assert isinstance(p, helper.ThresholdLevelsMap)
    assert p.KHEMIN == 1
    
    p = helper.ConcentrationMapFactory.create_instance(const.ConcentrationMapType.VOLCANIC_ERUPTION, 1)
    assert isinstance(p, helper.VolcanicEruptionMap)
    assert p.KHEMIN == 1
         
    p = helper.ConcentrationMapFactory.create_instance(const.ConcentrationMapType.DEPOSITION_6, 1)
    assert isinstance(p, helper.Deposition6Map)
    assert p.KHEMIN == 1
    
    p = helper.ConcentrationMapFactory.create_instance(const.ConcentrationMapType.MASS_LOADING, 1)
    assert isinstance(p, helper.MassLoadingMap)
    assert p.KHEMIN == 1
        
    p = helper.ConcentrationMapFactory.create_instance(const.ConcentrationMapType.TIME_OF_ARRIVAL, 1)
    assert isinstance(p, helper.TimeOfArrivalMap)
    assert p.KHEMIN == 1
    
    p = helper.ConcentrationMapFactory.create_instance(99999, 1)
    assert isinstance(p, helper.AbstractConcentrationMap)
    assert p.KHEMIN == 1
    

def test_DepositionMapFactory_create_instance():
    p = helper.DepositionMapFactory.create_instance(const.ConcentrationMapType.VOLCANIC_ERUPTION, 1)
    assert isinstance(p, helper.Deposition6Map)
    assert p.KHEMIN == 1
    
    p = helper.DepositionMapFactory.create_instance(const.ConcentrationMapType.TIME_OF_ARRIVAL, 1)
    assert isinstance(p, helper.TimeOfArrivalMap)
    assert p.KHEMIN == 1
    
    p = helper.DepositionMapFactory.create_instance(99999, 1)
    assert isinstance(p, helper.DepositionMap)
    assert p.KHEMIN == 1
    
        
def test_AbstractConcentrationMap___init__():
    p = helper.AbstractConcentrationMap(2, 4, "MAP ID")
    assert p.KMAP == 2
    assert p.KHEMIN == 4
    assert p.map_id == "MAP ID"
    
    
def test_AbstractConcentrationMap_has_banner():
    p = helper.AbstractConcentrationMap(2, 4)
    assert p.has_banner() == False


def test_AbstractConcentrationMap_guess_mass_unit():
    p = helper.AbstractConcentrationMap(2, 4)
    assert p.guess_mass_unit("mass") == "mass"
    

def test_AbstractConcentrationMap_guess_volume_unit():
    p = helper.AbstractConcentrationMap(2, 4)
    assert p.guess_volume_unit("mass") == ""
 
   
def test_AbstractConcentrationMap_format_conc():
    p = helper.AbstractConcentrationMap(2, 4)
    assert p.format_conc(None) == " "
    assert p.format_conc(False) == " "
    assert p.format_conc('abc') == " "
    # integer
    assert p.format_conc(int(2)) == "2"
    # floating-point number
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
    # test with numpy data types.
    assert p.format_conc(numpy.float64(2.56789)) == "2"
    #assert p.format_conc(numpy.float32(2.56789)) == "2"


def test_AbstractConcentrationMap_draw_explanation_text():
    p = helper.AbstractConcentrationMap(2, 4)
    assert p.draw_explanation_text(None, 0, 1.25, None, None, None) == 1.25
   

def test_AbstractConcentrationMap_set_map_id():
    p = helper.AbstractConcentrationMap(2, 4)
    p.set_map_id("Conc")
    assert p.map_id == "Conc"
   

def test_AbstractConcentrationMap_scale_exposure():
    p = helper.AbstractConcentrationMap(2, 4)
    conc_type = helper.LevelConcentration()
    TFACT = 2.5;
    
    assert p.scale_exposure(TFACT, conc_type, 2.0) == pytest.approx(2.5)
  

def test_AbstractConcentrationMap_undo_scale_exposure():
    p = helper.AbstractConcentrationMap(2, 4)
    conc_type = helper.LevelConcentration()

    try:    
        p.undo_scale_exposure(conc_type)
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
  

def test_AbstractConcentrationMap_need_time_scaling():
    p = helper.AbstractConcentrationMap(2, 4)
    assert p.need_time_scaling() == False
  

def test_AbstractConcentrationMap_scale_time():
    p = helper.AbstractConcentrationMap(2, 4)
    conc_type = helper.LevelConcentration()
    TFACT = 2.5;

    assert p.scale_time(TFACT, conc_type, 2.0, False) == pytest.approx(2.5)


def test_ConcentrationMap___init__():
    p = helper.ConcentrationMap(4)
    assert p.KMAP == 1
    assert p.KHEMIN == 4
    assert p.map_id == "Concentration"
    

def test_ConcentrationMap_guess_volume_unit():
    p = helper.ConcentrationMap(4)
    assert p.guess_volume_unit("mass") == "/m^3"
    assert p.guess_volume_unit("ppm") == ""
    
        
def test_ConcentrationMap_get_map_id_line():
    p = helper.ConcentrationMap(4)
    conc_type = helper.LevelConcentration()
    conc_unit = "mass/m^3"
    level1 = util.LengthInMeters(1.0)
    level2 = util.LengthInMeters(2.0)
    
    assert p.get_map_id_line(conc_type, conc_unit, level1, level2) == "Concentration ($mass/m^3$) at level 2 m"
    

def test_ExposureMap___init__():
    p = helper.ExposureMap(3)
    assert p.KMAP == 2
    assert p.KHEMIN == 3
    assert p.map_id == "Exposure"
    

def test_ExposureMap_guess_volume_unit():
    p = helper.ExposureMap(4)
    assert p.guess_volume_unit("rem") == ""
    assert p.guess_volume_unit("rem/hr") == ""
    assert p.guess_volume_unit("Sv") == ""
    assert p.guess_volume_unit("Sv/hr") == ""
    assert p.guess_volume_unit("mass") == "\u2013s/m^3"
    
        
def test_ExposureMap_get_map_id_line():
    p = helper.ExposureMap(4)
    conc_type = helper.LevelConcentration()
    conc_unit = "mass/m^3"
    level1 = util.LengthInMeters(1.0)
    level2 = util.LengthInMeters(2.0)
    
    assert p.get_map_id_line(conc_type, conc_unit, level1, level2) == "Exposure ($mass/m^3$) at level 2 m"
  

def test_ExposureMap_need_time_scaling():
    p = helper.ExposureMap(4)
    assert p.need_time_scaling() == True
  

def test_ExposureMap_scale_time(cdump2):
    p = helper.ExposureMap(4)
    conc_type = helper.LevelConcentration()
    ls = helper.VerticalLevelSelector()
    ps = helper.PollutantSelector(0)
    conc_type.initialize(cdump2, ls, ps)
    t_grids = list(filter(lambda g: g.time_index == 0 and g.vert_level in ls and g.pollutant_index in ps, cdump2.grids))
    conc_type.update_min_max(t_grids)
    TFACT = 2.5;

    assert p.scale_time(TFACT, conc_type, 2.0, False) == pytest.approx(2.0 * 2.5)
    assert conc_type.min_concs[0] * 1.0e+15 == pytest.approx(1.871257)
    assert conc_type.max_concs[0] * 1.0e+13 == pytest.approx(8.047535)
    
    assert p.scale_time(TFACT, conc_type, 2.0, True) == pytest.approx(2.0 * 2.5)
    assert conc_type.min_concs[0] * 1.0e+15 == pytest.approx(2.0 * 1.871257)
    assert conc_type.max_concs[0] * 1.0e+13 == pytest.approx(2.0 * 8.047535)


def test_DepositionMap___init__():
    p = helper.DepositionMap(4)
    assert p.KMAP == 3
    assert p.KHEMIN == 4
    assert p.map_id == "Deposition"
    

def test_DepositionMap_guess_volume_unit():
    p = helper.DepositionMap(4)
    assert p.guess_volume_unit("mass") == "/m^2"
    
        
def test_DepositionMap_get_map_id_line():
    p = helper.DepositionMap(4)
    conc_type = helper.LevelConcentration()
    conc_unit = "mass/m^3"
    level1 = util.LengthInMeters(1.0)
    level2 = util.LengthInMeters(2.0)
    
    assert p.get_map_id_line(conc_type, conc_unit, level1, level2) == "Deposition ($mass/m^3$) at ground-level"


def test_ThresholdLevelsMap___init__():
    p = helper.ThresholdLevelsMap(3)
    assert p.KMAP == 4
    assert p.KHEMIN == 3
    assert p.map_id == "Concentration"
    
    
def test_ThresholdLevelsMap_has_banner():
    p = helper.ThresholdLevelsMap(4)
    assert p.has_banner() == True
    
    
def test_ThresholdLevelsMap_get_banner():
    p = helper.ThresholdLevelsMap(4)
    assert p.get_banner() == "Not for Public Dissemination"

    
def test_ThresholdLevelsMap_guess_volume_unit():
    p = helper.ThresholdLevelsMap(4)
    assert p.guess_volume_unit("mass") == "/m^3"
    assert p.guess_volume_unit("ppm") == ""
    
        
def test_ThresholdLevelsMap_get_map_id_line():
    p = helper.ThresholdLevelsMap(4)
    conc_type = helper.LevelConcentration()
    conc_unit = "mass/m^3"
    level1 = util.LengthInMeters(1.0)
    level2 = util.LengthInMeters(2.0)
    
    assert p.get_map_id_line(conc_type, conc_unit, level1, level2) == "Concentration ($mass/m^3$) at level 2 m"


def test_ThresholdLevelsMap_format_conc():
    p = helper.ThresholdLevelsMap(4)
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
    p = helper.ThresholdLevelsMap(4)
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
    p = helper.VolcanicEruptionMap(4)
    assert p.KMAP == 5
    assert p.KHEMIN == 4
    assert p.map_id == "Concentration"
    
    
def test_VolcanicEruptionMap_has_banner():
    p = helper.VolcanicEruptionMap(4)
    assert p.has_banner() == True
    
    
def test_VolcanicEruptionMap_get_banner():
    p = helper.VolcanicEruptionMap(4)
    assert p.get_banner() == "*** Hypothetical eruption ***"

   
def test_VolcanicEruptionMap_guess_volume_unit():
    p = helper.VolcanicEruptionMap(4)
    assert p.guess_volume_unit("mass") == "/m^3"
    
        
def test_VolcanicEruptionMap_get_map_id_line():
    p = helper.VolcanicEruptionMap(4)
    conc_type = helper.LevelConcentration()
    conc_unit = "mass/m^3"
    level1 = util.LengthInMeters(1.0)
    level2 = util.LengthInMeters(2.0)
    
    assert p.get_map_id_line(conc_type, conc_unit, level1, level2) == "Concentration ($mass/m^3$) at level 2 m"
    
    
def test_VolcanicEruptionMap_draw_explanation_text():
    p = helper.VolcanicEruptionMap(4)
    axes = plt.axes()
    
    try:
        y = p.draw_explanation_text(axes, 0, 1.25, 12.0, 14.0, ["AGEL"]) == 1.25
        assert y < 1.25
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))

    plt.close(axes.get_figure())
    

def test_Deposition6Map___init__():
    p = helper.Deposition6Map(4)
    assert p.KMAP == 6
    assert p.KHEMIN == 4
    assert p.map_id == "Deposition"
    

def test_Deposition6Map_guess_volume_unit():
    p = helper.Deposition6Map(4)
    assert p.guess_volume_unit("mass") == "/m^2"
    
        
def test_Deposition6Map_get_map_id_line():
    p = helper.Deposition6Map(4)
    conc_type = helper.LevelConcentration()
    conc_unit = "mass/m^3"
    level1 = util.LengthInMeters(1.0)
    level2 = util.LengthInMeters(2.0)
    
    assert p.get_map_id_line(conc_type, conc_unit, level1, level2) == "Deposition ($mass/m^3$) at ground-level"

   
def test_MassLoadingMap___init__():
    p = helper.MassLoadingMap(4)
    assert p.KMAP == 7
    assert p.KHEMIN == 4
    assert p.map_id == "Mass loading"
  
   
def test_MassLoadingMap_guess_volume_unit():
    p = helper.MassLoadingMap(4)
    assert p.guess_volume_unit("mass") == "/m^2"
    
        
def test_MassLoadingMap_get_map_id_line():
    p = helper.MassLoadingMap(4)
    conc_type = helper.LevelConcentration()
    conc_unit = "mass/m^2"
    level1 = util.LengthInMeters(1.0)
    level2 = util.LengthInMeters(2.0)
    
    assert p.get_map_id_line(conc_type, conc_unit, level1, level2) == "Mass loading ($mass/m^2$) at level 2 m"


def test_MassLoadingMap_scale_exposure(cdump2):
    p = helper.MassLoadingMap(4)
    conc_type = helper.LevelConcentration()
    ls = helper.VerticalLevelSelector()
    ps = helper.PollutantSelector(0)
    conc_type.initialize(cdump2, ls, ps)
    t_grids = list(filter(lambda g: g.time_index == 0 and g.vert_level in ls and g.pollutant_index in ps, cdump2.grids))
    conc_type.update_min_max(t_grids)
    TFACT = 2.5;

    assert p.scale_exposure(TFACT, conc_type, 2.0) == pytest.approx(2.0 * 2.5)
    assert conc_type.min_concs[0] * 1.0e+15 == pytest.approx(2.0 * 1.871257)
    assert conc_type.max_concs[0] * 1.0e+13 == pytest.approx(2.0 * 8.047535)
    

def test_MassLoadingMap_undo_scale_exposure(cdump2):
    p = helper.MassLoadingMap(4)
    conc_type = helper.LevelConcentration()
    ls = helper.VerticalLevelSelector()
    ps = helper.PollutantSelector(0)
    conc_type.initialize(cdump2, ls, ps)
    t_grids = list(filter(lambda g: g.time_index == 0 and g.vert_level in ls and g.pollutant_index in ps, cdump2.grids))
    conc_type.update_min_max(t_grids)
    TFACT = 2.5;
    
    p.scale_exposure(TFACT, conc_type, 2.0)
    assert conc_type.min_concs[0] * 1.0e+15 == pytest.approx(2.0 * 1.871257)
    assert conc_type.max_concs[0] * 1.0e+13 == pytest.approx(2.0 * 8.047535)
    
    p.undo_scale_exposure(conc_type)
    assert conc_type.min_concs[0] * 1.0e+15 == pytest.approx(1.871257)
    assert conc_type.max_concs[0] * 1.0e+13 == pytest.approx(8.047535)


   
def test_TimeOfArrivalMap___init__():
    p = helper.TimeOfArrivalMap(4)
    assert p.KMAP == 8
    assert p.KHEMIN == 4
    assert p.map_id == "Time-Of-Arrival (h)"
  
   
def test_TimeOfArrivalMap_guess_mass_unit():
    p = helper.TimeOfArrivalMap(4)
    assert p.guess_mass_unit("mass") == "hours"
   
   
def test_TimeOfArrivalMap_guess_volume_unit():
    p = helper.TimeOfArrivalMap(4)
    assert p.guess_volume_unit("mass") == ""
    
        
def test_TimeOfArrivalMap_get_map_id_line():
    p = helper.TimeOfArrivalMap(4)
    conc_type = helper.VerticalAverageConcentration()
    conc_unit = "mass/m^2"
    level1 = util.LengthInMeters(1.0)
    level2 = util.LengthInMeters(2.0)
    
    assert p.get_map_id_line(conc_type, conc_unit, level1, level2) == "Time-Of-Arrival (h) averaged between 1 m and 2 m"


def test_TimeOfArrivalMap_scale_exposure(cdump2):
    p = helper.TimeOfArrivalMap(4)
    conc_type = helper.LevelConcentration()
    ls = helper.VerticalLevelSelector()
    ps = helper.PollutantSelector(0)
    conc_type.initialize(cdump2, ls, ps)
    t_grids = list(filter(lambda g: g.time_index == 0 and g.vert_level in ls and g.pollutant_index in ps, cdump2.grids))
    conc_type.update_min_max(t_grids)
    TFACT = 2.5;

    # exposure scaling is not used. just check if calls are ok.   
    assert p.scale_exposure(TFACT, conc_type, 2.0) == pytest.approx(2.0 * 2.5)
    

def test_TimeOfArrivalMap_undo_scale_exposure(cdump2):
    p = helper.TimeOfArrivalMap(4)
    conc_type = helper.LevelConcentration()
    ls = helper.VerticalLevelSelector()
    ps = helper.PollutantSelector(0)
    conc_type.initialize(cdump2, ls, ps)
    t_grids = list(filter(lambda g: g.time_index == 0 and g.vert_level in ls and g.pollutant_index in ps, cdump2.grids))
    conc_type.update_min_max(t_grids)
    TFACT = 2.5;

    # exposure scaling is not used. just check if calls are ok.    
    p.scale_exposure(TFACT, conc_type, 2.0)
    p.undo_scale_exposure(conc_type)


def test_DepositSumFactory_create_instance():
    o = helper.DepositSumFactory.create_instance(const.DepositionType.NONE)
    assert isinstance(o, helper.NullDeposit)
    
    o = helper.DepositSumFactory.create_instance(const.DepositionType.TIME)
    assert isinstance(o, helper.TimeDeposit)
    
    o = helper.DepositSumFactory.create_instance(const.DepositionType.SUM)
    assert isinstance(o, helper.SumDeposit)
    
    o = helper.DepositSumFactory.create_instance(const.DepositionType.TOTAL)
    assert isinstance(o, helper.TotalDeposit)
    
    o = helper.DepositSumFactory.create_instance(const.DepositionType.TOTAL, False)
    assert isinstance(o, helper.NullDeposit)
    
    try:
        o = helper.DepositSumFactory.create_instance(99999)
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "unknown deposition type 99999"
    

def test_NullDeposit___init__():
    o = helper.NullDeposit()
    assert o is not None
    assert o.summation_from_datetime == None
    assert o.gis_filename_maker is not None


def test_NullDeposit_initialize(cdump3):
    o = helper.NullDeposit()
    ts = helper.TimeIndexSelector()
    ps = helper.PollutantSelector()
    
    try:
        o.initialize(cdump3.grids, ts, ps)
        assert o.summation_from_datetime == datetime.datetime(1983, 9, 25, 18, 0, 0, 0, pytz.utc)
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
        

def test_NullDeposit_add(cdump3):
    o = helper.NullDeposit()
    ts = helper.TimeIndexSelector()
    ps = helper.PollutantSelector()
    o.initialize(cdump3.grids, ts, ps)
    
    try:
        o.add( [cdump3.grids[2]] )  # next time index
        assert o.summation_from_datetime == datetime.datetime(1983, 9, 25, 21, 0, 0, 0, pytz.utc)
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
    

def test_NullDeposit_get_grids_to_plot(cdump2):
    o = helper.NullDeposit()
    ts = helper.TimeIndexSelector()
    ps = helper.PollutantSelector()
    o.initialize(cdump2.grids, ts, ps)
    
    a = o.get_grids_to_plot(cdump2.grids)
    assert len(a) == 0


def test_NullDeposit_make_gis_basename():
    o = helper.NullDeposit()
    assert o.make_gis_basename(2, "ps") == None


def test_TimeDeposit___init__():
    o = helper.TimeDeposit()
    assert o is not None
    assert o.gis_filename_maker is not None


def test_TimeDeposit_get_grids_to_plot(cdump2):
    o = helper.TimeDeposit()
    ts = helper.TimeIndexSelector()
    ps = helper.PollutantSelector()
    o.initialize(cdump2.grids, ts, ps)
    
    a = o.get_grids_to_plot(cdump2.grids)
    assert len(a) == 4


def test_TimeDeposit_make_gis_basename():
    o = helper.TimeDeposit()
    assert o.make_gis_basename(2, "ps") == "GIS_DEP_ps_02"


def test_SumDeposit___init__():
    o = helper.SumDeposit()
    assert o.gis_filename_maker is not None
    assert o.summation_grid is None


def test_SumDeposit_initialize(cdump3):
    o = helper.SumDeposit()
    ts = helper.TimeIndexSelector(2, 99999)
    ps = helper.PollutantSelector()
    
    o.initialize(cdump3.grids, ts, ps)
    
    assert o.summation_from_datetime == datetime.datetime(1983, 9, 25, 18, 0, 0, 0, pytz.utc)
    
    # the summation grid should have accumulated concentrations from time index 0 to 1.
    assert o.summation_grid.conc[23, 26] * 1.0e+7 == pytest.approx(19.36063 + 5.659043)
    
    # change the time index selector to include index 0.
    ts = helper.TimeIndexSelector()
        
    o.initialize(cdump3.grids, ts, ps)
    
    assert o.summation_grid.conc[23, 26] * 1.0e+7 == 0.0
    

def test_SumDeposit_add(cdump3):
    o = helper.SumDeposit()
    ts = helper.TimeIndexSelector(1, 99999)
    ps = helper.PollutantSelector()
    utc = pytz.utc
    
    # initialize with grids at time index at 0.
    o.initialize(cdump3.grids, ts, ps)
    
    assert o.summation_from_datetime == datetime.datetime(1983, 9, 25, 18, 0, 0, 0, pytz.utc)
    
    # find grids at time index 1.
    t_grids = list(filter(lambda g: g.vert_level == 0 and g.time_index == 1, cdump3.grids))

    o.add(t_grids, True)
    
    # summation_from_datetime should not change.
    assert o.summation_from_datetime == datetime.datetime(1983, 9, 25, 18, 0, 0, 0, pytz.utc)
    
    # the summation grid should have accumulated concentrations from time index 0 to 1.
    assert o.summation_grid.conc[23, 26] * 1.0e+7 == pytest.approx(19.36063 + 5.659043)
    assert o.summation_grid.starting_datetime == datetime.datetime(1983, 9, 25, 21, 0, 0, 0, utc)


def test_SumDeposit_get_grids_to_plot(cdump3):
    o = helper.SumDeposit()
    ts = helper.TimeIndexSelector(1, 99999)
    ps = helper.PollutantSelector()
    
    # initialize with grids at time index at 0.
    o.initialize(cdump3.grids, ts, ps)
    
    # find grids at time index 1.
    t_grids = list(filter(lambda g: g.vert_level == 0 and g.time_index == 1, cdump3.grids))

    grids = o.get_grids_to_plot(t_grids, False)
    
    assert len(grids) == 1
    assert grids[0] is o.summation_grid
    

def test_SumDeposit__update_properties(cdump3):
    o = helper.SumDeposit()
    ts = helper.TimeIndexSelector(1, 99999)
    ps = helper.PollutantSelector()
    utc = pytz.utc
    
    # initialize with grids at time index at 0.
    o.initialize(cdump3.grids, ts, ps)
    
    # check what we know.
    assert o.summation_grid.time_index == 0
    assert o.summation_grid.ending_datetime == datetime.datetime(1983, 9, 25, 21, 0, 0, 0, utc)
    assert o.summation_grid.ending_forecast_hr == 0
    assert o.summation_grid.nonzero_conc_count == 14
    assert o.summation_grid.extension.min_conc is None
    assert o.summation_grid.extension.max_conc is None
    
    # find grids at time index 1.
    t_grids = list(filter(lambda g: g.vert_level == 0 and g.time_index == 1, cdump3.grids))

    o._update_properties(t_grids)
    
    assert o.summation_grid.time_index == 1
    assert o.summation_grid.ending_datetime == datetime.datetime(1983, 9, 26, 0, 0, 0, 0, utc)
    assert o.summation_grid.ending_forecast_hr == 0
    assert o.summation_grid.nonzero_conc_count == 14
    assert o.summation_grid.extension.min_conc * 1.0e+10 == pytest.approx(9.859312)
    assert o.summation_grid.extension.max_conc * 1.0e+06 == pytest.approx(4.231850)
    

def test_SumDeposit_make_gis_basename():
    o = helper.SumDeposit()
    assert o.make_gis_basename(2, "ps") == "GIS_DEP_ps_02"


def test_TotalDeposit___init__():
    o = helper.TotalDeposit()
    assert isinstance(o, helper.TotalDeposit)
    assert o.gis_filename_maker is not None


def test_TotalDeposit_get_grids_to_plot(cdump3):
    o = helper.TotalDeposit()
    ts = helper.TimeIndexSelector(1, 99999)
    ps = helper.PollutantSelector()
    utc = pytz.utc

    # initialize with grids at time index at 0.
    o.initialize(cdump3.grids, ts, ps)
    
    # find grids
    t_grids = list(filter(lambda g: g.vert_level == 0 and g.time_index >= 1, cdump3.grids))
    o.add(t_grids)

    # test with the last_timeQ set to False
    last = [ t_grids[-1] ]
    grids = o.get_grids_to_plot(last, False)

    assert len(grids) == 0

    # test with the last_timeQ set to True
    grids = o.get_grids_to_plot(last, True)
    
    assert len(grids) == 1
    assert o.summation_grid.time_index == 7
    assert o.summation_grid.ending_datetime == datetime.datetime(1983, 9, 26, 18, 0, 0, 0, utc)
    assert o.summation_grid.ending_forecast_hr == 0
    assert o.summation_grid.nonzero_conc_count == 349
    assert o.summation_grid.extension.min_conc * 1.0e+10 == pytest.approx(4.308542)
    assert o.summation_grid.extension.max_conc * 1.0e+06 == pytest.approx(4.231850)


def test_TotalDeposit_make_gis_basename():
    o = helper.TotalDeposit()
    assert o.make_gis_basename(2, "ps") == "GIS_DEP_ps_02"

