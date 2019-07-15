import abc
import logging
import math
import numpy
import os
import sys

from hysplitdata.const import HeightUnit
from hysplitplot import const


logger = logging.getLogger(__name__)


def run(mainFunction, programName):
    """Provides a common main entry point.

    Initializes a logger, prints banner, calls the main function, and exits
    with a code returned by the main function.

    :param mainFunction: main function to be executed. It should return an integer.
    :param programName: program name.
    """
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s"
    )

    logging.info("This is {0}.".format(programName))

    exitCode = mainFunction()
    logging.info("exiting with code [{0}]".format(exitCode))

    sys.exit(exitCode)

def myzip(xlist, ylist):
    if sys.version_info[0] >= 3:
        # Python 3 or later
        return list(zip(xlist, ylist))
    else:
        # Python 1 and 2
        return zip(xlist, ylist)

def convert_int_to_bool(val):
    # limit the integer value to 0 or 1 for historical reasons.
    return False if max(0, min(1, int(val))) == 0 else True

def sign(a, b):
    return abs(a) if b >= 0 else -abs(a)

def nearest_int(a):
    return int(round(a))

def make_color(r, g, b):
    ir = nearest_int(r*255)
    ig = nearest_int(g*255)
    ib = nearest_int(b*255)
    return "#{:02x}{:02x}{:02x}".format(ir, ig, ib)

def make_int_if_same(a):
    ia = int(a)
    return ia if float(ia) == a else a

def is_valid_lonlat(ll):
    lon, lat = ll
    return False if lon == 99.0 and lat == 99.0 else True

def union_ranges(a, b):
    if a == None or len(a) == 0:
        return b
    elif b == None or len(b) == 0:
        return a
    else:
        amin = min(a[0], b[0])
        amax = max(a[1], b[1])
        return [amin, amax]

def make_file_list(input_endpoints):
    files = []

    if input_endpoints[0:1] == "+":
        list_file = input_endpoints[1:]
        if os.path.exists(list_file):
            with open(input_endpoints[1:], "r") as f:
                try:
                    for line in f:
                        files.append(line.rstrip())
                    f.close()
                except:
                    raise Exception("FATAL ERROR - Cannot read file: {0}".format(list_file))
        else:
            raise Exception("FATAL ERROR - File not found: {0}".format(list_file))
    elif input_endpoints.count("+"):
        files = input_endpoints.split("+")
    else:
        files.append(input_endpoints)

    return files

def normalize_output_filename(pathname, ext="ps"):
    n, x = os.path.splitext(pathname)

    if ext == "ps":  # still default
        if len(x) > 1:
            ext = x[1:]  # skip the dot

    return n + "." + ext, n, ext
    
def get_iso_8601_str(dt, time_zone=None):
    t = dt if time_zone is None else dt.astimezone(time_zone)
    if t.tzinfo is None or t.tzinfo.utcoffset(t).total_seconds() == 0:
        return t.strftime("%Y-%m-%dT%H:%M:%SZ")
    return t.strftime("%Y-%m-%dT%H:%M:%S%z")
    
def calc_ring_distance(ext_sz, grid_delta, center_loc, ring_number, ring_distance):
    ext_lon, ext_lat = ext_sz
    if ring_distance == 0.0:
        # max radius extent adjusted for latitude
        logger.debug("QLON %f, HLAT %f", ext_lon, center_loc[1])
        ext_lon = ext_lon * math.cos(center_loc[1] / 57.3)
        kspan = nearest_int(math.sqrt(ext_lon*ext_lon + ext_lat*ext_lat))
        # circle distance interval in km
        ring_distance = 111.0 * grid_delta * kspan / max(ring_number, 1)
    else:
        kspan = nearest_int(ring_distance * max(ring_number,1) / (111.0 * grid_delta))
    logger.debug("lon %f, lat %f, delta %f, kspan %d", ext_lon, ext_lat, grid_delta, kspan)

    if ring_distance <= 10.0:
        ring_distance = int(ring_distance) * 1.0
    elif ring_distance <= 100.0:
        ring_distance = int(ring_distance/10.0) * 10.0
    else:
        ring_distance = int(ring_distance/100.0) * 100.0

    return kspan, ring_distance

def nonzero_min(a):
    if numpy.count_nonzero(a) == 0:
        return None
    
    return numpy.min(numpy.ma.masked_where(a==0, a))


class AbstractLengthFactory():
    
    @staticmethod
    def create_factory(len_unit):
        if len_unit == HeightUnit.METERS:
            return LengthInMetersFactory()
        elif len_unit == HeightUnit.FEET:
            return LengthInFeetFactory()
        else:
            raise Exception("unknown length unit type {0}".format(len_unit))
        
    @abc.abstractmethod
    def create_instance(self, v, unit):
        """Returns a concrete factory for length instances."""
        
        
class LengthInMetersFactory():
    
    def create_instance(self, v, unit=HeightUnit.METERS):
        if unit == HeightUnit.FEET:
            v *= 0.3048
            
        return LengthInMeters(v)
    

class LengthInFeetFactory():
    
    def create_instance(self, v, unit=HeightUnit.METERS):
        if unit == HeightUnit.METERS:
            v *= 3.28084
            
        return LengthInFeet(v)
    

class LengthInMeters():
    
    def __init__(self, v, truncated=True):
        self.v = v
        self.truncated = truncated
        
    def __repr__(self):
        return "{0} m".format(nearest_int(self.v)) if self.truncated else "{0:.1f} m".format(self.v)
    

class LengthInFeet():
    
    def __init__(self, v, truncated=True):
        self.v = v
        self.truncated = truncated
        
    def __repr__(self):
        return "{0} ft".format(nearest_int(self.v)) if self.truncated else "{0:.1f} ft".format(self.v)