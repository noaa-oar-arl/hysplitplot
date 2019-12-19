# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_mapproj.py
#
# Performs unit tests on functions and class methods declared in mapproj.py.
# ---------------------------------------------------------------------------

import cartopy.crs
import math
import numpy
import pytest

from hysplitdata.traj import model
from hysplitplot import mapproj, mapbox, const
from hysplitplot.traj import plot


def create_map_box(s):
    d = model.TrajectoryDump()
    r = model.TrajectoryDumpFileReader(d)
    r.set_end_hour_duration(s.end_hour_duration)
    r.set_vertical_coordinate(s.vertical_coordinate, s.height_unit)
    r.read("data/tdump")
    s.vertical_coordinate = r.vertical_coordinate
    
    map_box = mapbox.MapBox()
    map_box.allocate()
    for t in d.trajectories:
        map_box.add(t.starting_loc)
        lons = t.longitudes
        lats = t.latitudes
        for k in range(len(lons)):
            map_box.add((lons[k], lats[k]))
    if s.ring_number >= 0:
        map_box.determine_plume_extent()
        map_box.clear_hit_map()
        map_box.set_ring_extent(s)
    return map_box


@pytest.fixture
def lambert_proj():
    s = plot.TrajectoryPlotSettings()
    s.map_projection = const.MapProjection.LAMBERT
    s.center_loc = [-125.0, 45.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    testMapBox = create_map_box(s)
    m = mapproj.MapProjectionFactory.create_instance(s.map_projection, s.zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0], testMapBox)
    return m


# For testing the AbstractMapProjection abstract class
class AbstractMapProjectionTest(mapproj.AbstractMapProjection):
    
    def __init__(self, proj_type, zoom_factor, center_loc, scale, grid_deltas):
        super(AbstractMapProjectionTest, self).__init__(proj_type, zoom_factor, center_loc, scale, grid_deltas)
        
    def get_tangent_lat(self, center_loc):
        return 0.0
    
    def create_crs(self):
        raise Exception("This should not happen")


# For testing the PoleExcludingProjection abstract class
class PoleExcludingPorjectionTest(mapproj.PoleExcludingProjection):
    
    def __init__(self, proj_type, zoom_factor, center_loc, scale, grid_deltas):
        super(PoleExcludingPorjectionTest, self).__init__(proj_type, zoom_factor, center_loc, scale, grid_deltas)
     
    def get_tangent_lat(self, center_loc):
        pass
   
    def create_crs(self):
        pass
    
    
