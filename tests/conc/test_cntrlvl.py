# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_cntrlvl.py
#
# Performs unit tests on the source code in conc/cntrlvl.py.
# ---------------------------------------------------------------------------

import pytest
import math

from hysplitdata.const import HeightUnit
from hysplitdata.conc import model
from ...hysplitplot import const, util
from ...hysplitplot.conc import cntrlvl, helper, plot


@pytest.fixture
def cdump():
    s = plot.ConcentrationPlotSettings()
    d = model.ConcentrationDump()
    r = model.ConcentrationDumpFileReader(d)
    r.read("data/cdump")
    return d


@pytest.fixture
def contourLevels():
    c = []
    c.append(cntrlvl.LabelledContourLevel(10.0, "L1"))
    c.append(cntrlvl.LabelledContourLevel(15.0, "L2"))
    c.append(cntrlvl.LabelledContourLevel(20.0, "L3"))
    c.append(cntrlvl.LabelledContourLevel(25.0, "L4"))
    return c

# declare concrete classes below to test their corresponding abstract class.


class AbstractContourLevelGeneratorTest(cntrlvl.AbstractContourLevelGenerator):

    def make_levels(self, min_conc, max_conc, max_levels):
        pass

    def compute_color_table_offset(self, levels):
        return 0


def test_LabelledContourLevel___init__():
    o = cntrlvl.LabelledContourLevel(10.0, "USER1")
    assert o.level == 10.0
    assert o.label == "USER1"

    o = cntrlvl.LabelledContourLevel()
    assert o.level == 0.0
    assert o.label == ""


def test_LabelledContourLevel___repr__():
    o = cntrlvl.LabelledContourLevel(10.0, "USER1")
    assert str(o) == "LabelledContourLevel(USER1, 10.0)"


def test_LabelledContourLevel___lt__():
    o1 = cntrlvl.LabelledContourLevel(10.0, "USER1")
    o2 = cntrlvl.LabelledContourLevel(15.0, "USER1")
    assert o1 < o2

    o3 = cntrlvl.LabelledContourLevel(15.0, "USER2")
    assert o2 < o3


def test_ContourLevelGeneratorFactory_create_instance(contourLevels):
    cntr_levels = None
    cutoff = 3.14e-15
    user_color = None

    o = cntrlvl.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.EXPONENTIAL_DYNAMIC,
                                                          cntr_levels,
                                                          cutoff,
                                                          user_color)
    assert isinstance(o, cntrlvl.ExponentialDynamicLevelGenerator)

    o = cntrlvl.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.EXPONENTIAL_FIXED,
                                                          cntr_levels,
                                                          cutoff,
                                                          user_color)
    assert isinstance(o, cntrlvl.ExponentialFixedLevelGenerator)

    o = cntrlvl.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.CLG_60,
                                                          cntr_levels,
                                                          cutoff,
                                                          user_color)
    assert isinstance(o, cntrlvl.ExponentialDynamicLevelGeneratorVariation2)

    o = cntrlvl.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.CLG_61,
                                                          cntr_levels,
                                                          cutoff,
                                                          user_color)
    assert isinstance(o, cntrlvl.ExponentialFixedLevelGeneratorVariation2)

    o = cntrlvl.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.LINEAR_DYNAMIC,
                                                          cntr_levels,
                                                          cutoff,
                                                          user_color)
    assert isinstance(o, cntrlvl.LinearDynamicLevelGenerator)

    o = cntrlvl.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.LINEAR_FIXED,
                                                          cntr_levels,
                                                          cutoff,
                                                          user_color)
    assert isinstance(o, cntrlvl.LinearFixedLevelGenerator)

    o = cntrlvl.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.USER_SPECIFIED,
                                                          contourLevels,
                                                          cutoff,
                                                          None)
    assert isinstance(o, cntrlvl.UserSpecifiedLevelGenerator)

    try:
        o = cntrlvl.ContourLevelGeneratorFactory.create_instance(100000,
                                                              None,
                                                              cutoff,
                                                              None)
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "unknown method 100000 for contour level generation"

    o = cntrlvl.ContourLevelGeneratorFactory.create_instance(const.ContourLevelGenerator.CLG_60,
                                                          cntr_levels,
                                                          cutoff,
                                                          user_color,
                                                          True, 0.75)
    assert isinstance(o, cntrlvl.NearMinLevelDecorator)
    assert isinstance(o.level_generator, cntrlvl.ExponentialDynamicLevelGeneratorVariation2)
    assert o.min_multiplier == pytest.approx(0.75)


