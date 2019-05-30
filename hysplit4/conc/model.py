import logging
import datetime
import struct
import numpy

from hysplit4 import const


logger = logging.getLogger(__name__)


class ConcentrationDump:
    
    def __init__(self):
        self.meteo_model = None    # meteorological model identification
        self.meteo_starting_datetime = None
        self.meteo_forecast_hour = 0
        self.release_datetime = []
        self.release_locs = []
        self.release_heights = []
        self.grid_deltas = None     # (dlon, dlat)
        self.grid_loc = None        # grid lower left corner (lon, lat)
        self.grid_sz = None
        self.vert_levels = []
        self.pollutants = []
        self.conc_grids = []        # index by pollutants
        self.__latitudes = []
        self.__longitudes = []
        
        return
    
    def get_reader(self):
        return ConcentrationDumpFileReader(self)
    
    def dump(self, stream):
        stream.write("----- begin ConcentrationDump\n")
        for k, v in self.__dict__.items():
            stream.write("{0} = {1}\n".format(k, v))

        for g in self.conc_grids:
            g.dump(stream)
        
        stream.write("----- end ConcentrationDump\n")
 
    def get_unique_start_locations(self):
        all = self.release_locs
        return all if len(all) == 0 else list(set(all))
    
    def get_unique_start_levels(self):
        all = self.release_heights
        return all if len(all) == 0 else list(set(all))
    
    def get_pollutant(self, pollutant_index):
        return "SUM" if pollutant_index < 0 else self.pollutants[pollutant_index]
    
    def find_conc_grids_by_pollutant(self, name):
        return list(filter(lambda g: g.pollutant == name, self.conc_grids))
        
    def find_conc_grids_by_pollutant_index(self, index):
        if index == -1:
            # The index value of -1 indicates all pollutants are selected.
            return self.conc_grids
        
        return self.find_conc_grids_by_pollutant(self.pollutants[index])

    def find_conc_grids_by_time_index(self, index):
        return list(filter(lambda g: g.time_index == index, self.conc_grids))
    
    @property
    def latitudes(self):
        return self.__latitudes
 
    @latitudes.setter
    def latitudes(self, lats):
        self.__latitudes = lats
           
    @property
    def longitudes(self):
        return self.__longitudes

    @longitudes.setter
    def longitudes(self, lons):
        self.__longitudes = lons
        
        
class ConcentrationGrid:
    
    def __init__(self, parent):
        self.parent = parent
        self.time_index = -1
        self.pollutant_index = -1
        self.vert_level_index = -1
        self.pollutant = None       # name of the pollutant
        self.vert_level = 0         # height in meters above ground
        self.starting_datetime = None
        self.ending_datetime = None
        self.starting_forecast_hr = 0
        self.ending_forecast_hr = 0
        self.__conc = None            # conc[lon_index, lat_index]
    
    def dump(self, stream):
        stream.write("conc grid: pollutant {0}, level {1}, start {2}, end {3}, grid {4}\n".format(
            self.pollutant, self.vert_level, self.starting_datetime, self.ending_datetime,
            self.conc))
    
    def is_forward_calculation(self):
        return True if self.starting_datetime <= self.ending_datetime else False
           
    @property
    def conc(self):
        return self.__conc

    @conc.setter
    def conc(self, c):
        self.__conc = c
        
    @property
    def latitudes(self):
        return self.parent.latitudes
    
    @property
    def longitudes(self):
        return self.parent.longitudes
    
    def copy_properties_except_conc(self, o):
        self.parent = o.parent
        self.time_index = o.time_index
        self.pollutant_index = o.pollutant_index
        self.vert_level_index = o.vert_level_index
        self.pollutant = o.pollutant # name of the pollutant
        self.vert_level = o.vert_level         # height in meters above ground
        self.starting_datetime = o.starting_datetime
        self.ending_datetime = o.ending_datetime
        self.starting_forecast_hr = o.starting_forecast_hr
        self.ending_forecast_hr = o.ending_forecast_hr
    
    def repair_pollutant(self, pollutant_index):
        self.pollutant_index = pollutant_index
        self.pollutant = self.parent.get_pollutant(pollutant_index)

    def get_duration_in_sec(self):
        d = self.ending_datetime - self.starting_datetime
        return d.total_seconds()
        
