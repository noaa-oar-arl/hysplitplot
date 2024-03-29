# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# cntr.py
#
# For converting matplotlib's contour data to an internal format.
# ---------------------------------------------------------------------------

import copy
import logging
import numpy
from matplotlib.path import Path
import sys

from hysplitplot import util


logger = logging.getLogger(__name__)


class ContourSet:

    def __init__(self):
        self.contours = []
        self.contour_orders = []
        self.min_concentration = 0
        self.max_concentration = 0
        self.min_concentration_str = "0"
        self.max_concentration_str = "0"
        self.time_of_arrivals = None

    def has_contour_lines(self):
        for x in self.contours:
           if x.has_contour_lines():
              return True
        return False


class Contour:

    def __init__(self, contour_set):
        self.parent = contour_set
        self.polygons = []
        self.raw_color = None
        self.color = None
        self.level = None
        self.level_str = None
        self.label = None
        self.concentration_unit = ""

    def has_contour_lines(self):
        for x in self.polygons:
           if x.has_contour_lines():
              return True
        return False
   
    def clone(self):
       o = Contour(self.parent)
       for p in self.polygons:
          o.polygons.append(p.clone())
       o.raw_color = self.raw_color
       o.color = self.color
       o.level = self.level
       o.level_str = self.level_str
       o.label = self.label
       o.concentration_unit = self.concentration_unit
       return o


class Polygon:

    def __init__(self, contour):
        self.parent = contour
        self.boundaries = []

    def has_contour_lines(self):
        for x in self.boundaries:
           if x.has_contour_lines():
              return True
        return False

    def clone(self):
        o = Polygon(self.parent)
        for b in self.boundaries:
           o.boundaries.append(b.clone())
        return o


class Boundary:

    def __init__(self, polygon):
        self.parent = polygon
        self.hole = False       # It is hole if points are ordered clockwise.
        self.longitudes = []
        self.latitudes = []

    def has_contour_lines(self):
        if len(self.latitudes) == 0:
           return False
        return True

    def clone(self):
        o = Boundary(self.parent)
        o.hole = self.hole
        o.longitudes = self.longitudes.copy()
        o.latitudes = self.latitudes.copy()
        return o

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
            if util.is_crossing_date_line(lons[k-1], lons[k]):
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


def _reduce_points(path, min_pts=5000, step=5):
    if len(path) > min_pts:
        logger.warning("More than %d points: keeping only 1 out of %d "
                       "points", min_pts, step)
        return path[0::step]
    return path


def convert_matplotlib_quadcontourset(quadContourSet):
    contour_set = ContourSet()

    if quadContourSet is not None:
        logger.debug(f'quadContourSet.levels {quadContourSet.levels}, '
                     f'colors {quadContourSet.colors}, '
                     f'allsegs len {len(quadContourSet.allsegs)}')
        for k, segs in enumerate(quadContourSet.allsegs):
            contour = Contour(contour_set)
            contour.color = quadContourSet.colors[k]
            contour.level = quadContourSet.levels[k]
            contour_set.contours.append(contour)
            contour_set.contour_orders.append(k)
            for j, seg in enumerate(segs):
                polygon = Polygon(contour)
                contour.polygons.append(polygon)
                # separate boundaries
                codes = quadContourSet.allkinds[k][j]
                paths = _separate_paths(seg, codes, Path.MOVETO)
                for path in paths:
                    boundary = Boundary(polygon)
                    polygon.boundaries.append(boundary)
                    lonlats = _reduce_points(path)
                    boundary.copy_with_dateline_crossing_fix(lonlats)
                    if boundary.compute_area() < 0:
                        boundary.hole = True
                    else:
                        boundary.hole = False

    return contour_set


def convert_matplotlib_rectangle_collections(rect_colls):
    contour_set = ContourSet()
    
    if rect_colls is not None:
        for k, coll in enumerate(rect_colls):
            contour = Contour(contour_set)
            contour_set.contours.append(contour)
            contour_set.contour_orders.append(k)
            polygon = Polygon(contour)
            contour.polygons.append(polygon)
            for r in coll:
                x0, y0 = r.get_xy()
                w = r.get_width()
                h = r.get_height()
                boundary = Boundary(polygon)
                polygon.boundaries.append(boundary)
                lonlats = [[x0 + w, y0], [x0, y0], [x0, y0 + h], [x0 + w, y0 + h], [x0 + w, y0]]
                boundary.copy_with_dateline_crossing_fix(lonlats)
                boundary.hole = False
    
    return contour_set