def test_AbstractContourLevelGenerator___init__():
    o = AbstractContourLevelGeneratorTest()
    assert o is not None
    assert hasattr(o, "global_min")
    assert hasattr(o, "global_max")


def test_AbstractContourLevelGenerator_set_global_min_max():
    o = AbstractContourLevelGeneratorTest()
    o.set_global_min_max(0.25, 0.75)
    assert o.global_min == pytest.approx(0.25)
    assert o.global_max == pytest.approx(0.75)


def test_AbstractContourLevelGenerator_get_min_conc():
    o = AbstractContourLevelGeneratorTest()
    o.set_global_min_max(0.25, 0.75)
    assert o.get_min_conc(0.5) == pytest.approx(0.5)


def test_AbstractContourLevelGenerator_get_max_conc():
    o = AbstractContourLevelGeneratorTest()
    o.set_global_min_max(0.25, 0.75)
    assert o.get_max_conc(0.5) == pytest.approx(0.5)


def test_ExponentialDynamicLevelGenerator___init__():
    cutoff = 3.14e-15
    o = cntrlvl.ExponentialDynamicLevelGenerator(cutoff, force_base_10=True)
    assert o is not None
    assert o.cutoff == pytest.approx(3.14e-15)
    assert o.force_base_10 == True


def test_ExponentialDynamicLevelGenerator__compute_interval():
    o = cntrlvl.ExponentialDynamicLevelGenerator(0)

    cint, cint_inverse = o._compute_interval(1.39594e-15, 8.17302e-13)
    assert cint == pytest.approx(10.0)
    assert cint_inverse == pytest.approx(0.1)

    cint, cint_inverse = o._compute_interval(1.39594e-15, 8.17302e-6)
    assert cint == pytest.approx(100.0)
    assert cint_inverse == pytest.approx(0.01)

    o.force_base_10 = True

    cint, cint_inverse = o._compute_interval(1.39594e-15, 8.17302e-6)
    assert cint == pytest.approx(10.0)
    assert cint_inverse == pytest.approx(0.1)


def test_ExponentialDynamicLevelGenerator_make_levels():
    o = cntrlvl.ExponentialDynamicLevelGenerator(3.14e-19)

    # base 10.0

    # when int(log10(max_conc)) < 0
    levels = o.make_levels(1.39594e-15, 8.17302e-13, 4)
    # levels = [1.e-16 1.e-15 1.e-14 1.e-13]
    assert levels * 1.e+16 == pytest.approx((1.0, 10.0, 100.0, 1000.0))
    assert levels[-1] < 8.17302e-13

    # when int(log10(max_conc)) == 0
    levels = o.make_levels(0.0005, 0.5, 4)
    # leves = [0.0001 0.001  0.01   0.1   ]
    assert levels == pytest.approx((0.0001, 0.001, 0.01, 0.1))
    assert levels[-1] < 0.5

    # when int(log10(max_conc)) > 0
    levels = o.make_levels(0.5, 500.0, 4)
    # levels = [  0.1   1.   10.  100. ]
    assert levels == pytest.approx((0.1, 1.0, 10.0, 100.0))
    assert levels[-1] < 500.0

    # base 100.0

    # when int(log10(max_conc)) < 0
    levels = o.make_levels(1.39594e-15, 8.17302e-07, 4)
    assert levels * 1.e+13 == pytest.approx((0.1, 10.0, 1000.0, 100000.0))
    assert levels[-1] < 8.17302e-07

    # when int(log10(max_conc)) == 0
    levels = o.make_levels(0.5e-9, 0.5, 4)
    assert levels * 1.e+8 == pytest.approx((1., 100., 10000., 1000000.))
    assert levels[-1] < 0.5

    # when int(log10(max_conc)) > 0
    levels = o.make_levels(0.5e-6, 500.0, 4)
    assert levels == pytest.approx((0.0001, 0.01, 1.0, 100.0))
    assert levels[-1] < 500.0

    # force base 10

    o.force_base_10 = True

    # when int(log10(max_conc)) < 0
    levels = o.make_levels(1.39594e-15, 8.17302e-7, 4)
    assert levels * 1.e+10 == pytest.approx((1.0, 10.0, 100.0, 1000.0))
    assert levels[-1] < 8.17302e-07

    # when int(log10(max_conc)) == 0
    levels = o.make_levels(0.5e-9, 0.5, 4)
    assert levels == pytest.approx((0.0001, 0.001, 0.01, 0.1))
    assert levels[-1] < 0.5

    # when int(log10(max_conc)) > 0
    levels = o.make_levels(0.5e-6, 500.0, 4)
    assert levels == pytest.approx((0.1, 1.0, 10.0, 100.0))
    assert levels[-1] < 500.0
    #
    # when cmax is zero
    #
    levels = o.make_levels(0, 0, 4)
    assert levels == pytest.approx((0.001, 0.01, 0.1, 1.0))

    # When the cutoff exceeds the min and max values.
    o = cntrlvl.ExponentialDynamicLevelGenerator(1.0)
    levels = o.make_levels(1.0e-16, 1.0e-12, 4)
    assert levels == pytest.approx((1.0))

    # When the cutoff is between the min and max values
    o = cntrlvl.ExponentialDynamicLevelGenerator(1.0e-14)
    levels = o.make_levels(1.0e-16, 1.0e-12, 4)
    assert levels * 1.0e+15 == pytest.approx((10., 100.))
    assert levels[-1] < 1.0e-12


