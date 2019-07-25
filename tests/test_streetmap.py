import cartopy
import contextily
import matplotlib.pyplot as plt
import os
import pytest

from hysplitplot import const, mapbox, mapfile, mapproj, streetmap


class AbstractMapBackgroundTest(streetmap.AbstractMapBackground):
    
    def __init__(self):
        super(AbstractMapBackgroundTest, self).__init__()
    
    def draw_underlay(self, ax, crs):
        pass
    
    def update_extent(self, ax, projection, data_crs):
        pass
    
    def read_background_map(self, filename):
        pass
    

class AbstractStreetMapTest(streetmap.AbstractStreetMap):
    
    def __init__(self):
        super(AbstractStreetMapTest, self).__init__()
    
    @property
    def min_zoom(self):
        return 0
    
    @property
    def max_zoom(self):
        return 15
    
    @property
    def tile_url(self):
        return contextily.sources.ST_TERRAIN
    
    @property
    def attribution(self):
        return "copy left"
    
    
    
def test_MapBackgroundFactory_create_instance():
    o = streetmap.MapBackgroundFactory.create_instance(False, 0)
    assert isinstance(o, streetmap.HYSPLITMapBackground)
    
    o = streetmap.MapBackgroundFactory.create_instance(True, const.StreetMap.STAMEN_TERRAIN)
    assert isinstance(o, streetmap.StamenStreetMap)
    assert o.tile_url == contextily.sources.ST_TERRAIN
        
    o = streetmap.MapBackgroundFactory.create_instance(True, const.StreetMap.STAMEN_TONER)
    assert isinstance(o, streetmap.StamenStreetMap)
    assert o.tile_url == contextily.sources.ST_TONER_LITE
            
    o = streetmap.MapBackgroundFactory.create_instance(True, 999999)
    assert isinstance(o, streetmap.StamenStreetMap)
    assert o.tile_url == contextily.sources.ST_TERRAIN


def test_AbstractMapBackground___init__():
    o = AbstractMapBackgroundTest()
    assert o.map_color == "#1f77b4"
    assert o.color_mode == const.Color.COLOR
    assert o.lat_lon_label_interval_option == const.LatLonLabel.AUTO
    assert o.lat_lon_label_interval == pytest.approx(1.0)
    assert o.fix_map_color_fn is None


def test_AbstractMapBackground_set_color():
    o = AbstractMapBackgroundTest()
    o.set_color("r")
    assert o.map_color == "r"


def test_AbstractMapBackground_set_color_mode():
    o = AbstractMapBackgroundTest()
    assert o.color_mode == const.Color.COLOR
    o.set_color_mode( const.Color.BLACK_AND_WHITE )
    assert o.color_mode == const.Color.BLACK_AND_WHITE


def test_AbstractMapBackground_override_fix_map_color_fn():
    o = AbstractMapBackgroundTest()
    assert o.fix_map_color_fn is None
    o.override_fix_map_color_fn(lambda clr, mode: "b")
    assert o.fix_map_color_fn is not None
    assert o.fix_map_color_fn("r", 3) == "b"


def test_AbstractMapBackground_set_lat_lon_label_option():
    o = AbstractMapBackgroundTest()
    assert o.lat_lon_label_interval_option == const.LatLonLabel.AUTO
    assert o.lat_lon_label_interval == pytest.approx( 1.0 )
    o.set_lat_lon_label_option( const.LatLonLabel.SET, 0.25 )
    assert o.lat_lon_label_interval_option == const.LatLonLabel.SET
    assert o.lat_lon_label_interval == pytest.approx( 0.25 )


def test_HYSPLITMapBackground___init__():
    o = streetmap.HYSPLITMapBackground()
    assert o._GRIDLINE_DENSITY == pytest.approx( 0.25 )
    assert len(o.background_maps) == 0

 
