# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_plot.py
#
# Performs unit tests on functions and class methods declared in traj/color.py.
# ---------------------------------------------------------------------------

from hysplitplot import const
from hysplitplot.traj import plot
from hysplitplot.traj.color import (
   ColorCycle,
   ColorCycleFactory,
   HeightColorCycle,
   ItemizedColorCycle,
   MonoColorCycle
)


def test_ColorCycle___init__():
    cc = ColorCycle()
    assert cc.max_colors == 18
    assert cc.index == -1

    cc = ColorCycle(28)
    assert cc.max_colors == 18

    cc = ColorCycle(0)
    assert cc.max_colors == 3


def test_ColorCycle_next_color():
    cc = ColorCycle()
    for c in cc._colors:
        assert cc.next_color(0, 0) == c
    assert cc.next_color(0, 0) == "#ff0000"  #"r"


def test_ColorCycle_reset():
    cc = ColorCycle()
    assert cc.next_color(0, 0) == "#ff0000"  #"r"
    cc.reset()
    assert cc.index == -1
    assert cc.next_color(0, 0) == "#ff0000"  #"r"


def test_ItemizedColorCycle___init__():
    try:
        cc = ItemizedColorCycle()
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))


def test_ItemizedColorCycle_next_color():
    cc = ItemizedColorCycle()
    assert cc.next_color(None, "0") == "#330033"
    assert cc.next_color(None, "1") == "#ff0000"  #"r"
    assert cc.next_color(None, "2") == "#0000ff"  #"b"
    assert cc.next_color(None, "7") == "#3399cc"
    
    assert cc.next_color(None, "8") == "#ff9900"
    assert cc.next_color(None, "9") == "#eda4ff"
    
    assert cc.next_color(None, "a") == "#ccff00"
    assert cc.next_color(None, "j") == "#ff0000"  #"r"


def test_MonoColorCycle___init__():
    try:
        cc = MonoColorCycle()
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))


def test_MonoColorCycle_next_color():
    cc = MonoColorCycle()
    assert cc.next_color(None, None) == "#000000"  #"k"
    assert cc.next_color(None, None) == "#000000"  #"k"


def test_HeightColorCycle___init__():
    try:
        cc = HeightColorCycle()
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))


def test_HeightColorCycle_next_color():
    cc = HeightColorCycle()
    assert cc.next_color(0, None) == "#ff0000"  #"r"
    assert cc.next_color(6, None) == "#3399cc"
    assert cc.next_color(cc.max_colors, None) == "#ff0000"  #"r"


def test_ColorCycleFactory_create_instance():
    s = plot.TrajectoryPlotSettings()

    s.color = const.Color.COLOR
    cc = ColorCycleFactory.create_instance(s, 1)
    assert isinstance(cc, ColorCycle)
    assert cc.max_colors == 3

    s.color = const.Color.COLOR
    cc = ColorCycleFactory.create_instance(s, 2)
    assert isinstance(cc, HeightColorCycle)
    assert cc.max_colors == 18

    s.color = const.Color.ITEMIZED
    cc = ColorCycleFactory.create_instance(s, 2)
    assert isinstance(cc, ItemizedColorCycle)

    s.color = const.Color.BLACK_AND_WHITE
    cc = ColorCycleFactory.create_instance(s, 2)
    assert isinstance(cc, MonoColorCycle)
