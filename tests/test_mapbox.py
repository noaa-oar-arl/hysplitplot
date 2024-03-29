# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_mapbox.py
#
# Performs unit tests on functions and class methods declared in mapbox.py.
# ---------------------------------------------------------------------------

import numpy
import pytest

from hysplitplot import mapbox, const
from hysplitplot.traj import plot


def test_MapBox___init__():
    mb = mapbox.MapBox()

    assert mb._lon_hit_map is None
    assert mb._lat_hit_map is None
    assert mb.sz == [360, 181]
    assert mb.grid_delta == 1.0
    assert mb.grid_corner == [-180.0, -90.0]
    assert mb.plume_sz == [0.0, 0.0]
    assert mb.plume_loc == [0, 0]
    assert mb.hit_count == 0
    assert mb.bounding_box is None

    mb = mapbox.MapBox(grid_corner=[-84.0, -23.0], grid_size=[10.0, 5.0], grid_delta=0.5)
    assert mb.sz == [20, 10]
    assert mb.grid_delta == 0.5
    assert mb.grid_corner == [-84.0, -23.0]


def test_MapBox__normalize_lon():
    mb = mapbox.MapBox();
    assert mb._normalize_lon(-185.0) == pytest.approx( 175.0)
    assert mb._normalize_lon( 185.0) == pytest.approx(-175.0)
    assert mb._normalize_lon(  45.0) == pytest.approx(  45.0)


def test_MapBox__normalize_lat():
    mb = mapbox.MapBox();
    assert mb._normalize_lat(-95.0) == pytest.approx(-90.0)
    assert mb._normalize_lat( 95.0) == pytest.approx( 90.0)
    assert mb._normalize_lat( 45.0) == pytest.approx( 45.0)


def test_MapBox_allocate():
    mb = mapbox.MapBox();

    mb.hit_count = 1
    mb.allocate()

    assert mb._lon_hit_map is not None
    assert mb._lat_hit_map is not None
    assert mb._lon_hit_map.shape == (360,)
    assert mb._lat_hit_map.shape == (181,)
    assert mb.hit_count == 0


def test_MapBox_add():
    mb = mapbox.MapBox()
    mb.allocate()

    mb.add((-120.3, 45.3))
    assert mb._lon_hit_map[59] == 1
    assert mb._lat_hit_map[135] == 1
    assert mb.hit_count == 1

    mb.add((-120.9, 45.8))
    assert mb._lon_hit_map[59] == 2
    assert mb._lat_hit_map[135] == 2
    assert mb.hit_count == 2

    # Test a point near the longitude maximum.
    mb.add((359.696, 45.3))
    assert mb._lon_hit_map[179] == 1
    assert mb._lat_hit_map[135] == 3
    assert mb.hit_count == 3


def test_MapBox_add_conc():
    mb = mapbox.MapBox()
    mb.allocate()

    conc = numpy.array([
        [0, 0, 0, 0, 0],
        [0, 1, 2, 3, 0],
        [0, 0, 1, 2, 0],
        [0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0]])
    lats = [35.0, 35.5, 36.0, 36.5, 37.0]
    lons = [-90.0, -89.5, -89.0, -88.5, -88.0]
    mb.add_conc(conc, lons, lats)

    assert mb._lon_hit_map[91] == 5
    assert mb._lon_hit_map[90] == 1
    assert mb._lat_hit_map[126] == 3
    assert mb._lat_hit_map[125] == 3
    assert mb.hit_count == 6


def test_MapBox_determine_plume_extent():
    mb = mapbox.MapBox()
    mb.allocate()

    mb.add((-120.3, 45.3))
    mb.determine_plume_extent()

    assert mb.plume_sz == [1.0, 1.0]
    assert mb.plume_loc == [59, 135]
    assert mb.bounding_box == pytest.approx((-121.0, -120.0, 45.0, 46.0))


def test_MapBox_determine_plume_extent_case2():
    """
    Test with a plume crossing the grid domain
    """
    mb = mapbox.MapBox()
    mb.allocate()

    conc = numpy.array([
        [1, 1],
        [1, 1],
        [1, 1],
        [1, 1],
        [1, 1]])
    lats_left = [35.0, 36.0, 37.0, 38.0, 39.0]
    lons_left = [-180.0, -179.0]
    mb.add_conc(conc, lons_left, lats_left)

    lats_right = [37.0, 38.0, 39.0, 40.0, 41.0]
    lons_right = [178.0, 179.0]
    mb.add_conc(conc, lons_right, lats_right)

    mb.determine_plume_extent()

    assert mb.plume_sz == [4.0, 7.0]
    assert mb.plume_loc == [358, 125]
    assert mb.bounding_box == pytest.approx((178.0, -178.0, 35.0, 42.0))


