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


class ConcentrationDumpProperty:
    
    def __init__(self, cdump):
        self.cdump = cdump
        self.min_average = 1.0e+25
        self.max_average = 0.0
        self.min_concs = [1.0e+25] * len(cdump.vert_levels)  # at each vertical level
        self.max_concs = [0.0] * len(cdump.vert_levels)   # at each vertical level 
        return
    
    def dump(self, stream):
        stream.write("----- begin ConcentrationDumpProperty\n")
        for k, v in self.__dict__.items():
            stream.write("{0} = {1}\n".format(k, v))

        stream.write("----- end ConcentrationDumpProperty\n")
        
    def update_average_min_max(self, vmin, vmax):
        if vmin is not None:
            self.min_average = min(self.min_average, vmin)
            
        if vmax is not None:
            self.max_average = max(self.max_average, vmax)

    def update_min_max_at_level(self, vmin, vmax, level_index):
        if vmin is not None:
            self.min_concs[level_index] = min(self.min_concs[level_index], vmin)
            
        if vmax is not None:
            self.max_concs[level_index] = max(self.max_concs[level_index], vmax)

    # TODO: refactor using classes
    def scale_conc(self, KAVG, CONADJ, DEPADJ):
        if self.cdump.vert_levels[0] == 0:
            self.min_concs[0] *= DEPADJ
            self.max_concs[0] *= DEPADJ
            if KAVG == const.ConcentrationType.EACH_LEVEL:
                self.min_concs[1:] = [x * CONADJ for x in self.min_concs[1:]]
                self.max_concs[1:] = [x * CONADJ for x in self.max_concs[1:]]
            else:
                self.min_average *= CONADJ
                self.max_average *= CONADJ
        else:
            if KAVG == const.ConcentrationType.EACH_LEVEL:
                self.min_concs = [x * CONADJ for x in self.min_concs]
                self.max_concs = [x * CONADJ for x in self.max_concs]
            else:
                self.min_average *= CONADJ
                self.max_average *= CONADJ
    
    # TODO: refactor using classes
    def scale_exposure(self, KAVG, factor):
        if KAVG == const.ConcentrationType.EACH_LEVEL:
            self.min_concs[:] = [x * factor for x in self.min_concs]
            self.max_concs[:] = [x * factor for x in self.max_concs]
        else:
            self.min_average *= factor
            self.max_average *= factor
                

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

