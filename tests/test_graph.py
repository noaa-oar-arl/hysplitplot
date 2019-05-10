import sys
import os
import pytest
import math
import numpy
import geopandas
import cartopy.crs
from hysplit4 import graph
from hysplit4.traj import plot


# Notes:
# 1) _CYLSET, _CYL2XY, and _CYL2LL of the CylindricalCoordinate class are indirectly tested.
#    We will not write unit tests for them.
# 2) Numerical results for coordinate transforms and projections are compared with
#    values obtained by running the FORTRAN code.


@pytest.fixture
def lambert_coord():
    coord = graph.LambertCoordinate()
    coord.setup([-125.0, 45.0], 500.0, 500.0, (1.0, 1.0))
    return coord


@pytest.fixture
def cyl_coord():
    coord = graph.CylindricalCoordinate()
    coord.setup([-125.0, 45.0], 500.0, 500.0, [1.0, 1.0])
    return coord


@pytest.fixture
def clusterList():
    return graph.ClusterList(1).get_reader().read("data/CLUSLIST_4")


def create_map_box(s):
    # TODO: add a method in the module that does this and simplify this fixture.
    d = plot.TrajectoryPlotData()
    r = plot.TrajectoryDataFileReader(d)
    r.adjust_settings("data/tdump", s)
    r.read("data/tdump", s)
    map_box = graph.MapBox()
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
    s.map_projection = plot.TrajectoryPlotSettings.MapProjection.LAMBERT
    s.center_loc = [-125.0, 45.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    testMapBox = create_map_box(s)
    m = graph.MapProjection.create_instance(s, [-125.0, 45.0], 1.3, [1.0, 1.0], testMapBox)
    return m


def test_ARLMap___init__():
    m = graph.ARLMap()

    assert m.segments != None


def test_ARLMap_get_reader():
    m = graph.ARLMap()
    r = m.get_reader()

    assert isinstance(r, graph.ARLMapReader)


def test_Segment___init__():
    s = graph.ARLMap.Segment(1, 40.0, -90.0, "k", 0.08)

    assert s.number == 1
    assert s.latitudes == 40.0
    assert s.longitudes == -90.0
    assert s.color == "k"
    assert s.thickness == 0.08


def test_ARLMapReader___init__():
    m = graph.ARLMap()
    r = graph.ARLMapReader(m)

    assert r.map is m
    assert len(r.colors) > 0
    assert len(r.thickness) > 0
    assert r.colors["default"] == "#6699cc"
    assert r.thickness["default"] == 0.01


def test_ARLMapReader_read():
    r = graph.ARLMap().get_reader()
    m = r.read("data/arlmap_truncated")
    assert isinstance(m, graph.ARLMap)

    assert len(m.segments) == 4

    s = m.segments[1]
    assert s.number == 2
    assert len(s.latitudes) == 99
    assert s.latitudes[0] == 60.89
    assert s.latitudes[98] == 62.85
    assert len(s.longitudes) == 99
    assert s.longitudes[0] == -115.02
    assert s.longitudes[98] == -109.23
    assert s.color == "#6699cc"
    assert s.thickness == 0.01

    s = m.segments[3]
    assert s.number == 4
    assert len(s.latitudes) == 4
    assert s.latitudes[0] == 60.31
    assert s.latitudes[3] == 69.64
    assert len(s.longitudes) == 4
    assert s.longitudes[0] == -141.0
    assert s.longitudes[3] == -141.0
    assert s.color == "#6699cc"
    assert s.thickness == 0.01


def test_ARLMapReader_read__case2():
    r = graph.ARLMap().get_reader()
    m = r.read("data/arlmap_test")
    assert isinstance(m, graph.ARLMap)

    assert len(m.segments) == 4

    # BOUNDARY
    s = m.segments[0]
    assert s.color == "#000000"
    assert s.thickness == 0.01

    # COUNTIES
    s = m.segments[1]
    assert s.color == "#cccccc"
    assert s.thickness == 0.008

    # ROADS
    s = m.segments[2]
    assert s.color == "#cc0000"
    assert s.thickness == 0.008

    # RIVERS
    s = m.segments[3]
    assert s.color == "#0000cc"
    assert s.thickness == 0.008


def test_ARLMapConverter_converter():
    m = graph.ARLMap().get_reader().read("data/arlmap_truncated")
    cs = graph.ARLMapConverter.convert(m)
    assert len(cs) > 0
    for c in cs:
        assert isinstance(c, graph.DrawableBackgroundMap)
        assert isinstance(c.map, geopandas.geoseries.GeoSeries)
        assert c.linestyle == "-"
        assert c.linewidth == 0.5
        assert c.linecolor == "#6699cc"


def test_ARLMapConverter_style_ref():
    assert graph.ARLMapConverter.style_ref("#6699cc", 0.008) == "#6699cc_0.008"
    assert graph.ARLMapConverter.style_ref("#6699cc", 0.01) == "#6699cc_0.01"


def test_DrawableBackgroundMap___init__():
    o = None
    d = graph.DrawableBackgroundMap(o, "k", 0.008)
    assert d.map is None
    assert d.linestyle == "-"
    assert d.linewidth == 0.4 # scaled
    assert d.linecolor == "k"


def test_ShapeFile___init__():
    s = graph.ShapeFile()
    assert s.filename == "arlmap.shp"
    assert s.dash == 0
    assert s.thickness == 0.01
    assert s.red == 0.4
    assert s.blue == 0.6
    assert s.green == 0.8


def test_ShapeFileReader___init__():
    r = graph.ShapeFilesReader()
    assert len(r.shapefiles) == 0


def test_ShapeFileReader_read():
    list = graph.ShapeFilesReader().read("data/shapefiles_arl.txt")
    assert len(list) == 1

    s = list[0]
    assert s.filename == "arlmap.shp"
    assert s.dash == 0
    assert s.thickness == pytest.approx(0.01)
    assert s.red == pytest.approx(0.4)
    assert s.green == pytest.approx(0.6)
    assert s.blue == pytest.approx(0.8)


def test_ShapeFileReader_parse_line():
    r = graph.ShapeFilesReader()

    t = r.parse_line("'arlmap.shp' 0 0.1 0.4 0.6 0.8")
    assert len(t) == 6
    assert t[0] == "arlmap.shp"
    assert t[1] == "0"
    assert t[2] == "0.1"
    assert t[3] == "0.4"
    assert t[4] == "0.6"
    assert t[5] == "0.8"

    t = r.parse_line("'arlmap.shp_''_' 0 0.1 0.4 0.6 0.8")
    assert len(t) == 6
    assert t[0] == "arlmap.shp_'_"


def test_ShapeFileReader_warn_and_create_sample():
    r = graph.ShapeFilesReader()
    try:
        r.warn_and_create_sample("__shapefiles_test.txt")
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex).startswith("file not found __shapefiles_test.txt: please see")
        os.remove("__shapefiles_test.txt")