def test_MapBox_need_to_refine_grid():
    mb = mapbox.MapBox()

    mb.plume_sz = [0.0, 0.0]
    assert mb.need_to_refine_grid() == True

    mb.plume_sz = [2.5, 0.0]
    assert mb.need_to_refine_grid() == False

    mb.plume_sz = [0.0, 2.5]
    assert mb.need_to_refine_grid() == False


def test_MapBox_refine_grid():
    mb = mapbox.MapBox()
    mb.allocate()

    mb.add((-120.3, 45.3))
    mb.determine_plume_extent()
    mb.refine_grid()

    assert mb.grid_corner == [-121.0, 45.0]
    assert mb.grid_delta == 0.10
    assert mb.sz == [10, 10]
    assert mb._lon_hit_map is None
    assert mb._lat_hit_map is None


def test_MapBox_refine_grid_case2():
    """
    Test with a plume crossing the grid domain
    """
    mb = mapbox.MapBox()
    mb.allocate()
    conc = numpy.array([
        [1, 1],
        [1, 1],
        [1, 1],
        [1, 1],
        [1, 1]])
    lats_left = [35.0, 36.0, 37.0, 38.0, 39.0]
    lons_left = [-180.0, -179.0]
    mb.add_conc(conc, lons_left, lats_left)
    lats_right = [37.0, 38.0, 39.0, 40.0, 41.0]
    lons_right = [178.0, 179.0]
    mb.add_conc(conc, lons_right, lats_right)
    mb.determine_plume_extent()
    assert mb.bounding_box == pytest.approx((178.0, -178.0, 35.0, 42.0))
    
    mb.refine_grid()

    assert mb.grid_corner == [178.0, 35.0]
    assert mb.grid_delta == 0.10
    assert mb.sz == [40, 70]
    assert mb._lon_hit_map is None
    assert mb._lat_hit_map is None

    # Repeat with the same conc array

    mb.allocate()
    mb.add_conc(conc, lons_left, lats_left)
    mb.add_conc(conc, lons_right, lats_right)
    mb.determine_plume_extent()
    assert mb.plume_sz == pytest.approx([3.1, 6.1])
    assert mb.plume_loc == [0, 0]
    assert mb.bounding_box == pytest.approx((178.0, -178.9, 35.0, 41.1))


def test_MapBox_clear_hit_map():
    mb = mapbox.MapBox()
    mb.allocate()
    mb.add((-120.3, 45.3))
    assert mb._lon_hit_map[59] == 1
    assert mb._lat_hit_map[135] == 1
    assert mb.hit_count == 1

    mb.clear_hit_map()

    assert mb._lon_hit_map[59] == 0
    assert mb._lat_hit_map[135] == 0
    assert mb.hit_count == 0


def test_MapBox_set_ring_extent():
    mb = mapbox.MapBox()
    mb.allocate()
    mb.plume_sz = [40.0, 10.0]
    s = plot.TrajectoryPlotSettings()
    s.center_loc = (-120.3, 45.3)
    s.ring_number = 2
    s.ring_distance = 101.0

    mb.set_ring_extent(s, (-120.3, 45.3))

    assert s.ring_distance == 100.0
    assert mb.bounding_box == pytest.approx((-122.1018, -118.4982, 43.49820, 47.10180))


def test_MapBox_set_ring_extent_case2():
    """
    Test ring_number = 0
    """
    mb = mapbox.MapBox()
    mb.allocate()
    mb.plume_sz = [40.0, 10.0]
    s = plot.TrajectoryPlotSettings()
    s.center_loc = (-120.3, 45.3)
    s.ring_number = 0
    s.ring_distance = 202.0

    mb.set_ring_extent(s, (-120.3, 45.3))

    assert s.ring_distance == 200.0
    assert mb.bounding_box == pytest.approx((-122.1018, -118.4982, 43.49820, 47.10180))


def test_MapBox_get_bounding_box_corners():
    mb = mapbox.MapBox()
    mb.allocate()
    
    corners = mb.get_bounding_box_corners()
    assert len(corners) == 0

    mb.plume_sz = [40.0, 10.0]
    s = plot.TrajectoryPlotSettings()
    s.center_loc = (-120.3, 45.3)
    s.ring_number = 2
    s.ring_distance = 101.0
    mb.set_ring_extent(s, (-120.3, 45.3))

    corners = mb.get_bounding_box_corners()
    assert len(corners) == 4
    assert corners[0] == pytest.approx((-122.1018, 43.49820))
    assert corners[1] == pytest.approx((-118.4982, 43.49820))
    assert corners[2] == pytest.approx((-118.4982, 47.10180))
    assert corners[3] == pytest.approx((-122.1018, 47.10180))