def test_ExponentialDynamicLevelGenerator_compute_color_table_offset():
    o = cntrlvl.ExponentialDynamicLevelGenerator(0)
    o.set_global_min_max(1.39594e-15, 8.17302e-13)
    levels = o.make_levels(1.39594e-15, 8.17302e-13, 4)

    assert o.compute_color_table_offset(levels) == 0

    o.set_global_min_max(1.39594e-15, 8.17302e-12)

    assert o.compute_color_table_offset(levels) == 1

    assert o.compute_color_table_offset([1.0e-13]) == 1


def test_ExponentialFixedLevelGenerator___init__():
    cutoff = 3.14e-15
    o = cntrlvl.ExponentialFixedLevelGenerator(cutoff, force_base_10=True)
    assert o is not None
    assert o.cutoff == pytest.approx(3.14e-15)
    assert o.force_base_10 == True


def test_ExponentialFixedLevelGenerator_get_min_conc():
    o = cntrlvl.ExponentialFixedLevelGenerator(3.14e-19)
    o.set_global_min_max(1.39594e-15, 8.17302e-13)
    assert o.get_min_conc(1.0e-14) * 1.0e+15 == pytest.approx(1.39594)


def test_ExponentialFixedLevelGenerator_get_max_conc():
    o = cntrlvl.ExponentialFixedLevelGenerator(3.14e-19)
    o.set_global_min_max(1.39594e-15, 8.17302e-13)
    assert o.get_max_conc(1.0e-14) * 1.0e+15 == pytest.approx(8.17302e+02)


def test_ExponentialFixedLevelGenerator_make_levels():
    o = cntrlvl.ExponentialFixedLevelGenerator(3.14e-19)
    o.set_global_min_max(1.39594e-15, 8.17302e-13)

    levels = o.make_levels(1.39594e-16, 8.17302e-12, 4)

    # levels should be generated using the global min and max.
    assert levels * 1.e+16 == pytest.approx((1.0, 10.0, 100.0, 1000.0))
    assert levels[-1] < 8.17302e-12

    # when cmax is zero
    o.set_global_min_max(0, 0)
    levels = o.make_levels(1.39594e-16, 8.17302e-12, 4)
    assert levels == pytest.approx((0.001, 0.01, 0.1, 1.0))

    # When the cutoff exceeds the min and max values.
    o = cntrlvl.ExponentialFixedLevelGenerator(1.0)
    o.set_global_min_max(1.0e-16, 1.0e-12)
    levels = o.make_levels(1.0e-16, 1.0e-12, 4)
    assert levels == pytest.approx((1.0))

    # When the cutoff is between the min and max values
    o = cntrlvl.ExponentialFixedLevelGenerator(1.0e-14)
    o.set_global_min_max(1.0e-16, 1.0e-12)
    levels = o.make_levels(1.0e-16, 1.0e-12, 4)
    assert levels * 1.0e+15 == pytest.approx((10., 100.))
    assert levels[-1] < 1.0e-12


def test_ExponentialFixedLevelGenerator_compute_color_table_offset():
    o = cntrlvl.ExponentialFixedLevelGenerator(0)
    o.set_global_min_max(1.39594e-15, 8.17302)
    levels = o.make_levels(1.39594e-15, 8.17302e-13, 4)
    assert o.compute_color_table_offset(levels) == 0


