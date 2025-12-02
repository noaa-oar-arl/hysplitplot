# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_clrtbl.py
#
# Performs unit tests on functions and class methods declared in conc/clrtbl.py.
# ---------------------------------------------------------------------------

import pytest

from ...hysplitplot import const
from ...hysplitplot.conc import plot, clrtbl


@pytest.fixture
def userColors():
    c = []
    c.append((0.4, 0.4, 0.4))
    c.append((0.5, 0.5, 0.5))
    c.append((0.6, 0.6, 0.6))
    c.append((0.7, 0.7, 0.7))
    return c


# declare concrete classes below to test their corresponding abstract class.


class AbstractColorTableTest(clrtbl.AbstractColorTable):

    def __init__(self, ncolors, color_opacity=100):
        super(AbstractColorTableTest, self).__init__(ncolors, color_opacity)

    @property
    def raw_colors(self):
        pass

    @property
    def colors(self):
        pass


def test_ColorTableFactory():
    p = clrtbl.ColorTableFactory()
    assert len(p.COLOR_TABLE_FILE_NAMES) == 2


def test_ColorTableFactory_create_instance():
    p = plot.ConcentrationPlot()
    s = p.settings

    saved = clrtbl.ColorTableFactory.COLOR_TABLE_FILE_NAMES
    clrtbl.ColorTableFactory.COLOR_TABLE_FILE_NAMES = ["data/CLRTBL.CFG"]

    # DefaultChemicalThresholdColorTable
    s.KMAP = const.ConcentrationMapType.THRESHOLD_LEVELS
    s.KHEMIN = 1
    ct = clrtbl.ColorTableFactory.create_instance(s)
    assert isinstance(ct, clrtbl.DefaultChemicalThresholdColorTable)
    assert ct.scaled_opacity == pytest.approx(1.0)
    # repeat with the color opacity specified
    ct = clrtbl.ColorTableFactory.create_instance(s, 50)
    assert isinstance(ct, clrtbl.DefaultChemicalThresholdColorTable)
    assert ct.scaled_opacity == pytest.approx(0.5)

    # UserColorTable
    s.KMAP = const.ConcentrationMapType.CONCENTRATION
    s.user_color = True
    s.parse_contour_levels("10E+2:USER1:100050200+10E+3:USER2:100070200")
    ct = clrtbl.ColorTableFactory.create_instance(s)
    assert isinstance(ct, clrtbl.UserColorTable)
    assert ct.scaled_opacity == pytest.approx(1.0)
    # repeat with the color opacity specified
    ct = clrtbl.ColorTableFactory.create_instance(s, 50)
    assert isinstance(ct, clrtbl.UserColorTable)
    assert ct.scaled_opacity == pytest.approx(0.5)

    # DefaultColorTable
    s.user_color = False
    ct = clrtbl.ColorTableFactory.create_instance(s)
    assert isinstance(ct, clrtbl.DefaultColorTable)
    assert ct.scaled_opacity == pytest.approx(1.0)
    # repeat with the color opacity specified
    ct = clrtbl.ColorTableFactory.create_instance(s, 50)
    assert isinstance(ct, clrtbl.DefaultColorTable)
    assert ct.scaled_opacity == pytest.approx(0.5)

    # check conversion to grayscale table
    s.color = const.ConcentrationPlotColor.BLACK_AND_WHITE
    ct = clrtbl.ColorTableFactory.create_instance(s)
    assert isinstance(ct, clrtbl.DefaultColorTable)
    for rgb in ct.rgbs:
        r, g, b, a = rgb
        assert r == g and g == b
        assert a == pytest.approx(1.0)

    clrtbl.ColorTableFactory.COLOR_TABLE_FILE_NAMES = saved


def test_ColorTableFactory__get_color_table_filename():
    p = clrtbl.ColorTableFactory()
    assert p._get_color_table_filename() == None

    saved = clrtbl.ColorTableFactory.COLOR_TABLE_FILE_NAMES
    clrtbl.ColorTableFactory.COLOR_TABLE_FILE_NAMES = ["data/CLRTBL.CFG"]
    assert p._get_color_table_filename() == "data/CLRTBL.CFG"
    clrtbl.ColorTableFactory.COLOR_TABLE_FILE_NAMES = saved


def test_AbstractColorTable___init__():
    o = AbstractColorTableTest(4, 50)
    assert hasattr(o, "ncolors")
    assert hasattr(o, "rgbs")
    assert hasattr(o, "offset")
    assert o.ncolors == 4
    assert o.scaled_opacity == pytest.approx(0.5)
    assert o.offset == 0
    assert o.use_offset == False


def test_AbstractColorTable_get_reader():
    o = AbstractColorTableTest(4)
    r = o.get_reader()
    assert isinstance(r, clrtbl.ColorTableReader)
    assert r.color_table is o


