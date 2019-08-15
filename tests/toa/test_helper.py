import datetime
import numpy
import pytest
import pytz

from hysplitdata.conc import model
from hysplitplot import util
from hysplitplot.conc import helper as chelper
from hysplitplot.toa import helper


class TimeOfArrivalTest(helper.TimeOfArrival):
    
    def __init__(self, parent):
        super(TimeOfArrivalTest, self).__init__(parent)
    
    def get_map_id_line(self):
        return "NONE"


@pytest.fixture
def toa_gen():
    time_selector = chelper.TimeIndexSelector()
    conc_type = chelper.VerticalAverageConcentration()
    o = helper.TimeOfArrivalGenerator(time_selector, conc_type)
    
    cdump = model.ConcentrationDump().get_reader().read("data/rsmc.cdump2")
    
    level_selector = chelper.VerticalLevelSelector()
    pollutant_selector = chelper.PollutantSelector()
    # important to normalize the time index selector
    o.time_selector.normalize(cdump.grids[-1].time_index)
    
    o.conc_type.initialize(cdump, level_selector, pollutant_selector)
    return o, cdump


def test_TimeOfArrivalGenerator___init__():
    time_selector = chelper.TimeIndexSelector()
    conc_type = chelper.VerticalAverageConcentration()
    o = helper.TimeOfArrivalGenerator(time_selector, conc_type)
    assert len(o.hours) == 12
    assert o.hours[0] == 6 and o.hours[-1] == 72
    assert len(o.bitmasks) == len(o.hours)
    assert o.bitmasks[0] == 1 and o.bitmasks[-1] == 2048
    assert hasattr(o, "grid")
    assert hasattr(o, "above_ground_toa_bits")
    assert hasattr(o, "deposition_toa_bits")
    assert o.time_selector is time_selector
    assert o.conc_type is conc_type
    assert o.time_period_count == 0


def test_TimeOfArrivalGenerator__get_bitmasks(toa_gen):
    o, _ = toa_gen
    assert o._get_bitmasks(helper.TimeOfArrival.DAY_0) == [1, 2, 4, 8]
    assert o._get_bitmasks(helper.TimeOfArrival.DAY_1) == [16, 32, 64, 128]
    assert o._get_bitmasks(helper.TimeOfArrival.DAY_2) == [256, 512, 1024, 2048]


def test_TimeOfArrivalGenerator__get_lumped_bitmasks_before(toa_gen):
    o, _ = toa_gen
    assert o._get_lumped_bitmasks_before(helper.TimeOfArrival.DAY_0) == None
    assert o._get_lumped_bitmasks_before(helper.TimeOfArrival.DAY_1) == 0x0f
    assert o._get_lumped_bitmasks_before(helper.TimeOfArrival.DAY_2) == 0xff


def test_TimeOfArrivalGenerator__get_toa_hours_for(toa_gen):
    o, _ = toa_gen
    assert o._get_toa_hours_for(helper.TimeOfArrival.DAY_0) == pytest.approx([ 6, 12, 18, 24])
    assert o._get_toa_hours_for(helper.TimeOfArrival.DAY_1) == pytest.approx([30, 36, 42, 48])
    assert o._get_toa_hours_for(helper.TimeOfArrival.DAY_2) == pytest.approx([54, 60, 66, 72])


def test_TimeOfArrivalGenerator_process_conc_data(toa_gen):
    o, cdump = toa_gen

    o.process_conc_data(cdump)
    
    assert o.grid is not None
    assert o.grid.nonzero_conc_count == 122853
    assert o.above_ground_toa_bits is not None
    assert o.above_ground_toa_bits.shape == (701, 1201)
    assert o.deposition_toa_bits is not None
    assert o.deposition_toa_bits.shape == (701, 1201)
    assert o.time_period_count == 24