def test_ExponentialDynamicLevelGeneratorVariation2___init__():
    cutoff = 3.14e-15
    o = cntrlvl.ExponentialDynamicLevelGeneratorVariation2(cutoff, force_base_sqrt10=True)
    assert o is not None
    assert o.cutoff == pytest.approx(3.14e-15)
    assert o.force_base_sqrt10 == True


def test_ExponentialDynamicLevelGeneratorVariation2__compute_interval():
    o = cntrlvl.ExponentialDynamicLevelGeneratorVariation2(0)

    cint, cint_inverse = o._compute_interval(1.39594e-15, 8.17302e-13)
    assert cint == pytest.approx(math.sqrt(10.0))
    assert cint_inverse == pytest.approx(1.0 / math.sqrt(10.0))

    cint, cint_inverse = o._compute_interval(1.39594e-15, 8.17302e-6)
    assert cint == pytest.approx(10.0)
    assert cint_inverse == pytest.approx(0.1)

    o.force_base_sqrt10 = True

    cint, cint_inverse = o._compute_interval(1.39594e-15, 8.17302e-6)
    assert cint == pytest.approx(math.sqrt(10.0))
    assert cint_inverse == pytest.approx(1.0 / math.sqrt(10.0))


def test_ExponentialDynamicLevelGeneratorVariation2_make_levels():
    o = cntrlvl.ExponentialDynamicLevelGeneratorVariation2(3.14e-19)

    # base sqrt(10.0)

    # when int(log10(max_conc)) < 0
    levels = o.make_levels(1.39594e-15, 8.17302e-13, 4)
    assert levels * 1.e+16 == pytest.approx((100.0, 316.22776602, 1000.0, 3162.27766))
    assert levels[-1] < 8.17302e-13

    # when int(log10(max_conc)) == 0
    levels = o.make_levels(0.0005, 0.5, 4)
    # leves = [0.0001 0.001  0.01   0.1   ]
    assert levels == pytest.approx((0.01, 0.0316227766, 0.1, 0.316227766))
    assert levels[-1] < 0.5

    # when int(log10(max_conc)) > 0
    levels = o.make_levels(0.5, 500.0, 4)
    assert levels == pytest.approx((10., 31.6227766, 100.0, 316.227766))
    assert levels[-1] < 500.0

    # base 10.0

    # when int(log10(max_conc)) < 0
    levels = o.make_levels(1.39594e-15, 8.17302e-07, 4)
    assert levels * 1.e+10 == pytest.approx((1.0, 10.0, 100.0, 1000.0))
    assert levels[-1] < 8.17302e-07

    # when int(log10(max_conc)) == 0
    levels = o.make_levels(0.5e-9, 0.5, 4)
    assert levels == pytest.approx((0.0001, 0.001, 0.01, 0.1))
    assert levels[-1] < 0.5

    # when int(log10(max_conc)) > 0
    levels = o.make_levels(0.5e-6, 500.0, 4)
    assert levels == pytest.approx((0.1, 1.0, 10.0, 100.0))
    assert levels[-1] < 500.0

    # force base sqrt(10)

    o.force_base_sqrt10 = True

    # when int(log10(max_conc)) < 0
    levels = o.make_levels(1.39594e-15, 8.17302e-7, 4)
    assert levels * 1.e+10 == pytest.approx((100.0, 316.22776602, 1000.0, 3162.27766))
    assert levels[-1] < 8.17302e-7

    # when int(log10(max_conc)) == 0
    levels = o.make_levels(0.5e-9, 0.5, 4)
    assert levels == pytest.approx((0.01, 0.0316227766, 0.1, 0.316227766))
    assert levels[-1] < 0.5

    # when int(log10(max_conc)) > 0
    levels = o.make_levels(0.5e-6, 500.0, 4)
    assert levels == pytest.approx((10.0, 31.622776602, 100.0, 316.22776602))
    assert levels[-1] < 500.0

    # when cmax is zero
    levels = o.make_levels(0, 0, 4)
    assert levels == pytest.approx((0.0316227766, 0.1, 0.31622777, 1.0))

    # When the cutoff exceeds the min and max values.
    o = cntrlvl.ExponentialDynamicLevelGeneratorVariation2(1.0)
    levels = o.make_levels(1.0e-16, 1.0e-12, 4)
    assert levels == pytest.approx((1.0))

    # When the cutoff is between the min and max values
    o = cntrlvl.ExponentialDynamicLevelGeneratorVariation2(2.5e-14)
    levels = o.make_levels(1.0e-16, 1.0e-12, 4)
    assert levels * 1.e+16 == pytest.approx((316.22776602, 1000.0, 3162.2776602))
    assert levels[-1] < 1.0e-12