class ConcentrationDumpFileReader:
    
    def __init__(self, conc_dump):
        self.conc_dump = conc_dump
        
    def read(self, filename):
        cdump = self.conc_dump
     
        str_code = "utf-8"  # byte to string
        
        # 16 repeitions of hhf
        chunk_sz = 16
        pre = struct.Struct(">hhfhhfhhfhhfhhfhhfhhfhhfhhfhhfhhfhhfhhfhhfhhfhhf")
        
        pollutant_dict = dict() # to map a pollutant to its array index
        level_dict = dict()     # to map a level to its array index

        current_time_index = 0
        
        cur = 0
        with open(filename, "rb") as f:
            buff = f.read()
            buffsz = len(buff)
            logger.debug("buffer size %d", buffsz)
    
            cur += 4
            v = struct.unpack_from('>4siiiiiii', buff, cur); cur += 36;
            cdump.meteo_model = v[0].decode(str_code)
            cdump.meteo_starting_datetime = datetime.datetime(v[1], v[2], v[3], v[4])
            cdump.meteo_forecast_hour = v[5]
            logger.debug("starting location count %d", v[6]);
            logger.debug("packing flag %d", v[7])
            start_loc_count = v[6]
            packing_flag = v[7]
    
            for k in range(start_loc_count):
                cur += 4;
                v = struct.unpack_from('>iiiifffi', buff, cur); cur += 36;
                cdump.release_datetime.append(datetime.datetime(v[0], v[1], v[2], v[3], v[7]));
                cdump.release_locs.append((v[5], v[4]))
                cdump.release_heights.append(v[6])
    
            cur += 4
            v = struct.unpack_from('>iiffff', buff, cur); cur += 28;
            logger.debug("lat/lon point counts %d, %d", v[0], v[1])
            lat_cnt = v[0]
            lon_cnt = v[1]
            cdump.grid_sz = (v[1], v[0])
            cdump.grid_deltas = (v[3], v[2])
            cdump.grid_loc = (v[5], v[4])
            cdump.longitudes = [k * cdump.grid_deltas[0] + cdump.grid_loc[0] for k in range(cdump.grid_sz[0])]
            cdump.latitudes = [k * cdump.grid_deltas[1] + cdump.grid_loc[1] for k in range(cdump.grid_sz[1])]
    
            cur += 4
            v = struct.unpack_from('>i', buff, cur); cur += 4;
            logger.debug("conc grid vertical levels %d", v[0])
            vert_level_count = v[0]
            for k in range(vert_level_count):
                v = struct.unpack_from('>i', buff, cur); cur += 4;
                cdump.vert_levels.append(v[0])
                level_dict[v[0]] = k
            cur += 4
            logger.debug("vertical levels %s", cdump.vert_levels)
            
            cur += 4
            v = struct.unpack_from('>i', buff, cur); cur += 4;
            logger.debug("pollutants %d", v[0])
            pollutant_count = v[0]
            for k in range(pollutant_count):
                v = struct.unpack_from('>4s', buff, cur); cur += 4;
                str = v[0].decode(str_code)
                cdump.pollutants.append(str)
                pollutant_dict[str] = k
            cur += 4
            logger.debug("pollutants %s", cdump.pollutants)
    
            while cur < buffsz:
                cur += 4;
                v = struct.unpack_from('>iiiiii', buff, cur); cur += 28;
                sample_start_time = datetime.datetime(v[0], v[1], v[2], v[3], v[4])
                sample_start_forecast = v[5]
        
                cur += 4;
                v = struct.unpack_from('>iiiiii', buff, cur); cur += 28;
                sample_end_time = datetime.datetime(v[0], v[1], v[2], v[3], v[4])
                sample_end_forecast = v[5]
        
                for p_idx in range(pollutant_count):
                    for l_idx in range(vert_level_count):
                        cg = ConcentrationGrid(cdump)
                        cdump.conc_grids.append(cg)
                        
                        cg.time_index = current_time_index
                        cg.starting_datetime = sample_start_time
                        cg.ending_datetime = sample_end_time
                        cg.starting_forecast_hr = sample_start_forecast
                        cg.ending_forecast_hr = sample_end_forecast
                        
                        cur += 4;
                        v = struct.unpack_from('>4si', buff, cur); cur += 8;
                        cg.pollutant = v[0].decode(str_code)
                        cg.vert_level = v[1]
                        cg.pollutant_index = pollutant_dict[cg.pollutant]
                        cg.vert_level_index = level_dict[v[1]]
                        logger.debug("grid for pollutant %s, height %d", cg.pollutant, cg.vert_level)
            
                        if packing_flag == 0:
                            count = lon_cnt * lat_cnt
                            fmt = ">{0}f".format(count)
                            v = struct.unpack_from(fmt, buff, cur); cur += 4 * count
                            cg.conc = numpy.array(v).reshape(lon_cnt, lat_cnt)
                        else:
                            cg.conc = numpy.zeros((lon_cnt, lat_cnt))
                            v = struct.unpack_from('>i', buff, cur); cur += 4;
                            count = v[0]
                            chunk = int(count / chunk_sz)
                            for k in range(chunk):
                                v = pre.unpack_from(buff, cur); cur += 8 * chunk_sz;
                                for j in range(chunk_sz):
                                    i = (j << 1) + j
                                    cg.conc[v[i+1]-1, v[i]-1] = v[i+2]
                            left = count % chunk_sz
                            if left > 0:
                                for k in range(left):
                                    v = struct.unpack_from('>hhf', buff, cur); cur += 8;
                                    cg.conc[v[1]-1, v[0]-1] = v[2]
                        cur += 4;
                        
                current_time_index += 1
                
        return self.conc_dump
    