def test_MapProjectionFactory_create_instance():
    zoom_factor = 0.50
    
    map_box = mapbox.MapBox()
    map_box.allocate()
    map_box.add((-120.5, 45.5))
    map_box.determine_plume_extent()

    map_proj = const.MapProjection.POLAR
    m = mapproj.MapProjectionFactory.create_instance(map_proj, zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, mapproj.PolarProjection)

    map_proj = const.MapProjection.LAMBERT
    m = mapproj.MapProjectionFactory.create_instance(map_proj, zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, mapproj.LambertProjection)

    map_proj = const.MapProjection.MERCATOR
    m = mapproj.MapProjectionFactory.create_instance(map_proj, zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, mapproj.MercatorProjection)

    map_proj = const.MapProjection.CYL_EQU
    m = mapproj.MapProjectionFactory.create_instance(map_proj, zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, mapproj.CylindricalEquidistantProjection)

    map_proj = const.MapProjection.WEB_MERCATOR
    m = mapproj.MapProjectionFactory.create_instance(map_proj, zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, mapproj.WebMercatorProjection)

    # Lambert grid is not permitted to contain the poles

    # when containing the north pole
    map_box.clear_hit_map()
    map_box.add((-120.5, 89.0))
    map_box.add((-120.5, 90.0))
    map_box.determine_plume_extent()

    map_proj = const.MapProjection.LAMBERT
    m = mapproj.MapProjectionFactory.create_instance(map_proj, zoom_factor, [-125.0, 89.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, mapproj.PolarProjection)

    # when containing the south pole
    map_box.clear_hit_map()
    map_box.add((-120.5, -89.0))
    map_box.add((-120.5, -90.0))
    map_box.determine_plume_extent()
    
    map_proj = const.MapProjection.LAMBERT
    m = mapproj.MapProjectionFactory.create_instance(map_proj, zoom_factor, [-125.0, -89.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, mapproj.PolarProjection)
    
    
def test_AbstractMapProjection___init__():
    m = AbstractMapProjectionTest(const.MapProjection.AUTO, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])

    assert m.proj_type == const.MapProjection.AUTO
    assert m.zoom_factor == 0.5
    assert m.scale == 1.3
    assert m.deltas == [1.0, 1.0]

    assert m.crs == None
    assert m.crs_geodetic is not None
    assert m.center_loc == [-125.0, 45.0]
    assert m.corners_xy == None
    assert m.corners_lonlat == None
    
    assert m.reflon == -125.0
    assert m.tnglat == 0.0


def test_AbstractMapProjection_calc_xy():
    s = plot.TrajectoryPlotSettings()
    s.map_projection = const.MapProjection.LAMBERT
    s.center_loc = [-125.0, 45.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    map_box = create_map_box(s)
    m = mapproj.MapProjectionFactory.create_instance(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0], map_box)

    assert m.calc_xy(-125.0,  45.0) == pytest.approx((1000.0, 1000.0))
    assert m.calc_xy(-125.0,  91.0) == pytest.approx((1000.0, 6343095.6))
    assert m.calc_xy(-125.0,  90.0) == pytest.approx((1000.0, 6343095.6))
    
    s.center_loc = [-125.0, -45.0]
    map_box = create_map_box(s)
    m = mapproj.MapProjectionFactory.create_instance(const.MapProjection.LAMBERT, 0.5, [-125.0, -45.0], 1.3, [1.0, 1.0], map_box)
    
    assert m.calc_xy(-125.0, -45.0) == pytest.approx((1000.0, 1000.0))
    assert m.calc_xy(-125.0, -90.0) == pytest.approx((1000.0, -6341095.6))
    assert m.calc_xy(-125.0, -91.0) == pytest.approx((1000.0, -6341095.6))


def test_AbstractMapProjection_calc_lonlat():
    s = plot.TrajectoryPlotSettings()
    s.map_projection = const.MapProjection.LAMBERT
    s.center_loc = [-125.0, 45.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    map_box = create_map_box(s)
    m = mapproj.MapProjectionFactory.create_instance(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0], map_box)

    assert m.calc_lonlat(1000.0, 1000.0) == pytest.approx((-125.0, 45.0))


def test_AbstractMapProjection_determine_projection():
    k_auto = const.MapProjection.AUTO
    k_polar = const.MapProjection.POLAR
    k_lambert = const.MapProjection.LAMBERT
    k_mercator = const.MapProjection.MERCATOR
    k_cylequ = const.MapProjection.CYL_EQU

    assert mapproj.AbstractMapProjection.determine_projection(k_polar,    [-125.0, 35.0]) == k_polar
    assert mapproj.AbstractMapProjection.determine_projection(k_lambert,  [-125.0, 35.0]) == k_lambert
    assert mapproj.AbstractMapProjection.determine_projection(k_mercator, [-125.0, 35.0]) == k_mercator
    assert mapproj.AbstractMapProjection.determine_projection(k_cylequ,   [-125.0, 35.0]) == k_cylequ

    assert mapproj.AbstractMapProjection.determine_projection(k_auto, [-125.0, 35.0]) == k_lambert
    assert mapproj.AbstractMapProjection.determine_projection(k_auto, [-125.0, 65.0]) == k_polar
    assert mapproj.AbstractMapProjection.determine_projection(k_auto, [-125.0,-65.0]) == k_polar
    assert mapproj.AbstractMapProjection.determine_projection(k_auto, [-125.0, 15.0]) == k_mercator
    assert mapproj.AbstractMapProjection.determine_projection(k_auto, [-125.0, 15.0]) == k_mercator


def test_AbstractMapProjection_refine_corners__lambert():
    s = plot.TrajectoryPlotSettings()
    s.map_projection = const.MapProjection.LAMBERT
    s.center_loc = [-125.0, 45.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    testMapBox = create_map_box(s)
    
    m = mapproj.MapProjectionFactory.create_instance(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0], testMapBox)

    m.refine_corners([-125.0, 45.0])

    assert m.corners_xy == pytest.approx((-646204.00, 647521.00, -496513.00, 498660.00))
    assert m.corners_lonlat == pytest.approx((-132.6304, -116.0894, 40.22594, 49.17515))


def test_AbstractMapProjection_refine_corners__polar():
    s = plot.TrajectoryPlotSettings()
    s.map_projection = const.MapProjection.POLAR
    s.center_loc = [-125.0, 85.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    testMapBox = create_map_box(s)
    
    m = mapproj.MapProjectionFactory.create_instance(const.MapProjection.POLAR, 0.5, [-125.0, 85.0], 1.3, [1.0, 1.0], testMapBox)

    m.refine_corners([-125.0, 85.0])
    
    assert m.corners_xy[0] == pytest.approx(-436934.00)
    assert m.corners_xy[1] == pytest.approx( 435959.00)
    assert m.corners_xy[2] == pytest.approx(-894702.00)
    assert m.corners_xy[3] == pytest.approx(-223246.00)
    assert m.corners_lonlat[0] == pytest.approx(-151.028895)
    assert m.corners_lonlat[1] == pytest.approx( -62.116090)
    assert m.corners_lonlat[2] == pytest.approx(  81.102733)
    assert m.corners_lonlat[3] == pytest.approx(  85.616902)


def test_AbstractMapProjection_refine_corners__mercator():
    s = plot.TrajectoryPlotSettings()
    s.map_projection = const.MapProjection.MERCATOR
    s.center_loc = [-125.0, 45.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    testMapBox = create_map_box(s)
    m = mapproj.MapProjectionFactory.create_instance(const.MapProjection.MERCATOR, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0], testMapBox)

    m.refine_corners([-125.0, 45.0])

    assert m.corners_xy[0] == pytest.approx(-918137.00)
    assert m.corners_xy[1] == pytest.approx( 920137.00)
    assert m.corners_xy[2] == pytest.approx(4897704.00)
    assert m.corners_xy[3] == pytest.approx(6311761.00)
    assert m.corners_lonlat[0] == pytest.approx(-133.2567)
    assert m.corners_lonlat[1] == pytest.approx(-116.7432)
    assert m.corners_lonlat[2] == pytest.approx(  40.40112)
    assert m.corners_lonlat[3] == pytest.approx(  49.40126)


def test_AbstractMapProjection_refine_corners__cylequ():
    s = plot.TrajectoryPlotSettings()
    s.map_projection = const.MapProjection.CYL_EQU
    s.center_loc = [-125.0, 5.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    testMapBox = create_map_box(s)
    m = mapproj.MapProjectionFactory.create_instance(const.MapProjection.CYL_EQU, 0.5, [-125.0, 5.0], 1.3, [1.0, 1.0], testMapBox)

    m.refine_corners([-125.0, 5.0])

    assert m.corners_xy[0] == pytest.approx(-6.0)
    assert m.corners_xy[1] == pytest.approx(15.0)
    assert m.corners_xy[2] == pytest.approx( 1.0)
    assert m.corners_xy[3] == pytest.approx( 9.0)
    assert m.corners_lonlat[0] == pytest.approx(-131.0000)
    assert m.corners_lonlat[1] == pytest.approx(-110.0000)
    assert m.corners_lonlat[2] == pytest.approx(   1.006790, 1.0e-5)
    assert m.corners_lonlat[3] == pytest.approx(   9.0978273)


def test_AbstractMapProjection_validate_corners(lambert_proj):
    corners = lambert_proj.validate_corners([400.0, 600.0, 480.0, 520.0])
    assert corners == pytest.approx((400.0, 600.0, 480.0, 520.0))


def test_AbstractMapProjection_scale_per_aspect_ratio():
    s = plot.TrajectoryPlotSettings()
    m = AbstractMapProjectionTest(s.map_projection, s.zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0])
    cnr = [ 498.888000, 501.112000, 493.328094, 506.671906 ]
    cnr2 = m.scale_per_aspect_ratio(cnr, 1.3)
    assert cnr2 == pytest.approx((491.326538, 508.673462, 493.328094, 506.671906))


def test_AbstractMapProjection_choose_corners(lambert_proj):
    cnr1 = [ 498.888000, 501.112000, 493.328094, 506.671906 ]
    cnr2 = [ 491.326538, 508.673462, 493.328094, 506.671906 ]
    cnr = lambert_proj.choose_corners(cnr1, cnr2)
    assert cnr == pytest.approx(cnr1)

    lambert_proj.TOLERANCE = -1.0
    cnr = lambert_proj.choose_corners(cnr1, cnr2)
    assert cnr == pytest.approx(cnr2)


def test_AbstractMapProjection_zoom_corners():
    s = plot.TrajectoryPlotSettings()
    m = AbstractMapProjectionTest(s.map_projection, s.zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0])
    cnr = [ 491.326538, 508.673462, 493.328094, 506.671906 ]
    assert m.zoom_corners(cnr, 0.5) == pytest.approx((486.989807, 513.010193, 489.992126, 510.007874))


def test_AbstractMapProjection_round_map_corners():
    s = plot.TrajectoryPlotSettings()
    m = AbstractMapProjectionTest(s.map_projection, s.zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0])
    cnr = [486.989807, 513.010193, 489.992126, 510.007874]
    assert m.round_map_corners(cnr) == pytest.approx((487.0, 513.0, 490.0, 510.0))


