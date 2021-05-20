# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_streetmap.py
#
# Performs unit tests on functions and class methods declared in streetmap.py.
# ---------------------------------------------------------------------------

import cartopy
import contextily
import geopandas
import matplotlib.pyplot as plt
import os
import pytest
import shapely.geometry

from hysplitplot import const, mapbox, mapfile, mapproj, streetmap


@pytest.fixture
def web_merc_proj():
    projection = mapproj.WebMercatorProjection(const.MapProjection.WEB_MERCATOR, 0.5, [166.739998, -42.369147], 1.3, [1.0, 1.0])
    projection.corners_xy = (-960687.0, 4469478.0, -7931520.0, -2501355.0)
    projection.corners_lonlat = (142.35, -168.87, -57.8292, -21.9153)
    return projection


@pytest.fixture
def lambert_proj():
    projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    projection.corners_xy = [1.0, 500.0, 1.0, 500.0]
    projection.corners_lonlat = [-95.0, -75.0, 25.0, 45.0]
    return projection


class AbstractMapBackgroundTest(streetmap.AbstractMapBackground):
    
    def __init__(self, projection):
        super(AbstractMapBackgroundTest, self).__init__(projection)
    
    def draw_underlay(self, ax, corners_xy, crs):
        pass
    
    def update_extent(self, ax, projection, data_crs):
        pass
    
    def read_background_map(self, filename):
        pass
    

class AbstractStreetMapTest(streetmap.AbstractStreetMap):
    
    def __init__(self, projection):
        super(AbstractStreetMapTest, self).__init__(projection)
    
    @property
    def min_zoom(self):
        return 0
    
    @property
    def max_zoom(self):
        return 15

    @property
    def tile_provider(self):
        return contextily.providers.Stamen.Terrain
    
    @property
    def attribution(self):
        return "copy left"
    
    
    
def test_MapBackgroundFactory_create_instance(web_merc_proj):
    # when use_street_map is false.
    o = streetmap.MapBackgroundFactory.create_instance(web_merc_proj, False, 0)
    assert isinstance(o, streetmap.HYSPLITMapBackground)
    
    o = streetmap.MapBackgroundFactory.create_instance(web_merc_proj, True, const.StreetMap.STAMEN_TERRAIN)
    assert isinstance(o, streetmap.StamenStreetMap)
    assert o.tile_provider.url == contextily.providers.Stamen.Terrain.url
        
    o = streetmap.MapBackgroundFactory.create_instance(web_merc_proj, True, const.StreetMap.STAMEN_TONER)
    assert isinstance(o, streetmap.StamenStreetMap)
    assert o.tile_provider.url == contextily.providers.Stamen.TonerLite.url
    
    # when an invalid street map type is used.
    o = streetmap.MapBackgroundFactory.create_instance(web_merc_proj, True, 999999)
    assert isinstance(o, streetmap.StamenStreetMap)
    assert o.tile_provider.url == contextily.providers.Stamen.Terrain.url

    # when a non-WEB-MERCATOR projection is used.
    m = mapproj.PolarProjection(const.MapProjection.POLAR, 0.5, [-125.0, 85.0], 1.3, [1.0, 1.0])
    o = streetmap.MapBackgroundFactory.create_instance(m, True, const.StreetMap.STAMEN_TERRAIN)
    assert isinstance(o, streetmap.HYSPLITMapBackground)
    

def test_AbstractMapBackground___init__(web_merc_proj):
    o = AbstractMapBackgroundTest(web_merc_proj)
    assert o.map_color == "#1f77b4"
    assert o.color_mode == const.Color.COLOR
    assert o.lat_lon_label_interval_option == const.LatLonLabel.AUTO
    assert o.lat_lon_label_interval == pytest.approx(1.0)
    assert o.fix_map_color_fn is None
    assert len(o.text_objs) == 0
    

def test_AbstractMapBackground_set_color(web_merc_proj):
    o = AbstractMapBackgroundTest(web_merc_proj)
    o.set_color("r")
    assert o.map_color == "r"


def test_AbstractMapBackground_set_color_mode(web_merc_proj):
    o = AbstractMapBackgroundTest(web_merc_proj)
    assert o.color_mode == const.Color.COLOR
    o.set_color_mode( const.Color.BLACK_AND_WHITE )
    assert o.color_mode == const.Color.BLACK_AND_WHITE