def test_ShapeFileConverter_convert():
    s = graph.ShapeFile()
    s.filename = "data/arlmap.shp"
    s.dash = 8
    s.thickness = 0.75
    s.red = 0.4
    s.green = 0.6
    s.blue = 0.8

    m = graph.ShapeFileConverter.convert(s)
    assert isinstance(m, graph.DrawableBackgroundMap)
    assert isinstance(m.map, geopandas.geodataframe.GeoDataFrame)
    assert len(m.map.crs) > 0 # must have initialized the CRS field.
    assert m.linestyle == (0, (4.5, 4.5))
    assert m.linewidth == pytest.approx(0.75*50)
    assert m.linecolor == "#6699cc"


def test_ShapeFileConverter_make_linestyle():
    assert graph.ShapeFileConverter.make_linestyle(0) == '-'
    assert graph.ShapeFileConverter.make_linestyle(1) == (0, (36.0, 36.0))
    assert graph.ShapeFileConverter.make_linestyle(2) == (0, (18.0, 18.0))
    assert graph.ShapeFileConverter.make_linestyle(4) == (0, (9.0, 9.0))
    assert graph.ShapeFileConverter.make_linestyle(-4) == (0, (9.0, 9.0))


def test_MapBox___init__():
    mb = graph.MapBox()

    assert mb.hit_map == None
    assert mb.sz == [360, 181]
    assert mb.grid_delta == 1.0
    assert mb.grid_corner == [0.0, -90.0]
    assert mb.plume_sz == [0.0, 0.0]
    assert mb.plume_loc == [0, 0]
    assert mb.hit_count == 0
    assert mb._i == 0
    assert mb._j == 0


