# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# maplimit.py
#
# Helper classes for determining map limits.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
import numpy
import logging

from .. import const
from . import helper

logger = logging.getLogger(__name__)


class HitmapConcGeneratorConfig:

   def __init__(self,
                level_selector,
                pollutant_selector,
                time_selector,
                scaled_conc_level_generator,
                scaled_depo_level_generator,
                contour_level_count):
      self.level_selector = level_selector
      self.pollutant_selector = pollutant_selector
      self.time_selector = time_selector
      self.scaled_conc_level_generator = scaled_conc_level_generator
      self.scaled_depo_level_generator = scaled_depo_level_generator
      self.contour_level_count = contour_level_count


class HitmapConcGeneratorFactory:

   @staticmethod
   def create_instance(method, config=None):
      if method == const.PlotRangeDetermination.MIN_CONTOUR_LEVEL:
         logger.debug("Plot range will be determined by MIN_CONTOUR_LEVEL")
         return MinContourLevelBasedHitmapConcGenerator(
               config.level_selector,
               config.pollutant_selector,
               config.time_selector,
               config.scaled_conc_level_generator,
               config.scaled_depo_level_generator,
               config.contour_level_count)
      elif method != const.PlotRangeDetermination.NONZERO:
         logger.warn(f"Unknown method for determining plot range: {method}."
                     " Will use the default method.")

      logger.debug("Plot range will be determined by NONZERO")
      return LegacyHitmapConcGenerator(config.level_selector,
                                       config.pollutant_selector,
                                       config.time_selector)


class AbstractHitmapConcGenerator(ABC):

   def __init__(self, level_selector, pollutant_selector, time_selector):
      self.level_selector = level_selector
      self.pollutant_selector = pollutant_selector
      self.time_selector = time_selector

   @abstractmethod
   def make_conc(self, grids):
      pass


class LegacyHitmapConcGenerator(AbstractHitmapConcGenerator):
   """
   For a legacy algorithm that determines the spatial extent of concentration plots
   using non-zero concentration values.
   """

   def __init__(self, level_selector, pollutant_selector, time_selector):
      super().__init__(level_selector, pollutant_selector, time_selector)

   def make_conc(self, grids):
      # summation of all concentration grids of interest
      conc = helper.sum_conc_grids_of_interest(grids,
                                               self.level_selector,
                                               self.pollutant_selector,
                                               self.time_selector)
      return conc


class MinContourLevelBasedHitmapConcGenerator(AbstractHitmapConcGenerator):
   """
   Use the minimum contour level shown on plots to determine the spatial extent
   of concentration plots.
   """

   def __init__(self, level_selector, pollutant_selector, time_selector,
                scaled_conc_level_generator, scaled_depo_level_generator,
                contour_level_count):
      super().__init__(level_selector, pollutant_selector, time_selector)
      self.scaled_conc_level_generator = scaled_conc_level_generator
      self.scaled_depo_level_generator = scaled_depo_level_generator
      self.contour_level_count = contour_level_count

   def make_conc(self, grids):
      conc = None
      fn = lambda g: \
         g.time_index in self.time_selector and \
         g.pollutant_index in self.pollutant_selector and \
         g.vert_level in self.level_selector

      filtered = list(filter(fn, grids))
      for g in filtered:
         if conc is None:
            conc = numpy.zeros_like(g.conc)

         if g.vert_level == 0:
            scaled_level_generator = self.scaled_depo_level_generator
         else:
            scaled_level_generator = self.scaled_conc_level_generator

         # Find the concentration threshold using the smallest contour level
         contour_levels = scaled_level_generator.make_levels(g,
                                                             self.contour_level_count)
         threshold = min(contour_levels) / scaled_level_generator.last_scaling_factor

         # Add the concentration values over the threshold.
         mask = numpy.greater(g.conc, threshold)
         conc[mask] += g.conc[mask]

      return conc