def test_AbstractMapBackground_override_fix_map_color_fn(web_merc_proj):
    o = AbstractMapBackgroundTest(web_merc_proj)
    assert o.fix_map_color_fn is None
    o.override_fix_map_color_fn(lambda clr, mode: "b")
    assert o.fix_map_color_fn is not None
    assert o.fix_map_color_fn("r", 3) == "b"


def test_AbstractMapBackground_set_lat_lon_label_option(web_merc_proj):
    o = AbstractMapBackgroundTest(web_merc_proj)
    assert o.lat_lon_label_interval_option == const.LatLonLabel.AUTO
    assert o.lat_lon_label_interval == pytest.approx( 1.0 )
    o.set_lat_lon_label_option( const.LatLonLabel.SET, 0.25 )
    assert o.lat_lon_label_interval_option == const.LatLonLabel.SET
    assert o.lat_lon_label_interval == pytest.approx( 0.25 )


def test_AbstractMapBackground_clear_text_objs(web_merc_proj):
    o = AbstractMapBackgroundTest(web_merc_proj)
    axes = plt.axes()
    t = axes.text(0, 0, "test")
    assert len(axes.texts) == 1
    o.text_objs.append(t)
    
    o.clear_text_objs(axes)
    
    assert len(o.text_objs) == 0
    assert len(axes.texts) == 0
    
    plt.close(axes.figure)

    
def test_HYSPLITMapBackground___init__(lambert_proj):
    o = streetmap.HYSPLITMapBackground(lambert_proj)
    assert o._GRIDLINE_DENSITY == pytest.approx( 0.25 )
    assert len(o.background_maps) == 0
    assert hasattr(o, "frozen_collection_count") and o.frozen_collection_count is None

 
def test_HYSPLITMapBackground_read_background_map(lambert_proj):
    o = streetmap.HYSPLITMapBackground(lambert_proj)
    o.read_background_map("data/arlmap_truncated")
    maps = o.background_maps

    assert maps is not None
    assert len(maps) > 0
    assert isinstance(maps[0], mapfile.DrawableBackgroundMap)
    assert maps[0].map.crs == mapproj.AbstractMapProjection._WGS84


def test_HYSPLITMapBackground__fix_arlmap_filename():
    assert streetmap.HYSPLITMapBackground._fix_arlmap_filename("data/arlmap_truncated") == "data/arlmap_truncated"
    assert streetmap.HYSPLITMapBackground._fix_arlmap_filename("data/nonexistent") == None


def test_HYSPLITMapBackground__fix_map_color(lambert_proj):
    o = streetmap.HYSPLITMapBackground(lambert_proj)

    color_mode = const.Color.BLACK_AND_WHITE
    assert o._fix_map_color('#6699cc', color_mode) == 'k' # black

    color_mode = const.Color.COLOR
    assert o._fix_map_color('#6699cc', color_mode) == '#6699cc'

    color_mode = const.Color.ITEMIZED
    assert o._fix_map_color('#6699cc', color_mode) == '#6699cc'

    o.override_fix_map_color_fn(lambda clr, mode: "r")
    assert o._fix_map_color('#6699cc', color_mode) == 'r'


def test_HYSPLITMapBackground__is_crossing_bounds(lambert_proj):
    o = streetmap.HYSPLITMapBackground(lambert_proj)
    outside = lambda x: x < -10 or x > 10
    assert o._is_crossing_bounds([6, 8, 10, -9], outside) == False
    assert o._is_crossing_bounds([-5, -2, 2, 5], outside) == False
    assert o._is_crossing_bounds([8, 10, 12, -10], outside) == True