def test_TimeOfArrivalGenerator_make_deposition_data(toa_gen):
    o, cdump = toa_gen
    o.process_conc_data(cdump)
    
    colors = ("#111111", "#222222", "#333333", "#444444", "#808080")
    
    t = o.make_deposition_data(helper.TimeOfArrival.DAY_0, colors)
    assert isinstance(t, helper.DepositionTimeOfArrival)
    assert t.grid is not None
    assert t.contour_levels == pytest.approx((40, 60, 80, 100))
    assert t.fill_colors == ("#111111", "#222222", "#333333", "#444444")
    assert t.starting_datetime == datetime.datetime(2019, 7, 16, 11, 0, 0, 0, pytz.utc)
    assert t.ending_datetime   == datetime.datetime(2019, 7, 17, 11, 0, 0, 0, pytz.utc)
    
    t = o.make_deposition_data(helper.TimeOfArrival.DAY_1, colors)
    assert isinstance(t, helper.DepositionTimeOfArrival)
    assert t.grid is not None
    assert t.contour_levels == pytest.approx((40, 60, 80, 100, 120))
    assert t.fill_colors == ("#111111", "#222222", "#333333", "#444444", "#808080")
    assert t.starting_datetime == datetime.datetime(2019, 7, 16, 11, 0, 0, 0, pytz.utc)
    assert t.ending_datetime   == datetime.datetime(2019, 7, 18, 11, 0, 0, 0, pytz.utc)
    
    t = o.make_deposition_data(helper.TimeOfArrival.DAY_2, colors)
    assert isinstance(t, helper.DepositionTimeOfArrival)
    assert t.grid is not None
    assert t.contour_levels == pytest.approx((40, 60, 80, 100, 120))
    assert t.fill_colors == ("#111111", "#222222", "#333333", "#444444", "#808080")
    assert t.starting_datetime == datetime.datetime(2019, 7, 16, 11, 0, 0, 0, pytz.utc)
    assert t.ending_datetime   == datetime.datetime(2019, 7, 19, 11, 0, 0, 0, pytz.utc)

   
def test_TimeOfArrivalGenerator_make_plume_data(toa_gen):
    o, cdump = toa_gen
    o.process_conc_data(cdump)
    
    colors = ("#111111", "#222222", "#333333", "#444444", "#808080")
    
    t = o.make_plume_data(helper.TimeOfArrival.DAY_0, colors)
    assert isinstance(t, helper.PlumeTimeOfArrival)
    assert t.grid is not None
    assert t.contour_levels == pytest.approx((40, 60, 80, 100))
    assert t.fill_colors == ("#111111", "#222222", "#333333", "#444444")
    assert t.starting_datetime == datetime.datetime(2019, 7, 16, 11, 0, 0, 0, pytz.utc)
    assert t.ending_datetime   == datetime.datetime(2019, 7, 17, 11, 0, 0, 0, pytz.utc)
    
    t = o.make_plume_data(helper.TimeOfArrival.DAY_1, colors)
    assert isinstance(t, helper.PlumeTimeOfArrival)
    assert t.grid is not None
    assert t.contour_levels == pytest.approx((40, 60, 80, 100, 120))
    assert t.fill_colors == ("#111111", "#222222", "#333333", "#444444", "#808080")
    assert t.starting_datetime == datetime.datetime(2019, 7, 16, 11, 0, 0, 0, pytz.utc)
    assert t.ending_datetime   == datetime.datetime(2019, 7, 18, 11, 0, 0, 0, pytz.utc)
    
    t = o.make_plume_data(helper.TimeOfArrival.DAY_2, colors)
    assert isinstance(t, helper.PlumeTimeOfArrival)
    assert t.grid is not None
    assert t.contour_levels == pytest.approx((40, 60, 80, 100, 120))
    assert t.fill_colors == ("#111111", "#222222", "#333333", "#444444", "#808080")
    assert t.starting_datetime == datetime.datetime(2019, 7, 16, 11, 0, 0, 0, pytz.utc)
    assert t.ending_datetime   == datetime.datetime(2019, 7, 19, 11, 0, 0, 0, pytz.utc)


def test_TimeOfArrival___init__():
    cdump = model.ConcentrationDump().get_reader().read("data/rsmc.cdump2")
    g = cdump.grids[0]
    o = TimeOfArrivalTest(g)
    assert o.grid is g
    assert hasattr(o, "contour_levels")
    assert hasattr(o, "display_levels")
    assert hasattr(o, "fill_colors")
    assert hasattr(o, "starting_datetime")
    assert hasattr(o, "ending_datetime")


def test_TimeOfArrival_has_data():
    cdump = model.ConcentrationDump().get_reader().read("data/rsmc.cdump2")
    g = cdump.grids[0]
    o = TimeOfArrivalTest(g)
    
    o.grid.nonzero_conc_count = 1
    assert o.has_data() == True

    o.grid.nonzero_conc_count = 0
    assert o.has_data() == False


def test_TimeOfArrival_longitudes():
    cdump = model.ConcentrationDump().get_reader().read("data/rsmc.cdump2")
    g = cdump.grids[0]
    o = TimeOfArrivalTest(g)
    
    assert len(o.longitudes) == 1201


