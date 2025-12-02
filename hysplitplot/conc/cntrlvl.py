# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# cntrlvl.py
#
# Classes for generating contour levels.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
import math
import numpy
import logging

from .. import const, util

logger = logging.getLogger(__name__)


class LabelledContourLevel:

    def __init__(self, level=0.0, label=""):
        self.level = level
        self.label = label

    def __repr__(self):
        return "LabelledContourLevel({0}, {1})".format(self.label, self.level)

    def __lt__(self, x):
        if self.level == x.level:
            return self.label < x.label
        return self.level < x.level


class ContourLevelGeneratorFactory:

    @staticmethod
    def create_instance(generator, cntr_levels, cutoff, user_colorQ,
                        add_near_min_cntr=False, near_min_multiplier=0.8):
        if generator == const.ContourLevelGenerator.EXPONENTIAL_DYNAMIC:
            o = ExponentialDynamicLevelGenerator(cutoff)
        elif generator == const.ContourLevelGenerator.CLG_50:
            o = ExponentialDynamicLevelGenerator(cutoff,
                                                 force_base_10=True)
        elif generator == const.ContourLevelGenerator.CLG_51:
            o = ExponentialDynamicLevelGenerator(cutoff,
                                                 force_base_10=True)
        elif generator == const.ContourLevelGenerator.EXPONENTIAL_FIXED:
            o = ExponentialFixedLevelGenerator(cutoff)
        elif generator == const.ContourLevelGenerator.LINEAR_DYNAMIC:
            o = LinearDynamicLevelGenerator()
        elif generator == const.ContourLevelGenerator.LINEAR_FIXED:
            o = LinearFixedLevelGenerator()
        elif generator == const.ContourLevelGenerator.USER_SPECIFIED:
            o = UserSpecifiedLevelGenerator(cntr_levels)
        elif generator == const.ContourLevelGenerator.CLG_60:
            o = ExponentialDynamicLevelGeneratorVariation2(cutoff,
                                                           force_base_sqrt10=True)
        elif generator == const.ContourLevelGenerator.CLG_61:
            o = ExponentialFixedLevelGeneratorVariation2(cutoff,
                                                         force_base_sqrt10=True)
        else:
            raise Exception("unknown method {0} for contour level "
                            "generation".format(generator))
        if add_near_min_cntr:
            return NearMinLevelDecorator(o, near_min_multiplier)
        return o


class AbstractContourLevelGenerator(ABC):

    def __init__(self, **kwargs):
        self.global_min = None
        self.global_max = None
        return

    def set_global_min_max(self, conc_min, conc_max):
        self.global_min = conc_min
        self.global_max = conc_max

    def get_min_conc(self, frame_min):
        """
        A child class may override this method to return the global min.
        """
        return frame_min

    def get_max_conc(self, frame_max):
        """
        A child class may override this method to return the global max.
        """
        return frame_max

    @abstractmethod
    def make_levels(self, frame_min, frame_max, max_levels):
        pass

    @abstractmethod
    def compute_color_table_offset(self, levels):
        pass


