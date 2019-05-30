import logging
import numpy
import sys

from hysplit4 import util, const


logger = logging.getLogger(__name__)


class ConcentrationDumpProperty:
    
    def __init__(self, cdump):
        self.cdump = cdump
        self.min_average = 0.0
        self.max_average = 0.0
        self.min_concs = []   # at each vertical level
        self.max_concs = []   # at each vertical level 
        return
    
    def dump(self, stream):
        stream.write("----- begin ConcentrationDumpProperty\n")
        for k, v in self.__dict__.items():
            stream.write("{0} = {1}\n".format(k, v))

        stream.write("----- end ConcentrationDumpProperty\n")
        
    def get_vertical_average_analyzer(self):
        return VerticalAverageAnalyzer(self)

    def get_vertical_level_analyzer(self):
        return VerticalLevelAnalyzer(self)

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
                
# TODO: split to classes                
class VerticalAverageAnalyzer:
    
    def __init__(self, cdump_prop):
        self.cdump_prop = cdump_prop
        self.selected_level_indices = []
        self.delta_z = []
        self.inverse_weight = 1.0
    
    def analyze(self, time_selector, pollutant_selector, level_selector):
        cdump = self.cdump_prop.cdump
        
        # prepare weights and return if there is an error
        if not self._prepare_weighted_averaging(cdump, level_selector):
            return
        
        avgmax = 0.0
        avgmin = 1.0e+25
        
        for t_index in time_selector:
            avg = self._average_vertically(t_index, pollutant_selector)
       
            if avg is not None:
                avgmax = max(avgmax, avg.max())
                nz_min = util.nonzero_min(avg)
                if nz_min is not None:
                    avgmin = min(avgmin, nz_min)
    
        self.cdump_prop.max_average = avgmax
        self.cdump_prop.min_average = avgmin
                
        return self.cdump_prop
    
    def _prepare_weighted_averaging(self, cdump, level_selector):

        self.selected_level_indices.clear()
        
        for k, level in enumerate(cdump.vert_levels):
            if (level > 0) and (level in level_selector):
                self.selected_level_indices.append(k)
        
        self.delta_z.clear()
        
        last = 0
        for k in self.selected_level_indices:
            level = cdump.vert_levels[k]
            self.delta_z.append(level - last)
            last = level
            
        w = sum(self.delta_z)
        if w == 0:
            logger.error("No concentration grids found for vertical averaging between levels {0} and {1}.".format(level_min, level_max))
            return False
        
        self.inverse_weight = 1.0 / w
        return True
            
    def _average_vertically(self, time_index, pollutant_selector):
        cdump = self.cdump_prop.cdump

        # allocate workspace
        grids = []
        for k in self.selected_level_indices:
            grids.append(numpy.zeros(cdump.grid_sz))
        
        # summation across pollutants
        k = 0
        for level_index in self.selected_level_indices:
            fn = lambda g: \
                    g.time_index == time_index and \
                    g.vert_level_index == level_index and \
                    g.pollutant_index in pollutant_selector
                       
            for g in list(filter(fn, cdump.conc_grids)):
                grids[k] += g.conc

            k += 1
            
        # vertical average
        avg = numpy.empty(cdump.grid_sz)
        for i in range(cdump.grid_sz[0]):
            for j in range(cdump.grid_sz[1]):
                # stardard layer weighted vertical average
                vsum = 0.0
                    
                for k, c in enumerate(grids):
                    vsum += c[i, j] * self.delta_z[k]
                    
                avg[i, j] = vsum * self.inverse_weight

        return avg


   
class VerticalLevelAnalyzer:
    
    def __init__(self, cdump_prop):
        self.cdump_prop = cdump_prop
    
    def analyze(self, time_selector, pollutant_selector=None):
        cdump = self.cdump_prop.cdump

        level_count = len(cdump.vert_levels)
        cmin = numpy.full(level_count, 1.0e+25)
        cmax = numpy.full(level_count, 0.0)
        
        for t_index in time_selector:
            grids = cdump.find_conc_grids_by_time_index(t_index)
            for g in grids:
                if (pollutant_selector is None) or (g.pollutant_index in pollutant_selector):
                    k = g.vert_level_index
                    cmin[k] = min(cmin[k], util.nonzero_min(g.conc))
                    cmax[k] = max(cmax[k], g.conc.max())
    
        self.cdump_prop.min_concs = cmin
        self.cdump_prop.max_concs = cmax
                
        return self.cdump_prop
