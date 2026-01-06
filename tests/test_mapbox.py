# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_mapbox.py
#
# Performs unit tests on functions and class methods declared in mapbox.py.
# ---------------------------------------------------------------------------

import numpy
import pytest

from ..hysplitplot import mapbox, const
from ..hysplitplot.traj import plot


def test_LongitudeInterval__init__():
   o = mapbox.LongitudeInterval()
   assert o._l == 0.
   assert o._r == 0.


def test_LongitudeInterval__normalize_angle():
   o = mapbox.LongitudeInterval()

   assert o._normalize_angle(0.0) == pytest.approx(0.0)
   assert o._normalize_angle(179.0) == pytest.approx(179.0)
   assert o._normalize_angle(180.0) == pytest.approx(-180.0)
   assert o._normalize_angle(181.0) == pytest.approx(-179.0)
   assert o._normalize_angle(-179.0) == pytest.approx(-179.0)
   assert o._normalize_angle(-180.0) == pytest.approx(-180.0)
   assert o._normalize_angle(-181.0) == pytest.approx(179.0)


def test_LongitudeInterval_is_angle_inside():
   o = mapbox.LongitudeInterval(-90.0, 90.0)

   assert o.is_angle_inside(-90.0) is True
   assert o.is_angle_inside(0.0) is True
   assert o.is_angle_inside(90.0) is True

   assert o.is_angle_inside(-91.0) is False
   assert o.is_angle_inside(91.0) is False


def test_LongitudeInterval_is_angle_inside_case2():
   o = mapbox.LongitudeInterval(170.0, -170.0)

   assert o.is_angle_inside(169.0) is False
   assert o.is_angle_inside(170.0) is True
   assert o.is_angle_inside(179.0) is True
   assert o.is_angle_inside(-180.0) is True
   assert o.is_angle_inside(-175.0) is True
   assert o.is_angle_inside(-170.0) is True
   assert o.is_angle_inside(-169.0) is False


def test_LongitudeInterval_length():
   o = mapbox.LongitudeInterval(-90.0, 90.0)
   assert o.length == pytest.approx(180.0)

   p = mapbox.LongitudeInterval(170.0, -170.0)
   assert p.length == pytest.approx(20.0)


def test_LongitudeInterval_union():
   o = mapbox.LongitudeInterval(-90.0, 90.0)

   o.union(45.0)
   assert o._l == pytest.approx(-90.0)
   assert o._r == pytest.approx(90.0)

   o.union(-45.0)
   assert o._l == pytest.approx(-90.0)
   assert o._r == pytest.approx(90.0)

   o.union(-91.0)
   assert o._l == pytest.approx(-91.0)
   assert o._r == pytest.approx(90.0)

   o.union(95.0)
   assert o._l == pytest.approx(-91.0)
   assert o._r == pytest.approx(95.0)


def test_LongitudeInterval_union_case1a():
   o = mapbox.LongitudeInterval(-170.0, 170.0)

   o.union(-175.0)
   assert o._l == pytest.approx(-175.0)
   assert o._r == pytest.approx(170.0)

   o.union(179.0)
   assert o._l == pytest.approx(179.0)
   assert o._r == pytest.approx(170.0)


def test_LongitudeInterval_union_case2():
   o = mapbox.LongitudeInterval(170.0, -170.0)

   o.union(-175.0)
   assert o._l == pytest.approx(170.0)
   assert o._r == pytest.approx(-170.0)

   o.union(175.0)
   assert o._l == pytest.approx(170.0)
   assert o._r == pytest.approx(-170.0)

   o.union(-165.0)
   assert o._l == pytest.approx(170.0)
   assert o._r == pytest.approx(-165.0)

   o.union(165.0)
   assert o._l == pytest.approx(165.0)
   assert o._r == pytest.approx(-165.0)


