import logging
import numpy
import sys

from hysplit4.conc import model
from hysplit4 import util, const


logger = logging.getLogger(__name__)


def sum_over_pollutants_per_level(grids, level_selector, pollutant_selector):
    """Returns an array of concentration grids at each vertical level.
    
    Summation of concentration over pollutants is performed if necessary.
    All concentration grids specified by the grids argument are assumed to have
    the same time index.
    """
    
    # select grids
    fn = lambda g: g.vert_level in level_selector and g.pollutant_index in pollutant_selector
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
            v_grids.append(g)
       
    return v_grids


def sum_conc_grids_of_interest(grids, level_selector, pollutant_selector, time_selector): 
    fn = lambda g: \
            g.time_index in time_selector and \
            g.pollutant_index in pollutant_selector and \
            g.vert_level in level_selector
            
    filtered = list(filter(fn, grids))
    
    sum = numpy.copy(filtered[0].conc)
    for g in filtered[1:]:
        sum += g.conc
        
    return sum
    
    
def find_nonzero_min_max(mat):
    """Find the non-zero minimum value and the maximum value of a numpy matrix"""
    vmax = None
    vmin = None
        
    if mat is not None:
        vmax = mat.max()
        vmin = util.nonzero_min(mat)    # may return None.

    return vmin, vmax


def get_lower_level(current_level, levels):
    sorted_levels = sorted(levels)

    k = sorted_levels.index(current_level)
    if k > 0:
        return sorted_levels[k - 1]
    else:
        return 0.0
    

class TimeIndexSelector:
    
    def __init__(self, first_index=0, last_index=9999, step=1):
        self.__min = first_index
        self.__max = last_index
        self.step = step
 
    def __iter__(self):
        return iter(range(self.first, self.last + 1, self.step))
 
    def __contains__(self, time_index):
        return True if (time_index >= self.__min and time_index <= self.__max) else False
       
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
        return True if (self.__index < 0 or self.__index == pollutant_index) else False

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
        return True if (level >= self.__min and level <= self.__max) else False
 
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
        AbstractGridFilter.__init__(self)
        self.grids = self._filter(grids, time_index_selector)
    
    @staticmethod
    def _filter(grids, time_index_selector):
        fn = lambda g: g.time_index in time_index_selector
        return AbstractGridFilter._filter(grids, fn)
    

class VerticalLevelGridFilter(AbstractGridFilter):
    
    def __init__(self, grids, level_selector):
        AbstractGridFilter.__init__(self)
        self.grids = self._filter(grids, level_selector)
        
    @staticmethod
    def _filter(grids, level_selector):
        fn = lambda g: g.vert_level in level_selector
        return AbstractGridFilter._filter(grids, fn)


class VerticalAverageCalculator:
    
    def __init__(self, cdump, level_selector):
        self.selected_level_indices = []
        self.delta_z = dict()               # the dictionary key is a vertical level index.
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
            logger.error("No concentration grids found for vertical averaging between levels {0} and {1}.".format(level_selector.min, level_selector.max))
            return False
        
        self.inverse_weight = 1.0 / w
        return True
            
    def average(self, grids):

        # vertical average
        avg = numpy.zeros(grids[0].conc.shape)
        
        for g in grids:
            avg += g.conc * self.delta_z[g.vert_level_index]
        
        return (avg * self.inverse_weight)


class ConcentrationTypeFactory:
    
    @staticmethod
    def create_instance(conc_type):
        if conc_type == const.ConcentrationType.EACH_LEVEL:
            return LevelConcentration()
        elif conc_type == const.ConcentrationType.VERTICAL_AVERAGE:
            return VerticalAverageConcentration()
        
        raise Exception("unknown concentration type {0}".format(conc_type))
        
        
class ConcentrationType:
    
    def __init__(self):
        self.cdump = None
        self.level_selector = None
        self.pollutant_selector = None
    
    def initialize(self, cdump, level_selector, pollutant_selector):
        self.cdump = cdump
        self.level_selector = level_selector
        self.pollutant_selector = pollutant_selector


