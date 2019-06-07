import logging
import datetime
import struct
import numpy
import copy

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
        self.grids = []        # orderred first by pollutants and then by vertical levels
        self.__latitudes = []
        self.__longitudes = []
        
        return
    
    def get_reader(self):
        return ConcentrationDumpFileReader(self)
    
    def dump(self, stream):
        stream.write("----- begin ConcentrationDump\n")
        for k, v in self.__dict__.items():
            stream.write("{0} = {1}\n".format(k, v))

        for g in self.grids:
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
        self.pollutant = None           # name of the pollutant
        self.vert_level = 0             # height in meters above ground
        self.starting_datetime = None
        self.ending_datetime = None
        self.starting_forecast_hr = 0
        self.ending_forecast_hr = 0
        self.__conc = None              # conc[lat_index, lon_index]
        self.nonzero_conc_count = None  # number of non-zero conc. values. None if no counting was done.
        self.extension = None           # for extending the data structure

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
    
    def clone(self, deep_copy_conc=True):
        o = ConcentrationGrid(self.parent)
        o.time_index = self.time_index
        o.pollutant_index = self.pollutant_index
        o.vert_level_index = self.vert_level_index
        o.pollutant = self.pollutant
        o.vert_level = self.vert_level
        o.starting_datetime = copy.deepcopy(self.starting_datetime)
        o.ending_datetime = copy.deepcopy(self.ending_datetime)
        o.starting_forecast_hr = self.starting_forecast_hr
        o.ending_forecast_hr = self.ending_forecast_hr
        o.conc = copy.deepcopy(self.conc)
        o.nonzero_conc_count = self.nonzero_conc_count
        o.extension = None if self.extension is None else self.extension.clone()
        return o
    
    def clone_except_conc(self):
        o = self.clone(False)
        return o
    
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
                        g = ConcentrationGrid(cdump)
                        cdump.grids.append(g)
                        
                        g.time_index = current_time_index
                        g.starting_datetime = sample_start_time
                        g.ending_datetime = sample_end_time
                        g.starting_forecast_hr = sample_start_forecast
                        g.ending_forecast_hr = sample_end_forecast
                        
                        cur += 4;
                        v = struct.unpack_from('>4si', buff, cur); cur += 8;
                        g.pollutant = v[0].decode(str_code)
                        g.vert_level = v[1]
                        g.pollutant_index = pollutant_dict[g.pollutant]
                        g.vert_level_index = level_dict[v[1]]
                        logger.debug("grid for pollutant %s, height %d", g.pollutant, g.vert_level)
            
                        if packing_flag == 0:
                            count = lon_cnt * lat_cnt
                            fmt = ">{0}f".format(count)
                            v = struct.unpack_from(fmt, buff, cur); cur += 4 * count
                            # TODO: test this line. may need to transpose it.
                            g.conc = numpy.array(v).reshape(lat_cnt, lon_cnt)
                        else:
                            g.conc = numpy.zeros((lat_cnt, lon_cnt))
                            v = struct.unpack_from('>i', buff, cur); cur += 4;
                            g.nonzero_conc_count = count = v[0]
                            chunk = int(count / chunk_sz)
                            for k in range(chunk):
                                v = pre.unpack_from(buff, cur); cur += 8 * chunk_sz;
                                for j in range(chunk_sz):
                                    i = (j << 1) + j
                                    g.conc[v[i+1]-1, v[i]-1] = v[i+2]
                            left = count % chunk_sz
                            if left > 0:
                                for k in range(left):
                                    v = struct.unpack_from('>hhf', buff, cur); cur += 8;
                                    g.conc[v[1]-1, v[0]-1] = v[2]
                        cur += 4;
                        
                current_time_index += 1
                
        return self.conc_dump
