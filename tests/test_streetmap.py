import matplotlib.pyplot as plt
import pytest

from hysplitplot import streetmap


def test_StreetMap___init__():
    o = streetmap.StreetMap()
    assert o.min_zoom == 0
    assert o.max_zoom > o.min_zoom and o.max_zoom < 20
    assert len(o.tile_widths) > 0
    assert o.last_extent is None
    

def test_StreetMap__compute_tile_widths():
    o = streetmap.StreetMap()
    w = o._compute_tile_widths()
    assert o.min_zoom == 0
    assert o.max_zoom == 15
    assert len(w) == 16
    assert w[0] == pytest.approx( 360.0 )
    assert w[1] == pytest.approx( 180.0 )
    assert w[2] == pytest.approx(  90.0 )
    assert w[3] == pytest.approx(  45.0 )
    assert w[4] == pytest.approx(  22.5 )
    

def test_StreetMap__compute_initial_zoom():
    o = streetmap.StreetMap()
    latb = 30.0; latt = 35.0;
    assert o._compute_initial_zoom(0.0, latb, 360.0, latt) == 0
    assert o._compute_initial_zoom(0.0, latb, 185.0, latt) == 1
    assert o._compute_initial_zoom(0.0, latb, 180.0, latt) == 1
    assert o._compute_initial_zoom(0.0, latb,  95.0, latt) == 2
    assert o._compute_initial_zoom(0.0, latb,  90.0, latt) == 2


def test_StreetMap_draw():
    ax = plt.axes()
    ax.axis( (-85.0, -80.0, 30.0, 40.0) )
    o = streetmap.StreetMap()

    try:
        corners_xy = (-85.0, -80.0, 30.0, 40.0)
        corners_lonlat = (-85.0, -80.0, 30.0, 40.0)
        o.draw(ax, corners_xy, corners_lonlat)
        plt.close(ax.get_figure())
    except Exception as ex:
        pytest.fail("Unexpected exception: {}".format(ex))

    assert o.last_extent is not None