class VerticalAverageConcentration(ConcentrationType):
    
    def __init__(self):
        ConcentrationType.__init__(self)
        self.average_calc = None
        self.min_average = 1.0e+25
        self.max_average = 0.0
        return 
    
    def initialize(self, cdump, level_selector, pollutant_selector):
        ConcentrationType.initialize(self, cdump, level_selector, pollutant_selector)
        self.average_calc = VerticalAverageCalculator(cdump, level_selector)

    def prepare_grids_for_plotting(self, t_grids):
        
        v_grids = sum_over_pollutants_per_level(t_grids,
                                                self.level_selector,
                                                self.pollutant_selector)
        v_avg = self.average_calc.average(v_grids)
                
        g = v_grids[0].clone_except_conc()
        g.conc = v_avg
        g.vert_level_index = -1
        return [g]
        
    def update_min_max(self, t_grids):
        v_grids = sum_over_pollutants_per_level(t_grids,
                                                self.level_selector,
                                                self.pollutant_selector)
        logger.debug("VERT GRIDS %s", v_grids)
        
        v_avg = self.average_calc.average(v_grids)
        logger.debug("VERT AVG %s", v_avg)
        
        vmin, vmax = find_nonzero_min_max(v_avg)
        self.update_average_min_max(vmin, vmax)
        
    def update_average_min_max(self, vmin, vmax):
        if vmin is not None:
            self.min_average = min(self.min_average, vmin)
            
        if vmax is not None:
            self.max_average = max(self.max_average, vmax)
            
        logger.debug("average min %g, max %g", self.min_average, self.max_average)

    def scale_conc(self, CONADJ, DEPADJ):
        self.min_average *= CONADJ
        self.max_average *= CONADJ

    def scale_exposure(self, factor):
        self.min_average *= factor
        self.max_average *= factor
        logger.debug("exposure scaling factor %g, min avg %g, max avg %g", factor, self.min_average, self.max_average)
  
    @property
    def contour_min_conc(self):
        return self.min_average
    
    @property
    def contour_max_conc(self):
        return self.max_average
    
    def get_plot_conc_range(self, vert_level_index):
        return self.min_average, self.max_average

    
class LevelConcentration(ConcentrationType):
    
    def __init__(self):
        ConcentrationType.__init__(self)
        self.min_concs = None  # at each vertical level
        self.max_concs = None  # at each vertical level 
    
    def initialize(self, cdump, level_selector, pollutant_selector):
        ConcentrationType.initialize(self, cdump, level_selector, pollutant_selector)
        self.min_concs = [1.0e+25] * len(cdump.vert_levels)  # at each vertical level
        self.max_concs = [0.0] * len(cdump.vert_levels)   # at each vertical level 
        
    def update_min_max(self, t_grids):
        for g in t_grids:
            vmin, vmax = find_nonzero_min_max(g.conc)
            self.update_min_max_at_level(vmin, vmax, g.vert_level_index)
    
    def update_min_max_at_level(self, vmin, vmax, level_index):
        if vmin is not None:
            self.min_concs[level_index] = min(self.min_concs[level_index], vmin)
            
        if vmax is not None:
            self.max_concs[level_index] = max(self.max_concs[level_index], vmax)

        logger.debug("level %d: min %g, max %g",
                     level_index,
                     self.min_concs[level_index],
                     self.max_concs[level_index])

    def prepare_grids_for_plotting(self, t_grids):
        
        v_grids = sum_over_pollutants_per_level(t_grids,
                                                self.level_selector,
                                                self.pollutant_selector)
        
        # remove grids with vertical level = 0 m.
        grids = list(filter(lambda g: g.vert_level > 0, v_grids))
        
        # sort by vertical level
        grids = sorted(grids, key=lambda g: g.vert_level)
        
        return grids
    
    def scale_conc(self, CONADJ, DEPADJ):
        if self.cdump.vert_levels[0] == 0:
            self.min_concs[0] *= DEPADJ
            self.max_concs[0] *= DEPADJ
            self.min_concs[1:] = [x * CONADJ for x in self.min_concs[1:]]
            self.max_concs[1:] = [x * CONADJ for x in self.max_concs[1:]]
        else:
            self.min_concs = [x * CONADJ for x in self.min_concs]
            self.max_concs = [x * CONADJ for x in self.max_concs]

    def scale_exposure(self, factor):
        self.min_concs[:] = [x * factor for x in self.min_concs]
        self.max_concs[:] = [x * factor for x in self.max_concs]
        logger.debug("exposure scaling factor %g, min_concs %s", factor, self.min_concs)
        logger.debug("exposure scaling factor %g, max_concs %s", factor, self.max_concs)
       
    @property
    def contour_min_conc(self):
        return self.min_concs[-1]
    
    @property
    def contour_max_conc(self):
        return self.max_concs[-1]
    
    def get_plot_conc_range(self, vert_level_index):
        return self.min_concs[vert_level_index], self.max_concs[vert_level_index]