def test_MapBoxFactory_create_instance():
    o = mapbox.MapBoxFactory.create_instance(kind=1)
    assert isinstance(o, mapbox.MapBoxUsingBoundingBox)
    assert o.grid_delta == pytest.approx(0.125)

    # Test with spans smaller than 2.0 degrees.
    o = mapbox.MapBoxFactory.create_instance(lat_span=1.0, lon_span=1.0)
    assert isinstance(o, mapbox.MapBox)
    assert o.grid_delta == pytest.approx(0.10)
    assert o._sz == [10, 10]

    # Test with spans smaller than 5.0 but larger than 2.0.
    o = mapbox.MapBoxFactory.create_instance(lat_span=2.5, lon_span=2.5)
    assert isinstance(o, mapbox.MapBox)
    assert o.grid_delta == pytest.approx(0.20)
    assert o._sz == [12, 12]

    # Test with spans larger than 5.0.
    o = mapbox.MapBoxFactory.create_instance(lat_span=10.0, lon_span=10.0)
    assert isinstance(o, mapbox.MapBox)
    assert o.grid_delta == pytest.approx(1.0)
    assert o._sz == [360, 181]


def test_AbstractMapBox___init__():
    mb = mapbox.MapBox()  # use a concrete class

    assert mb.grid_delta == 1.0
    assert mb.grid_corner == [-180.0, -90.0]
    assert mb.hit_count == 0
    assert mb.bounding_box is None


def test_AbstractMapBox__update_grid_delta():
    mb = mapbox.MapBox()  # use a concrete class
    assert mb.grid_delta == 1.0

    mb._update_grid_delta(0.5)
    assert mb.grid_delta == 0.5


def test_AbstractMapBox_bounding_box():
    mb = mapbox.MapBox()

    mb._bbox = (-90., -88., 37.0, 38.0,)
    assert mb.bounding_box == pytest.approx((-90., -88., 37., 38.,))


def test_AbstractMapBox_get_bounding_box_center():
    mb = mapbox.MapBox()

    mb._bbox = (-90., -88., 37.0, 38.0,)
    assert mb.get_bounding_box_center() == pytest.approx((-89., 37.5,))

    mb._bbox = (178.0, -178.0, 37.0, 38.0,)
    assert mb.get_bounding_box_center() == pytest.approx((-180.0, 37.5,))


def test_AbstractMapBox_get_bounding_box_corners():
    mb = mapbox.MapBox()
    mb.allocate()

    corners = mb.get_bounding_box_corners()
    assert len(corners) == 0

    mb._plume_sz = [40.0, 10.0]
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


def test_AbstractMapBox__normalize_lon():
    mb = mapbox.MapBox();
    assert mb._normalize_lon(-185.0) == pytest.approx(175.0)
    assert mb._normalize_lon(185.0) == pytest.approx(-175.0)
    assert mb._normalize_lon(45.0) == pytest.approx(45.0)


def test_AbstractMapBox__normalize_lat():
    mb = mapbox.MapBox();
    assert mb._normalize_lat(-95.0) == pytest.approx(-90.0)
    assert mb._normalize_lat(95.0) == pytest.approx(90.0)
    assert mb._normalize_lat(45.0) == pytest.approx(45.0)


def test_AbstractMapBox_set_ring_extent():
    mb = mapbox.MapBox()
    mb.allocate()
    mb._plume_sz = [40.0, 10.0]
    s = plot.TrajectoryPlotSettings()
    s.center_loc = (-120.3, 45.3)
    s.ring_number = 2
    s.ring_distance = 101.0

    mb.set_ring_extent(s, (-120.3, 45.3))

    assert s.ring_distance == 100.0
    assert mb.bounding_box == pytest.approx((-122.1018, -118.4982, 43.49820, 47.10180))


def test_AbstractMapBox_set_ring_extent_case2():
    """
    Test ring_number = 0
    """
    mb = mapbox.MapBox()
    mb.allocate()
    mb._plume_sz = [40.0, 10.0]
    s = plot.TrajectoryPlotSettings()
    s.center_loc = (-120.3, 45.3)
    s.ring_number = 0
    s.ring_distance = 202.0

    mb.set_ring_extent(s, (-120.3, 45.3))

    assert s.ring_distance == 200.0
    assert mb.bounding_box == pytest.approx((-122.1018, -118.4982, 43.49820, 47.10180))