class ExponentialDynamicLevelGenerator(AbstractContourLevelGenerator):
    """
    Contour levels may change from frame to frame.
    """

    def __init__(self, cutoff, **kwargs):
        super(ExponentialDynamicLevelGenerator, self).__init__(**kwargs)
        self.cutoff = cutoff
        self.force_base_10 = kwargs.get("force_base_10", False)

    def _compute_interval(self, min_conc, max_conc):
        cint = 10.0
        cint_inverse = 0.1
        if (not self.force_base_10) and max_conc > 1.0e+8 * min_conc:
            cint = 100.0
            cint_inverse = 0.01
        return cint, cint_inverse

    def make_levels(self, min_conc, max_conc, max_levels):
        logger.debug("EDLG: making %d levels using min %g, max %g",
                     max_levels, min_conc, max_conc)

        cint, cint_inverse = self._compute_interval(min_conc, max_conc)

        if max_conc > 0:
            y = math.log(max_conc) / math.log(cint)
            if y > 0:
                nexp = int(y)
            else:
                nexp = int(y) - 1
        else:
            nexp = 0  # sets the highest contour level to 1.0

        # Use a numpy ndarray to allow the *= operator.
        levels = numpy.empty(max_levels, dtype=float)

        a = math.pow(cint, nexp)
        if a < self.cutoff:
            levels[0] = self.cutoff
            levels.resize(1)
        else:
            levels[0] = a
            # ensure level[0] < max_conc
            if (a > max_conc or math.isclose(a, max_conc)) and max_conc > 0:
                levels[0] *= cint_inverse
            for k in range(1, max_levels):
                a = levels[k - 1] * cint_inverse
                if a >= self.cutoff:
                    levels[k] = a
                else:
                    levels.resize(k)
                    break

        logger.debug("contour levels: %s", levels)

        return numpy.flip(levels)

    def compute_color_table_offset(self, levels):
        if levels[-1] > self.global_max:
            return 0

        if len(levels) > 1:
            cint = levels[-1] / levels[-2]
        else:
            cint, _ = self._compute_interval(self.global_min, self.global_max)

        # Limit looping to 32 which is the number of colors in CLRTBL.CFG
        current = levels[-1]
        for k in range(0, 32):
            offset = k
            if current <= self.global_max < current * cint:
                break
            else:
                current *= cint

        return offset


class ExponentialFixedLevelGenerator(ExponentialDynamicLevelGenerator):
    """
    Contour levels are the same across all frames.
    """

    def __init__(self, cutoff, **kwargs):
        super(ExponentialFixedLevelGenerator, self).__init__(cutoff, **kwargs)

    def get_min_conc(self, frame_min):
        return self.global_min

    def get_max_conc(self, frame_max):
        return self.global_max

    def make_levels(self, min_conc, max_conc, max_levels):
        logger.debug("EFLG: making %d levels using global min %g, max %g",
                     max_levels, self.global_min, self.global_max,)
        return super(ExponentialFixedLevelGenerator, self).make_levels(
               self.global_min, self.global_max, max_levels)

    def compute_color_table_offset(self, levels):
        return 0


class ExponentialDynamicLevelGeneratorVariation2(ExponentialDynamicLevelGenerator):
    """
    This is a variation of the exponential level generator.
    Contour levels may change from frame to frame.
    
    Contour intervals are apart by a factor of sqrt(10) instead of 10
    unless the min and max concentrations differ by a factor of 10^5.
    This results in denser contour levels near the max concentration value.
    """

    def __init__(self, cutoff, **kwargs):
        super(ExponentialDynamicLevelGeneratorVariation2, self).__init__(cutoff, **kwargs)
        self.cutoff = cutoff
        self.force_base_sqrt10 = kwargs.get("force_base_sqrt10", False)

    def _compute_interval(self, min_conc, max_conc):
        cint = math.sqrt(10.0)
        cint_inverse = 1.0 / cint
        if (not self.force_base_sqrt10) and max_conc > 1.0e+5 * min_conc:
            cint = 10.0
            cint_inverse = 0.1
        return cint, cint_inverse

    def make_levels(self, min_conc, max_conc, max_levels):
        logger.debug("EDLGV2: making %d levels using min %g, max %g",
                     max_levels, min_conc, max_conc)
        return super(ExponentialDynamicLevelGeneratorVariation2, self).make_levels(
                        min_conc, max_conc, max_levels)


class ExponentialFixedLevelGeneratorVariation2(ExponentialDynamicLevelGeneratorVariation2):
    """
    This is a variation of the exponential level generator.
    Contour levels are the same from frame to frame.
    
    Contour intervals are apart by a factor of sqrt(10) instead of 10
    unless the min and max concentrations differ by a factor of 10^5.
    This results in denser contour levels near the max concentration value.
    """

    def __init__(self, cutoff, **kwargs):
        super(ExponentialFixedLevelGeneratorVariation2, self).__init__(cutoff, **kwargs)

    def get_min_conc(self, frame_min):
        return self.global_min

    def get_max_conc(self, frame_max):
        return self.global_max

    def make_levels(self, min_conc, max_conc, max_levels):
        logger.debug("EFLGV2: making %d levels using global min %g, max %g",
                     max_levels, self.global_min, self.global_max)
        return super(ExponentialFixedLevelGeneratorVariation2, self).make_levels(
               self.global_min, self.global_max, max_levels)

    def compute_color_table_offset(self, levels):
        return 0