def test_HYSPLITMapBackground_read_background_map():
    o = streetmap.HYSPLITMapBackground()
    o.read_background_map("data/arlmap_truncated")
    maps = o.background_maps

    assert maps is not None
    assert len(maps) > 0
    assert isinstance(maps[0], mapfile.DrawableBackgroundMap)
    assert maps[0].map.crs == mapproj.AbstractMapProjection._WGS84


def test_HYSPLITMapBackground__fix_arlmap_filename():
    assert streetmap.HYSPLITMapBackground._fix_arlmap_filename("data/arlmap_truncated") == "data/arlmap_truncated"
    assert streetmap.HYSPLITMapBackground._fix_arlmap_filename("data/nonexistent") == None


def test_HYSPLITMapBackground__fix_map_color():
    o = streetmap.HYSPLITMapBackground()

    color_mode = const.Color.BLACK_AND_WHITE
    assert o._fix_map_color('#6699cc', color_mode) == 'k' # black

    color_mode = const.Color.COLOR
    assert o._fix_map_color('#6699cc', color_mode) == '#6699cc'

    color_mode = const.Color.ITEMIZED
    assert o._fix_map_color('#6699cc', color_mode) == '#6699cc'

    o.override_fix_map_color_fn(lambda clr, mode: "r")
    assert o._fix_map_color('#6699cc', color_mode) == 'r'


def test_HYSPLITMapBackground_draw_underlay():
    o = streetmap.HYSPLITMapBackground()
        
    projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    projection.corners_xy = [1.0, 500.0, 1.0, 500.0]
    projection.corners_lonlat = [-95.0, -75.0, 25.0, 45.0]
    data_crs = cartopy.crs.PlateCarree()
    
    axes = plt.axes(projection=projection.crs)

    # with no map
    try:
        o.draw_underlay(axes, data_crs)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))

    # with an arlmap
    o.read_background_map("data/arlmap_truncated")
    try:
        o.draw_underlay(axes, data_crs)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))
    
    # with a shapefile
    os.chdir("data")
    o.read_background_map("shapefiles_arl.txt")
    try:
        o.draw_underlay(axes, data_crs)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))
    os.chdir("..")
    plt.close(axes.figure)


def test_HYSPLITMapBackground_update_extent():
    o = streetmap.HYSPLITMapBackground()
    
    projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    projection.corners_xy = [1.0, 500.0, 1.0, 500.0]
    projection.corners_lonlat = [-95.0, -75.0, 25.0, 45.0]
    data_crs = cartopy.crs.PlateCarree()
    
    axes = plt.axes(projection=projection.crs)

    try:
        o.update_extent(axes, projection, data_crs)
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))
    

def test_HYSPLITMapBackground__update_gridlines():
    o = streetmap.HYSPLITMapBackground()
    
    projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    projection.corners_xy = [1.0, 500.0, 1.0, 500.0]
    projection.corners_lonlat = [-95.0, -75.0, 25.0, 45.0]
    data_crs = cartopy.crs.PlateCarree()
    
    axes = plt.axes(projection=projection.crs)

    try:
        o._update_gridlines(axes, projection, data_crs, 'k', const.LatLonLabel.AUTO, 1.0)
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_HYSPLITMapBackground__get_gridline_spacing():
    o = streetmap.HYSPLITMapBackground()
    assert o._get_gridline_spacing([-130.0, -110.0, 45.0, 55.0], const.LatLonLabel.NONE, 1.0) == 0.0
    assert o._get_gridline_spacing([-130.0, -110.0, 45.0, 55.0], const.LatLonLabel.SET, 3.14) == 3.14
    assert o._get_gridline_spacing([-130.0, -110.0, 45.0, 55.0], const.LatLonLabel.AUTO, 1.0) == 5.0
    
    
