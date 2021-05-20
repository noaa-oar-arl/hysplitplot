# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_mapfile.py
#
# Performs unit tests on functions and class methods declared in mapfile.py.
# ---------------------------------------------------------------------------

import geopandas
import os
import pytest

from hysplitplot import mapfile


def test_ARLMap___init__():
    m = mapfile.ARLMap()

    assert m.segments != None


def test_ARLMap_get_reader():
    m = mapfile.ARLMap()
    r = m.get_reader()

    assert isinstance(r, mapfile.ARLMapReader)


def test_Segment___init__():
    s = mapfile.ARLMap.Segment(1, 40.0, -90.0, "k", 0.08)

    assert s.number == 1
    assert s.latitudes == 40.0
    assert s.longitudes == -90.0
    assert s.color == "k"
    assert s.thickness == 0.08


def test_ARLMapReader___init__():
    m = mapfile.ARLMap()
    r = mapfile.ARLMapReader(m)

    assert r.map is m
    assert len(r.colors) > 0
    assert len(r.thickness) > 0
    assert r.colors["default"] == "#6699cc"
    assert r.thickness["default"] == 0.01


def test_ARLMapReader_read():
    r = mapfile.ARLMap().get_reader()
    m = r.read("data/arlmap_truncated")
    assert isinstance(m, mapfile.ARLMap)

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
    r = mapfile.ARLMap().get_reader()
    m = r.read("data/arlmap_test")
    assert isinstance(m, mapfile.ARLMap)

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
    m = mapfile.ARLMap().get_reader().read("data/arlmap_truncated")
    cs = mapfile.ARLMapConverter.convert(m)
    assert len(cs) > 0
    for c in cs:
        assert isinstance(c, mapfile.DrawableBackgroundMap)
        assert isinstance(c.map, geopandas.geoseries.GeoSeries)
        assert c.linestyle == "-"
        assert c.linewidth == 0.5
        assert c.linecolor == "#6699cc"


def test_ARLMapConverter_style_ref():
    assert mapfile.ARLMapConverter.style_ref("#6699cc", 0.008) == "#6699cc_0.008"
    assert mapfile.ARLMapConverter.style_ref("#6699cc", 0.01) == "#6699cc_0.01"


def test_DrawableBackgroundMap___init__():
    o = None
    d = mapfile.DrawableBackgroundMap(o, "k", 0.008)
    assert d.map is None
    assert d.linestyle == "-"
    assert d.linewidth == 0.4 # scaled
    assert d.linecolor == "k"


def test_ShapeFile___init__():
    s = mapfile.ShapeFile()
    assert s.filename == "arlmap.shp"
    assert s.dash == 0
    assert s.thickness == 0.01
    assert s.red == 0.4
    assert s.blue == 0.6
    assert s.green == 0.8


def test_ShapeFileReader___init__():
    r = mapfile.ShapeFilesReader()
    assert len(r.shapefiles) == 0


def test_ShapeFileReader_read():
    list = mapfile.ShapeFilesReader().read("data/shapefiles_arl.txt")
    assert len(list) == 1

    s = list[0]
    assert s.filename == "arlmap.shp"
    assert s.dash == 0
    assert s.thickness == pytest.approx(0.01)
    assert s.red == pytest.approx(0.4)
    assert s.green == pytest.approx(0.6)
    assert s.blue == pytest.approx(0.8)


def test_ShapeFileReader_parse_line():
    r = mapfile.ShapeFilesReader()

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
    r = mapfile.ShapeFilesReader()
    try:
        r.warn_and_create_sample("__shapefiles_test.txt")
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex).startswith("file not found __shapefiles_test.txt: please see")
        os.remove("__shapefiles_test.txt")


def test_ShapeFileConverter_convert():
    s = mapfile.ShapeFile()
    s.filename = "data/arlmap.shp"
    s.dash = 8
    s.thickness = 0.75
    s.red = 0.4
    s.green = 0.6
    s.blue = 0.8

    m = mapfile.ShapeFileConverter.convert(s)
    assert isinstance(m, mapfile.DrawableBackgroundMap)
    assert isinstance(m.map, geopandas.geodataframe.GeoDataFrame)
    assert m.map.crs is not None or len(m.map.crs) > 0 # must have initialized the CRS field.
    assert m.linestyle == (0, (4.5, 4.5))
    assert m.linewidth == pytest.approx(0.75*50)
    assert m.linecolor == "#6699cc"


def test_ShapeFileConverter_make_linestyle():
    assert mapfile.ShapeFileConverter.make_linestyle(0) == '-'
    assert mapfile.ShapeFileConverter.make_linestyle(1) == (0, (36.0, 36.0))
    assert mapfile.ShapeFileConverter.make_linestyle(2) == (0, (18.0, 18.0))
    assert mapfile.ShapeFileConverter.make_linestyle(4) == (0, (9.0, 9.0))
    assert mapfile.ShapeFileConverter.make_linestyle(-4) == (0, (9.0, 9.0))
