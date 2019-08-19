# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_cntr.py
#
# Performs unit tests on functions and class methods declared in conc/cntr.py.
# ---------------------------------------------------------------------------

import datetime
import logging
import matplotlib.pyplot as plt
import os
import pytest

from hysplitdata.conc import model
from hysplitplot import const
from hysplitplot.conc import cntr


logger = logging.getLogger(__name__)


@pytest.fixture
def cdump_two_pollutants():
    return model.ConcentrationDump().get_reader().read("data/cdump_two_pollutants")
    

def test_ContourSet___init__():
    o = cntr.ContourSet()
    assert hasattr(o, "raw_colors")
    assert hasattr(o, "colors")
    assert hasattr(o, "levels")
    assert hasattr(o, "levels_str")
    assert hasattr(o, "labels")
    assert hasattr(o, "contours")
    assert hasattr(o, "contour_orders")
    assert hasattr(o, "concentration_unit")
    assert hasattr(o, "min_concentration")
    assert hasattr(o, "max_concentration")
    assert hasattr(o, "min_concentration_str")
    assert hasattr(o, "max_concentration_str")
    assert hasattr(o, "time_of_arrivals") and o.time_of_arrivals is None


def test_Contour___init__():
    cs = cntr.ContourSet()
    o = cntr.Contour(cs)
    assert o.parent is cs
    assert hasattr(o, "polygons")


def test_Polygon___init__():
    cs = cntr.ContourSet()
    c = cntr.Contour(cs)
    o = cntr.Polygon(c)
    assert o.parent is c
    assert hasattr(o, "boundaries")


def test_Boundary___init__():
    cs = cntr.ContourSet()
    c = cntr.Contour(cs)
    p = cntr.Polygon(c)
    o = cntr.Boundary(p)
    assert o.parent is p
    assert hasattr(o, "hole")
    assert hasattr(o, "longitudes")
    assert hasattr(o, "latitudes")
    
    
def test_Boundary_copy_with_dateline_crossing_fix():
    cs = cntr.ContourSet()
    c = cntr.Contour(cs)
    p = cntr.Polygon(c)
    o = cntr.Boundary(p)
    
    o.copy_with_dateline_crossing_fix( [(0,0), (1,1.1), (2,2), (0,0)] )
    assert o.longitudes == pytest.approx( (0, 1, 2, 0) )
    assert o.latitudes == pytest.approx( (0, 1.1, 2, 0) )
    
    o.copy_with_dateline_crossing_fix( [(170,0), (175,1.1), (-185,2), (-190,0)] )
    assert o.longitudes == pytest.approx( (170, 175, 175, 170) )
    assert o.latitudes == pytest.approx( (0, 1.1, 2, 0) )
    

def test_Boundary__crossing_date_line():
    lons = [170, 175, -185, -190]
    assert cntr.Boundary._crossing_date_line(lons) == True
    
    lons = [170, 175, 177, 178]
    assert cntr.Boundary._crossing_date_line(lons) == False   
 

def test_compute_area():
    cs = cntr.ContourSet()
    c = cntr.Contour(cs)
    p = cntr.Polygon(c)
    o = cntr.Boundary(p)
    o.longitudes = [0, 1, 1, 0, 0]
    o.latitudes = [0, 0, 1, 1, 0]
    assert o.compute_area() == pytest.approx(1.0)
    
    
def test_Boundary__compute_polygon_area():
    # clockwise, area < 0
    x = [0, 0, 1, 1, 0]
    y = [0, 1, 1, 0, 0]
    area = cntr.Boundary._compute_polygon_area(x, y)
    assert area == pytest.approx(-1.0)
    
    # counterclockwise, area > 0
    x = [0, 1, 1, 0, 0]
    y = [0, 0, 1, 1, 0]
    area = cntr.Boundary._compute_polygon_area(x, y)
    assert area == pytest.approx(1.0)
   
    
def test__separate_paths():
    path_codes = [1, 2, 2, 79]
    seg = [(0,0), (1,1), (2,2), (0,0)]
    
    paths = cntr._separate_paths(seg, path_codes, 1)

    assert paths == [ [(0,0), (1,1), (2,2), (0,0)] ]
    
    path_codes = [1, 2, 2, 79, 1, 2, 2, 79]
    seg = [(0,0), (1,1), (2,2), (0,0), (5,5), (6,6), (7,7), (5,5)]
    
    paths = cntr._separate_paths(seg, path_codes, 1)

    assert paths == [ [(0,0), (1,1), (2,2), (0,0)], [(5,5), (6,6), (7,7), (5,5)] ]


def test__reduce_points():
    pts = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    # expect no reduction
    a = cntr._reduce_points(pts)
    assert len(a) == 11
    
    # expect reduction in the number of points
    a = cntr._reduce_points(pts, 10)
    assert len(a) == 3
    assert a[0] == 0
    assert a[1] == 5
    assert a[2] == 10
    
    a = cntr._reduce_points(pts, 10, 2)
    assert len(a) == 6
    assert a[0] == 0
    assert a[1] == 2
    assert a[2] == 4
    assert a[5] == 10


def test_convert_matplotlib_quadcontourset(cdump_two_pollutants):
    g = cdump_two_pollutants.grids[0]
    
    ax = plt.axes()
    quad_contour_set = plt.contourf(g.longitudes, g.latitudes, g.conc,
                                    [1.0e-15, 1.0e-12],
                                    colors=["#ff0000", "#00ff00"],
                                    extend="max")
    plt.close(ax.figure)
    
    contour_set = cntr.convert_matplotlib_quadcontourset(quad_contour_set)
    
    assert len(contour_set.contours) == 2
    assert len(contour_set.contour_orders) == 2
    assert contour_set.contour_orders == pytest.approx( [0, 1] )
    assert len(contour_set.contours[0].polygons) == 11
    assert len(contour_set.contours[0].polygons[0].boundaries) == 29
    
    b = contour_set.contours[0].polygons[0].boundaries[0]
    assert len(b.longitudes) == 421
    assert len(b.latitudes) == 421
    assert b.hole == False
    assert b.longitudes[0] == pytest.approx(-84.22)
    
    
    