def test_ExponentialDynamicLevelGeneratorVariation2_compute_color_table_offset():
    o = cntrlvl.ExponentialDynamicLevelGeneratorVariation2(0)
    o.set_global_min_max(1.39594e-15, 8.17302e-13)
    levels = o.make_levels(1.39594e-15, 8.17302e-13, 4)

    # levels = [1.00000000e-14, 3.16227766e-14, 1.00000000e-13, 3.16227766e-13]
    assert o.compute_color_table_offset(levels) == 0

    o.set_global_min_max(1.39594e-15, 8.17302e-12)

    assert o.compute_color_table_offset(levels) == 2

    assert o.compute_color_table_offset([1.0e-13]) == 3


def test_ExponentialFixedLevelGeneratorVariation2___init__():
    cutoff = 3.14e-15
    o = cntrlvl.ExponentialFixedLevelGeneratorVariation2(cutoff)
    assert o is not None
    assert o.cutoff == pytest.approx(3.14e-15)


def test_ExponentialFixedLevelGeneratorVariation2_get_min_conc():
    o = cntrlvl.ExponentialFixedLevelGeneratorVariation2(3.14e-19)
    o.set_global_min_max(1.39594e-15, 8.17302e-13)
    assert o.get_min_conc(1.0e-14) * 1.0e+15 == pytest.approx(1.39594)


def test_ExponentialFixedLevelGeneratorVariation2_get_max_conc():
    o = cntrlvl.ExponentialFixedLevelGeneratorVariation2(3.14e-19)
    o.set_global_min_max(1.39594e-15, 8.17302e-13)
    assert o.get_max_conc(1.0e-14) * 1.0e+15 == pytest.approx(8.17302e+2)


def test_ExponentialFixedLevelGeneratorVariation2_make_levels():
    o = cntrlvl.ExponentialFixedLevelGeneratorVariation2(3.14e-19)

    # levels should be generated using the global min and max.
    # when int(log10(max_conc)) < 0
    o.set_global_min_max(1.39594e-15, 8.17302e-13)
    levels = o.make_levels(1.39594e-16, 8.17302e-12, 4)
    assert levels * 1.e+16 == pytest.approx((100.0, 316.22776602, 1000.0, 3162.27766))
    assert levels[-1] < 8.17302e-13

    # when int(log10(max_conc)) == 0
    o.set_global_min_max(0.0005, 0.5)
    levels = o.make_levels(0.5, 50.0, 4)
    assert levels == pytest.approx((0.01, 0.0316227766, 0.1, 0.316227766))
    assert levels[-1] < 0.5

    # when int(log10(max_conc)) > 0
    o.set_global_min_max(0.5, 500.0)
    levels = o.make_levels(50.0, 5000.0, 4)
    assert levels == pytest.approx((10., 31.6227766, 100.0, 316.227766))
    assert levels[-1] < 500.0

    # when cmax is zero
    o.set_global_min_max(0, 0)
    levels = o.make_levels(1.39594e-16, 8.17302e-12, 4)
    assert levels == pytest.approx((0.0316227766, 0.1, 0.316227766, 1.0))

    # When the cutoff exceeds the min and max values.
    o = cntrlvl.ExponentialFixedLevelGeneratorVariation2(1.0)
    o.set_global_min_max(1.0e-16, 1.0e-12)
    levels = o.make_levels(1.0e-16, 1.0e-12, 4)
    assert levels == pytest.approx((1.0))

    # When the cutoff is between the min and max values
    o = cntrlvl.ExponentialFixedLevelGeneratorVariation2(1.25e-14)
    o.set_global_min_max(1.0e-16, 1.0e-12)
    levels = o.make_levels(1.0e-16, 1.0e-12, 4)
    assert levels * 1.0e+16 == pytest.approx((316.22776602, 1000.0, 3162.2776602))
    assert levels[-1] < 1.0e-12


def test_ExponentialFixedLevelGeneratorVariation2_compute_color_table_offset():
    o = cntrlvl.ExponentialFixedLevelGeneratorVariation2(0)
    o.set_global_min_max(1.39594e-15, 8.17302)
    levels = o.make_levels(1.39594e-15, 8.17302e-13, 4)
    assert o.compute_color_table_offset(levels) == 0