def test_MapBox_allocate():
    mb = graph.MapBox();

    mb.hit_count = 1
    mb.allocate()

    assert mb.hit_map is not None
    assert mb.hit_map.shape == (360, 181)
    assert mb.hit_count == 0


def test_MapBox_add():
    mb = graph.MapBox()
    mb.allocate()

    mb.add((-120.5, 45.5))

    assert mb.hit_map[239, 135] == 1
    assert mb.hit_count == 1
    assert mb._i == 239
    assert mb._j == 135


def test_MapBox_determine_plume_extent():
    mb = graph.MapBox()
    mb.allocate()

    mb.add((-120.5, 45.5))
    mb.determine_plume_extent()

    assert mb.plume_sz == [1.0, 1.0]
    assert mb.plume_loc == [239, 135]


def test_MapBox_need_to_refine_grid():
    mb = graph.MapBox()

    mb.plume_sz = [0.0, 0.0]
    assert mb.need_to_refine_grid() == True

    mb.plume_sz = [2.5, 0.0]
    assert mb.need_to_refine_grid() == False

    mb.plume_sz = [0.0, 2.5]
    assert mb.need_to_refine_grid() == False


def test_MapBox_refine_grid():
    mb = graph.MapBox()
    mb.allocate()

    mb.add((-120.5, 45.5))
    mb.determine_plume_extent()
    mb.refine_grid()

    assert mb.grid_corner == [239.0, 45.0]
    assert mb.grid_delta == 0.10
    assert mb.sz == [10, 10]
    assert mb.hit_map is None


def test_MapBox_clear_hit_map():
    mb = graph.MapBox()
    mb.allocate()
    mb.add((-120.5, 45.5))
    assert mb.hit_map[239, 135] == 1
    assert mb.hit_count == 1

    mb.clear_hit_map()

    assert mb.hit_map[239, 135] == 0
    assert mb.hit_count == 0


def test_MapBox_set_ring_extent():
    mb = graph.MapBox()
    mb.allocate()
    mb.plume_sz = [40.0, 10.0]
    s = plot.TrajectoryPlotSettings()
    s.center_loc = (-120.5, 45.5)
    s.ring_number = 4
    s.ring_distance = 101.0

    mb.set_ring_extent(s)

    assert s.ring_distance == 100.0
    assert mb.hit_map[239, 138] == 0
    assert mb.hit_map[239, 137] == 1
    assert mb.hit_map[239, 136] == 1
    assert mb.hit_map[239, 135] == 2
    assert mb.hit_map[239, 134] == 1
    assert mb.hit_map[239, 133] == 1
    assert mb.hit_map[239, 132] == 0


def test_CoordinateBase___init__():
    coord = graph.CoordinateBase()

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
    coord = graph.LambertCoordinate()

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
    coord = graph.CoordinateBase()
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

    graph.CoordinateBase._STLMBR(par, 45.0, -125.0)

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
    graph.CoordinateBase._STLMBR(par, 45.0, -125.0)

    graph.CoordinateBase._STCM1P(par, 500.0, 500.0, 45.0, -125.0, 45.0, -125.0, 50.0, 0.0)

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
    graph.CoordinateBase._STLMBR(par, 45.0, -125.0)

    par[6] = 1.0
    assert graph.CoordinateBase._CGSZLL(par, 45.0, -125.0) == pytest.approx(1.31870687)


def test_CoordinateBase__CLL2XY(lambert_coord):
    par = lambert_coord.parmap
    xy = graph.CoordinateBase._CLL2XY(par, 44.5, -125.5)
    assert xy == pytest.approx((499.206848, 498.890442))


def test_CoordinateBase__CXY2LL(lambert_coord):
    par = lambert_coord.parmap
    latlon = graph.CoordinateBase._CXY2LL(par, 499.993134, 500.007507)
    assert latlon == pytest.approx((45.0033798, -125.004364))


