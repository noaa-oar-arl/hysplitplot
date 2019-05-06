import logging
import pytest
import matplotlib.pyplot as plt
import cartopy
from hysplit4 import tick


logger = logging.getLogger(__name__)


@pytest.fixture
def axesLambertConformal():
    axes = plt.axes(projection=cartopy.crs.LambertConformal())
    extent = [-147.52235864685662, -73.94983397779585, 29.80182764295516, 61.71015552072515]
    axes.set_extent(extent, cartopy.crs.PlateCarree())
    return axes


def test_projection_xticks(axesLambertConformal):
    axes = axesLambertConformal

    x = range(-150, -60, 10)

    tick.projection_xticks(axes, x)

    majorTicks = axes.xaxis.majorTicks
    assert len(majorTicks) == 9

    assert majorTicks[0].label1.get_text() == '-150'
    assert majorTicks[1].label1.get_text() == '-140'
    assert majorTicks[2].label1.get_text() == '-130'
    assert majorTicks[3].label1.get_text() == '-120'
    assert majorTicks[4].label1.get_text() == '-110'
    assert majorTicks[5].label1.get_text() == '-100'
    assert majorTicks[6].label1.get_text() == '-90'
    assert majorTicks[7].label1.get_text() == '-80'
    assert majorTicks[8].label1.get_text() == '-70'

    assert majorTicks[0].label1.get_position() == (0, 0)
    assert majorTicks[1].label1.get_position() == (0, 0)
    assert majorTicks[2].label1.get_position() == (0, 0)
    assert majorTicks[3].label1.get_position() == (0, 0)
    assert majorTicks[4].label1.get_position() == (0, 0)
    assert majorTicks[5].label1.get_position() == (0, 0)
    assert majorTicks[6].label1.get_position() == (0, 0)
    assert majorTicks[7].label1.get_position() == (0, 0)
    assert majorTicks[8].label1.get_position() == (0, 0)


def test_projection_yticks(axesLambertConformal):
    axes = axesLambertConformal

    y = range(20, 80, 10)

    tick.projection_yticks(axes, y)

    majorTicks = axes.yaxis.majorTicks
    assert len(majorTicks) == 4

    assert majorTicks[0].label1.get_text() == '30'
    assert majorTicks[1].label1.get_text() == '40'
    assert majorTicks[2].label1.get_text() == '50'
    assert majorTicks[3].label1.get_text() == '60'

    assert majorTicks[0].label1.get_position() == (0, 0)
    assert majorTicks[1].label1.get_position() == (0, 0)
    assert majorTicks[2].label1.get_position() == (0, 0)
    assert majorTicks[3].label1.get_position() == (0, 0)


def test_addMargin():
    x1, x2, y1, y2 = tick._add_margin([-180.0, 180.0, -90.0, 90.0], 0.25)
    assert x1 == -180.0
    assert x2 ==  180.0
    assert y1 ==  -90.0
    assert y2 ==   90.0

    x1, x2, y1, y2 = tick._add_margin([-90.0, 70.0, -50.0, 40.0], 0.10)
    assert x1 == -106.0
    assert x2 ==   86.0
    assert y1 ==  -59.0
    assert y2 ==   49.0

    x1, x2, y1, y2 = tick._add_margin([70.0, -90.0, 40.0, -50.0], 0.10)
    assert x1 == -106.0
    assert x2 ==   86.0
    assert y1 ==  -59.0
    assert y2 ==   49.0