def test_HYSPLITMapBackground__remove_spurious_hlines(lambert_proj):
    o = streetmap.HYSPLITMapBackground(lambert_proj)
    corners_xy = [-50, 50, -80, 80]
    data_crs = cartopy.crs.Geodetic()
    
    try:
        o._remove_spurious_hlines(data_crs, corners_xy, data_crs)
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex).startswith("Unexpected map type")

    a = shapely.geometry.LineString([[-10, 0], [10, 0]])
    g = geopandas.GeoSeries(a)
    fixed = o._remove_spurious_hlines(g, corners_xy, data_crs)
    assert len(fixed.values) == 1
        
    # a geometry object that crosses the longitudinal bound
    a = shapely.geometry.LineString([[-51, 0], [50, 0]])
    g = geopandas.GeoSeries(a)
    fixed = o._remove_spurious_hlines(g, corners_xy, data_crs)
    assert len(fixed.values) == 0
        
    a = shapely.geometry.Polygon([[-10, 0], [10, 0], [-10, 0]])
    g = geopandas.GeoSeries(a)
    fixed = o._remove_spurious_hlines(g, corners_xy, data_crs)
    assert len(fixed.values) == 1
    
    a = shapely.geometry.Polygon([[-51, 0], [50, 0], [-51, 0]])
    g = geopandas.GeoSeries(a)
    fixed = o._remove_spurious_hlines(g, corners_xy, data_crs)
    assert len(fixed.values) == 0
            
    a = shapely.geometry.MultiLineString([[[-10, 0], [10, 0]]])
    g = geopandas.GeoSeries(a)
    fixed = o._remove_spurious_hlines(g, corners_xy, data_crs)
    assert len(fixed.values) == 1
    
    a = shapely.geometry.MultiLineString([[[-51, 0], [50, 0]]])
    g = geopandas.GeoSeries(a)
    fixed = o._remove_spurious_hlines(g, corners_xy, data_crs)
    assert len(fixed.values) == 0
    
    a = shapely.geometry.MultiPolygon([(
        ((-10, 0), (0, 10), (10, 0), (-10, 0)),
        [((0.1,0.1), (0.1,0.2), (0.2,0.2), (0.2,0.1))]
    )])
    g = geopandas.GeoSeries(a)
    fixed = o._remove_spurious_hlines(g, corners_xy, data_crs)
    assert len(fixed.values) == 1
    
    a = shapely.geometry.MultiPolygon([(
        ((-51, 0), (50, 0), (25, 10), (-51, 0)),
        [((0.1,0.1), (0.1,0.2), (0.2,0.2), (0.2,0.1))]
    )])
    g = geopandas.GeoSeries(a)
    fixed = o._remove_spurious_hlines(g, corners_xy, data_crs)
    assert len(fixed.values) == 0
    
    a = shapely.geometry.Point( (100, 100) )
    g = geopandas.GeoSeries(a)
    try:
        fixed = o._remove_spurious_hlines(g, corners_xy, data_crs)
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex).startswith("Unexpected geometry type")


def test_HYSPLITMapBackground_draw_underlay(lambert_proj):
    o = streetmap.HYSPLITMapBackground(lambert_proj)
    data_crs = cartopy.crs.Geodetic()
    axes = plt.axes(projection=lambert_proj.crs)

    # with no map
    o.frozen_collection_count = 1
    try:
        o.draw_underlay(axes, lambert_proj.corners_xy, data_crs)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))
    assert o.frozen_collection_count is None

    # with an arlmap
    o.frozen_collection_count = 1
    o.read_background_map("data/arlmap_truncated")
    try:
        o.draw_underlay(axes, lambert_proj.corners_xy, data_crs)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))
    assert o.frozen_collection_count is None
    
    # with a shapefile
    os.chdir("data")
    o.frozen_collection_count = 1
    o.read_background_map("shapefiles_arl.txt")
    try:
        o.draw_underlay(axes, lambert_proj.corners_xy, data_crs)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))
    assert o.frozen_collection_count is None
    os.chdir("..")
    plt.close(axes.figure)


def test_HYSPLITMapBackground_update_extent(lambert_proj):
    o = streetmap.HYSPLITMapBackground(lambert_proj)
    data_crs = cartopy.crs.Geodetic()
    axes = plt.axes(projection=lambert_proj.crs)

    try:
        o.update_extent(axes, data_crs)
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))
   

def test_HYSPLITMapBackground__erase_gridlines(lambert_proj):
    o = streetmap.HYSPLITMapBackground(lambert_proj)
    data_crs = cartopy.crs.Geodetic()
    axes = plt.axes(projection=lambert_proj.crs)

    axes.collections.append( 0 )

    o._erase_gridlines(axes)
    
    assert o.frozen_collection_count == 1

    axes.collections.append( 1 )
    axes.collections.append( 2 )
    
    o._erase_gridlines(axes)
    
    assert len(axes.collections) == 1
    
    plt.close(axes.figure)
        