def test_AbstractColorTable_set_rgb():
    o = AbstractColorTableTest(2)
    o.rgbs = [(0, 0, 0), (.5, .5, .5)]

    o.set_rgb(0, (.2, .2, .2))
    assert o.rgbs[0] == pytest.approx((0.2, 0.2, 0.2, 1.0))

    # repeat with an alpha value specified
    o.set_rgb(0, (.1, .2, .2, 0.75))
    assert o.rgbs[0] == pytest.approx((0.1, 0.2, 0.2, 0.75))


def test_AbstractColorTable_change_to_grayscale():
    o = AbstractColorTableTest(2)
    o.rgbs = [(0, 0, 0), (.5, .6, .7)]

    o.change_to_grayscale()

    assert o.rgbs[0] == pytest.approx((0.0, 0.0, 0.0, 1.0))
    assert o.rgbs[1] == pytest.approx((0.5815, 0.5815, 0.5815, 1.0))

    # repeat with an alpha value specified
    o.scaled_opacity = 0.50
    o.rgbs = [(0, 0, 0), (.5, .6, .7)]
    o.change_to_grayscale()
    assert o.rgbs[0] == pytest.approx((0.0, 0.0, 0.0, 0.5))
    assert o.rgbs[1] == pytest.approx((0.5815, 0.5815, 0.5815, 0.5))


def test_AbstractColorTable_get_luminance():
    assert AbstractColorTableTest.get_luminance((0.5, 0.6, 0.7)) == pytest.approx(0.5815)
    assert AbstractColorTableTest.get_luminance((0.5, 0.6, 0.7, 0.8)) == pytest.approx(0.5815)


def test_AbstractColorTable_create_plot_colors():
    clrs = AbstractColorTableTest.create_plot_colors([(.5, .5, .5), (1., 1., 1.)])
    assert len(clrs) == 2
    assert clrs[0] == "#808080"
    assert clrs[1] == "#ffffff"

    # include alpha
    clrs = AbstractColorTableTest.create_plot_colors([(.5, .5, .5, 0.0), (1., 1., 1., 0.5)])
    assert len(clrs) == 2
    assert clrs[0] == "#80808000"
    assert clrs[1] == "#ffffff80"


def test_AbstractColorTable_set_offset():
    o = AbstractColorTableTest(4)

    o.enable_offset(True)

    o.set_offset(1)
    assert o.offset == 1

    o.set_offset(2)
    assert o.offset == 2

    o.enable_offset(False)

    o.set_offset(1)
    assert o.offset == 0

    o.set_offset(2)
    assert o.offset == 0


def test_AbstractColorTable_enable_offset():
    o = AbstractColorTableTest(4)

    o.enable_offset()
    assert o.use_offset == True

    o.enable_offset(False)
    assert o.use_offset == False

    o.enable_offset(True)
    assert o.use_offset == True


def test_DefaultColorTable___init__():
    o = clrtbl.DefaultColorTable(3, False)
    assert o.ncolors == 3
    assert o.scaled_opacity == pytest.approx(1.0)
    assert o.skip_std_colors == False
    assert len(o.rgbs) == 32
    assert o.rgbs[3] == pytest.approx((0.0, 1.0, 0.0, 1.0))
    assert hasattr(o, "colors")
    assert hasattr(o, "raw_colors")
    assert o._DefaultColorTable__current_offset == 0

    # repeat with an alpha value
    o = clrtbl.DefaultColorTable(3, False, 50)
    assert o.scaled_opacity == pytest.approx(0.5)


def test_DefaultColorTable_raw_colors():
    o = clrtbl.DefaultColorTable(3, False)
    clrs = o.raw_colors
    assert len(clrs) == 3
    assert clrs[0] == pytest.approx((0.0, 1.0, 0.0, 1.0))
    assert clrs[1] == pytest.approx((0.0, 0.0, 1.0, 1.0))
    assert clrs[2] == pytest.approx((1.0, 1.0, 0.0, 1.0))

    o = clrtbl.DefaultColorTable(3, True)
    clrs = o.raw_colors
    assert len(clrs) == 3
    assert clrs[0] == pytest.approx((1.0, 1.0, 0.0, 1.0))
    assert clrs[1] == pytest.approx((1.0, 0.6, 0.0, 1.0))
    assert clrs[2] == pytest.approx((1.0, 0.0, 0.0, 1.0))

    o.enable_offset(True)
    o.set_offset(1)

    clrs = o.raw_colors
    assert len(clrs) == 3
    assert clrs[0] == pytest.approx((0.8, 1.0, 0.0, 1.0))
    assert clrs[1] == pytest.approx((1.0, 1.0, 0.0, 1.0))
    assert clrs[2] == pytest.approx((1.0, 0.6, 0.0, 1.0))


def test_DefaultColorTable_colors():
    o = clrtbl.DefaultColorTable(3, False)
    clrs = o.colors
    assert len(clrs) == 3
    assert clrs[0] == "#00ff00"
    assert clrs[1] == "#0000ff"
    assert clrs[2] == "#ffff00"

    o = clrtbl.DefaultColorTable(3, True)
    clrs = o.colors
    assert len(clrs) == 3
    assert clrs[0] == "#ffff00"
    assert clrs[1] == "#ff9900"
    assert clrs[2] == "#ff0000"

    o.enable_offset(True)
    o.set_offset(1)

    clrs = o.colors
    assert len(clrs) == 3
    assert clrs[0] == "#ccff00"
    assert clrs[1] == "#ffff00"
    assert clrs[2] == "#ff9900"