def test_LinearDynamicLevelGenerator___init__():
    o = cntrlvl.LinearDynamicLevelGenerator()
    assert o is not None


def test_LinearDynamicLevelGenerator__compute_interval():
    o = cntrlvl.LinearDynamicLevelGenerator()
    assert o._compute_interval(1.0, 10.0) == pytest.approx((2.0, 0.5))
    assert o._compute_interval(0.0, 0.0) == pytest.approx((1.0, 1.0))


def test_LinearDynamicLevelGenerator_make_levels():
    o = cntrlvl.LinearDynamicLevelGenerator()

    levels = o.make_levels(1.0, 10.0, 4)
    assert levels == pytest.approx((2., 4., 6., 8.))

    # when cmax is zero
    levels = o.make_levels(0.0, 0.0, 4)
    assert levels == pytest.approx((1., 2., 3., 4.))


def test_LinearDynamicLevelGenerator_compute_color_table_offset():
    o = cntrlvl.LinearDynamicLevelGenerator()
    o.set_global_min_max(0, 10.0)
    levels = o.make_levels(1.0, 10.0, 4)

    # levels[-1] = 8.0
    assert o.compute_color_table_offset(levels) == 1

    o.set_global_min_max(0, 9.0)

    assert o.compute_color_table_offset(levels) == 0

    assert o.compute_color_table_offset([4.0]) == 2


def test_LinearFixedLevelGenerator___init__():
    o = cntrlvl.LinearFixedLevelGenerator()
    assert o is not None


def test_LinearFixedLevelGenerator_get_min_conc():
    o = cntrlvl.LinearFixedLevelGenerator()
    o.set_global_min_max(1.0, 10.0)
    assert o.get_min_conc(5.0) == pytest.approx(1.0)


def test_LinearFixedLevelGenerator_get_max_conc():
    o = cntrlvl.LinearFixedLevelGenerator()
    o.set_global_min_max(1.0, 10.0)
    assert o.get_max_conc(5.0) == pytest.approx(10.0)


def test_LinearFixedLevelGenerator_make_levels():
    o = cntrlvl.LinearFixedLevelGenerator()
    o.set_global_min_max(1.0, 10.0)

    levels = o.make_levels(1.0, 50.0, 4)

    # levels should be generated using the global min and max.
    assert levels == pytest.approx((2., 4., 6., 8.))

    # when cmax is zero
    o.set_global_min_max(0.0, 0.0)
    levels = o.make_levels(1.0, 50.0, 4)
    assert levels == pytest.approx((1., 2., 3., 4.))


def test_LinearFixedLevelGenerator_compute_color_table_offset():
    o = cntrlvl.LinearFixedLevelGenerator()
    o.set_global_min_max(0, 10.0)
    levels = o.make_levels(1.0, 10.0, 4)

    assert o.compute_color_table_offset(levels) == 0

    o.set_global_min_max(0, 12.0)

    assert o.compute_color_table_offset(levels) == 0


def test_UserSpecifiedLevelGenerator___init__(contourLevels):
    o = cntrlvl.UserSpecifiedLevelGenerator(contourLevels)
    assert o is not None
    assert len(contourLevels) == 4
    assert len(o.contour_levels) == 4

    o = cntrlvl.UserSpecifiedLevelGenerator(None)
    assert o is not None
    assert len(o.contour_levels) == 0


def test_UserSpecifiedLevelGenerator_make_levels(contourLevels):
    o = cntrlvl.UserSpecifiedLevelGenerator(contourLevels)

    levels = o.make_levels(1.0, 10.0, 4)

    assert levels == pytest.approx((10., 15., 20., 25.))


def test_UserSpecifiedLevelGenerator_compute_color_table_offset(contourLevels):
    o = cntrlvl.UserSpecifiedLevelGenerator(contourLevels)

    levels = o.make_levels(1.0, 10.0, 4)

    assert levels == pytest.approx((10., 15., 20., 25.))

    o.set_global_min_max(0, 100.0)
    assert o.compute_color_table_offset(levels) == 0


def test_NearMinLevelDecorator___init__():
    p = cntrlvl.ExponentialDynamicLevelGeneratorVariation2(3.14e-19)
    o = cntrlvl.NearMinLevelDecorator(p)
    assert o.level_generator is not None
    assert o.min_multiplier == pytest.approx(0.8)


