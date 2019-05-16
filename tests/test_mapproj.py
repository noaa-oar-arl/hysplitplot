import pytest
import math
import numpy
import cartopy.crs
from hysplit4 import mapproj, mapbox, const
from hysplit4.traj import plot, model


# Notes:
# 1) _CYLSET, _CYL2XY, and _CYL2LL of the CylindricalCoordinate class are indirectly tested.
#    We will not write unit tests for them.
# 2) Numerical results for coordinate transforms and projections are compared with
#    values obtained by running the FORTRAN code.


@pytest.fixture
def lambert_coord():
    coord = mapproj.LambertCoordinate()
    coord.setup([-125.0, 45.0], 500.0, 500.0, (1.0, 1.0))
    return coord


@pytest.fixture
def cyl_coord():
    coord = mapproj.CylindricalCoordinate()
    coord.setup([-125.0, 45.0], 500.0, 500.0, [1.0, 1.0])
    return coord


def create_map_box(s):
    # TODO: add a method in the module that does this and simplify this fixture.
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
    m = mapproj.MapProjectionFactory.create_instance(s, [-125.0, 45.0], 1.3, [1.0, 1.0], testMapBox)
    return m


def test_CoordinateBase___init__():
    coord = mapproj.CoordinateBase()

    assert coord.EARTH_RADIUS == 6371.2
    assert coord.RADPDG == math.pi/180.0
    assert coord.DGPRAD == 180.0/math.pi

    assert len(coord.parmap) == 9
    assert coord.grid == 0.0
    assert coord.reflon == 0.0
    assert coord.tnglat == 0.0
    assert coord.slat == 0.0
    assert coord.slon == 0.0
    assert coord.glat == 0.0
    assert coord.glon == 0.0


def test_CoordinateBase_setup():
    # Create an instance of a child class as setup() requires a method defined by a child class.
    coord = mapproj.LambertCoordinate()

    coord.setup([-125.0, 45.0], 500.0, 500.0, (1.0, 1.0))

    assert coord.grid == 50.0
    assert coord.reflon == -125.0

    assert coord.tnglat == 45.0
    assert coord.slat == 45.0
    assert coord.slon == -125.0
    assert coord.glat == 45.0
    assert coord.glon == -125.0

    assert coord.parmap[0] == pytest.approx(0.707106769)
    assert coord.parmap[1] == pytest.approx(-125.0)
    assert coord.parmap[2] == pytest.approx(500.0)
    assert coord.parmap[3] == pytest.approx(389.786743)
    assert coord.parmap[4] == pytest.approx(1.0)
    assert coord.parmap[5] == pytest.approx(0.0)
    assert coord.parmap[6] == pytest.approx(37.9159317)
    assert coord.parmap[7] == pytest.approx(1.41248202)
    assert coord.parmap[8] == pytest.approx(-1153.58179, 1.3e-3)


def test_CoordinateBase_init_params():
    coord = mapproj.CoordinateBase()
    coord.grid = 50.0
    coord.reflon = -125.0
    coord.tnglat = 45.0
    coord.slat = 45.0
    coord.slon = -125.0
    coord.glat = 45.0
    coord.glon = -125.0

    coord.init_params(500.0, 500.0)

    assert coord.parmap[0] == pytest.approx(0.707106769)
    assert coord.parmap[1] == pytest.approx(-125.0)
    assert coord.parmap[2] == pytest.approx(500.0)
    assert coord.parmap[3] == pytest.approx(389.786743)
    assert coord.parmap[4] == pytest.approx(1.0)
    assert coord.parmap[5] == pytest.approx(0.0)
    assert coord.parmap[6] == pytest.approx(37.9159317)
    assert coord.parmap[7] == pytest.approx(1.41248202)
    assert coord.parmap[8] == pytest.approx(-1153.58179, 1.3e-3)


def test_CoordinateBase_rescale(lambert_coord):
    lonlat = (-148.0149298024163, -85.45743431680421, 25.62901482380674, 56.187678495569685)
    xy = lambert_coord.rescale((1.0, 1.0), lonlat)
    assert xy == pytest.approx((97.0, 75.0))


