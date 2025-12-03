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
                contour_level_count,
                depo_sum):
      self.level_selector = level_selector
      self.pollutant_selector = pollutant_selector
      self.time_selector = time_selector
      self.scaled_conc_level_generator = scaled_conc_level_generator
      self.scaled_depo_level_generator = scaled_depo_level_generator
      self.contour_level_count = contour_level_count
      self.depo_sum = depo_sum


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
               config.contour_level_count,
               config.depo_sum)
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
                contour_level_count, depo_sum):
      super().__init__(level_selector, pollutant_selector, time_selector)
      self.scaled_conc_level_generator = scaled_conc_level_generator
      self.scaled_depo_level_generator = scaled_depo_level_generator
      self.contour_level_count = contour_level_count
      self.conc_type = scaled_conc_level_generator.conc_type
      self.conc_map = scaled_conc_level_generator.conc_map
      self.CONADJ = scaled_conc_level_generator.CONADJ
      self.depo_sum = depo_sum

   def make_conc(self, grids):
      conc = None

      if logger.isEnabledFor(logging.DEBUG):
         logger.debug('Examining conc grids')
         for k, g in enumerate(grids):
            logger.debug('grid %d, time idx %d, level %d, pollutant idx %d',
                         k, g.time_index, g.vert_level, g.pollutant_index)

      self.depo_sum.initialize(grids,
                               self.time_selector,
                               self.pollutant_selector)

      for t_index in self.time_selector:
         t_grids = helper.TimeIndexGridFilter(grids,
                                              helper.TimeIndexSelector(t_index, t_index))
         initial_timeQ = (t_index == self.time_selector.first)
         logger.debug('At time index %d, %d conc grid(s)', t_index, len(t_grids.grids))

         grids_above_ground, grids_on_ground = \
               self.conc_type.prepare_grids_for_plotting(t_grids)
         logger.debug("grid counts: above the ground %d, on the ground %d",
                      len(grids_above_ground), len(grids_on_ground))

         self.depo_sum.add(grids_on_ground, initial_timeQ)

         # concentration unit conversion factor
         TFACT = self.CONADJ
         if self.conc_map.need_time_scaling():
             f = abs(grids_above_ground[0].get_duration_in_sec())
             TFACT = self.conc_map.scale_time(TFACT,
                                              self.conc_type,
                                              f,
                                              initial_timeQ)

         for g in grids_above_ground:
            logger.debug('Examining conc grid at time idx %d, level %d', t_index, g.vert_level)
            # Find the concentration threshold using the smallest contour level
            contour_levels = self.scaled_conc_level_generator.make_levels(g,
                                                                          self.contour_level_count,
                                                                          TFACT=TFACT)
            threshold = min(contour_levels) / self.scaled_conc_level_generator.last_scaling_factor

            # Add the concentration values over the threshold.
            mask = numpy.greater(g.conc, threshold)
            if conc is None:
               conc = numpy.zeros_like(g.conc)
            conc[mask] += g.conc[mask]

         grids_on_ground = self.depo_sum.get_grids_to_plot(grids_on_ground,
                                                           t_index == self.time_selector.last)
         for g in grids_on_ground:
            logger.debug('Examining conc grid at time idx %d, level %d', t_index, g.vert_level)
            contour_levels = self.scaled_depo_level_generator.make_levels(g,
                                                                          self.contour_level_count)
            threshold = min(contour_levels) / self.scaled_depo_level_generator.last_scaling_factor

            # Add the concentration values over the threshold.
            mask = numpy.greater(g.conc, threshold)
            if conc is None:
               conc = numpy.zeros_like(g.conc)
            conc[mask] += g.conc[mask]

      return conc
