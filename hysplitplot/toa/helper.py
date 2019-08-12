from abc import ABC, abstractmethod
import copy
import datetime
import logging
import numpy

from hysplitplot.conc import helper


logger = logging.getLogger(__name__)


class TimeOfArrivalGenerator:
    
    def __init__(self, time_selector, conc_type):
        # Time-of-arrivals 6, 12, 18, ....
        self.hours = numpy.linspace(6, 72, num=12)
        # Bitmasks 1, 2, 4, ... for time-of-arrivals 6, 12, 18, ..., respectively.
        self.bitmasks = [(1 << k) for k in range(len(self.hours))]
        self.grid = None
        self.instantaneous_toa_bits = None
        self.integrated_toa_bits = None
        self.time_selector = time_selector
        self.conc_type = conc_type
        self.time_period_count = 0
        self.starting_datetime = None
        self.ending_datetime = None
        
    def _get_bitmasks(self, day):
        if day == TimeOfArrival.DAY_0:
            return [1, 2, 4, 8]
        elif day == TimeOfArrival.DAY_1:
            return [16, 32, 64, 128]
        else:
            return [256, 512, 1024, 2048]

    def _get_lumped_bitmasks_before(self, day):
        if day == TimeOfArrival.DAY_0:
            return None
        elif day == TimeOfArrival.DAY_1:
            return 0x0f
        else:
            return 0x0ff
    
    def _get_toa_hours_for(self, day):
        if day == TimeOfArrival.DAY_0:
            return self.hours[0:4]
        elif day == TimeOfArrival.DAY_1:
            return self.hours[4:8]
        else: 
            return self.hours[8:]

    def process_conc_data(self, cdump):
        self.instantaneous_toa_bits = numpy.zeros(cdump.grids[0].conc.shape, dtype=int)
        self.integrated_toa_bits = numpy.zeros(cdump.grids[0].conc.shape, dtype=int)

        conc_sum = numpy.zeros(cdump.grids[0].conc.shape, dtype=float)
        
        hour_index = 0
        release_date_time = cdump.release_datetimes[0]
        dt_range_lower = release_date_time
        dt_range_upper = release_date_time + datetime.timedelta(hours=self.hours[hour_index])
        
        for t_index in self.time_selector:
            t_grids = helper.TimeIndexGridFilter(cdump.grids,
                                                 helper.TimeIndexSelector(t_index, t_index))
            initial_timeQ = (t_index == self.time_selector.first)
            
            grids_above_ground, grids_on_ground = self.conc_type.prepare_grids_for_plotting(t_grids)
            logger.debug("grid counts: above the ground %d, on the ground %d",
                         len(grids_above_ground), len(grids_on_ground))

            if t_grids[0].ending_datetime > dt_range_upper:
                if hour_index + 1 < len(self.hours):
                    hour_index += 1
                    dt_range_lower = dt_range_upper
                    dt_range_upper = release_date_time + datetime.timedelta(hours=self.hours[hour_index])
        
            if t_grids[0].starting_datetime >= dt_range_lower and t_grids[0].ending_datetime <= dt_range_upper:
                logger.debug("Instantaneous time-of-arrival: start time {}, hour {}".format(t_grids[0].starting_datetime, self.hours[hour_index]))
                if self.grid is None:
                    self.grid = t_grids[0].clone_except_conc()
                    self.grid.nonzero_conc_count = 0
                    
                for g in grids_above_ground:
                    loc = numpy.where(g.conc > 0)
                    self.instantaneous_toa_bits[loc] |= self.bitmasks[hour_index]
                    self.grid.nonzero_conc_count += len(loc[0])

            for g in grids_above_ground:
                conc_sum += g.conc

            if t_grids[0].ending_datetime == dt_range_upper:
                logger.debug("Integrated time-of-arrival: start time {}, hour {}".format(t_grids[0].starting_datetime, self.hours[hour_index]))
                loc = numpy.where( conc_sum > 0 )
                self.integrated_toa_bits[loc] |= self.bitmasks[hour_index]
                
            self.time_period_count += 1

    def save_as_file(self, filename):
        logger.debug("Writing to {}".format(filename))
        bits = self.instantaneous_toa_bits
        with open(filename, "wt") as f:
            nrow, ncol = bits.shape
            for j in range(nrow):
                row = bits[j]
                n = 0
                for i in range(ncol):
                    if row[i] != 0:
                        f.write("{} {} {}\n".format(i, j, row[i]))
                        n += 1
                if n > 0:
                    f.write("\n")

    def make_instantaneous_data(self, day, color_table):
        toa = InstantaneousTimeOfArrival(self.grid, self.instantaneous_toa_bits)

        prev_bitmask = self._get_lumped_bitmasks_before(day)
        
        toa.fill_colors = copy.copy( color_table.colors )
        
        contour_bitmasks = copy.deepcopy( self._get_bitmasks(day) )
        contour_bitmasks.reverse()
        
        contour_values = [40, 60, 80, 100]
                
        for k, s in enumerate(contour_bitmasks):
            c = numpy.copy(self.instantaneous_toa_bits)
            c &= s
            loc = numpy.where(c > 0)
            toa.grid.conc[loc] = contour_values[k]
            logger.debug("Time-of-arrival: bitmask {}, value {}, count {}".format(s, contour_values[k], len(loc[0])))
        
        if prev_bitmask is not None:
            c = numpy.copy(self.instantaneous_toa_bits)
            c &= prev_bitmask
            loc = numpy.where(c > 0)
            toa.grid.conc[loc] = 120
            contour_values.append( 120 )
            toa.fill_colors.append( "#808080" ) # gray
                
        toa.contour_levels = [1.0e-7] + contour_values
        
        toa.display_levels = []
        hours = numpy.flip( self._get_toa_hours_for(day) )
        for hr in hours:
            hr = int(hr)
            toa.display_levels.append( "{}-{} hours".format(hr - 6, hr) )
        if prev_bitmask is not None:
            hr = int(hours[-1]) - 6
            toa.display_levels.append( "{}-{} hours".format(0, hr) )
        
        toa.starting_datetime = self.grid.parent.release_datetimes[0]
        toa.ending_datetime = toa.starting_datetime + datetime.timedelta(hours=hours[0])
        
        return toa
    
    def make_integrated_data(self, day, color_table):
        toa = IntegratedTimeOfArrival(self.grid, self.integrated_toa_bits)

        prev_bitmask = self._get_lumped_bitmasks_before(day)
        
        toa.fill_colors = copy.copy( color_table.colors )
        
        contour_bitmasks = copy.deepcopy( self._get_bitmasks(day) )
        contour_bitmasks.reverse()
        
        contour_values = [40, 60, 80, 100]
                
        for k, s in enumerate(contour_bitmasks):
            c = numpy.copy(self.integrated_toa_bits)
            c &= s
            loc = numpy.where(c > 0)
            toa.grid.conc[loc] = contour_values[k]
            logger.debug("Time-of-arrival: bitmask {}, value {}, count {}".format(s, contour_values[k], len(loc[0])))
        
        if prev_bitmask is not None:
            c = numpy.copy(self.integrated_toa_bits)
            c &= prev_bitmask
            loc = numpy.where(c > 0)
            toa.grid.conc[loc] = 120
            contour_values.append( 120 )
            toa.fill_colors.append( "#808080" ) # gray
                
        toa.contour_levels = [1.0e-7] + contour_values
        
        toa.display_levels = []
        hours = numpy.flip( self._get_toa_hours_for(day) )
        for hr in hours:
            hr = int(hr)
            toa.display_levels.append( "{}-{} hours".format(hr - 6, hr) )
        if prev_bitmask is not None:
            hr = int(hours[-1]) - 6
            toa.display_levels.append( "{}-{} hours".format(0, hr) )
        
        toa.starting_datetime = self.grid.parent.release_datetimes[0]
        toa.ending_datetime = toa.starting_datetime + datetime.timedelta(hours=hours[0])
        
        return toa