def test_CoordinateBase__CSPANF():
    assert graph.CoordinateBase._CSPANF(-181.0, -180.0, 180.0) ==  179.0
    assert graph.CoordinateBase._CSPANF(-180.0, -180.0, 180.0) == -180.0
    assert graph.CoordinateBase._CSPANF(   0.0, -180.0, 180.0) ==    0.0
    assert graph.CoordinateBase._CSPANF( 180.0, -180.0, 180.0) == -180.0
    assert graph.CoordinateBase._CSPANF( 181.0, -180.0, 180.0) == -179.0

    assert graph.CoordinateBase._CSPANF(-91.0, -90.0, 90.0) ==  89.0
    assert graph.CoordinateBase._CSPANF(-90.0, -90.0, 90.0) == -90.0
    assert graph.CoordinateBase._CSPANF(  0.0, -90.0, 90.0) ==   0.0
    assert graph.CoordinateBase._CSPANF( 90.0, -90.0, 90.0) == -90.0
    assert graph.CoordinateBase._CSPANF( 91.0, -90.0, 90.0) == -89.0


def test_CoordinateBase__CNLLXY(lambert_coord):
    par = lambert_coord.parmap

    xy = graph.CoordinateBase._CNLLXY(par, 90.0, 0.0)
    assert xy == pytest.approx((0.0, 1.41421354))

    xy = graph.CoordinateBase._CNLLXY(par, 56.0, -125.0)
    assert xy == pytest.approx((0.0, 0.802434325))


def test_CoordinateBase__CNXYLL(lambert_coord):
    par = lambert_coord.parmap

    latlon = graph.CoordinateBase._CNXYLL(par, -0.190484017, 0.509445071)
    assert latlon == pytest.approx((32.5308914, -141.813660))


def test_CoorinateBase_normalize_lon():
    assert graph.CoordinateBase.normalize_lon( -1.0) == 359.0
    assert graph.CoordinateBase.normalize_lon(  0.0) ==   0.0
    assert graph.CoordinateBase.normalize_lon(180.0) == 180.0
    assert graph.CoordinateBase.normalize_lon(360.0) == 360.0
    assert graph.CoordinateBase.normalize_lon(361.0) ==   1.0


def test_LambertCoordinate___init__():
    coord = graph.LambertCoordinate()

    assert len(coord.parmap) == 9


def test_LambertCoordinate_set_tangent_lat():
    coord = graph.LambertCoordinate()

    coord.set_tangent_lat((-125.0, 45.0))

    assert coord.tnglat == 45.0
    assert coord.slat == 45.0
    assert coord.slon == -125.0
    assert coord.glat == 45.0
    assert coord.glon == -125.0


def test_PolarCoordinate___init__():
    coord = graph.PolarCoordinate()

    assert len(coord.parmap) == 9


def test_PolarCoordinate_set_tangent_lat():
    coord = graph.PolarCoordinate()
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
    coord = graph.MercatorCoordinate()

    assert len(coord.parmap) == 9


def test_MercatorCoordinate_set_tangent_lat():
    coord = graph.MercatorCoordinate()
    coord.reflon = 45.0

    coord.set_tangent_lat((-125.0, 45.0))

    assert coord.tnglat == 0.0
    assert coord.slat == 45.0
    assert coord.slon == -125.0
    assert coord.glat == 0.0
    assert coord.glon == 45.0


def test_CylindricalCoordinate___init__():
    coord = graph.CylindricalCoordinate()

    assert len(coord.parmap) == 9
    assert coord.xypdeg == 0.0
    assert coord.coslat == 0.0
    assert coord.rlat == 0.0
    assert coord.rlon == 0.0
    assert coord.xr == 0.0
    assert coord.yr == 0.0


def test_CylindricalCoordinate_set_tangent_lat():
    coord = graph.CylindricalCoordinate()
    coord.reflon = 45.0

    coord.set_tangent_lat((-125.0, 45.0))

    assert coord.tnglat == 0.0
    assert coord.slat == 45.0
    assert coord.slon == -125.0
    assert coord.glat == 0.0
    assert coord.glon == 45.0


def test_CylindricalCoordinate_init_params():
    coord = graph.CylindricalCoordinate()
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