def test_CoordinateBase_calc_xy(lambert_coord):
    xy = lambert_coord.calc_xy(-120.0, 40.0)
    assert xy == pytest.approx((508.54451380782945, 489.13002239488370))


def test_CoordinateBase_calc_lonlat(lambert_coord):
    lonlat = lambert_coord.calc_lonlat(508.54451380782945, 489.13002239488370)
    assert lonlat == pytest.approx((-120.0, 40.0))


def test_CoordinateBase__STLMBR():
    par = numpy.zeros(9, dtype=float)

    mapproj.CoordinateBase._STLMBR(par, 45.0, -125.0)

    assert par[0] == pytest.approx(0.707106769)
    assert par[1] == pytest.approx(-125.0)
    assert par[2] == pytest.approx(0.0)
    assert par[3] == pytest.approx(0.0)
    assert par[4] == pytest.approx(1.0)
    assert par[5] == pytest.approx(0.0)
    assert par[6] == pytest.approx(6371.20020)
    assert par[7] == pytest.approx(1.41248202)
    assert par[8] == pytest.approx(-1153.58179, 1.3e-3)


def test_CoordinateBase__STCM1P():
    par = numpy.zeros(9, dtype=float)
    mapproj.CoordinateBase._STLMBR(par, 45.0, -125.0)

    mapproj.CoordinateBase._STCM1P(par, 500.0, 500.0, 45.0, -125.0, 45.0, -125.0, 50.0, 0.0)

    assert par[0] == pytest.approx(0.707106769)
    assert par[1] == pytest.approx(-125.0)
    assert par[2] == pytest.approx(500.0)
    assert par[3] == pytest.approx(389.786743)
    assert par[4] == pytest.approx(1.0)
    assert par[5] == pytest.approx(0.0)
    assert par[6] == pytest.approx(37.9159317)
    assert par[7] == pytest.approx(1.41248202)
    assert par[8] == pytest.approx(-1153.58179, 1.3e-3)


def test_CoordinateBase__CGSZLL():
    par = numpy.zeros(9, dtype=float)
    mapproj.CoordinateBase._STLMBR(par, 45.0, -125.0)

    par[6] = 1.0
    assert mapproj.CoordinateBase._CGSZLL(par, 45.0, -125.0) == pytest.approx(1.31870687)


def test_CoordinateBase__CLL2XY(lambert_coord):
    par = lambert_coord.parmap
    xy = mapproj.CoordinateBase._CLL2XY(par, 44.5, -125.5)
    assert xy == pytest.approx((499.206848, 498.890442))


def test_CoordinateBase__CXY2LL(lambert_coord):
    par = lambert_coord.parmap
    latlon = mapproj.CoordinateBase._CXY2LL(par, 499.993134, 500.007507)
    assert latlon == pytest.approx((45.0033798, -125.004364))


def test_CoordinateBase__CSPANF():
    assert mapproj.CoordinateBase._CSPANF(-181.0, -180.0, 180.0) ==  179.0
    assert mapproj.CoordinateBase._CSPANF(-180.0, -180.0, 180.0) == -180.0
    assert mapproj.CoordinateBase._CSPANF(   0.0, -180.0, 180.0) ==    0.0
    assert mapproj.CoordinateBase._CSPANF( 180.0, -180.0, 180.0) == -180.0
    assert mapproj.CoordinateBase._CSPANF( 181.0, -180.0, 180.0) == -179.0

    assert mapproj.CoordinateBase._CSPANF(-91.0, -90.0, 90.0) ==  89.0
    assert mapproj.CoordinateBase._CSPANF(-90.0, -90.0, 90.0) == -90.0
    assert mapproj.CoordinateBase._CSPANF(  0.0, -90.0, 90.0) ==   0.0
    assert mapproj.CoordinateBase._CSPANF( 90.0, -90.0, 90.0) == -90.0
    assert mapproj.CoordinateBase._CSPANF( 91.0, -90.0, 90.0) == -89.0