def test_MapBox___init__():
    mb = mapbox.MapBox()
    assert mb._lon_hit_map is None
    assert mb._lat_hit_map is None

    mb = mapbox.MapBox(grid_corner=[-84.0, -23.0], grid_size=[10.0, 5.0], grid_delta=0.5)
    assert mb._sz == [20, 10]
    assert mb._plume_sz == [0, 0]
    assert mb._plume_loc == [0, 0]
    assert mb.grid_delta == 0.5
    assert mb.grid_corner == [-84.0, -23.0]


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

    assert mb._plume_sz == [1.0, 1.0]
    assert mb._plume_loc == [59, 135]
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

    assert mb._plume_sz == [4.0, 7.0]
    assert mb._plume_loc == [358, 125]
    assert mb.bounding_box == pytest.approx((178.0, -178.0, 35.0, 42.0))


def test_MapBox_need_to_refine_grid():
    mb = mapbox.MapBox()

    mb._plume_sz = [0.0, 0.0]
    assert mb.need_to_refine_grid() == True

    mb._plume_sz = [2.5, 0.0]
    assert mb.need_to_refine_grid() == False

    mb._plume_sz = [0.0, 2.5]
    assert mb.need_to_refine_grid() == False


def test_MapBox_refine_grid():
    mb = mapbox.MapBox()
    mb.allocate()

    mb.add((-120.3, 45.3))
    mb.determine_plume_extent()
    mb.refine_grid()

    assert mb.grid_corner == [-121.0, 45.0]
    assert mb.grid_delta == 0.10
    assert mb._sz == [10, 10]
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
    assert mb.grid_delta == 0.1
    assert mb._sz == [40, 70]
    assert mb._lon_hit_map is None
    assert mb._lat_hit_map is None

    # Repeat with the same conc array

    mb.allocate()
    mb.add_conc(conc, lons_left, lats_left)
    mb.add_conc(conc, lons_right, lats_right)
    mb.determine_plume_extent()
    assert mb._plume_sz == pytest.approx([3.1, 6.1])
    assert mb._plume_loc == [0, 0]
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


def test_MapBoxUsingBoundingBox___init__():
    mb = mapbox.MapBoxUsingBoundingBox()
    assert mb._left == 0
    assert mb._right == 0
    assert mb._top == 0
    assert mb._bottom == 0


def test_MapBoxUsingBoundingBox_add():
    mb = mapbox.MapBoxUsingBoundingBox()
    mb.allocate()

    mb.add((-120.3, 45.3))
    assert mb.hit_count == 1
    assert mb.bounding_box == pytest.approx([-120.3, -120.3, 45.3, 45.3])

    mb.add((-120.9, 45.8))
    assert mb.hit_count == 2
    assert mb.bounding_box == pytest.approx([-120.9, -120.3, 45.3, 45.8])

    # Test a point near the longitude maximum.
    mb.add((359.696, 45.3))
    assert mb.hit_count == 3
    assert mb.bounding_box == pytest.approx([-120.9, -0.304, 45.3, 45.8])


def test_MapBoxUsingBoundingBox_add_conc():
    mb = mapbox.MapBoxUsingBoundingBox()
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

    assert mb.hit_count == 6
    assert mb.bounding_box == pytest.approx([-89.5, -88.0, 35.5, 37.0])


def test_MapBoxUsingBoundingBox_determine_plume_extent():
    mb = mapbox.MapBoxUsingBoundingBox()
    mb.allocate()

    mb.add((-120.3, 45.3))
    mb.determine_plume_extent()

    assert mb.bounding_box == pytest.approx((-120.3, -120.3, 45.3, 45.3))


def test_MapBoxUsingBoundingBox_determine_plume_extent_case2():
    """
    Test with a plume crossing the grid domain
    """
    mb = mapbox.MapBoxUsingBoundingBox()
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
    assert mb.grid_delta == pytest.approx(0.4)


def test_MapBoxUsingBoundingBox_need_to_refine_grid():
    mb = mapbox.MapBoxUsingBoundingBox()
    assert mb.need_to_refine_grid() == False


def test_MapBoxUsingBoundingBox_refine_grid():
    mb = mapbox.MapBoxUsingBoundingBox()
    try:
        mb.refine_grid()
    except Exception as e:
        pytest.fail(f"Unexpected exception: {str(e)}")