class LinearDynamicLevelGenerator(AbstractContourLevelGenerator):

    def __init__(self):
        super(LinearDynamicLevelGenerator, self).__init__()

    def _compute_interval(self, min_conc, max_conc):
        if max_conc > 0:
            nexp = util.nearest_int(math.log10(max_conc * 0.25))
            if nexp < 0:
                nexp -= 1
        else:
            nexp = 0
        cint = math.pow(10.0, nexp)
        if max_conc > 6 * cint:
            cint *= 2.0
        return cint, 1.0 / cint

    def make_levels(self, min_conc, max_conc, max_levels):
        logger.debug("LDLG: making %d levels using min %g, max %g",
                     max_levels, min_conc, max_conc)
        cint, _ = self._compute_interval(min_conc, max_conc)

        levels = numpy.empty(max_levels, dtype=float)
        for k in range(len(levels)):
            levels[k] = cint * (k + 1)

        logger.debug("contour levels: %s", levels)
        return levels

    def compute_color_table_offset(self, levels):
        if levels[-1] > self.global_max:
            return 0

        if len(levels) > 1:
            cint = levels[1] - levels[0]
        else:
            cint, _ = self._compute_interval(self.global_min, self.global_max)

        # Limit looping to 32 which is the number of colors in CLRTBL.CFG
        current = levels[-1]
        for k in range(0, 32):
            offset = k
            if current <= self.global_max < current + cint:
                break
            else:
                current += cint

        return offset


class LinearFixedLevelGenerator(LinearDynamicLevelGenerator):

    def __init__(self):
        super(LinearFixedLevelGenerator, self).__init__()

    def get_min_conc(self, frame_min):
        return self.global_min

    def get_max_conc(self, frame_max):
        return self.global_max

    def make_levels(self, min_conc, max_conc, max_levels):
        logger.debug("LFLG: making %d levels using global min %g, max %g",
                     max_levels, self.global_min, self.global_max)
        return LinearDynamicLevelGenerator.make_levels(self,
                                                       self.global_min,
                                                       self.global_max,
                                                       max_levels)

    def compute_color_table_offset(self, levels):
        return 0


class UserSpecifiedLevelGenerator(AbstractContourLevelGenerator):

    def __init__(self, user_specified_levels):
        super(UserSpecifiedLevelGenerator, self).__init__()
        if user_specified_levels is None:
            self.contour_levels = []
        else:
            self.contour_levels = [o.level for o in user_specified_levels]

    def make_levels(self, min_conc, max_conc, max_levels):
        logger.debug("USLG: making %d levels using user-specified values",
                     max_levels)
        return self.contour_levels

    def compute_color_table_offset(self, levels):
        return 0


class NearMinLevelDecorator(AbstractContourLevelGenerator):
   """
   A small value is added to pick up all non-zero concentration values.
   """

   def __init__(self, level_generator, min_multiplier=0.8):
      self.level_generator = level_generator
      self.min_multiplier = min_multiplier

   def set_min_multiplier(self, min_multiplier):
      self.min_multiplier = min_multiplier

   def _approx_le(self, a, b, tol=1.0e-5):
      if a <= b:
         return True
      elif a != 0:
         return abs(a - b) <= abs(a * tol)
      return abs(b) <= abs(tol)

   def set_global_min_max(self, cmin, cmax):
      self.level_generator.set_global_min_max(cmin, cmax)

   def make_levels(self, min_conc, max_conc, max_levels):
      logger.debug("NMLD: making %d levels using min %g, max %g or global min %g, max %g",
                   max_levels, min_conc, max_conc,
                   self.level_generator.global_min,
                   self.level_generator.global_max)
      b = self.level_generator.make_levels(min_conc, max_conc, max_levels)
      logger.debug(f'initial contour levels {b}')

      # find a value small enough to draw contour lines for non-zero values.
      actual_min = self.level_generator.get_min_conc(min_conc)
      v = self.min_multiplier * actual_min
      logger.debug(f'mul {self.min_multiplier}, min {actual_min}, near min {v}')
      if v == 0.0:
         v = min_conc
      if hasattr(self.level_generator, 'cutoff'):
         if v < self.level_generator.cutoff:
            v = self.level_generator.cutoff
      logger.debug(f'final near min {v}')

      if self._approx_le(b[0], v):
         logger.debug(f'near min {v} too close to min {b[0]}: ignored')
         return b

      logger.debug(f'adding {v} to contour levels')
      a = numpy.array([v], dtype=float)
      return numpy.append(a, b)

   def compute_color_table_offset(self, levels):
      return self.level_generator.compute_color_table_offset(levels)