class ConcentrationMapFactory:
    
    @staticmethod
    def create_instance(KMAP, KHEMIN):
        if KMAP == const.ConcentrationMapType.THRESHOLD_LEVELS:
            return ThresholdLevelsMap(KMAP, KHEMIN)
        elif KMAP == const.ConcentrationMapType.VOLCANIC_ERUPTION:
            return VolcanicEruptionMap(KMAP, KHEMIN)
        else:
            return ConcentrationMap(KMAP, KHEMIN)
        

class ConcentrationMap:
    
    def __init__(self, KMAP, KHEMIN):
        self.KMAP = KMAP
        self.KHEMIN = KHEMIN

    def has_banner(self):
        return False
    
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
 
    def draw_explanation_text(self, axes, x, y, font_sz, line_skip, contour_labels):
        return y
    
   
class ThresholdLevelsMap(ConcentrationMap):
    
    def __init__(self, KMAP, KHEMIN):
        ConcentrationMap.__init__(self, KMAP, KHEMIN)
    
    def has_banner(self):
        return True
    
    def get_banner(self):
        return "Not for Public Dissemination"

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
    
    def draw_explanation_text(self, axes, x, y, font_sz, line_skip, contour_labels):
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
                      transform=axes.transAxes)
            
            for str in par:
                axes.text(x + dx + x, y, str, color="k", fontsize=font_sz,
                          horizontalalignment="left", verticalalignment="top",
                          transform=axes.transAxes)
                y -= line_skip
            
        axes.hlines(y, 0.05, 0.95,
                    color="k",
                    linewidth=0.125, transform=axes.transAxes)
        
        return y


class VolcanicEruptionMap(ConcentrationMap):
    
    def __init__(self, KMAP, KHEMIN):
        ConcentrationMap.__init__(self, KMAP, KHEMIN)
        
    def has_banner(self):
        return True
    
    def get_banner(self):
        return "*** Hypothetical eruption ***"

    def draw_explanation_text(self, axes, x, y, font_sz, line_skip, contour_labels):
        lines = ["Initial ash mass, see below", "For real eruption, see", "    SIGMET and VAAC products"]
        
        y -= line_skip * 1.5
        axes.hlines(y, 0.05, 0.95,
                    color="k",
                    linewidth=0.125, 
                    transform=axes.transAxes)
        y -= line_skip * 0.5
        
        for str in lines:
            axes.text(x, y, str, color="r", fontsize=font_sz,
                  horizontalalignment="left", verticalalignment="top",
                  transform=axes.transAxes)
            y -= line_skip
            
        axes.hlines(y, 0.05, 0.95,
                    color="k",
                    linewidth=0.125, transform=axes.transAxes)
        
        return y