def test_HYSPLITMapBackground__update_gridlines(lambert_proj):
    o = streetmap.HYSPLITMapBackground(lambert_proj)
    data_crs = cartopy.crs.Geodetic()
    axes = plt.axes(projection=lambert_proj.crs)

    try:
        o._update_gridlines(axes, lambert_proj, data_crs, 'k', const.LatLonLabel.AUTO, 1.0)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))
    
    #assert len(o.text_objs) > 0
    assert o.frozen_collection_count is not None
    plt.close(axes.figure)


def test_HYSPLITMapBackground__get_gridline_spacing(lambert_proj):
    o = streetmap.HYSPLITMapBackground(lambert_proj)
    assert o._get_gridline_spacing([-130.0, -110.0, 45.0, 55.0], const.LatLonLabel.NONE, 1.0) == 0.0
    assert o._get_gridline_spacing([-130.0, -110.0, 45.0, 55.0], const.LatLonLabel.SET, 3.14) == 3.14
    assert o._get_gridline_spacing([-130.0, -110.0, 45.0, 55.0], const.LatLonLabel.AUTO, 1.0) == 5.0
    
    
def test_HYSPLITMapBackground__calc_gridline_spacing(lambert_proj):
    o = streetmap.HYSPLITMapBackground(lambert_proj)
    assert o._calc_gridline_spacing([-130.0, -110.0, 45.0, 55.0]) == 5.0
    assert o._calc_gridline_spacing([-120.0, -110.0, 35.0, 55.0]) == 5.0
    # across the dateline
    assert o._calc_gridline_spacing([+350.0, -10.0, 35.0, 55.0]) == 5.0
    # test min.
    assert o._calc_gridline_spacing([0.0, 0.1, 0.0, 0.1]) == 0.2
    

def test_HYSPLITMapBackground__collect_tick_values():
    t = streetmap.HYSPLITMapBackground._collect_tick_values(-1800, 1800, 100, 0.1, (-120, -80))
    assert t == pytest.approx((-130, -120, -110, -100, -90, -80, -70))


def test_HYSPLITMapBackground__draw_latlon_labels():
    projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    map_box = mapbox.MapBox()
    map_box.allocate()
    map_box.add((-120.5, 45.5))
    map_box.determine_plume_extent()
    projection.do_initial_estimates(map_box, [-125.0, 45.0])
    
    o = streetmap.HYSPLITMapBackground(projection)

    data_crs = cartopy.crs.Geodetic()
    
    axes = plt.axes()
    
    try:
        o._draw_latlon_labels(axes, projection, data_crs, 1.0, 1.0, 'k')
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))


def test_AbstractStreetMap___init__(web_merc_proj):
    o = AbstractStreetMapTest(web_merc_proj)
    assert len(o.tile_widths) > 0
    assert o.last_extent is None


def test_AbstractStreetMap__compute_tile_widths(web_merc_proj):
    o = AbstractStreetMapTest(web_merc_proj)
    w = o._compute_tile_widths()
    assert o.min_zoom == 0
    assert o.max_zoom == 15
    assert len(w) == 16
    assert w[0] == pytest.approx( 360.0 )
    assert w[1] == pytest.approx( 180.0 )
    assert w[2] == pytest.approx(  90.0 )
    assert w[3] == pytest.approx(  45.0 )
    assert w[4] == pytest.approx(  22.5 )


def test_AbstractStreetMap__compute_initial_zoom(web_merc_proj):
    o = AbstractStreetMapTest(web_merc_proj)
    latb = 30.0; latt = 35.0;
    assert o._compute_initial_zoom(0.0, latb, 360.0, latt) == 0
    assert o._compute_initial_zoom(0.0, latb, 185.0, latt) == 1
    assert o._compute_initial_zoom(0.0, latb, 180.0, latt) == 1
    assert o._compute_initial_zoom(0.0, latb,  95.0, latt) == 2
    assert o._compute_initial_zoom(0.0, latb,  90.0, latt) == 2
    assert o._compute_initial_zoom(135.0, latb, -135.0, latt) == 2