def test_MapProjection___init__():
    s = plot.TrajectoryPlotSettings()
    m = graph.MapProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])

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
    k_auto = plot.TrajectoryPlotSettings.MapProjection.AUTO
    k_polar = plot.TrajectoryPlotSettings.MapProjection.POLAR
    k_lambert = plot.TrajectoryPlotSettings.MapProjection.LAMBERT
    k_mercator = plot.TrajectoryPlotSettings.MapProjection.MERCATOR
    k_cylequ = plot.TrajectoryPlotSettings.MapProjection.CYL_EQU

    assert graph.MapProjection.determine_projection(k_polar,    [-125.0, 35.0]) == k_polar
    assert graph.MapProjection.determine_projection(k_lambert,  [-125.0, 35.0]) == k_lambert
    assert graph.MapProjection.determine_projection(k_mercator, [-125.0, 35.0]) == k_mercator
    assert graph.MapProjection.determine_projection(k_cylequ,   [-125.0, 35.0]) == k_cylequ

    assert graph.MapProjection.determine_projection(k_auto, [-125.0, 35.0]) == k_lambert
    assert graph.MapProjection.determine_projection(k_auto, [-125.0, 65.0]) == k_polar
    assert graph.MapProjection.determine_projection(k_auto, [-125.0,-65.0]) == k_polar
    assert graph.MapProjection.determine_projection(k_auto, [-125.0, 15.0]) == k_mercator
    assert graph.MapProjection.determine_projection(k_auto, [-125.0, 15.0]) == k_mercator