def test_TimeOfArrival_latitudes():
    cdump = model.ConcentrationDump().get_reader().read("data/rsmc.cdump2")
    g = cdump.grids[0]
    o = TimeOfArrivalTest(g)
    
    assert len(o.latitudes) == 701


def test_TimeOfArrival_data():
    cdump = model.ConcentrationDump().get_reader().read("data/rsmc.cdump2")
    g = cdump.grids[0]
    o = TimeOfArrivalTest(g)
    
    assert o.data.shape == (701, 1201)


def test_TimeOfArrival_create_contour():
    cdump = model.ConcentrationDump().get_reader().read("data/rsmc.cdump2")
    g = cdump.grids[0]
    o = TimeOfArrivalTest(g)
    
    # Case for day 0.
    
    toa_bits = numpy.array([[1, 1,12],
                            [3, 4, 8]], dtype=numpy.int32)
    toa_bitmasks = [1, 2, 4, 8]
    toa_hours = numpy.linspace(6, 24, num=4)
    prev_bitmask = None
    fill_colors = ("#111", "#222", "#333", "#444", "#888")
    
    o.create_contour(toa_bits, toa_bitmasks, toa_hours, prev_bitmask, fill_colors)
    
    assert o.contour_levels == [40, 60, 80, 100]
    assert o.display_levels == ["18-24 hours", "12-18 hours", "6-12 hours", "0-6 hours"]
    assert o.grid.conc[0] == pytest.approx( [100, 100,  60] )
    assert o.grid.conc[1] == pytest.approx( [100,  60,  40] )
    assert o.starting_datetime == datetime.datetime(2019, 7, 16, 11, 0, 0, 0, pytz.utc)
    assert o.ending_datetime   == datetime.datetime(2019, 7, 17, 11, 0, 0, 0, pytz.utc)
      
    # Case for day 1.
    
    toa_bits = numpy.array([[24, 16, 192],
                            [48, 64, 128]], dtype=numpy.int32)
    toa_bitmasks = [16, 32, 64, 128]
    toa_hours = numpy.linspace(30, 48, num=4)
    prev_bitmask = 0x0f
    fill_colors = ("#111", "#222", "#333", "#444")
    
    o.create_contour(toa_bits, toa_bitmasks, toa_hours, prev_bitmask, fill_colors)
    
    assert o.contour_levels == [40, 60, 80, 100, 120]
    assert o.display_levels == ["42-48 hours", "36-42 hours", "30-36 hours", "24-30 hours", "0-24 hours"]
    assert o.grid.conc[0] == pytest.approx( [120, 100,  60] )
    assert o.grid.conc[1] == pytest.approx( [100,  60,  40] )
    assert o.starting_datetime == datetime.datetime(2019, 7, 16, 11, 0, 0, 0, pytz.utc)
    assert o.ending_datetime   == datetime.datetime(2019, 7, 18, 11, 0, 0, 0, pytz.utc)
    assert o.fill_colors == ["#111", "#222", "#333", "#444", "#808080"]
    
    
def test_DepositionTimeOfArrival___init__():
    cdump = model.ConcentrationDump().get_reader().read("data/rsmc.cdump2")
    g = cdump.grids[0]
    o = helper.DepositionTimeOfArrival(g)
    
    starting_datetime = datetime.datetime(2019, 7, 16, 11, 0, 0, 0, pytz.utc)
    ending_datetime = datetime.datetime(2019, 7, 18, 11, 0, 0, 0, pytz.utc)
    
    s = o.get_map_id_line(0, 500, starting_datetime, ending_datetime)
    assert s == "Time of arrival (h) at ground-level" \
                "\nIntegrated from 1100 16 Jul to 1100 18 Jul 2019 (UTC)"
    
    
def test_PlumeTimeOfArrival___init__():
    cdump = model.ConcentrationDump().get_reader().read("data/rsmc.cdump2")
    g = cdump.grids[0]
    o = helper.PlumeTimeOfArrival(g)
    
    starting_datetime = datetime.datetime(2019, 7, 16, 11, 0, 0, 0, pytz.utc)
    ending_datetime = datetime.datetime(2019, 7, 18, 11, 0, 0, 0, pytz.utc)
    lower_vert_level = util.LengthInMeters(0)
    upper_vert_level = util.LengthInMeters(500)
    s = o.get_map_id_line(lower_vert_level, upper_vert_level, starting_datetime, ending_datetime)
    assert s == "Time of arrival (h) averaged between 0 m and 500 m" \
                "\nIntegrated from 1100 16 Jul to 1100 18 Jul 2019 (UTC)"










