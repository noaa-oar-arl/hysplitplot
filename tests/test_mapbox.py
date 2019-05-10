import pytest
from hysplit4 import mapbox, const
from hysplit4.traj import plot


def test_MapBox___init__():
    mb = mapbox.MapBox()

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
    mb = mapbox.MapBox();

    mb.hit_count = 1
    mb.allocate()

    assert mb.hit_map is not None
    assert mb.hit_map.shape == (360, 181)
    assert mb.hit_count == 0


def test_MapBox_add():
    mb = mapbox.MapBox()
    mb.allocate()

    mb.add((-120.5, 45.5))

    assert mb.hit_map[239, 135] == 1
    assert mb.hit_count == 1
    assert mb._i == 239
    assert mb._j == 135


def test_MapBox_determine_plume_extent():
    mb = mapbox.MapBox()
    mb.allocate()

    mb.add((-120.5, 45.5))
    mb.determine_plume_extent()

    assert mb.plume_sz == [1.0, 1.0]
    assert mb.plume_loc == [239, 135]


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

    mb.add((-120.5, 45.5))
    mb.determine_plume_extent()
    mb.refine_grid()

    assert mb.grid_corner == [239.0, 45.0]
    assert mb.grid_delta == 0.10
    assert mb.sz == [10, 10]
    assert mb.hit_map is None


def test_MapBox_clear_hit_map():
    mb = mapbox.MapBox()
    mb.allocate()
    mb.add((-120.5, 45.5))
    assert mb.hit_map[239, 135] == 1
    assert mb.hit_count == 1

    mb.clear_hit_map()

    assert mb.hit_map[239, 135] == 0
    assert mb.hit_count == 0


def test_MapBox_set_ring_extent():
    mb = mapbox.MapBox()
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
