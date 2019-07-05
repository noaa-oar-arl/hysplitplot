import logging
import copy
import numpy
from matplotlib.path import Path


logger = logging.getLogger(__name__)


class ContourSet:
    
    def __init__(self):
        self.raw_colors = []
        self.colors = []
        self.levels = []
        self.labels = []
        self.contours = []
        self.concentration_unit = ""
        self.min_concentration = 0
        self.max_concentration = 0
        self.min_concentration_str = "0"
        self.max_concentration_str = "0"


class Contour:
    
    def __init__(self, contour_set):
        self.parent = contour_set
        self.polygons = []
        

class Polygon:
    
    def __init__(self, contour):
        self.parent = contour
        self.boundaries = []
        
        
class Boundary:
    
    def __init__(self, polygon):
        self.parent = polygon
        self.hole = False       # It is hole if points are ordered clockwise.
        self.longitudes = []
        self.latitudes = []

    def copy_with_dateline_crossing_fix(self, lonlats):
        lons, lats = numpy.transpose(lonlats)
        
        if self._crossing_date_line(lons):
            self.longitudes = [(v if v >= 0 else v + 360.0) for v in lons]
        else:
            self.longitudes = copy.deepcopy(lons)
        self.latitudes = copy.deepcopy(lats)
        
    @staticmethod
    def _crossing_date_line(lons):
        for k in range(1, len(lons)):
            if lons[k] < -180.0 and lons[k-1] > 0:
                return True
            
        return False
           
    def compute_area(self):
        return self._compute_polygon_area(self.longitudes, self.latitudes)
    
    @staticmethod
    def _compute_polygon_area(lons, lats):
        area = 0.0
        
        n = len(lons)
        if n == len(lats) and n > 0:
            area = (lons[0] + lons[-1]) * (lats[0] - lats[-1])
            for k in range(1, n):
                area += (lons[k] + lons[k-1]) * (lats[k] - lats[k-1])
            
            if lons[-1] != lons[0] or lats[-1] != lats[0]:
                area += (lons[0] + lons[-1]) * (lats[0] - lats[-1])
                
        return 0.5 * area


def _separate_paths(seg, path_codes, separator_code):
    head = [k for k, c in enumerate(path_codes) if c == separator_code]
    
    tail = copy.deepcopy(head)
    tail.append(len(path_codes))
    tail.pop(0)
    
    paths = []
    for h, t in zip(head, tail):
        paths.append(seg[h:t])
        
    return paths


def convert_matplotlib_quadcontourset(quadContourSet):
    contour_set = ContourSet()
    
    if quadContourSet is not None:
        for k, segs in enumerate(quadContourSet.allsegs):
            contour = Contour(contour_set)
            contour_set.contours.append(contour)
            for j, seg in enumerate(segs):
                polygon = Polygon(contour)
                contour.polygons.append(polygon)
                # separate boundaries
                codes = quadContourSet.allkinds[k][j]
                paths = _separate_paths(seg, codes, Path.MOVETO)
                for path in paths:
                    boundary = Boundary(polygon)
                    polygon.boundaries.append(boundary)
                    boundary.copy_with_dateline_crossing_fix(path)
                    boundary.hole = True if boundary.compute_area() < 0 else False
                    
    return contour_set