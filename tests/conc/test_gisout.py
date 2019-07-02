import pytest
import logging
from hysplit4.conc import gisout


logger = logging.getLogger(__name__)


def test_AbstractKMLContourWriter__compute_polygon_area():
    # clockwise, area < 0
    x = [0, 0, 1, 1, 0]
    y = [0, 1, 1, 0, 0]
    area = gisout.AbstractKMLContourWriter._compute_polygon_area(x, y)
    assert area == pytest.approx(-1.0)
    
    # counterclockwise, area > 0
    x = [0, 1, 1, 0, 0]
    y = [0, 0, 1, 1, 0]
    area = gisout.AbstractKMLContourWriter._compute_polygon_area(x, y)
    assert area == pytest.approx(1.0)
    