class TimeOfArrival(ABC):
    
    DAY_0 = 0
    DAY_1 = 1
    DAY_2 = 2
    
    def __init__(self, parent, toa_bits):
        self.grid = parent
        self.grid.conc = numpy.zeros(toa_bits.shape, dtype=int)
        self.contour_levels = None
        self.display_levels = None
        self.fill_colors = None
    
    def has_data(self):
        return self.grid.nonzero_conc_count > 0
    
    @property
    def longitudes(self):
        return self.grid.longitudes
    
    @property
    def latitudes(self):
        return self.grid.latitudes
    
    @property
    def data(self):
        return self.grid.conc

    @abstractmethod
    def get_map_id(self, starting_dt, ending_dt):
        pass

   
class InstantaneousTimeOfArrival(TimeOfArrival):
    
    def __init__(self, parent, toa_bits):
        super(InstantaneousTimeOfArrival, self).__init__(parent, toa_bits)
        
    def get_map_id(self, starting_dt, ending_dt):
        return ending_dt.strftime("Instantaneous concentration at %H%M %d %b %Y (%Z)")

    
class IntegratedTimeOfArrival(TimeOfArrival):
    
    def __init__(self, parent, toa_bits):
        super(IntegratedTimeOfArrival, self).__init__(parent, toa_bits)
        
    def get_map_id(self, starting_dt, ending_dt):
        str = starting_dt.strftime("Integrated from %H%M %d %b to")
        str += ending_dt.strftime(" %H%M %d %b %Y (%Z)")
        return str