def test_AbstractStreetMap_draw_underlay(web_merc_proj):
    o = AbstractStreetMapTest(web_merc_proj)
    o.last_extent = (1.0, 2.0, 3.0, 4.0)
    o.draw_underlay(None, (0.1, 0.2, 0.3, 0.4), None)
    assert o.last_extent is None


def test_AbstractStreetMap_update_extent(web_merc_proj):
    o = AbstractStreetMapTest(web_merc_proj)
    data_crs = cartopy.crs.Geodetic()
    
    axes = plt.axes(projection=web_merc_proj.crs)

    try:
        o.update_extent(axes, data_crs)
    except Exception as ex:
        raise pytest.fail("unexpected exception: {0}".format(ex))
    
    assert o.projection is web_merc_proj
    
    plt.close(axes.figure)


def test_AbstractStreetMap__compute_tile_count(web_merc_proj):
    o = AbstractStreetMapTest(web_merc_proj)
    assert o._compute_tile_count(-20.0, 20.0, 35.0, 65.0, 3) == 4
    assert o._compute_tile_count(142.35, -168.87, -58.07, -21.50, 3) == 2


def test_AbstractStreetMap__reproject_extent(web_merc_proj):
    o = AbstractStreetMapTest(web_merc_proj)

    ext = o._reproject_extent( (15028131.3, 20037508.3, -10018754.2, 0.0) )
    assert ext == pytest.approx( (-3533280.4, 1476096.6, -10018754.2, 0.0) )


def test_AbstractStreetMap__fetch_tiles(web_merc_proj):
    o = AbstractStreetMapTest(web_merc_proj)
    
    t = o._fetch_tiles(142.35, -168.87, -57.8292, -21.9153, 2)
    assert len(t) == 2
    assert t[0][1] == pytest.approx( (-8542657.5,  1476096.7, -10018754.2, -1.4162309e-09), abs=1.0)
    assert t[1][1] == pytest.approx( ( 1476096.7, 11494850.8, -10018754.2, -1.4162309e-09), abs=1.0)


def test_AbstractStreetMap_draw(lambert_proj):
    data_crs = cartopy.crs.Geodetic()
    
    ax = plt.axes(projection=lambert_proj.crs)
    ax.axis( (-85.0, -80.0, 30.0, 40.0) )
    o = AbstractStreetMapTest(lambert_proj)
    assert o.projection is lambert_proj

    try:
        corners_xy = (-85.0, -80.0, 30.0, 40.0)
        corners_lonlat = (-85.0, -80.0, 30.0, 40.0)
        o.draw(ax, corners_xy, corners_lonlat)
        plt.close(ax.get_figure())
    except Exception as ex:
        pytest.fail("Unexpected exception: {}".format(ex))

    assert o.last_extent is not None


def test_StamenStreetMap___init__(web_merc_proj):
    o = streetmap.StamenStreetMap(web_merc_proj, "TERRAIN")
    assert o.min_zoom == 0
    assert o.max_zoom == 15
    assert o.tile_provider.url == contextily.providers.Stamen.Terrain.url
    assert o.attribution.startswith("Map tiles by Stamen Design,")

    o = streetmap.StamenStreetMap(web_merc_proj, "TONER")
    assert o.min_zoom == 0
    assert o.max_zoom == 15
    assert o.tile_provider.url == contextily.providers.Stamen.TonerLite.url
    assert o.attribution.startswith("Map tiles by Stamen Design,")

    o = streetmap.StamenStreetMap(web_merc_proj, "UNKNOWN")
    assert o.min_zoom == 0
    assert o.max_zoom == 15
    assert o.tile_provider.url == contextily.providers.Stamen.Terrain.url
    assert o.attribution.startswith("Map tiles by Stamen Design,")  
 

def test_StamenStreetMap_min_zoom():
    # Tested by test_StamenStreetMap___init__.
    pass
 

def test_StamenStreetMap_max_zoom():
    # Tested by test_StamenStreetMap___init__.
    pass
 

def test_StamenStreetMap_tile_provider():
    # Tested by test_StamenStreetMap___init__.
    pass
 

def test_StamenStreetMap_attribution():
    # Tested by test_StamenStreetMap___init__.
    pass