def test_CoordinateBase__CNLLXY(lambert_coord):
    par = lambert_coord.parmap

    xy = mapproj.CoordinateBase._CNLLXY(par, 90.0, 0.0)
    assert xy == pytest.approx((0.0, 1.41421354))

    xy = mapproj.CoordinateBase._CNLLXY(par, 56.0, -125.0)
    assert xy == pytest.approx((0.0, 0.802434325))


def test_CoordinateBase__CNXYLL(lambert_coord):
    par = lambert_coord.parmap

    latlon = mapproj.CoordinateBase._CNXYLL(par, -0.190484017, 0.509445071)
    assert latlon == pytest.approx((32.5308914, -141.813660))


def test_CoorinateBase_normalize_lon():
    assert mapproj.CoordinateBase.normalize_lon( -1.0) == 359.0
    assert mapproj.CoordinateBase.normalize_lon(  0.0) ==   0.0
    assert mapproj.CoordinateBase.normalize_lon(180.0) == 180.0
    assert mapproj.CoordinateBase.normalize_lon(360.0) == 360.0
    assert mapproj.CoordinateBase.normalize_lon(361.0) ==   1.0


def test_LambertCoordinate___init__():
    coord = mapproj.LambertCoordinate()

    assert len(coord.parmap) == 9


def test_LambertCoordinate_set_tangent_lat():
    coord = mapproj.LambertCoordinate()

    coord.set_tangent_lat((-125.0, 45.0))

    assert coord.tnglat == 45.0
    assert coord.slat == 45.0
    assert coord.slon == -125.0
    assert coord.glat == 45.0
    assert coord.glon == -125.0


def test_PolarCoordinate___init__():
    coord = mapproj.PolarCoordinate()

    assert len(coord.parmap) == 9


def test_PolarCoordinate_set_tangent_lat():
    coord = mapproj.PolarCoordinate()
    coord.reflon = 45.0

    coord.set_tangent_lat((-125.0, 45.0))

    assert coord.tnglat == 90.0
    assert coord.slat == 90.0
    assert coord.slon == 0.0
    assert coord.glat == 45.0
    assert coord.glon == 45.0

    coord.set_tangent_lat((-125.0, -45.0))

    assert coord.tnglat == -90.0
    assert coord.slat == -90.0
    assert coord.slon == 0.0
    assert coord.glat == -45.0
    assert coord.glon == 45.0


def test_MercatorCoordinate___init__():
    coord = mapproj.MercatorCoordinate()

    assert len(coord.parmap) == 9


def test_MercatorCoordinate_set_tangent_lat():
    coord = mapproj.MercatorCoordinate()
    coord.reflon = 45.0

    coord.set_tangent_lat((-125.0, 45.0))

    assert coord.tnglat == 0.0
    assert coord.slat == 45.0
    assert coord.slon == -125.0
    assert coord.glat == 0.0
    assert coord.glon == 45.0


def test_CylindricalCoordinate___init__():
    coord = mapproj.CylindricalCoordinate()

    assert len(coord.parmap) == 9
    assert coord.xypdeg == 0.0
    assert coord.coslat == 0.0
    assert coord.rlat == 0.0
    assert coord.rlon == 0.0
    assert coord.xr == 0.0
    assert coord.yr == 0.0


def test_CylindricalCoordinate_set_tangent_lat():
    coord = mapproj.CylindricalCoordinate()
    coord.reflon = 45.0

    coord.set_tangent_lat((-125.0, 45.0))

    assert coord.tnglat == 0.0
    assert coord.slat == 45.0
    assert coord.slon == -125.0
    assert coord.glat == 0.0
    assert coord.glon == 45.0


def test_CylindricalCoordinate_init_params():
    coord = mapproj.CylindricalCoordinate()
    coord.grid = 50.0
    coord.reflon = -125.0
    coord.set_tangent_lat((-125.0, 45.0))

    coord.init_params(500.0, 500.0)

    assert coord.xypdeg == pytest.approx(2.22396851)
    assert coord.coslat == pytest.approx(1.0)
    assert coord.rlat == pytest.approx(45.0)
    assert coord.rlon == pytest.approx(235.0)
    assert coord.xr == pytest.approx(500.0)
    assert coord.yr == pytest.approx(500.0)