def test_DefaultChemicalThresholdColorTable___init__():
    o = clrtbl.DefaultChemicalThresholdColorTable(3, False)
    assert o.ncolors == 3
    assert o.scaled_opacity == pytest.approx(1.0)
    assert o.skip_std_colors == False
    assert len(o.rgbs) == 32
    assert o.rgbs[3] == pytest.approx((1.0, 0.5, 0.0, 1.0))
    assert hasattr(o, "colors")
    assert hasattr(o, "raw_colors")
    assert o._DefaultChemicalThresholdColorTable__current_offset == 0

    # repeat with an alpha value
    o = clrtbl.DefaultChemicalThresholdColorTable(3, False, 50)
    assert o.scaled_opacity == pytest.approx(0.5)


def test_DefaultChemicalThresholdColorTable_raw_colors():
    o = clrtbl.DefaultChemicalThresholdColorTable(3, False)
    clrs = o.raw_colors
    assert len(clrs) == 3
    assert clrs[2] == pytest.approx((1.0, 0.5, 0.0, 1.0))
    assert clrs[1] == pytest.approx((1.0, 1.0, 0.0, 1.0))
    assert clrs[0] == pytest.approx((0.8, 0.8, 0.8, 1.0))

    o.enable_offset(True)
    o.set_offset(1)

    clrs = o.raw_colors
    assert len(clrs) == 3
    assert clrs[2] == pytest.approx((1.0, 0.0, 0.0, 1.0))
    assert clrs[1] == pytest.approx((1.0, 0.5, 0.0, 1.0))
    assert clrs[0] == pytest.approx((1.0, 1.0, 0.0, 1.0))

    o = clrtbl.DefaultChemicalThresholdColorTable(3, True)
    clrs = o.raw_colors
    assert len(clrs) == 3
    assert clrs[2] == pytest.approx((1.0, 1.0, 1.0, 1.0))
    assert clrs[1] == pytest.approx((1.0, 1.0, 1.0, 1.0))
    assert clrs[0] == pytest.approx((1.0, 1.0, 1.0, 1.0))


def test_DefaultChemicalThresholdColorTable_colors():
    o = clrtbl.DefaultChemicalThresholdColorTable(3, False)
    clrs = o.colors
    assert len(clrs) == 3
    assert clrs[2] == "#ff8000"
    assert clrs[1] == "#ffff00"
    assert clrs[0] == "#cccccc"

    o.enable_offset(True)
    o.set_offset(1)

    clrs = o.colors
    assert len(clrs) == 3
    assert clrs[2] == "#ff0000"
    assert clrs[1] == "#ff8000"
    assert clrs[0] == "#ffff00"

    o = clrtbl.DefaultChemicalThresholdColorTable(3, True)
    clrs = o.colors
    assert len(clrs) == 3
    assert clrs[2] == "#ffffff"
    assert clrs[1] == "#ffffff"
    assert clrs[0] == "#ffffff"


def test_UserColorTable___init__(userColors):
    o = clrtbl.UserColorTable(userColors)
    assert o.scaled_opacity == pytest.approx(1.0)
    assert len(o.rgbs) == 4
    assert o.rgbs[0] == pytest.approx((0.4, 0.4, 0.4, 1.0))

    # repeat with an alpha value.
    o = clrtbl.UserColorTable(userColors, 50)
    assert o.scaled_opacity == pytest.approx(0.5)


def test_UserColorTable_raw_colors(userColors):
    o = clrtbl.UserColorTable(userColors)
    clrs = o.raw_colors
    assert len(clrs) == 4


def test_UserColorTable_colors(userColors):
    o = clrtbl.UserColorTable(userColors)
    clrs = o.colors
    assert len(clrs) == 4


def test_ColorTableReader___init__():
    tbl = clrtbl.DefaultColorTable(4, False)
    o = clrtbl.ColorTableReader(tbl)
    assert o.color_table is tbl


def test_ColorTableReader_read():
    tbl = clrtbl.DefaultColorTable(4, False)
    o = clrtbl.ColorTableReader(tbl)
    tbl2 = o.read("data/CLRTBL.CFG")
    assert tbl2 is tbl
    assert tbl2.rgbs[20] == pytest.approx((153.0 / 255.0, 0, 0, 1.0))

    # repeat with an alpha value specified
    tbl = clrtbl.DefaultColorTable(4, False, 50)
    o = clrtbl.ColorTableReader(tbl)
    tbl2 = o.read("data/CLRTBL.CFG")
    assert tbl2 is tbl
    assert tbl2.rgbs[20] == pytest.approx((153.0 / 255.0, 0, 0, 0.5))
