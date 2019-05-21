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
    
class ConcentrationDumpFileReader:
    
    def __init__(self, conc_dump):
        self.conc_dump = conc_dump
        
    def read(self, filename):
        cdump = self.conc_dump
     
        str_code = "utf-8"  # byte to string
        
        # 16 repeitions of hhf
        chunk_sz = 16
        pre = struct.Struct(">hhfhhfhhfhhfhhfhhfhhfhhfhhfhhfhhfhhfhhfhhfhhfhhf")
        
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
            cur += 4
    
            cur += 4
            v = struct.unpack_from('>i', buff, cur); cur += 4;
            logger.debug("pollutants %d", v[0])
            pollutant_count = v[0]
            for k in range(pollutant_count):
                v = struct.unpack_from('>4s', buff, cur); cur += 4;
                cdump.pollutants.append(v[0].decode(str_code))
            cur += 4
    
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
                        
                        cg.starting_datetime = sample_start_time
                        cg.ending_datetime = sample_end_time
                        cg.starting_forecast_hr = sample_start_forecast
                        cg.ending_forecast_hr = sample_end_forecast
                        
                        cur += 4;
                        v = struct.unpack_from('>4si', buff, cur); cur += 8;
                        cg.pollutant = v[0].decode(str_code)
                        cg.vert_level = v[1]
            
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
                                    cg.conc[v[i+1], v[i]] = v[i+2]
                            left = count % chunk_sz
                            if left > 0:
                                for k in range(left):
                                    v = struct.unpack_from('>hhf', buff, cur); cur += 8;
                                    cg.conc[v[1], v[0]] = v[2]
                        cur += 4;

        return self.conc_dump