def test_CylindricalCoordinate_rescale(cyl_coord):
    lonlat = (-146.583038, -60.2508850, 28.3630753, 61.6369324)
    xy = cyl_coord.rescale([1.0, 1.0], lonlat)
    assert xy == pytest.approx((193.0, 75.0))


def test_CylindricalCoordinate_calc_xy(cyl_coord):
    xy = cyl_coord.calc_xy(-125.0, 38.0)
    assert xy == pytest.approx((500.000000, 484.432220))


def test_CylindricalCoordinate_calc_xy(cyl_coord):
    lonlat = cyl_coord.calc_lonlat(500.000000, 484.432220)
    assert lonlat == pytest.approx((-125.0, 38.0))


def test_MapProjectionFactory_create_instance():
    s = plot.TrajectoryPlotSettings()
    map_box = mapbox.MapBox()
    map_box.allocate()
    map_box.add((-120.5, 45.5))
    map_box.determine_plume_extent()

    s.map_projection = const.MapProjection.POLAR
    m = mapproj.MapProjectionFactory.create_instance(s, [-125.0, 45.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, mapproj.PolarProjection)

    s.map_projection = const.MapProjection.LAMBERT
    m = mapproj.MapProjectionFactory.create_instance(s, [-125.0, 45.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, mapproj.LambertProjection)

    s.map_projection = const.MapProjection.MERCATOR
    m = mapproj.MapProjectionFactory.create_instance(s, [-125.0, 45.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, mapproj.MercatorProjection)

    s.map_projection = const.MapProjection.CYL_EQU
    m = mapproj.MapProjectionFactory.create_instance(s, [-125.0, 45.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, mapproj.CylindricalEquidistantProjection)

    # Lambert grid is not permitted to contain the poles

    # when containing the north pole
    map_box.clear_hit_map()
    map_box.add((-120.5, 89.0))
    map_box.add((-120.5, 90.0))
    map_box.determine_plume_extent()

    s.map_projection = const.MapProjection.LAMBERT
    m = mapproj.MapProjectionFactory.create_instance(s, [-125.0, 89.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, mapproj.PolarProjection)

    # when containing the south pole
    map_box.clear_hit_map()
    map_box.add((-120.5, -89.0))
    map_box.add((-120.5, -90.0))
    map_box.determine_plume_extent()

    s.map_projection = const.MapProjection.LAMBERT
    m = mapproj.MapProjectionFactory.create_instance(s, [-125.0, -89.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, mapproj.PolarProjection)
    
    
def test_MapProjection___init__():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.MapProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])

    assert m.settings is s
    assert m.scale == 1.3
    assert m.deltas == [1.0, 1.0]

    assert m.proj_type == None
    assert m.coord == None
    assert m.center_loc == [-125.0, 45.0]
    assert m.corners_xy == None
    assert m.corners_lonlat == None
    assert m.point_counts == None


def test_MapProjection_determine_projection():
    k_auto = const.MapProjection.AUTO
    k_polar = const.MapProjection.POLAR
    k_lambert = const.MapProjection.LAMBERT
    k_mercator = const.MapProjection.MERCATOR
    k_cylequ = const.MapProjection.CYL_EQU

    assert mapproj.MapProjection.determine_projection(k_polar,    [-125.0, 35.0]) == k_polar
    assert mapproj.MapProjection.determine_projection(k_lambert,  [-125.0, 35.0]) == k_lambert
    assert mapproj.MapProjection.determine_projection(k_mercator, [-125.0, 35.0]) == k_mercator
    assert mapproj.MapProjection.determine_projection(k_cylequ,   [-125.0, 35.0]) == k_cylequ

    assert mapproj.MapProjection.determine_projection(k_auto, [-125.0, 35.0]) == k_lambert
    assert mapproj.MapProjection.determine_projection(k_auto, [-125.0, 65.0]) == k_polar
    assert mapproj.MapProjection.determine_projection(k_auto, [-125.0,-65.0]) == k_polar
    assert mapproj.MapProjection.determine_projection(k_auto, [-125.0, 15.0]) == k_mercator
    assert mapproj.MapProjection.determine_projection(k_auto, [-125.0, 15.0]) == k_mercator


def test_MapProjection_refine_corners__lambert():
    s = plot.TrajectoryPlotSettings()
    s.map_projection = const.MapProjection.LAMBERT
    s.center_loc = [-125.0, 45.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    testMapBox = create_map_box(s)
    m = mapproj.MapProjectionFactory.create_instance(s, [-125.0, 45.0], 1.3, [1.0, 1.0], testMapBox)

    m.refine_corners(testMapBox, [-125.0, 45.0])

    assert m.corners_xy[0] == pytest.approx( 1.0)
    assert m.corners_xy[1] == pytest.approx(27.0)
    assert m.corners_xy[2] == pytest.approx( 1.0)
    assert m.corners_xy[3] == pytest.approx(21.0)
    assert m.corners_lonlat[0] == pytest.approx(-132.642365)
    assert m.corners_lonlat[1] == pytest.approx(-116.065727)
    assert m.corners_lonlat[2] == pytest.approx(  40.2330704)
    assert m.corners_lonlat[3] == pytest.approx(  49.1701241)
    assert m.point_counts == (27, 21)


def test_MapProjection_refine_corners__polar():
    s = plot.TrajectoryPlotSettings()
    s.map_projection = const.MapProjection.POLAR
    s.center_loc = [-125.0, 85.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    testMapBox = create_map_box(s)
    m = mapproj.MapProjectionFactory.create_instance(s, [-125.0, 85.0], 1.3, [1.0, 1.0], testMapBox)

    m.refine_corners(testMapBox, [-125.0, 85.0])

    assert m.corners_xy[0] == pytest.approx( 1.0)
    assert m.corners_xy[1] == pytest.approx(19.0)
    assert m.corners_xy[2] == pytest.approx( 1.0)
    assert m.corners_xy[3] == pytest.approx(15.0)
    assert m.corners_lonlat[0] == pytest.approx(-151.565033)
    assert m.corners_lonlat[1] == pytest.approx( -58.9624939)
    assert m.corners_lonlat[2] == pytest.approx(  80.9526520)
    assert m.corners_lonlat[3] == pytest.approx(  85.5652771)
    assert m.point_counts == (19, 15)


def test_MapProjection_refine_corners__mercator():
    s = plot.TrajectoryPlotSettings()
    s.map_projection = const.MapProjection.MERCATOR
    s.center_loc = [-125.0, 45.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    testMapBox = create_map_box(s)
    m = mapproj.MapProjectionFactory.create_instance(s, [-125.0, 45.0], 1.3, [1.0, 1.0], testMapBox)

    m.refine_corners(testMapBox, [-125.0, 45.0])

    assert m.corners_xy[0] == pytest.approx( 1.0)
    assert m.corners_xy[1] == pytest.approx(37.0)
    assert m.corners_xy[2] == pytest.approx( 1.0)
    assert m.corners_xy[3] == pytest.approx(29.0)
    assert m.corners_lonlat[0] == pytest.approx(-133.093643)
    assert m.corners_lonlat[1] == pytest.approx(-116.906357)
    assert m.corners_lonlat[2] == pytest.approx(  40.3761826)
    assert m.corners_lonlat[3] == pytest.approx(  49.2786980)
    assert m.point_counts == (37, 29)


def test_MapProjection_refine_corners__cylequ():
    s = plot.TrajectoryPlotSettings()
    s.map_projection = const.MapProjection.CYL_EQU
    s.center_loc = [-125.0, 5.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    testMapBox = create_map_box(s)
    m = mapproj.MapProjectionFactory.create_instance(s, [-125.0, 5.0], 1.3, [1.0, 1.0], testMapBox)

    m.refine_corners(testMapBox, [-125.0, 5.0])

    assert m.corners_xy[0] == pytest.approx( 1.0)
    assert m.corners_xy[1] == pytest.approx(53.0)
    assert m.corners_xy[2] == pytest.approx( 1.0)
    assert m.corners_xy[3] == pytest.approx(21.0)
    assert m.corners_lonlat[0] == pytest.approx(-130.845398)
    assert m.corners_lonlat[1] == pytest.approx(-107.463776)
    assert m.corners_lonlat[2] == pytest.approx(   0.503532410, 1.0e-5)
    assert m.corners_lonlat[3] == pytest.approx(   9.49646759 )
    assert m.point_counts == (53, 21)


def test_MapProjection_validate_corners(lambert_proj):
    corners = lambert_proj.validate_corners([400.0, 600.0, 480.0, 520.0])
    assert corners == pytest.approx((400.0, 600.0, 480.0, 520.0))


def test_MapProjection_scale_per_aspect_ratio():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.MapProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    cnr = [ 498.888000, 501.112000, 493.328094, 506.671906 ]
    cnr2 = m.scale_per_aspect_ratio(cnr, 1.3)
    assert cnr2 == pytest.approx((491.326538, 508.673462, 493.328094, 506.671906))


def test_MapProjection_choose_corners(lambert_proj):
    cnr1 = [ 498.888000, 501.112000, 493.328094, 506.671906 ]
    cnr2 = [ 491.326538, 508.673462, 493.328094, 506.671906 ]
    cnr = lambert_proj.choose_corners(cnr1, cnr2)
    assert cnr == pytest.approx(cnr1)

    lambert_proj.TOLERANCE = -1.0
    cnr = lambert_proj.choose_corners(cnr1, cnr2)
    assert cnr == pytest.approx(cnr2)


def test_MapProjection_zoom_corners():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.MapProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    cnr = [ 491.326538, 508.673462, 493.328094, 506.671906 ]
    assert m.zoom_corners(cnr, 0.5) == pytest.approx((486.989807, 513.010193, 489.992126, 510.007874))


def test_MapProjection_round_map_corners():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.MapProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    cnr = [486.989807, 513.010193, 489.992126, 510.007874]
    assert m.round_map_corners(cnr) == pytest.approx((487.0, 513.0, 490.0, 510.0))


def test_MapProjection_calc_corners_lonlat(lambert_proj):
    c = lambert_proj.calc_corners_lonlat([487.0, 513.0, 490.0, 510.0])
    assert c == pytest.approx((-132.642365, -116.065727, 40.2330704, 49.1701241))


def test_MapProjection_need_pole_exclusion():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.MapProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.need_pole_exclusion([]) == False


def test_MapProjection_exclude_pole(lambert_proj):
    lonlat = (-132.642365, -116.065727, 40.2330704, 81.0)
    corners = (487.0000053058765, 504.33309956494145, 490.00000650688287, 588.2847863455208)
    xy2, ll2 = lambert_proj.exclude_pole(corners, lonlat)
    assert xy2 == pytest.approx((corners[0], 504.6698474317799, corners[2], 585.243073015295))
    assert ll2 == pytest.approx((lonlat[0], lonlat[1], lonlat[2], 80.0))

    lonlat = (-132.642365, -116.065727, -81.0, -40.2330704)
    corners = (364.9428216453149, 545.0166492018224, -800.2763365088213, 220.80600641077086)
    xy2, ll2 = lambert_proj.exclude_pole(corners, lonlat)
    assert xy2 == pytest.approx((374.6819442561835, corners[1], -697.3232850810637, corners[3]))
    assert ll2 == pytest.approx((lonlat[0], lonlat[1], -80.0, lonlat[3]))


def test_MapProjection_do_initial_estimates():
    s = plot.TrajectoryPlotSettings()
    s.map_projection = const.MapProjection.LAMBERT
    s.center_loc = [-125.0, 45.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    map_box = create_map_box(s)
    proj = mapproj.LambertProjection(s, s.center_loc, 1.3, [1.0, 1.0])

    proj.do_initial_estimates(map_box, [-125.0, 45.0])

    assert proj.corners_xy == pytest.approx((499.206848, 500.779419,
                                             493.325073, 506.674988))
    assert proj.corners_lonlat == pytest.approx((-125.479248, -124.476982,
                                                41.9989433, 47.9988670))
    assert proj.center_loc == pytest.approx((-125.004364, 45.0000114))


def test_MapProjection_sanity_check():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.MapProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.sanity_check() == True


def test_MapProjection_create_proper_projection():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.MapProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    try:
        m.create_proper_instance(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
        pytest.fail("expected an exception")
    except Exception as ex:
        str(ex) == "This should not happen"


def test_MapProjection_create_crs():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.MapProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    try:
        m.create_crs()
        pytest.fail("expected an exception")
    except Exception as ex:
        str(ex) == "This should not happen"


def test_LambertProjection___init__():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.LambertProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.settings is not None
    assert m.proj_type == const.MapProjection.LAMBERT
    assert isinstance(m.coord, mapproj.LambertCoordinate)


def test_LambertProjection_sanity_check(lambert_proj):
    assert lambert_proj.sanity_check() == True

    c = list(lambert_proj.corners_xy)
    c[3] = 10000.0
    lambert_proj.corners_xy = c
    assert lambert_proj.sanity_check() == False


def test_LambertProjection_create_proper_projection(lambert_proj):
    m = lambert_proj
    o = lambert_proj.create_proper_projection(m.settings, m.center_loc, m.scale, m.deltas)
    assert isinstance(o, mapproj.PolarProjection)


def test_LambertProjection_need_pole_exclusion(lambert_proj):
    assert lambert_proj.need_pole_exclusion([-135.0, -115.0,-81.0, 55.0]) == True
    assert lambert_proj.need_pole_exclusion([-135.0, -115.0,-80.0, 55.0]) == False
    assert lambert_proj.need_pole_exclusion([-135.0, -115.0,-35.0, 55.0]) == False
    assert lambert_proj.need_pole_exclusion([-135.0, -115.0, 35.0, 55.0]) == False
    assert lambert_proj.need_pole_exclusion([-135.0, -115.0, 35.0, 80.0]) == False
    assert lambert_proj.need_pole_exclusion([-135.0, -115.0, 35.0, 80.1]) == True


def test_LambertProjection_create_crs(lambert_proj):
    o = lambert_proj.create_crs()
    assert isinstance(o, cartopy.crs.LambertConformal)


def test_PolarProjection___init__():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.PolarProjection(s, [-125.0, 85.0], 1.3, [1.0, 1.0])
    assert m.settings is not None
    assert m.proj_type == const.MapProjection.POLAR
    assert isinstance(m.coord, mapproj.PolarCoordinate)


def test_PolarProjection_create_crs():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.PolarProjection(s, [-125.0, 85.0], 1.3, [1.0, 1.0])
    o = m.create_crs()
    assert isinstance(o, cartopy.crs.NorthPolarStereo)

    m = mapproj.PolarProjection(s, [-125.0, -85.0], 1.3, [1.0, 1.0])
    o = m.create_crs()
    assert isinstance(o, cartopy.crs.SouthPolarStereo)


def test_MercatorProjection___init__():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.MercatorProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.settings is not None
    assert m.proj_type == const.MapProjection.MERCATOR
    assert isinstance(m.coord, mapproj.MercatorCoordinate)


def test_MercatorProjection_need_pole_exclusion():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.MercatorProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.need_pole_exclusion([-135.0, -115.0,-81.0, 55.0]) == True
    assert m.need_pole_exclusion([-135.0, -115.0,-80.0, 55.0]) == False
    assert m.need_pole_exclusion([-135.0, -115.0,-35.0, 55.0]) == False
    assert m.need_pole_exclusion([-135.0, -115.0, 35.0, 55.0]) == False
    assert m.need_pole_exclusion([-135.0, -115.0, 35.0, 80.0]) == False
    assert m.need_pole_exclusion([-135.0, -115.0, 35.0, 80.1]) == True


def test_MercatorProjection_create_crs():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.MercatorProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    o = m.create_crs()
    assert isinstance(o, cartopy.crs.Mercator)


def test_CylindricalEquidistantProjection___init__():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.CylindricalEquidistantProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.settings is not None
    assert m.proj_type == const.MapProjection.CYL_EQU
    assert isinstance(m.coord, mapproj.CylindricalCoordinate)


def test_CylindricalEquidistantProjection_create_crs():
    s = plot.TrajectoryPlotSettings()
    m = mapproj.CylindricalEquidistantProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    o = m.create_crs()
    assert isinstance(o, cartopy.crs.LambertCylindrical)
