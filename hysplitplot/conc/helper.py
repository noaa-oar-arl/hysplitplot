# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# helper.py
#
# Helper functions and classes for producing concentration plots and
# time-of-arrival plots.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
import copy
import logging
import numpy
import sys

from hysplitdata.conc import model
from hysplitplot import util, const


logger = logging.getLogger(__name__)


def sum_over_pollutants_per_level(grids, level_selector, pollutant_selector):
    """Returns an array of concentration grids at each vertical level.

    Summation of concentration over pollutants is performed if necessary.
    All concentration grids specified by the grids argument are assumed
    to have the same time index.
    """

    # select grids
    fn = lambda g: \
        g.vert_level in level_selector and \
        g.pollutant_index in pollutant_selector
    grids = list(filter(fn, grids))

    # obtain unique level indices
    level_indices = list(set([g.vert_level_index for g in grids]))
    if len(level_indices) == 0:
        return []

    v_grids = []
    for k in level_indices:
        a = list(filter(lambda g: g.vert_level_index == k, grids))
        if len(a) == 1:
            v_grids.append(a[0])
        elif len(a) > 1:
            # summation over pollutants at the same vertical level
            g = a[0].clone()
            g.repair_pollutant(pollutant_selector.index)
            for b in a[1:]:
                g.conc += b.conc
            if g.extension is not None:
                # update the min and max concentration values
                g.extension.update(g.conc)
            v_grids.append(g)

    return v_grids


def sum_conc_grids_of_interest(grids, level_selector, pollutant_selector,
                               time_selector):
    sum = None
    fn = lambda g: \
        g.time_index in time_selector and \
        g.pollutant_index in pollutant_selector and \
        g.vert_level in level_selector

    filtered = list(filter(fn, grids))
    if len(filtered) > 0:
        sum = numpy.copy(filtered[0].conc)
        for g in filtered[1:]:
            sum += g.conc

    return sum


def find_nonzero_min_max(mat):
    """Find the non-zero minimum value and the maximum value
    of a numpy matrix"""
    vmax = None
    vmin = None

    if mat is not None:
        vmax = mat.max()
        vmin = util.nonzero_min(mat)    # may return None.

    return vmin, vmax


def find_max_locs(g):
    v = numpy.amax(g.conc)
    if v > 0:
        loc = numpy.where(g.conc == v)
        y = [g.latitudes[k] for k in loc[0]]
        x = [g.longitudes[k] for k in loc[1]]
        return list(zip(x, y))
    else:
        return []


class TimeIndexSelector:

    def __init__(self, first_index=0, last_index=9999, step=1):
        self.__min = first_index
        self.__max = last_index
        self.step = step

    def __iter__(self):
        return iter(range(self.first + self.step - 1,
                          self.last + 1,
                          self.step))

    def __contains__(self, time_index):
        if time_index >= self.__min and time_index <= self.__max:
            return True
        return False

    @property
    def first(self):
        return self.__min

    @property
    def last(self):
        return self.__max

    def normalize(self, max_index):
        self.__max = min(self.__max, max_index)
        self.__min = max(0, self.__min)


class PollutantSelector:

    def __init__(self, pollutant_index=-1):
        self.__index = pollutant_index

    def __contains__(self, pollutant_index):
        if self.__index < 0 or self.__index == pollutant_index:
            return True
        return False

    @property
    def index(self):
        return self.__index

    def normalize(self, max_index):
        if self.__index > max_index:
            self.__index = max_index
        if self.__index < -1:
            self.__index = -1


class VerticalLevelSelector:

    def __init__(self, level_min=0, level_max=99999):
        self.__min = level_min  # level in meters
        self.__max = level_max  # level in meters

    def __contains__(self, level):
        if level >= self.__min and level <= self.__max:
            return True
        return False

    @property
    def min(self):
        return self.__min

    @property
    def max(self):
        return self.__max


class AbstractGridFilter:

    def __init__(self):
        self.grids = None

    def __iter__(self):
        return iter(self.grids)

    def __getitem__(self, key):
        return self.grids[key]

    @staticmethod
    def _filter(grids, fn):
        return list(filter(fn, grids))


class TimeIndexGridFilter(AbstractGridFilter):

    def __init__(self, grids, time_index_selector):
        super(TimeIndexGridFilter, self).__init__()
        self.grids = self._filter(grids, time_index_selector)

    @staticmethod
    def _filter(grids, time_index_selector):
        fn = lambda g: g.time_index in time_index_selector
        return AbstractGridFilter._filter(grids, fn)


class VerticalLevelGridFilter(AbstractGridFilter):

    def __init__(self, grids, level_selector):
        super(VerticalLevelGridFilter, self).__init__()
        self.grids = self._filter(grids, level_selector)

    @staticmethod
    def _filter(grids, level_selector):
        fn = lambda g: g.vert_level in level_selector
        return AbstractGridFilter._filter(grids, fn)


