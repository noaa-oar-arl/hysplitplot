# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_maplimit.py
#
# Performs unit tests on functions and class methods declared in conc/maplimit.py.
# ---------------------------------------------------------------------------

import numpy
import pytest
from unittest.mock import Mock

from hysplitdata.const import HeightUnit
from hysplitdata.conc import model
from ...hysplitplot import const, util
from ...hysplitplot.conc import helper, maplimit, plot, cntrlvl


@pytest.fixture
def cdump():
   s = plot.ConcentrationPlotSettings()
   d = model.ConcentrationDump()
   r = model.ConcentrationDumpFileReader(d)
   r.read("data/cdump")
   return d

#
# @pytest.fixture
# def scaled_conc_level_generator():
#    KMAP = const.ConcentrationMapType.CONCENTRATION
#    KAVG = const.ConcentrationType.EACH_LEVEL
#    KHEMIN = 0
#    level_generator = cntrlvl.ExponentialDynamicLevelGenerator(0)
#    level_generator.set_global_min_max(1.39594e-15, 8.17302e-12)
#    conc_type = helper.ConcentrationTypeFactory.create_instance(KAVG)
#    length_factory = util.AbstractLengthFactory.create_factory(HeightUnit.METERS)
#    conc_map = helper.ConcentrationMapFactory.create_instance(KMAP, KHEMIN)
#    vert_levels = [0, 100]
#    p = cntrlvl.ScaledConcContourLevelGenerator(level_generator, conc_type, length_factory,
#                                                conc_map=conc_map, vert_levels=vert_levels,
#                                                TFACT=1.0, LEVEL2=99999)
#    return p
#
#
# @pytest.fixture
# def scaled_depo_level_generator():
#    KAVG = const.ConcentrationType.EACH_LEVEL
#    level_generator = cntrlvl.ExponentialDynamicLevelGenerator(0)
#    level_generator.set_global_min_max(1.39594e-15, 8.17302e-12)
#    conc_type = helper.ConcentrationTypeFactory.create_instance(KAVG)
#    length_factory = util.AbstractLengthFactory.create_factory(HeightUnit.METERS)
#    p = cntrlvl.ScaledDepoContourLevelGenerator(level_generator, conc_type, length_factory,
#                                                DEPADJ=1.0)
#    return p


def test_HitmapConcGeneratorConfig__init__():
   level_selector = helper.VerticalLevelSelector()
   pollutant_selector = helper.PollutantSelector()
   time_selector = helper.TimeIndexSelector()
   scaled_conc_level_generator = Mock()
   scaled_depo_level_generator = Mock()
   contour_level_count = 4
   o = maplimit.HitmapConcGeneratorConfig(level_selector,
                                          pollutant_selector,
                                          time_selector,
                                          scaled_conc_level_generator,
                                          scaled_depo_level_generator,
                                          contour_level_count)
   assert o.level_selector is level_selector
   assert o.pollutant_selector is pollutant_selector
   assert o.time_selector is time_selector
   assert o.scaled_conc_level_generator is scaled_conc_level_generator
   assert o.scaled_depo_level_generator is scaled_depo_level_generator
   assert o.contour_level_count == 4


def test_HitmapConcGeneratorFactory_create_instance():
   factory = maplimit.HitmapConcGeneratorFactory()
   config = Mock()

   instance = factory.create_instance(0, config=config)
   assert isinstance(instance, maplimit.LegacyHitmapConcGenerator)
   assert instance.level_selector is config.level_selector
   assert instance.pollutant_selector is config.pollutant_selector
   assert instance.time_selector is config.time_selector

   instance = factory.create_instance(1, config=config)
   assert isinstance(instance, maplimit.MinContourLevelBasedHitmapConcGenerator)
   assert instance.level_selector is config.level_selector
   assert instance.pollutant_selector is config.pollutant_selector
   assert instance.time_selector is config.time_selector
   assert instance.scaled_conc_level_generator is config.scaled_conc_level_generator
   assert instance.scaled_depo_level_generator is config.scaled_depo_level_generator
   assert instance.contour_level_count == config.contour_level_count


def test_AbstractHitmapConcGenerator___init__():
   level_selector = helper.VerticalLevelSelector()
   pollutant_selector = helper.PollutantSelector()
   time_selector = helper.TimeIndexSelector()
   generator = maplimit.LegacyHitmapConcGenerator(level_selector, pollutant_selector, time_selector)
   assert generator.level_selector is level_selector
   assert generator.pollutant_selector is pollutant_selector
   assert generator.time_selector is time_selector


def test_LegacyHitmapConcGenerator___init__():
   level_selector = helper.VerticalLevelSelector()
   pollutant_selector = helper.PollutantSelector()
   time_selector = helper.TimeIndexSelector()
   generator = maplimit.LegacyHitmapConcGenerator(level_selector, pollutant_selector, time_selector)
   assert generator.level_selector is level_selector
   assert generator.pollutant_selector is pollutant_selector
   assert generator.time_selector is time_selector


def test_LegacyHitmapConcGenerator_make_conc(cdump):
   level_selector = helper.VerticalLevelSelector()
   pollutant_selector = helper.PollutantSelector()
   time_selector = helper.TimeIndexSelector()
   generator = maplimit.LegacyHitmapConcGenerator(level_selector, pollutant_selector, time_selector)
   conc = generator.make_conc(cdump.grids)
   mask = numpy.greater(conc, 0.0)
   assert mask.shape == (601, 601,)
   assert mask.sum() == 1112


def test_MinContourLevelBasedHitmapConcGenerator___init__():
   level_selector = helper.VerticalLevelSelector()
   pollutant_selector = helper.PollutantSelector()
   time_selector = helper.TimeIndexSelector()
   scaled_conc_level_generator = Mock()
   scaled_depo_level_generator = Mock()
   contour_level_count = 5
   generator = maplimit.MinContourLevelBasedHitmapConcGenerator(
       level_selector,
       pollutant_selector,
       time_selector,
       scaled_conc_level_generator,
       scaled_depo_level_generator,
       contour_level_count)
   assert generator.level_selector is level_selector
   assert generator.pollutant_selector is pollutant_selector
   assert generator.time_selector is time_selector
   assert generator.scaled_conc_level_generator is scaled_conc_level_generator
   assert generator.scaled_depo_level_generator is scaled_depo_level_generator
   assert generator.contour_level_count == contour_level_count


def test_MinContourLevelBasedHitmapConcGenerator_make_conc():
   p = plot.ConcentrationPlot()
   p.merge_plot_settings(None, ["-idata/cdump"])
   p.read_data_files()
   p._create_scaled_level_generators()
   #
   level_selector = helper.VerticalLevelSelector()
   pollutant_selector = helper.PollutantSelector()
   time_selector = helper.TimeIndexSelector()
   contour_level_count = 4
   generator = maplimit.MinContourLevelBasedHitmapConcGenerator(
       level_selector,
       pollutant_selector,
       time_selector,
       p.scaled_conc_level_generator,
       p.scaled_depo_level_generator,
       contour_level_count)
   #
   levels = p.scaled_conc_level_generator.make_levels(p.cdump.grids[0], contour_level_count)
   assert levels * 1.0e+15 == pytest.approx([1.0, 10.0, 100.0, 1000.0])
   #
   conc = generator.make_conc(p.cdump.grids)
   mask = numpy.greater(conc, 1.0e-15)
   assert mask.shape == (601, 601,)
   assert mask.sum() == 1004