class AbstractScaledContourLevelGenerator(ABC):
   """
   """

   def __init__(self, level_generator, **kwarg):
      self.level_generator = level_generator

      self.last_level1 = None
      self.last_level2 = None
      self.last_scaling_factor = None
      self.last_min_conc = None

   @abstractmethod
   def make_levels(self, g, cntr_level_count):
      pass

   def compute_color_table_offset(self, contour_levels):
      return self.level_generator.compute_color_table_offset(contour_levels)


class ScaledConcContourLevelGenerator(AbstractScaledContourLevelGenerator):

   def __init__(self, level_generator, conc_type, length_factory, **kwarg):
      super().__init__(level_generator, **kwarg)
      self.conc_type = conc_type
      self.length_factory = length_factory
      self.conc_map = kwarg['conc_map']
      self.vert_levels = kwarg['vert_levels']
      self.CONADJ = kwarg['CONADJ']
      self.LEVEL2 = kwarg['LEVEL2']

   def make_levels(self, g, contour_level_count, TFACT=1.0):
      LEVEL0 = self.conc_type.get_lower_level(g.vert_level,
                                              self.vert_levels)
      LEVEL2 = self.conc_type.get_upper_level(g.vert_level,
                                              self.LEVEL2)

      self.last_level1 = self.length_factory.create_instance(LEVEL0)
      self.last_level2 = self.length_factory.create_instance(LEVEL2)

      # Scaling should be done prior to determining the min and max
      # concentration values.
      f = float(g.vert_level - LEVEL0)
      self.last_scaling_factor = self.conc_map.scale_exposure(TFACT,
                                                              self.conc_type,
                                                              f)
      logger.debug('TFACT %g, hgt %g, scaling factor %g',
                   TFACT, f, self.last_scaling_factor)

      min_conc, max_conc = self.conc_type.get_plot_conc_range(g,
                                                              self.last_scaling_factor)
      self.last_min_conc = min_conc
      logger.debug('min conc %g, max conc %g', min_conc, max_conc)

      self.level_generator.set_global_min_max(self.conc_type.contour_min_conc,
                                              self.conc_type.contour_max_conc)
      logger.debug('global min conc %g, max conc %g',
                   self.conc_type.contour_min_conc,
                   self.conc_type.contour_max_conc)

      contour_levels = self.level_generator.make_levels(min_conc,
                                                        max_conc,
                                                        contour_level_count)
      logger.debug(f'cntr levels {contour_levels}')

      return contour_levels


class ScaledDepoContourLevelGenerator(AbstractScaledContourLevelGenerator):

   def __init__(self, level_generator, conc_type, length_factory, **kwarg):
      super().__init__(level_generator, **kwarg)
      self.conc_type = conc_type
      self.length_factory = length_factory
      self.DEPADJ = kwarg['DEPADJ']

      self.last_level1 = None
      self.last_level2 = None
      self.last_scaling_factor = None
      self.last_min_conc = None

   def make_levels(self, g, contour_level_count):
      self.level1 = self.length_factory.create_instance(0)
      self.level2 = self.length_factory.create_instance(0)

      self.last_scaling_factor = self.DEPADJ
      min_conc, max_conc = self.conc_type.get_plot_conc_range(
            g, self.last_scaling_factor)
      self.last_min_conc = min_conc

      self.level_generator.set_global_min_max(self.conc_type.ground_min_conc,
                                              self.conc_type.ground_max_conc)

      contour_levels = self.level_generator.make_levels(min_conc,
                                                        max_conc,
                                                        contour_level_count)

      return contour_levels