def test_AbstractMapProjection_calc_corners_lonlat(lambert_proj):
    c = lambert_proj.calc_corners_lonlat([-645202.80, 248127.59, -499632.13, 248127.59])
    assert c == pytest.approx((-132.6152, -121.7225, 40.19877, 47.18976))


def test_AbstractMapProjection_need_pole_exclusion():
    s = plot.TrajectoryPlotSettings()
    m = AbstractMapProjectionTest(s.map_projection, s.zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.need_pole_exclusion([]) == False


def test_AbstractMapProjection_exclude_pole(lambert_proj):
    lonlat = (-132.642365, -116.065727, 40.2330704, 81.0)
    x1, y1 = lambert_proj.calc_xy(lonlat[0], lonlat[2])
    x2, y2 = lambert_proj.calc_xy(lonlat[1], lonlat[3])
    corners = (x1, x2, y1, y2)
    # corners = (-645202.80, 248127.59, -499632.13, 248127.59)
    xy2, ll2 = lambert_proj.exclude_pole(corners, lonlat)
    assert xy2 == pytest.approx((corners[0], 233688.20, corners[2], 4245257.96))
    assert ll2 == pytest.approx((lonlat[0], lonlat[1], lonlat[2], 80.0))

    lonlat = (-132.642365, -116.065727, -81.0, -40.2330704)
    x1, y1 = lambert_proj.calc_xy(lonlat[0], lonlat[2])
    x2, y2 = lambert_proj.calc_xy(lonlat[1], lonlat[3])
    corners = (x1, x2, y1, y2)
    # corners = (-5172737.76, 1979594.58, -54208823.32, -12894066.05)
    xy2, ll2 = lambert_proj.exclude_pole(corners, lonlat)
    assert xy2 == pytest.approx((-6225037.2, corners[1], -59349580.7, corners[3]))
    assert ll2 == pytest.approx((lonlat[0], lonlat[1], -80.0, lonlat[3]))


def test_AbstractMapProjection_do_initial_estimates():
    s = plot.TrajectoryPlotSettings()
    s.map_projection = const.MapProjection.LAMBERT
    s.center_loc = [-125.0, 45.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    map_box = create_map_box(s)
    proj = mapproj.LambertProjection(s.map_projection, s.zoom_factor, s.center_loc, 1.3, [1.0, 1.0])

    proj.do_initial_estimates(map_box, [-125.0,  45.0])
    assert proj.corners_xy == pytest.approx((-38549.362, 39866.075, -330651.037, 332797.615))
    assert proj.corners_lonlat == pytest.approx((-125.47928, -124.47701, 41.99894, 47.99887))
    assert proj.center_loc == pytest.approx((-125.00436, 45.000663))
    
    proj.do_initial_estimates(map_box, [-125.0,  91.0])
    assert proj.corners_xy == pytest.approx((-1549.1589, 2560.0334, -330651.04, 6090755.3))
    assert proj.corners_lonlat == pytest.approx((-125.0309, -124.5000, 42.00000, 89.50000))
    assert proj.center_loc == pytest.approx((-125.0116, 70.03166))
    
    s.center_loc = [-125.0, -45.0]
    map_box = create_map_box(s)
    proj.do_initial_estimates(map_box, [-125.0, -91.0])
    assert proj.corners_xy == pytest.approx((-2087174.5, 3413163.2, -331425723.2, -14878255.5))
    assert proj.corners_lonlat == pytest.approx((-125.5000, -112.1061, -89.00000, -43.75291))
    assert proj.center_loc == pytest.approx((-124.70172, -87.55922))


def test_AbstractMapProjection_sanity_check():
    m = AbstractMapProjectionTest(const.MapProjection.AUTO, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.sanity_check() == True


def test_AbstractMapProjection_create_sane_projection():
    m = AbstractMapProjectionTest(const.MapProjection.AUTO, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    try:
        m.create_sane_projection(const.MapProjection.AUTO, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "This should not happen"


def test_PoleExcludingProjection__init__():
    m = PoleExcludingPorjectionTest(const.MapProjection.AUTO, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.zoom_factor == 0.5
    assert m.proj_type == const.MapProjection.AUTO
    assert m.scale == 1.3
    assert m.deltas == pytest.approx( (1.0, 1.0) )
    assert m.center_loc == pytest.approx( (-125.0, 45.0) )


def test_PoleExcludingProjection_sanity_check(lambert_proj):
    assert lambert_proj.sanity_check() == True

    # lonlat_corners (-125.4793, -124.4770, 41.9989, 47.9989)
    llon, rlon, blat, tlat = lambert_proj.corners_lonlat
    lambert_proj.corners_lonlat = (llon, rlon, blat, 85.00)
    assert lambert_proj.sanity_check() == False


def test_PoleExcludingProjection_create_sane_projection(lambert_proj):
    m = lambert_proj
    o = lambert_proj.create_sane_projection(const.MapProjection.LAMBERT,
                                              0.5,
                                              m.center_loc,
                                              m.scale,
                                              m.deltas)
    assert isinstance(o, mapproj.PolarProjection)


def test_PoleExcludingProjection_need_pole_exclusion(lambert_proj):
    assert lambert_proj.need_pole_exclusion([-135.0, -115.0,-81.0, 55.0]) == True
    assert lambert_proj.need_pole_exclusion([-135.0, -115.0,-80.0, 55.0]) == False
    assert lambert_proj.need_pole_exclusion([-135.0, -115.0,-35.0, 55.0]) == False
    assert lambert_proj.need_pole_exclusion([-135.0, -115.0, 35.0, 55.0]) == False
    assert lambert_proj.need_pole_exclusion([-135.0, -115.0, 35.0, 80.0]) == False
    assert lambert_proj.need_pole_exclusion([-135.0, -115.0, 35.0, 80.1]) == True


def test_LambertProjection___init__():
    m = mapproj.LambertProjection(const.MapProjection.AUTO, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.zoom_factor == 0.5
    assert m.proj_type == const.MapProjection.LAMBERT
    assert isinstance(m.crs, cartopy.crs.LambertConformal)


def test_LambertProjection_get_tangent_lat():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.LambertProjection(const.MapProjection.AUTO, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.get_tangent_lat([-125.0, 45.0]) ==  45.0
    assert m.get_tangent_lat([-125.0,  0.0]) ==   0.0
    assert m.get_tangent_lat([-125.0, -1.0]) ==  -1.0
 

def test_LambertProjection_create_crs(lambert_proj):
    o = lambert_proj.create_crs()
    assert isinstance(o, cartopy.crs.LambertConformal)


def test_PolarProjection___init__():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.PolarProjection(s.map_projection, s.zoom_factor, [-125.0, 85.0], 1.3, [1.0, 1.0])
    assert m.proj_type == const.MapProjection.POLAR
    assert isinstance(m.crs, cartopy.crs.NorthPolarStereo)


def test_PolarProjection_get_tangent_lat():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.PolarProjection(s.map_projection, s.zoom_factor, [-125.0, 85.0], 1.3, [1.0, 1.0])
    assert m.get_tangent_lat([-125.0, 45.0]) ==  90.0
    assert m.get_tangent_lat([-125.0,  0.0]) ==  90.0
    assert m.get_tangent_lat([-125.0, -1.0]) == -90.0
 

def test_PolarProjection_create_crs():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.PolarProjection(s.map_projection, s.zoom_factor, [-125.0, 85.0], 1.3, [1.0, 1.0])
    o = m.create_crs()
    assert isinstance(o, cartopy.crs.NorthPolarStereo)

    m = mapproj.PolarProjection(s.map_projection, s.zoom_factor, [-125.0, -85.0], 1.3, [1.0, 1.0])
    o = m.create_crs()
    assert isinstance(o, cartopy.crs.SouthPolarStereo)


def test_MercatorProjection___init__():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.MercatorProjection(s.map_projection, s.zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.proj_type == const.MapProjection.MERCATOR
    assert isinstance(m.crs, cartopy.crs.Mercator)


def test_MercatorProjection_get_tangent_lat():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.MercatorProjection(s.map_projection, s.zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.get_tangent_lat([-125.0, 45.0]) == 0.0
 

def test_MercatorProjection_create_crs():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.MercatorProjection(s.map_projection, s.zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0])
    o = m.create_crs()
    assert isinstance(o, cartopy.crs.Mercator)


def test_CylindricalEquidistantProjection___init__():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.CylindricalEquidistantProjection(s.map_projection, s.zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.zoom_factor == 0.5
    assert m.proj_type == const.MapProjection.CYL_EQU
    assert isinstance(m.crs, cartopy.crs.LambertCylindrical)


def test_CylindricalEquidistantProjection_get_tangent_lat():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.CylindricalEquidistantProjection(s.map_projection, s.zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.get_tangent_lat([-125.0, 45.0]) == 0.0
    

def test_CylindricalEquidistantProjection_create_crs():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.CylindricalEquidistantProjection(s.map_projection, s.zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0])
    o = m.create_crs()
    assert isinstance(o, cartopy.crs.LambertCylindrical)


def test_WebMercatorProjection___init__():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.WebMercatorProjection(s.map_projection, s.zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.zoom_factor == 0.5
    assert m.proj_type == const.MapProjection.WEB_MERCATOR
    assert type(m.crs).__name__ == "WebMercatorCRS"


def test_WebMercatorProjection_get_tangent_lat():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.WebMercatorProjection(s.map_projection, s.zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.get_tangent_lat([-125.0, 45.0]) == 0.0
    

def test_WebMercatorProjection_create_crs():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.WebMercatorProjection(s.map_projection, s.zoom_factor, [-125.0, 45.0], 1.3, [1.0, 1.0])
    o = m.create_crs()
    assert type(m.crs).__name__ == "WebMercatorCRS"


def test_WebMercatorCRS___init__():
    o = mapproj.WebMercatorCRS(0.0)
    assert o.central_longitude == pytest.approx(0.0)
    assert o.bounds == pytest.approx( (-20037508.3, 20037508.3, -20048966.1, 20048966.1) )

    o = mapproj.WebMercatorCRS(170.0)
    assert o.central_longitude == pytest.approx(170.0)
    assert o.bounds == pytest.approx( (-20037508.3, 20037508.3, -20048966.1, 20048966.1) )


def test_WebMercatorCRS___repr__():
    o = mapproj.WebMercatorCRS(170.0)
    assert str(o) == "WebMercatorCRS(central_longitude=170.0)"
    

def test_WebMercatorCRS_x_limits():
    o = mapproj.WebMercatorCRS(170.0)
    assert o.x_limits == pytest.approx( (-20037508.3, 20037508.3) )
    

def test_WebMercatorCRS_y_limits():
    o = mapproj.WebMercatorCRS(170.0)
    assert o.y_limits == pytest.approx( (-20048966.1, 20048966.1) )
    

def test_WebMercatorCRS_threshold():
    o = mapproj.WebMercatorCRS(170.0)
    assert o.threshold == pytest.approx( 2*200375.083 )


    
