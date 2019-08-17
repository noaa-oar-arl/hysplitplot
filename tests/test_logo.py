# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_logo.py
#
# Performs unit tests on functions and class methods declared in logo.py.
# ---------------------------------------------------------------------------

import matplotlib.pyplot as plt
import pytest

from hysplitplot import logo


def test_NOAALogoDrawer___init__():
    d = logo.NOAALogoDrawer()
    assert d.logo_width == 480.0
    assert d.logo_height == 480.0
    assert d.cx == 240.0
    assert d.cy == 240.0
    assert d.R == 200.0
    assert hasattr(d, "base_font_sz")
    assert hasattr(d, "font_sz1")
    assert hasattr(d, "font_sz2")
    assert hasattr(d, "plot_objs") and len(d.plot_objs) == 0
    

def test_NOAALogoDrawer_clear():
    d = logo.NOAALogoDrawer()
    axes = plt.axes()
    d.draw(axes, ((0.7, 0.0), (0.8, 0.1)))
    assert len(d.plot_objs) > 0
    d.clear()
    assert len(d.plot_objs) == 0
    plt.close(axes.figure)


def test_NOAALogoDrawer_draw():
    d = logo.NOAALogoDrawer()
    axes = plt.axes()
    try:
        d.draw(axes, ((0.7, 0.0), (0.8, 0.1)))
        plt.close(axes.figure)
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
    

def test_NOAALogoDrawer__draw_top_label():
    d = logo.NOAALogoDrawer()
    axes = plt.axes()
    try:
        d._draw_top_label(axes, axes.transData)
        plt.close(axes.figure)
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
        
    
def test_NOAALogoDrawer__draw_bottom_label():
    d = logo.NOAALogoDrawer()
    axes = plt.axes()
    try:
        d._draw_bottom_label(axes, axes.transData)
        plt.close(axes.figure)
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
   

def test_NOAALogoDrawer__draw_ref_circ():
    d = logo.NOAALogoDrawer()
    axes = plt.axes()
    try:
        d._draw_ref_circ(axes, axes.transData)
        plt.close(axes.figure)
    except Exception as ex:
        pytest.fail("unexpected exception: {0}".format(ex))