def test_HYSPLITMapBackground__calc_gridline_spacing():
    o = streetmap.HYSPLITMapBackground()
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
    o = streetmap.HYSPLITMapBackground()
    
    projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    map_box = mapbox.MapBox()
    map_box.allocate()
    map_box.add((-120.5, 45.5))
    map_box.determine_plume_extent()
    projection.do_initial_estimates(map_box, [-125.0, 45.0])
    
    data_crs = cartopy.crs.PlateCarree()
    
    axes = plt.axes()
    
    try:
        o._draw_latlon_labels(axes, projection, data_crs, 1.0, 1.0, 'k')
        plt.close(axes.figure)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))


def test_AbstractStreetMap___init__():
    o = AbstractStreetMapTest()
    assert len(o.tile_widths) > 0
    assert o.last_extent is None


def test_AbstractStreetMap__compute_tile_widths():
    o = AbstractStreetMapTest()
    w = o._compute_tile_widths()
    assert o.min_zoom == 0
    assert o.max_zoom == 15
    assert len(w) == 16
    assert w[0] == pytest.approx( 360.0 )
    assert w[1] == pytest.approx( 180.0 )
    assert w[2] == pytest.approx(  90.0 )
    assert w[3] == pytest.approx(  45.0 )
    assert w[4] == pytest.approx(  22.5 )
    

def test_AbstractStreetMap__compute_initial_zoom():
    o = AbstractStreetMapTest()
    latb = 30.0; latt = 35.0;
    assert o._compute_initial_zoom(0.0, latb, 360.0, latt) == 0
    assert o._compute_initial_zoom(0.0, latb, 185.0, latt) == 1
    assert o._compute_initial_zoom(0.0, latb, 180.0, latt) == 1
    assert o._compute_initial_zoom(0.0, latb,  95.0, latt) == 2
    assert o._compute_initial_zoom(0.0, latb,  90.0, latt) == 2


def test_AbstractStreetMap_update_extent():
    o = AbstractStreetMapTest()
    
    projection = mapproj.LambertProjection(const.MapProjection.LAMBERT, 0.5, [-125.0, 45.0], 1.3, [1.0, 1.0])
    projection.corners_xy = [1.0, 500.0, 1.0, 500.0]
    projection.corners_lonlat = [-95.0, -75.0, 25.0, 45.0]
    data_crs = cartopy.crs.PlateCarree()
    
    axes = plt.axes(projection=projection.crs)

    try:
        o.update_extent(axes, projection, data_crs)
    except Exception as ex:
        raise pytest.fail("unexpeced exception: {0}".format(ex))
    
    plt.close(axes.figure)


def test_AbstractStreetMap_draw():
    ax = plt.axes()
    ax.axis( (-85.0, -80.0, 30.0, 40.0) )
    o = AbstractStreetMapTest()

    try:
        corners_xy = (-85.0, -80.0, 30.0, 40.0)
        corners_lonlat = (-85.0, -80.0, 30.0, 40.0)
        o.draw(ax, corners_xy, corners_lonlat)
        plt.close(ax.get_figure())
    except Exception as ex:
        pytest.fail("Unexpected exception: {}".format(ex))

    assert o.last_extent is not None


def test_StamenStreetMap___init__():
    o = streetmap.StamenStreetMap("TERRAIN")
    assert o.min_zoom == 0
    assert o.max_zoom == 15
    assert o.tile_url == contextily.sources.ST_TERRAIN
    assert o.attribution.startswith("Map tiles by Stamen Design,")

    o = streetmap.StamenStreetMap("TONER")
    assert o.min_zoom == 0
    assert o.max_zoom == 15
    assert o.tile_url == contextily.sources.ST_TONER_LITE
    assert o.attribution.startswith("Map tiles by Stamen Design,")

    o = streetmap.StamenStreetMap("UNKNOWN")
    assert o.min_zoom == 0
    assert o.max_zoom == 15
    assert o.tile_url == contextily.sources.ST_TERRAIN
    assert o.attribution.startswith("Map tiles by Stamen Design,")  
    