class GridProperties:

    def __init__(self):
        self.min_conc = None
        self.max_conc = None
        # average min/max across pollutants and vertical levels of interest
        self.min_vert_avg_conc = None
        self.max_vert_avg_conc = None
        self.max_locs = None  # locations of the max conc.

    def clone(self):
        o = copy.copy(self)  # shallow copy because none of the members are an object.
        return o

    def update(self, conc):
        vmin, self.max_conc = find_nonzero_min_max(conc)
        self.min_conc = vmin if vmin is not None else 0.0
 
    def __repr__(self) -> str:
        return "GridProperties[min {}, max {}, avg min {}, avg max {}," \
               " max locs {}]".format(self.min_conc,
                                     self.max_conc,
                                     self.min_vert_avg_conc,
                                     self.max_vert_avg_conc,
                                     self.max_locs)


class VerticalAverageCalculator:

    def __init__(self, cdump, level_selector):
        self.selected_level_indices = []
        self.delta_z = dict()  # a vertical level index is the key here.
        self.inverse_weight = 1.0

        # prepare weights
        self._prepare_weighted_averaging(cdump, level_selector)

    def _prepare_weighted_averaging(self, cdump, level_selector):
        self.selected_level_indices.clear()

        for k, level in enumerate(cdump.vert_levels):
            if (level > 0) and (level in level_selector):
                self.selected_level_indices.append(k)

        self.delta_z.clear()

        last = 0
        for k in self.selected_level_indices:
            level = cdump.vert_levels[k]
            self.delta_z[k] = level - last
            last = level

        w = 0
        for v in self.delta_z.values():
            w += v

        if w == 0:
            logger.error("No concentration grids found for vertical "
                         "averaging between levels {0} and {1}.".format(
                             level_selector.min, level_selector.max))
            return False

        self.inverse_weight = 1.0 / w
        return True

    def average(self, grids):
        if len(grids) == 0:
            raise ValueError("vertical averaging requires one or "
                             "more concentration grids")

        # vertical average
        avg = numpy.zeros(grids[0].conc.shape)

        for g in grids:
            if g.vert_level_index in self.delta_z:
                avg += g.conc * self.delta_z[g.vert_level_index]

        return (avg * self.inverse_weight)