def test_NearMinLevelDecorator_set_min_multiplier():
    p = cntrlvl.ExponentialDynamicLevelGeneratorVariation2(3.14e-19)
    o = cntrlvl.NearMinLevelDecorator(p)
    o.set_min_multiplier(0.75)
    assert o.min_multiplier == pytest.approx(0.75)


def test_NearMinLevelDecorator__approx_le():
    p = cntrlvl.ExponentialDynamicLevelGeneratorVariation2(3.14e-19)
    o = cntrlvl.NearMinLevelDecorator(p)
    assert o._approx_le(0., 0.) is True
    assert o._approx_le(0., 10.) is True
    assert o._approx_le(10., 0.) is False
    #
    assert o._approx_le(0., -1.0e-6) is True
    assert o._approx_le(1.0, 0.70, 0.2) is False
    assert o._approx_le(1.0, 0.70, 0.5) is True


def test_NearMinLevelDecorator_set_global_min_max():
    p = cntrlvl.ExponentialDynamicLevelGeneratorVariation2(3.14e-19)
    o = cntrlvl.NearMinLevelDecorator(p)
    o.set_global_min_max(2.0, 8.0)
    assert o.level_generator.global_min == pytest.approx(2.0)
    assert o.level_generator.global_max == pytest.approx(8.0)


def test_NearMinLevelDecorator_make_levels():
    o = cntrlvl.NearMinLevelDecorator(cntrlvl.ExponentialDynamicLevelGeneratorVariation2(3.14e-19))

    # base sqrt(10.0)

    levels = o.make_levels(1.39594e-15, 8.17302e-13, 4)
    assert levels * 1.e+16 == pytest.approx((11.16752, 100.0, 316.22776602, 1000.0, 3162.2776602))

    # base 10.0

    levels = o.make_levels(1.39594e-15, 8.17302e-07, 4)
    assert levels * 1.e+13 == pytest.approx((1.116752e-02, 1000.0, 10000.0, 100000.0, 1000000.0))

    # force base sqrt(10)

    o.level_generator.force_base_sqrt10 = True
    levels = o.make_levels(1.39594e-15, 8.17302e-7, 4)
    assert levels * 1.e+10 == pytest.approx((1.116752e-05, 100.0, 316.22776602, 1000.0, 3162.2776602))

    # when cmax is zero
    levels = o.make_levels(0, 0, 4)
    assert levels == pytest.approx((3.14e-19, 0.031622777, 0.1, 0.31622777, 1.0))

    # When the cutoff exceeds the min and max values.
    o = cntrlvl.NearMinLevelDecorator(cntrlvl.ExponentialDynamicLevelGeneratorVariation2(1.0))
    levels = o.make_levels(1.0e-16, 1.0e-12, 4)
    assert levels == pytest.approx((1.0))

    # When the cutoff is between the min and max values
    o = cntrlvl.NearMinLevelDecorator(cntrlvl.ExponentialDynamicLevelGeneratorVariation2(5.0e-14))
    levels = o.make_levels(1.0e-16, 1.0e-12, 4)
    assert levels * 1.e+16 == pytest.approx((500.0, 1000.0, 3162.2776602))


def test_NearMinLevelDecorator_compute_color_table_offset():
    o = cntrlvl.NearMinLevelDecorator(cntrlvl.LinearDynamicLevelGenerator())
    o.level_generator.set_global_min_max(0, 10.0)
    levels = o.make_levels(1.0, 10.0, 4)

    # levels[-1] = 8.0
    assert o.compute_color_table_offset(levels) == 1


def test_AbstractScaledContourLevelGenerator___init__():
    KMAP = const.ConcentrationMapType.CONCENTRATION
    KAVG = const.ConcentrationType.EACH_LEVEL
    KHEMIN = 0
    level_generator = cntrlvl.ExponentialDynamicLevelGenerator(3.14e-15, force_base_10=True)
    conc_type = helper.ConcentrationTypeFactory.create_instance(KAVG)
    length_factory = util.AbstractLengthFactory.create_factory(HeightUnit.METERS)
    conc_map = helper.ConcentrationMapFactory.create_instance(KMAP, KHEMIN)
    vert_levels = [0, 100]
    p = cntrlvl.ScaledConcContourLevelGenerator(level_generator, conc_type, length_factory,  # Use a concrete class
                                                conc_map=conc_map, vert_levels=vert_levels,
                                                CONADJ=1.0, LEVEL2=99999)

    assert p.level_generator is level_generator
    assert hasattr(p, 'last_level1')
    assert hasattr(p, 'last_level2')
    assert hasattr(p, 'last_scaling_factor')
    assert hasattr(p, 'last_min_conc')