# TODO: better be split to LazyGridFilter and GridCopier
class LazyGridFilter:
    
    def __init__(self, cdump, time_index, pollutant_selector):
        self.cdump = cdump
        self.time_index = time_index
        self.pollutant_selector = pollutant_selector
        self.grids = None
    
    def _fetch(self):
        self.grids = self.filter_grids(self.cdump, self.time_index, self.pollutant_selector)
        return self.grids

    def __iter__(self):
        if self.grids is None:
            self._fetch()
            
        return iter(self.grids)
    
    def __getitem__(self, key):
        if self.grids is None:
            self._fetch()

        return self.grids[key]

    @staticmethod
    def filter_grids(cdump, time_index, pollutant_selector):
        grids = [ConcentrationGrid(cdump) for level in cdump.vert_levels]

        for k, level in enumerate(cdump.vert_levels):
            # filtering function
            fn = lambda g: \
                    g.time_index == time_index and \
                    g.vert_level_index == k and \
                    g.pollutant_index in pollutant_selector
            
            # summation across pollutants at a vertical level
            firstQ = True
            for g in list(filter(fn, cdump.conc_grids)):
                if firstQ:
                    grids[k].copy_properties_except_conc(g)
                    grids[k].repair_pollutant(pollutant_selector.index)
                    grids[k].conc = numpy.copy(g.conc)
                    firstQ = False
                else:
                    grids[k].conc += g.conc

        return grids


class GridSelector:
    
    def __init__(self):
        return

    def is_selected(self, conc_grid):
        return True


class VerticalLevelSelector(GridSelector):
    
    def __init__(self, level_min, level_max):
        GridSelector.__init__(self)
        self.__min = level_min  # level in meters
        self.__max = level_max  # level in meters

    def __contains__(self, level):
        return True if (level >= self.__min and level <= self.__max) else False
 
    def is_selected(self, conc_grid):
        return self.__contains__(conc_grid.vert_level)

    @property
    def min(self):
        return self.__min
    
    @property
    def max(self):
        return self.__max
   

class TimeIndexSelector(GridSelector):
    
    def __init__(self, first_index=0, last_index=99999, step=1):
        GridSelector.__init__(self)
        self.__min = first_index
        self.__max = last_index
        self.step = step
 
    def __iter__(self):
        return iter(range(self.first, self.last + 1, self.step))
 
    def __contains__(self, time_index):
        return True if (time_index >= self.__min and time_index <= self.__max) else False
       
    def is_selected(self, conc_grid):
        return self.__contains__(conc_grid.time_index)
    
    @property
    def first(self):
        return self.__min
    
    @property
    def last(self):
        return self.__max    

    def normalize(self, max_index):
        self.__max = min(self.__max, max_index)
        self.__min = max(0, self.__min)
    
        
class PollutantSelector(GridSelector):
    
    def __init__(self, pollutant_index=-1):
        GridSelector.__init__(self)
        self.__index = pollutant_index
    
    def __contains__(self, pollutant_index):
        return True if (self.__index < 0 or self.__index == pollutant_index) else False

    def is_selected(self, conc_grid):
        return self.__contains__(conc_grid.pollutant_index)
    
    @property
    def index(self):
        return self.__index
    
    def normalize(self, max_index):
        if self.__index > max_index:
            self.__index = max_index
        if self.__index < -1:
            self.__index = -1