class AbstractGisOutputFilename(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def get_basename(self, time_index, output_suffix, level1=0, level2=99999):
        pass


class GisOutputFilenameForVerticalAverageConc(AbstractGisOutputFilename):

    def __init__(self):
        super(GisOutputFilenameForVerticalAverageConc, self).__init__()

    def get_basename(self, time_index, output_suffix, level1=0, level2=99999):
        return "GIS_{0:05d}-{1:05d}_{2}_{3:02d}".format(
            int(level1), int(level2), output_suffix, time_index)


class GisOutputFilenameForLevelConc(AbstractGisOutputFilename):

    def __init__(self):
        super(GisOutputFilenameForLevelConc, self).__init__()

    def get_basename(self, time_index, output_suffix, level1=0, level2=99999):
        return "GIS_{0:05d}_{1}_{2:02d}".format(
            int(level1), output_suffix, time_index)


class GisOutputFilenameForDeposit(AbstractGisOutputFilename):

    def __init__(self):
        super(GisOutputFilenameForDeposit, self).__init__()

    def get_basename(self, time_index, output_suffix, level1=0, level2=99999):
        return "GIS_DEP_{0}_{1:02d}".format(output_suffix, time_index)


class KmlOutputFilename(AbstractGisOutputFilename):

    def __init__(self, output_basename="HYSPLIT"):
        super(KmlOutputFilename, self).__init__()
        self.output_basename = output_basename

    def get_basename(self, time_index, output_suffix, level1=0, level2=99999):
        return "{}_{}".format(self.output_basename, output_suffix)


class ConcentrationTypeFactory:

    @staticmethod
    def create_instance(conc_type):
        if conc_type == const.ConcentrationType.EACH_LEVEL:
            return LevelConcentration()
        elif conc_type == const.ConcentrationType.VERTICAL_AVERAGE:
            return VerticalAverageConcentration()

        raise Exception("unknown concentration type {0}".format(conc_type))


class ConcentrationType(ABC):

    def __init__(self):
        self.cdump = None
        self.level_selector = None
        self.pollutant_selector = None
        self.custom_layer_str = None
        self.gis_filename_maker = None
        self.kml_filename_maker = None

    def initialize(self, cdump, level_selector, pollutant_selector):
        self.cdump = cdump
        self.level_selector = level_selector
        self.pollutant_selector = pollutant_selector

    def set_custom_layer_str(self, s):
        self.custom_layer_str = None if s is None else s.strip()

    @abstractmethod
    def prepare_grids_for_plotting(self, t_grids):
        pass

    @abstractmethod
    def update_min_max(self, t_grids):
        pass

    @abstractmethod
    def scale_conc(self, CONADJ, DEPADJ):
        pass

    @abstractmethod
    def scale_exposure(self, factor):
        pass

    @abstractmethod
    def undo_scale_exposure(self):
        pass

    @abstractmethod
    def normalize_min_max(self):
        pass

    @property
    @abstractmethod
    def contour_min_conc(self):
        pass

    @property
    @abstractmethod
    def contour_max_conc(self):
        pass

    @abstractmethod
    def get_plot_conc_range(self, grid, scaling_factor):
        pass

    @abstractmethod
    def get_level_range_str(self, level1, level2):
        pass

    @abstractmethod
    def get_upper_level(self, grid_level, settings_level):
        pass

    def get_lower_level(self, current_level, levels):
        sorted_levels = sorted(levels)

        k = sorted_levels.index(current_level)
        if k > 0:
            return sorted_levels[k - 1]
        else:
            return 0.0

    def make_gis_basename(self, time_index, output_suffix, level1, level2):
        return self.gis_filename_maker.get_basename(time_index, output_suffix,
                                                    level1, level2)

    def make_kml_basename(self, time_index, output_suffix, level1, level2):
        return self.kml_filename_maker.get_basename(time_index, output_suffix)


class VerticalAverageConcentration(ConcentrationType):

    def __init__(self):
        super(VerticalAverageConcentration, self).__init__()
        self.average_calc = None
        self.min_average = 1.0e+25
        self.max_average = 0.0
        self.__min_average_stashed = self.min_average
        self.__max_average_stashed = self.max_average
        self.gis_filename_maker = GisOutputFilenameForVerticalAverageConc()
        self.kml_filename_maker = KmlOutputFilename()

    def initialize(self, cdump, level_selector, pollutant_selector):
        super(VerticalAverageConcentration, self).initialize(
            cdump,
            level_selector,
            pollutant_selector)
        self.average_calc = VerticalAverageCalculator(cdump, level_selector)

    def prepare_grids_for_plotting(self, t_grids):
        if self.level_selector is None or self.pollutant_selector is None:
            raise ValueError("level_selector or pollutant_selector is "
                             "not set: did you call initialize()?")

        v_grids = sum_over_pollutants_per_level(t_grids,
                                                self.level_selector,
                                                self.pollutant_selector)
        v_avg = self.average_calc.average(v_grids)

        g = v_grids[0].clone_except_conc()
        g.conc = v_avg
        g.nonzero_conc_count = numpy.count_nonzero(g.conc)
        g.vert_level_index = -1

        # grids on the ground
        if 0 in self.level_selector:
            gnd_grids = list(filter(lambda g: g.vert_level == 0, v_grids))
        else:
            ground_level_selector = VerticalLevelSelector(0, 0)
            gnd_grids = sum_over_pollutants_per_level(t_grids,
                                                      ground_level_selector,
                                                      self.pollutant_selector)

        return [g], gnd_grids

    def update_min_max(self, t_grids):
        v_grids = sum_over_pollutants_per_level(t_grids,
                                                self.level_selector,
                                                self.pollutant_selector)
        logger.debug("VERT GRIDS %s", v_grids)

        v_avg = self.average_calc.average(v_grids)
        logger.debug("VERT AVG %s", v_avg)

        vmin, vmax = find_nonzero_min_max(v_avg)
        self.update_average_min_max(vmin, vmax)

        # set extended grid properties
        for g in t_grids:
            g.extension = GridProperties()
            g.extension.min_vert_avg_conc = vmin if vmin is not None else 0.0
            g.extension.max_vert_avg_conc = vmax

    def update_average_min_max(self, vmin, vmax):
        if vmin is not None:
            self.min_average = min(self.min_average, vmin)

        if vmax is not None:
            self.max_average = max(self.max_average, vmax)

        logger.debug("average min %g, max %g",
                     self.min_average, self.max_average)

    def normalize_min_max(self):
        if self.min_average > self.max_average:
            # This happens if all concentration values are zero.
            self.min_average, self.max_average = \
                self.max_average, self.min_average

    def scale_conc(self, CONADJ, DEPADJ):
        self.min_average *= CONADJ
        self.max_average *= CONADJ

    def scale_exposure(self, factor):
        self.__min_average_stashed = self.min_average
        self.__max_average_stashed = self.max_average
        self.min_average *= factor
        self.max_average *= factor
        logger.debug("exposure scaling factor %g, min avg %g, max avg %g",
                     factor, self.min_average, self.max_average)

    def undo_scale_exposure(self):
        self.min_average = self.__min_average_stashed
        self.max_average = self.__max_average_stashed

    @property
    def contour_min_conc(self):
        return self.min_average

    @property
    def contour_max_conc(self):
        return self.max_average

    def get_plot_conc_range(self, grid, scaling_factor):
        return grid.extension.min_vert_avg_conc * scaling_factor, \
               grid.extension.max_vert_avg_conc * scaling_factor

    def get_level_range_str(self, level1, level2):
        """level1 and level2 are instances of the LengthInFeet or
        LengthInMeters class."""
        if self.custom_layer_str is not None:
            return "{0} {1} and {2}".format(self.custom_layer_str,
                                            level1, level2)
        return "averaged between {0} and {1}".format(level1, level2)

    def get_upper_level(self, grid_level, settings_level):
        return settings_level


class LevelConcentration(ConcentrationType):

    def __init__(self):
        super(LevelConcentration, self).__init__()
        # concentration values vertical level, across all grids of interest
        self.min_concs = None
        self.max_concs = None
        self.__min_concs_stashed = None
        self.__max_concs_stashed = None
        self.KAVG = 1
        self.alt_KAVG = 1
        self.ground_index = None
        self.gis_filename_maker = GisOutputFilenameForLevelConc()
        self.kml_filename_maker = KmlOutputFilename()

    def set_alt_KAVG(self, KAVG):
        self.alt_KAVG = KAVG

    def initialize(self, cdump, level_selector, pollutant_selector):
        super(LevelConcentration, self).initialize(cdump,
                                                   level_selector,
                                                   pollutant_selector)
        # min and max values at each vertical level
        self.min_concs = [1.0e+25] * len(cdump.vert_levels)
        self.max_concs = [0.0] * len(cdump.vert_levels)
        try:
            self.ground_index = cdump.vert_levels.index(0)
        except ValueError:
            self.ground_index = None

    def prepare_grids_for_plotting(self, t_grids):
        if self.level_selector is None or self.pollutant_selector is None:
            raise ValueError("level_selector or pollutant_selector is "
                             "not set: did you call initialize()?")

        v_grids = sum_over_pollutants_per_level(t_grids,
                                                self.level_selector,
                                                self.pollutant_selector)

        # remove grids with vertical level = 0 m.
        grids = list(filter(lambda g: g.vert_level > 0, v_grids))

        # sort by vertical level
        grids = sorted(grids, key=lambda g: g.vert_level)

        # grids on the ground
        if 0 in self.level_selector:
            gnd_grids = list(filter(lambda g: g.vert_level == 0, v_grids))
        else:
            ground_level_selector = VerticalLevelSelector(0, 0)
            gnd_grids = sum_over_pollutants_per_level(t_grids,
                                                      ground_level_selector,
                                                      self.pollutant_selector)

        return grids, gnd_grids

    def update_min_max(self, t_grids):
        for g in t_grids:
            vmin, vmax = find_nonzero_min_max(g.conc)
            self.update_min_max_at_level(vmin, vmax, g.vert_level_index)

            g.extension = GridProperties()
            g.extension.min_conc = vmin if vmin is not None else 0.0
            g.extension.max_conc = vmax

    def update_min_max_at_level(self, vmin, vmax, level_index):
        if vmin is not None:
            self.min_concs[level_index] = min(self.min_concs[level_index],
                                              vmin)

        if vmax is not None:
            self.max_concs[level_index] = max(self.max_concs[level_index],
                                              vmax)

        logger.debug("level %d: min %g, max %g",
                     level_index,
                     self.min_concs[level_index],
                     self.max_concs[level_index])

    def normalize_min_max(self):
        logger.debug("before normalization: min %s, max %s",
                     self.min_concs, self.max_concs)

        for k in range(len(self.min_concs) - 1, -1, -1):
            if self.max_concs[k] < self.min_concs[k]:
                # This happens when all concentration values at this level
                # are zero.

                repairedQ = False

                # copy min and max values at a lower level
                for j in range(k - 1, 0, -1):
                    if self.max_concs[j] >= self.min_concs[j]:
                        self.max_concs[k] = self.max_concs[j]
                        self.min_concs[k] = self.min_concs[j]
                        repairedQ = True
                        break

                if not repairedQ:
                    self.min_concs[k] = 0.0
                    self.max_concs[k] = 1.0e+25

        logger.debug("after normalization: min %s, max %s",
                     self.min_concs, self.max_concs)

    def scale_conc(self, CONADJ, DEPADJ):
        if self.cdump.vert_levels[0] == 0:
            self.min_concs[0] *= DEPADJ
            self.max_concs[0] *= DEPADJ
            self.min_concs[1:] = [x * CONADJ for x in self.min_concs[1:]]
            self.max_concs[1:] = [x * CONADJ for x in self.max_concs[1:]]
        else:
            self.min_concs = [x * CONADJ for x in self.min_concs]
            self.max_concs = [x * CONADJ for x in self.max_concs]
        logger.debug("scaled conc using CONADJ %g, "
                     "DEPADJ %g to min %s, max %s",
                     CONADJ, DEPADJ,
                     self.min_concs, self.max_concs)

    def scale_exposure(self, factor):
        self.__min_concs_stashed = self.min_concs
        self.__max_concs_stashed = self.max_concs
        self.min_concs = [x * factor for x in self.min_concs]
        self.max_concs = [x * factor for x in self.max_concs]
        logger.debug("exposure scaling factor %g, min_concs %s",
                     factor, self.min_concs)
        logger.debug("exposure scaling factor %g, max_concs %s",
                     factor, self.max_concs)

    def undo_scale_exposure(self):
        self.min_concs = self.__min_concs_stashed
        self.max_concs = self.__max_concs_stashed

    @property
    def contour_min_conc(self):
        return self.min_concs[-1]   # at the top level

    @property
    def contour_max_conc(self):
        return self.max_concs[-1]   # at the top level

    @property
    def ground_min_conc(self):
        return self.min_concs[self.ground_index]

    @property
    def ground_max_conc(self):
        return self.max_concs[self.ground_index]

    def get_plot_conc_range(self, grid, scaling_factor):
        return grid.extension.min_conc * scaling_factor, \
               grid.extension.max_conc * scaling_factor

    def get_level_range_str(self, level1, level2):
        if self.alt_KAVG == 3:
            if self.custom_layer_str is not None:
                return "{0} {1} and {2}".format(self.custom_layer_str,
                                                level1, level2)
            return "averaged between {0} and {1}".format(level1, level2)
        else:
            if self.custom_layer_str is not None:
                return "{0} {1}".format(self.custom_layer_str, level2)
            return "at level {0}".format(level2)

    def get_upper_level(self, grid_level, settings_level):
        return grid_level


class ConcentrationMapFactory:

    @staticmethod
    def create_instance(KMAP, KHEMIN):
        if KMAP == const.ConcentrationMapType.CONCENTRATION:
            return ConcentrationMap(KHEMIN)
        elif KMAP == const.ConcentrationMapType.EXPOSURE:
            return ExposureMap(KHEMIN)
        elif KMAP == const.ConcentrationMapType.DEPOSITION:
            return DepositionMap(KHEMIN)
        elif KMAP == const.ConcentrationMapType.THRESHOLD_LEVELS:
            return ThresholdLevelsMap(KHEMIN)
        elif KMAP == const.ConcentrationMapType.VOLCANIC_ERUPTION:
            return VolcanicEruptionMap(KHEMIN)
        elif KMAP == const.ConcentrationMapType.DEPOSITION_6:
            return Deposition6Map(KHEMIN)
        elif KMAP == const.ConcentrationMapType.MASS_LOADING:
            return MassLoadingMap(KHEMIN)
        elif KMAP == const.ConcentrationMapType.TIME_OF_ARRIVAL:
            return TimeOfArrivalMap(KHEMIN)
        else:
            return AbstractConcentrationMap(KMAP, KHEMIN)


class DepositionMapFactory:

    @staticmethod
    def create_instance(KMAP, KHEMIN):
        if KMAP == const.ConcentrationMapType.VOLCANIC_ERUPTION:
            return Deposition6Map(KHEMIN)
        elif KMAP == const.ConcentrationMapType.TIME_OF_ARRIVAL:
            return TimeOfArrivalMap(KHEMIN)

        return DepositionMap(KHEMIN)


class AbstractConcentrationMap:

    def __init__(self, KMAP, KHEMIN, map_id="Unspecified"):
        self.KMAP = KMAP
        self.KHEMIN = KHEMIN
        self.map_id = map_id

    def has_banner(self):
        return False

    def guess_mass_unit(self, mass_unit):
        return mass_unit

    def guess_volume_unit(self, mass_unit):
        return ""

    def format_conc(self, v):
        if not isinstance(v, int) and not isinstance(v, float):
            return " "

        if v >= 100000.0:
            f = "{:.1e}".format(v)
        elif v >= 10000.0:
            f = "{:5d}".format(int(v))
        elif v >= 1000.0:
            f = "{:4d}".format(int(v))
        elif v >= 100.0:
            f = "{:3d}".format(int(v))
        elif v >= 10.0:
            f = "{:2d}".format(int(v))
        elif v >= 1.0:
            f = "{:1d}".format(int(v))
        elif v >= 0.1:
            f = "{:3.1f}".format(v)
        elif v >= 0.01:
            f = "{:4.2f}".format(v)
        elif v >= 0.001:
            f = "{:5.3f}".format(v)
        elif v <= 0.0:
            f = " "
        else:
            f = "{:7.1e}".format(v)

        return f

    def draw_explanation_text(self, axes, x, y, font_sz, line_skip,
                              contour_labels):
        return y

    def set_map_id(self, str):
        self.map_id = str

    def scale_exposure(self, TFACT, conc_type, scaling_factor):
        # TFACT and concentration extrema are scaled for mass loading:
        # see MassLoadingMap.
        return TFACT

    def undo_scale_exposure(self, conc_type):
        pass

    def need_time_scaling(self):
        return False

    def scale_time(self, TFACT, conc_type, f, initial_timeQ):
        # See ExposureMap.
        return TFACT

    def get_color_at_max(self):
        return "r"  # red


class ConcentrationMap(AbstractConcentrationMap):

    def __init__(self, KHEMIN):
        super(ConcentrationMap, self).__init__(
            const.ConcentrationMapType.CONCENTRATION,
            KHEMIN,
            "Concentration")

    def guess_volume_unit(self, mass_unit):
        if mass_unit.startswith("ppm"):
            return ""
        else:
            return "/m^3"

    def get_map_id_line(self, conc_type, conc_unit, level1, level2):
        return "{0} (${1}$) {2}".format(
            self.map_id,
            conc_unit,
            conc_type.get_level_range_str(level1, level2))


class ExposureMap(AbstractConcentrationMap):

    def __init__(self, KHEMIN):
        super(ExposureMap, self).__init__(
            const.ConcentrationMapType.EXPOSURE,
            KHEMIN,
            "Exposure")

    def guess_volume_unit(self, mass_unit):
        if mass_unit.startswith("rem") or mass_unit.startswith("Sv"):
            # rem, rem/hr, Sv, or Sv/hr
            return ""
        else:
            return "\u2013s/m^3"  # \u2013 is an en-dash

    def get_map_id_line(self, conc_type, conc_unit, level1, level2):
        return "{0} (${1}$) {2}".format(
            self.map_id,
            conc_unit,
            conc_type.get_level_range_str(level1, level2))

    def need_time_scaling(self):
        return True

    def scale_time(self, TFACT, conc_type, f, initial_timeQ):
        # air conc to exposure
        if initial_timeQ:
            conc_type.scale_exposure(f)

        return TFACT * f


class DepositionMap(AbstractConcentrationMap):

    def __init__(self, KHEMIN):
        super(DepositionMap, self).__init__(
            const.ConcentrationMapType.DEPOSITION,
            KHEMIN,
            "Deposition")

    def guess_volume_unit(self, mass_unit):
        return "/m^2"

    def get_map_id_line(self, conc_type, conc_unit, level1, level2):
        return "{0} (${1}$) at ground-level".format(self.map_id,
                                                    conc_unit)


class ThresholdLevelsMap(AbstractConcentrationMap):

    def __init__(self, KHEMIN):
        super(ThresholdLevelsMap, self).__init__(
            const.ConcentrationMapType.THRESHOLD_LEVELS,
            KHEMIN,
            "Concentration")

    def has_banner(self):
        return True

    def get_banner(self):
        return "Not for Public Dissemination"

    def guess_volume_unit(self, mass_unit):
        if mass_unit.startswith("ppm"):
            return ""
        else:
            return "/m^3"

    def get_map_id_line(self, conc_type, conc_unit, level1, level2):
        return "{0} (${1}$) {2}".format(
                self.map_id,
                conc_unit,
                conc_type.get_level_range_str(level1, level2))

    def format_conc(self, v):
        if v >= 100000.0:
            f = "{:.1e}".format(v)
        elif v >= 10000.0:
            f = "{:5d}".format(int(v))
        elif v >= 1000.0:
            f = "{:4d}".format(int(v))
        elif v >= 100.0:
            f = "{:3d}".format(int(v))
        elif v >= 10.0:
            f = "{:4.1f}".format(v)
        elif v >= 1.0:
            f = "{:3.1f}".format(v)
        elif v >= 0.1:
            f = "{:3.1f}".format(v)
        elif v >= 0.01:
            f = "{:4.2f}".format(v)
        elif v >= 0.001:
            f = "{:5.3f}".format(v)
        elif v <= 0.0:
            f = " "
        else:
            f = "{:7.1e}".format(v)

        return f

    def draw_explanation_text(self, axes, x, y, font_sz, line_skip,
                              contour_labels):
        if len(contour_labels) > 0:
            label = contour_labels[0]
            if (not label.startswith("AEGL")) \
                    and (not label.startswith("ERPG")) \
                    and (not label.startswith("TEEL")) \
                    and (not label.startswith("PAC")):
                return y

        title = "ACUTE (SHORT-TERM) EFFECTS"
        pars = [["Life-threatening health", "effects possible"],
                ["Irreversible or other", "serious health effects that",
                 "could impair the ability to", "take protective action."],
                ["Mild, transient health", "effects."]]

        x = 0.05
        dx = 0.25

        y -= line_skip * 1.5

        axes.text(0.5, y, title, color="k", fontsize=font_sz,
                  horizontalalignment="center", verticalalignment="top",
                  clip_on=True,
                  transform=axes.transAxes)
        y -= line_skip

        axes.hlines(y, 0.05, 0.95,
                    color="k",
                    linewidth=0.125,
                    transform=axes.transAxes)

        for k, par in enumerate(pars):
            y -= line_skip * 0.5
            label = contour_labels[k] if len(contour_labels) > k else ""
            axes.text(x, y, label, color="k", fontsize=font_sz,
                      horizontalalignment="left", verticalalignment="top",
                      clip_on=True, transform=axes.transAxes)

            for str in par:
                axes.text(x + dx + x, y, str, color="k", fontsize=font_sz,
                          horizontalalignment="left", verticalalignment="top",
                          clip_on=True, transform=axes.transAxes)
                y -= line_skip

        axes.hlines(y, 0.05, 0.95,
                    color="k",
                    linewidth=0.125, transform=axes.transAxes)

        return y

    def get_color_at_max(self):
        return "k"  # black


class VolcanicEruptionMap(AbstractConcentrationMap):

    def __init__(self, KHEMIN):
        super(VolcanicEruptionMap, self).__init__(
            const.ConcentrationMapType.VOLCANIC_ERUPTION,
            KHEMIN,
            "Concentration")

    def has_banner(self):
        return True

    def get_banner(self):
        return "*** Hypothetical eruption ***"

    def guess_volume_unit(self, mass_unit):
        return "/m^3"

    def get_map_id_line(self, conc_type, conc_unit, level1, level2):
        return "{0} (${1}$) {2}".format(self.map_id,
                                        conc_unit,
                                        conc_type.get_level_range_str(
                                            level1, level2))

    def draw_explanation_text(self, axes, x, y, font_sz, line_skip,
                              contour_labels):
        lines = ["Initial ash mass, see below",
                 "For real eruption, see",
                 "    SIGMET and VAAC products"]

        y -= line_skip * 1.5
        axes.hlines(y, 0.05, 0.95,
                    color="k",
                    linewidth=0.125,
                    transform=axes.transAxes)
        y -= line_skip * 0.5

        for str in lines:
            axes.text(x, y, str, color="r", fontsize=font_sz,
                      horizontalalignment="left", verticalalignment="top",
                      clip_on=True, transform=axes.transAxes)
            y -= line_skip

        axes.hlines(y, 0.05, 0.95,
                    color="k",
                    linewidth=0.125, transform=axes.transAxes)

        return y


# TODO: better name
class Deposition6Map(AbstractConcentrationMap):

    def __init__(self, KHEMIN):
        super(Deposition6Map, self).__init__(
            const.ConcentrationMapType.DEPOSITION_6,
            KHEMIN,
            "Deposition")

    def guess_volume_unit(self, mass_unit):
        return "/m^2"

    def get_map_id_line(self, conc_type, conc_unit, level1, level2):
        return "{0} (${1}$) at ground-level".format(self.map_id,
                                                    conc_unit)


class MassLoadingMap(AbstractConcentrationMap):

    def __init__(self, KHEMIN):
        super(MassLoadingMap, self).__init__(
            const.ConcentrationMapType.MASS_LOADING,
            KHEMIN,
            "Mass loading")

    def guess_volume_unit(self, mass_unit):
        return "/m^2"

    def get_map_id_line(self, conc_type, conc_unit, level1, level2):
        return "{0} (${1}$) {2}".format(self.map_id,
                                        conc_unit,
                                        conc_type.get_level_range_str(
                                            level1, level2))

    def scale_exposure(self, TFACT, conc_type, scaling_factor):
        conc_type.scale_exposure(scaling_factor)
        return TFACT * scaling_factor

    def undo_scale_exposure(self, conc_type):
        conc_type.undo_scale_exposure()


class TimeOfArrivalMap(AbstractConcentrationMap):

    def __init__(self, KHEMIN):
        super(TimeOfArrivalMap, self).__init__(
            const.ConcentrationMapType.TIME_OF_ARRIVAL,
            KHEMIN,
            "Time-Of-Arrival (h)")

    def guess_mass_unit(self, mass_unit):
        return "hours"

    def guess_volume_unit(self, mass_unit):
        return ""

    def get_map_id_line(self, conc_type, conc_unit, level1, level2):
        return "{0} {1}".format(self.map_id,
                                conc_type.get_level_range_str(level1, level2))

    def scale_exposure(self, TFACT, conc_type, scaling_factor):
        return TFACT * scaling_factor

    def undo_scale_exposure(self, conc_type):
        pass


class DepositSumFactory:

    @staticmethod
    def create_instance(type, has_ground_level_grid=True):
        if not has_ground_level_grid \
                or type == const.DepositionType.NONE:
            return NullDeposit()
        elif type == const.DepositionType.TIME:
            return TimeDeposit()
        elif type == const.DepositionType.SUM:
            return SumDeposit()
        elif type == const.DepositionType.TOTAL:
            return TotalDeposit()

        raise Exception("unknown deposition type {0}".format(type))


class NullDeposit(ABC):

    def __init__(self):
        self.summation_from_datetime = None
        self.gis_filename_maker = GisOutputFilenameForDeposit()

    def initialize(self, grids, time_selector, pollutant_selector):
        if len(grids) > 0:
            self.summation_from_datetime = grids[0].starting_datetime

    def add(self, grids, first_timeQ=False):
        if len(grids) > 0:
            self.summation_from_datetime = grids[0].starting_datetime

    def get_grids_to_plot(self, grids_on_ground, last_timeQ=False):
        return []

    def make_gis_basename(self, time_index, output_suffix):
        return None


class TimeDeposit(NullDeposit):

    def __init__(self):
        super(TimeDeposit, self).__init__()
        self.gis_filename_maker = GisOutputFilenameForDeposit()

    def get_grids_to_plot(self, grids_on_ground, last_timeQ=False):
        return grids_on_ground

    def make_gis_basename(self, time_index, output_suffix):
        return self.gis_filename_maker.get_basename(time_index, output_suffix)


class SumDeposit(NullDeposit):

    def __init__(self):
        super(SumDeposit, self).__init__()
        self.gis_filename_maker = GisOutputFilenameForDeposit()
        self.summation_grid = None

    def initialize(self, grids, time_selector, pollutant_selector):
        super(SumDeposit, self).initialize(grids,
                                           time_selector,
                                           pollutant_selector)

        # sum concentration grids right before the first time index
        a = list(filter(lambda g:
                        g.time_index < time_selector.first and
                        g.pollutant_index in pollutant_selector and
                        g.vert_level == 0, grids))
        if len(a) > 0:
            self.summation_grid = a[0].clone()
            if self.summation_grid.extension is None:
                self.summation_grid.extension = GridProperties()
            for g in a[1:]:
                self.summation_grid.conc += g.conc
            return

        # summation must be starting from the first time index.
        # let the time-loop handle the summation.

        a = list(filter(lambda g:
                        g.time_index == time_selector.first and
                        g.pollutant_index in pollutant_selector and
                        g.vert_level == 0, grids))
        if len(a) > 0:
            self.summation_grid = a[0].clone_except_conc()
            self.summation_grid.conc = numpy.zeros(a[0].conc.shape)
            if self.summation_grid.extension is None:
                self.summation_grid.extension = GridProperties()

    def add(self, grids_on_ground, first_timeQ=False):
        # do not update self.summation_from_datetime
        for k, g in enumerate(grids_on_ground):
            self.summation_grid.conc += g.conc
            if first_timeQ and k == 0:
                self.summation_grid.starting_datetime = g.starting_datetime
                self.summation_grid.starting_forecast_hr = \
                    g.starting_forecast_hr

    def get_grids_to_plot(self, grids_on_ground, last_timeQ=False):
        self._update_properties(grids_on_ground)
        return [self.summation_grid]

    def _update_properties(self, grids_on_ground):
        if len(grids_on_ground) > 0 and self.summation_grid is not None:
            g = grids_on_ground[0]
            s = self.summation_grid
            s.time_index = g.time_index
            s.ending_datetime = g.ending_datetime
            s.ending_forecast_hr = g.ending_forecast_hr
            s.nonzero_conc_count = numpy.count_nonzero(s.conc)
            if s.extension is not None:
                s.extension.update(s.conc)

    def make_gis_basename(self, time_index, output_suffix):
        return self.gis_filename_maker.get_basename(time_index, output_suffix)


class TotalDeposit(SumDeposit):

    def __init__(self):
        super(TotalDeposit, self).__init__()
        self.gis_filename_maker = GisOutputFilenameForDeposit()

    def get_grids_to_plot(self, grids_on_ground, last_timeQ=False):
        if last_timeQ:
            self._update_properties(grids_on_ground)
            return [self.summation_grid]

        return []

    def make_gis_basename(self, time_index, output_suffix):
        return self.gis_filename_maker.get_basename(time_index, output_suffix)