def test_AbstractScaledContourLevelGenerator_compute_color_table_offset():
    KMAP = const.ConcentrationMapType.CONCENTRATION
    KAVG = const.ConcentrationType.EACH_LEVEL
    KHEMIN = 0
    level_generator = cntrlvl.ExponentialDynamicLevelGenerator(0)
    level_generator.set_global_min_max(1.39594e-15, 8.17302e-12)
    levels = level_generator.make_levels(1.39594e-15, 8.17302e-13, 4)
    conc_type = helper.ConcentrationTypeFactory.create_instance(KAVG)
    length_factory = util.AbstractLengthFactory.create_factory(HeightUnit.METERS)
    conc_map = helper.ConcentrationMapFactory.create_instance(KMAP, KHEMIN)
    vert_levels = [0, 100]
    p = cntrlvl.ScaledConcContourLevelGenerator(level_generator, conc_type, length_factory,  # Use a concrete class
                                                conc_map=conc_map, vert_levels=vert_levels,
                                                CONADJ=1.0, LEVEL2=99999)

    assert p.compute_color_table_offset([1.0e-13]) == 1


def test_ScaledConcContourLevelGenerator___init__():
    KMAP = const.ConcentrationMapType.CONCENTRATION
    KAVG = const.ConcentrationType.EACH_LEVEL
    KHEMIN = 0
    level_generator = cntrlvl.ExponentialDynamicLevelGenerator(0)
    level_generator.set_global_min_max(1.39594e-15, 8.17302e-12)
    levels = level_generator.make_levels(1.39594e-15, 8.17302e-13, 4)
    conc_type = helper.ConcentrationTypeFactory.create_instance(KAVG)
    length_factory = util.AbstractLengthFactory.create_factory(HeightUnit.METERS)
    conc_map = helper.ConcentrationMapFactory.create_instance(KMAP, KHEMIN)
    vert_levels = [0, 100]
    p = cntrlvl.ScaledConcContourLevelGenerator(level_generator, conc_type, length_factory,  # Use a concrete class
                                                conc_map=conc_map, vert_levels=vert_levels,
                                                CONADJ=1.0, LEVEL2=99999)

    assert p.conc_type is conc_type
    assert p.length_factory is length_factory
    assert p.conc_map is conc_map
    assert p.vert_levels == pytest.approx([0, 100])
    assert p.CONADJ == 1.0
    assert p.LEVEL2 == 99999


def test_ScaledConcContourLevelGenerator_make_levels():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump"])
    p.read_data_files()
    p._create_scaled_level_generators()

    o = p.scaled_conc_level_generator
    levels = o.make_levels(p.cdump.grids[0], 4)
    assert levels == pytest.approx([0, 1.0e-14, 1.0e-13, 1.0e-12])


def test_ScaledDepoContourLevelGenerator___init__():
    KAVG = const.ConcentrationType.EACH_LEVEL
    level_generator = cntrlvl.ExponentialDynamicLevelGenerator(0)
    level_generator.set_global_min_max(1.39594e-15, 8.17302e-12)
    levels = level_generator.make_levels(1.39594e-15, 8.17302e-13, 4)
    conc_type = helper.ConcentrationTypeFactory.create_instance(KAVG)
    length_factory = util.AbstractLengthFactory.create_factory(HeightUnit.METERS)
    p = cntrlvl.ScaledDepoContourLevelGenerator(level_generator, conc_type, length_factory,  # Use a concrete class
                                                DEPADJ=1.0)

    assert p.conc_type is conc_type
    assert p.length_factory is length_factory
    assert p.DEPADJ == 1.0


def test_ScaledDepoContourLevelGenerator_make_levels():
    p = plot.ConcentrationPlot()
    p.merge_plot_settings(None, ["-idata/cdump_deposit"])
    p.read_data_files()
    p._create_scaled_level_generators()

    o = p.scaled_depo_level_generator
    levels = o.make_levels(p.cdump.grids[0], 4)
    assert levels == pytest.approx([1.0e-9, 1.0e-8, 1.0e-7, 1.0e-6])