def test_MapProjection_create_instance():
    s = plot.TrajectoryPlotSettings()
    map_box = graph.MapBox()
    map_box.allocate()
    map_box.add((-120.5, 45.5))
    map_box.determine_plume_extent()

    s.map_projection = s.MapProjection.POLAR
    m = graph.MapProjection.create_instance(s, [-125.0, 45.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, graph.PolarProjection)

    s.map_projection = s.MapProjection.LAMBERT
    m = graph.MapProjection.create_instance(s, [-125.0, 45.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, graph.LambertProjection)

    s.map_projection = s.MapProjection.MERCATOR
    m = graph.MapProjection.create_instance(s, [-125.0, 45.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, graph.MercatorProjection)

    s.map_projection = s.MapProjection.CYL_EQU
    m = graph.MapProjection.create_instance(s, [-125.0, 45.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, graph.CylindricalEquidistantProjection)

    # Lambert grid is not permitted to contain the poles

    # when containing the north pole
    map_box.clear_hit_map()
    map_box.add((-120.5, 89.0))
    map_box.add((-120.5, 90.0))
    map_box.determine_plume_extent()

    s.map_projection = s.MapProjection.LAMBERT
    m = graph.MapProjection.create_instance(s, [-125.0, 89.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, graph.PolarProjection)

    # when containing the south pole
    map_box.clear_hit_map()
    map_box.add((-120.5, -89.0))
    map_box.add((-120.5, -90.0))
    map_box.determine_plume_extent()

    s.map_projection = s.MapProjection.LAMBERT
    m = graph.MapProjection.create_instance(s, [-125.0, -89.0], 1.3, [1.0, 1.0], map_box)
    assert isinstance(m, graph.PolarProjection)


def test_MapProjection_refine_corners__lambert():
    s = plot.TrajectoryPlotSettings()
    s.map_projection = plot.TrajectoryPlotSettings.MapProjection.LAMBERT
    s.center_loc = [-125.0, 45.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    testMapBox = create_map_box(s)
    m = graph.MapProjection.create_instance(s, [-125.0, 45.0], 1.3, [1.0, 1.0], testMapBox)

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
    s.map_projection = plot.TrajectoryPlotSettings.MapProjection.POLAR
    s.center_loc = [-125.0, 85.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    testMapBox = create_map_box(s)
    m = graph.MapProjection.create_instance(s, [-125.0, 85.0], 1.3, [1.0, 1.0], testMapBox)

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
    s.map_projection = plot.TrajectoryPlotSettings.MapProjection.MERCATOR
    s.center_loc = [-125.0, 45.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    testMapBox = create_map_box(s)
    m = graph.MapProjection.create_instance(s, [-125.0, 45.0], 1.3, [1.0, 1.0], testMapBox)

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
    s.map_projection = plot.TrajectoryPlotSettings.MapProjection.CYL_EQU
    s.center_loc = [-125.0, 5.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    testMapBox = create_map_box(s)
    m = graph.MapProjection.create_instance(s, [-125.0, 5.0], 1.3, [1.0, 1.0], testMapBox)

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
    m = graph.MapProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
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
    m = graph.MapProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    cnr = [ 491.326538, 508.673462, 493.328094, 506.671906 ]
    assert m.zoom_corners(cnr, 0.5) == pytest.approx((486.989807, 513.010193, 489.992126, 510.007874))


def test_MapProjection_round_map_corners():
    s = plot.TrajectoryPlotSettings()
    m = graph.MapProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    cnr = [486.989807, 513.010193, 489.992126, 510.007874]
    assert m.round_map_corners(cnr) == pytest.approx((487.0, 513.0, 490.0, 510.0))


def test_MapProjection_calc_corners_lonlat(lambert_proj):
    c = lambert_proj.calc_corners_lonlat([487.0, 513.0, 490.0, 510.0])
    assert c == pytest.approx((-132.642365, -116.065727, 40.2330704, 49.1701241))


def test_MapProjection_need_pole_exclusion():
    s = plot.TrajectoryPlotSettings()
    m = graph.MapProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
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
    s.map_projection = plot.TrajectoryPlotSettings.MapProjection.LAMBERT
    s.center_loc = [-125.0, 45.0]
    s.ring_number = 4
    s.ring_distance = 0.0
    map_box = create_map_box(s)
    proj = graph.LambertProjection(s, s.center_loc, 1.3, [1.0, 1.0])

    proj.do_initial_estimates(map_box, [-125.0, 45.0])

    assert proj.corners_xy == pytest.approx((499.206848, 500.779419,
                                             493.325073, 506.674988))
    assert proj.corners_lonlat == pytest.approx((-125.479248, -124.476982,
                                                41.9989433, 47.9988670))
    assert proj.center_loc == pytest.approx((-125.004364, 45.0000114))


def test_MapProjection_sanity_check():
    s = plot.TrajectoryPlotSettings()
    m = graph.MapProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.sanity_check() == True


def test_MapProjection_create_proper_projection():
    s = plot.TrajectoryPlotSettings()
    m = graph.MapProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    try:
        m.create_proper_instance(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
        pytest.fail("expected an exception")
    except Exception as ex:
        str(ex) == "This should not happen"


def test_MapProjection_create_crs():
    s = plot.TrajectoryPlotSettings()
    m = graph.MapProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    try:
        m.create_crs()
        pytest.fail("expected an exception")
    except Exception as ex:
        str(ex) == "This should not happen"


def test_LambertProjection___init__():
    s = plot.TrajectoryPlotSettings()
    m = graph.LambertProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.settings is not None
    assert m.proj_type == plot.TrajectoryPlotSettings.MapProjection.LAMBERT
    assert isinstance(m.coord, graph.LambertCoordinate)


def test_LambertProjection_sanity_check(lambert_proj):
    assert lambert_proj.sanity_check() == True

    c = list(lambert_proj.corners_xy)
    c[3] = 10000.0
    lambert_proj.corners_xy = c
    assert lambert_proj.sanity_check() == False


def test_LambertProjection_create_proper_projection(lambert_proj):
    m = lambert_proj
    o = lambert_proj.create_proper_projection(m.settings, m.center_loc, m.scale, m.deltas)
    assert isinstance(o, graph.PolarProjection)


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
    m = graph.PolarProjection(s, [-125.0, 85.0], 1.3, [1.0, 1.0])
    assert m.settings is not None
    assert m.proj_type == plot.TrajectoryPlotSettings.MapProjection.POLAR
    assert isinstance(m.coord, graph.PolarCoordinate)


def test_PolarProjection_create_crs():
    s = plot.TrajectoryPlotSettings()
    m = graph.PolarProjection(s, [-125.0, 85.0], 1.3, [1.0, 1.0])
    o = m.create_crs()
    assert isinstance(o, cartopy.crs.NorthPolarStereo)

    m = graph.PolarProjection(s, [-125.0, -85.0], 1.3, [1.0, 1.0])
    o = m.create_crs()
    assert isinstance(o, cartopy.crs.SouthPolarStereo)


def test_MercatorProjection___init__():
    s = plot.TrajectoryPlotSettings()
    m = graph.MercatorProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.settings is not None
    assert m.proj_type == plot.TrajectoryPlotSettings.MapProjection.MERCATOR
    assert isinstance(m.coord, graph.MercatorCoordinate)


def test_MercatorProjection_need_pole_exclusion():
    s = plot.TrajectoryPlotSettings()
    m = graph.MercatorProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.need_pole_exclusion([-135.0, -115.0,-81.0, 55.0]) == True
    assert m.need_pole_exclusion([-135.0, -115.0,-80.0, 55.0]) == False
    assert m.need_pole_exclusion([-135.0, -115.0,-35.0, 55.0]) == False
    assert m.need_pole_exclusion([-135.0, -115.0, 35.0, 55.0]) == False
    assert m.need_pole_exclusion([-135.0, -115.0, 35.0, 80.0]) == False
    assert m.need_pole_exclusion([-135.0, -115.0, 35.0, 80.1]) == True


def test_MercatorProjection_create_crs():
    s = plot.TrajectoryPlotSettings()
    m = graph.MercatorProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    o = m.create_crs()
    assert isinstance(o, cartopy.crs.Mercator)


def test_CylindricalEquidistantProjection___init__():
    s = plot.TrajectoryPlotSettings()
    m = graph.CylindricalEquidistantProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    assert m.settings is not None
    assert m.proj_type == plot.TrajectoryPlotSettings.MapProjection.CYL_EQU
    assert isinstance(m.coord, graph.CylindricalCoordinate)


def test_CylindricalEquidistantProjection_create_crs():
    s = plot.TrajectoryPlotSettings()
    m = graph.CylindricalEquidistantProjection(s, [-125.0, 45.0], 1.3, [1.0, 1.0])
    o = m.create_crs()
    assert isinstance(o, cartopy.crs.LambertCylindrical)


def test_LabelsConfig___init__():
    c = graph.LabelsConfig()
    assert c.cfg is not None


def test_LabelsConfig_get():
    c = graph.LabelsConfig()
    assert c.get("TITLE") == "NOAA HYSPLIT MODEL"
    assert c.get("NONEXISTENT") == ""


def test_LabelsConfig_get_reader():
    c = graph.LabelsConfig()
    r = c.get_reader()
    assert isinstance(r, graph.LabelsConfigReader)
    assert r.obj == c


def test_LabelsConfig_after_reading_file():
    c = graph.LabelsConfig()
    s = plot.TrajectoryPlotSettings()
    assert s.height_unit == s.HeightUnit.METER
    c.after_reading_file(s)
    assert s.height_unit == s.HeightUnit.METER
    c.cfg["VUNIT"] = "FEET"
    c.after_reading_file(s)
    assert s.height_unit == s.HeightUnit.FEET
    

def test_LabelsConfigReader_read():
    c = graph.LabelsConfig()
    r = c.get_reader()
    o = r.read("data/LABELS.CFG")
    assert isinstance(o, graph.LabelsConfig)
    assert c.get("TITLE") == "Sagebrush Exp #5"
    assert c.get("MAPID") == "Air Concentration"
    assert c.get("LAYER") == " between"
    assert c.get("UNITS") == "ppt"
    assert c.get("VOLUM") == ""
    assert c.get("RELEASE") == ""

    # create a scratch file.
    with open("__scratch.cfg", "wt") as f:
        f.write("'NTXBOXL&','2&'\n")
        f.write("'TXBOXL&','line 1&'\n")
        f.write("'TXBOXL&','line 2&'\n")

    c = graph.LabelsConfig()
    c.get_reader().read("__scratch.cfg")
    assert c.get("NTXBOXL") == "2"
    assert c.get("TXBOXL") == ["line 1", "line 2"]

    # when the CFG file has an issue
    with open("__scratch.cfg", "wt") as f:
        f.write("'TXBOXL&','line 1&'\n")
        f.write("'TXBOXL&','line 2&'\n")
        f.write("'NTXBOXL&','2&'\n")

    c = graph.LabelsConfig()
    try:
        c.get_reader().read("__scratch.cfg")
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "Consistency check failed. Please fix __scratch.cfg"

    os.remove("__scratch.cfg")


def test_LabelsConfigReader_check_consistency():
    r = graph.LabelsConfig().get_reader()
    assert r.check_consistency("data/LABELS.CFG") == True

    # when TXBOXL appears before NTXBOXL
    with open("__scratch.cfg", "wt") as f:
        f.write("'TXBOXL&','line 1&'\n")
        f.write("'NTXBOXL&','2&'\n")

    c = graph.LabelsConfig()
    assert c.get_reader().check_consistency("__scratch.cfg") == False

    # when the TXBOXL count is not equal to NTXBOXL
    with open("__scratch.cfg", "wt") as f:
        f.write("'NTXBOXL&','2&'\n")
        f.write("'TXBOXL&','line 1&'\n")
        f.write("'TITLE&','MODEL&'\n")

    c = graph.LabelsConfig()
    assert c.get_reader().check_consistency("__scratch.cfg") == False

    os.remove("__scratch.cfg")


def test_LabelsConfigReader_parse_line():
    r = graph.LabelsConfig().get_reader()
    assert r.parse_line("'TITLE&','MODEL&'") == ("TITLE", "MODEL")
    assert r.parse_line("'TITLE&' , 'MODEL&'") == ("TITLE", "MODEL")
    assert r.parse_line("'TITLE&','MODEL ESCAPED '' &'") == ("TITLE", "MODEL ESCAPED ' ")


def test_StationPlotConfig___init__():
    c = graph.StationPlotConfig()
    assert c.stations is not None
    assert len(c.stations) == 0


def test_StationPlotConfig_get_reader():
    c = graph.StationPlotConfig()
    r = c.get_reader()
    assert isinstance(r, graph.StationPlotConfigReader)
    assert r.cfg is c


def test_Station___init__():
    s = graph.StationPlotConfig.Station(30.0, -120.0, "STATION")
    assert s.longitude == -120.0
    assert s.latitude == 30.0
    assert s.label == "STATION"


def test_StationPlotConfigReader___init__():
    c = graph.StationPlotConfig()
    r = graph.StationPlotConfigReader(c)
    assert r.cfg == c


def test_StationPlotConfigReader_read():
    r = graph.StationPlotConfig().get_reader()
    c = r.read("data/STATIONPLOT.CFG")
    assert isinstance(c, graph.StationPlotConfig)
    assert len(c.stations) == 3
    assert c.stations[0].latitude == 40.0
    assert c.stations[0].longitude == -125.0
    assert c.stations[0].label == "STATION_1"
    assert c.stations[1].latitude == 50.0
    assert c.stations[1].longitude == -90.0
    assert c.stations[1].label == "STATION_2"
    assert c.stations[2].latitude == 40.0
    assert c.stations[2].longitude == -90.0
    assert c.stations[2].label == ""


def test_ClusterList___init__():
    cl = graph.ClusterList(1)
    assert cl.percent is not None
    assert cl.start_index == 1
    assert cl.total_traj == 0


def test_ClusterList_get_label(clusterList):
    assert clusterList.get_label(-1) == ""
    assert clusterList.get_label(0) == "1 (30%)"
    assert clusterList.get_label(1) == "2 (10%)"
    assert clusterList.get_label(2) == "3 (38%)"
    assert clusterList.get_label(3) == "4 (22%)"
    assert clusterList.get_label(4) == ""


def test_ClusterList_get_reader():
    cl = graph.ClusterList(1)
    r = cl.get_reader()
    assert isinstance(r, graph.ClusterListReader)
    assert r.clist is cl
   
    
def test_ClusterList_clear(clusterList):
    assert len(clusterList.percent) == 4
    assert clusterList.total_traj > 0
    clusterList.clear()
    assert len(clusterList.percent) == 0
    assert clusterList.total_traj == 0
    

def test_ClusterListReader___init__():
    cl = graph.ClusterList(1)
    r = graph.ClusterListReader(cl)
    assert r.clist is cl


def test_ClusterListReader_read():
    r = graph.ClusterList(1).get_reader()
    cl = r.read("data/CLUSLIST_4")
    assert cl is r.clist
    assert len(cl.percent) == 4
    assert cl.total_traj == 112
    assert cl.percent[0] == 30
    assert cl.percent[1] == 10
    assert cl.percent[2] == 38
    assert cl.percent[3] == 22
    
    
def test_union_ranges():
    r = graph.union_ranges(None, None)
    assert r == None

    r = graph.union_ranges(None, [1, 3])
    assert r == [1, 3]

    r = graph.union_ranges([1, 3], None)
    assert r == [1, 3]

    r = graph.union_ranges([1, 3], [0, 2])
    assert r == [0, 3]
