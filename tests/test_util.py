# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_util.py
#
# Performs unit tests on functions and class methods declared in util.py.
# ---------------------------------------------------------------------------

import datetime
import numpy
import os
import pytest
import pytz

from hysplitdata.const import HeightUnit
from hysplitplot import util, const


def test_myzip():
    a = util.myzip([1, 2], [3, 4])

    assert len(a) == 2
    assert a[0] == (1, 3)
    assert a[1] == (2, 4)


def test_convert_int_to_bool():
    assert util.convert_int_to_bool(-1) == False # strange but it is to retain the existing capability.
    assert util.convert_int_to_bool(0) == False
    assert util.convert_int_to_bool(1) == True
    assert util.convert_int_to_bool(2) == True


def test_sign():
    assert util.sign( 10.0,  1.0) ==  10.0
    assert util.sign( 10.0, -1.0) == -10.0
    assert util.sign(-10.0,  1.0) ==  10.0
    assert util.sign(-10.0, -1.0) == -10.0


def test_nearest_int():
    assert util.nearest_int( 9.4) ==  9
    assert util.nearest_int( 9.5) == 10
    assert util.nearest_int(10.0) == 10
    assert util.nearest_int(10.4) == 10

    assert util.nearest_int(-10.4) == -10
    assert util.nearest_int(-10.0) == -10
    assert util.nearest_int( -9.6) == -10
    assert util.nearest_int( -9.5) == -10
    assert util.nearest_int( -9.4) ==  -9


def test_make_color():
    assert util.make_color(0.4, 0.6, 0.8) == "#6699cc"
    assert util.make_color(0.4, 0.6, 0.8, 0.5) == "#6699cc80"


def test_make_int_if_same():
    assert util.make_int_if_same(1.3) == 1.3
    assert util.make_int_if_same(1.0) == 1
    assert util.make_int_if_same(45.0) == 45
    assert util.make_int_if_same(45.1) == 45.1
   

def test_is_valid_lonlat():
    assert util.is_valid_lonlat((99.0, 99.0)) == False
    assert util.is_valid_lonlat((99.0,  0.0)) == True
    
    
def test_union_ranges():
    r = util.union_ranges(None, None)
    assert r == None

    r = util.union_ranges(None, [1, 3])
    assert r == [1, 3]

    r = util.union_ranges([1, 3], None)
    assert r == [1, 3]

    r = util.union_ranges([1, 3], [0, 2])
    assert r == [0, 3]


def test_make_file_list():

    list = util.make_file_list("tdump")
    assert len(list) == 1
    assert list[0] == "tdump"

    list = util.make_file_list("tdump_back+tdump_fwrd")
    assert len(list) == 2
    assert list[0] == "tdump_back"
    assert list[1] == "tdump_fwrd"

    list = util.make_file_list("+data/INFILES")
    assert len(list) == 3
    assert list[0] == "tdump_001"
    assert list[1] == "tdump_002"
    assert list[2] == "tdump_003"

    try:
        list = util.make_file_list("+data/nonexistent_file")
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "FATAL ERROR - File not found: data/nonexistent_file"


def test_normalize_output_format():
    # extension in the filename has the highest priority
    assert util.normalize_output_format("output.pdf", "ps", "png") == "pdf"
    assert util.normalize_output_format("output.pdf", "ps", "png") == "pdf"
    assert util.normalize_output_format("output.pdf", "3141", "ps") == "pdf"
    assert util.normalize_output_format("OUTPUT.PDF", "3141", "ps") == "pdf"

    # when the filename has no extension, the suffix is consulted.
    assert util.normalize_output_format("output", "pdf", "png") == "pdf"
    assert util.normalize_output_format("output", "PDF", "png") == "pdf"
    assert util.normalize_output_format("output", "3141", "png") == "png"
    assert util.normalize_output_format("output", "3141", "PNG") == "png"
    
    
def test_normalize_output_filename():
    n, b, x = util.normalize_output_filename("output.PS", "ps")
    assert (n, b, x) == ("output.PS", "output", "PS")

    n, b, x = util.normalize_output_filename("output.pdf", "ps")
    assert (n, b, x) == ("output.pdf", "output", "pdf")

    n, b, x = util.normalize_output_filename("output.", "ps")
    assert (n, b, x) == ("output.ps", "output", "ps")

    n, b, x = util.normalize_output_filename("output", "ps")
    assert (n, b, x) == ("output.ps", "output", "ps")


def test_join_file():
    with open("join.1", "wt") as f1:
        f1.write("123")
    with open("join.2", "wt") as f2:
        f2.write("456")
    
    util.join_file("join.1", "join.2")
    
    with open("join.2", "rt") as o:
        str = o.read()
        
    assert str == "456123"
    os.remove("join.1")
    os.remove("join.2")


def test_get_iso_8601_str():
    utc = pytz.utc
    dt = datetime.datetime(1983, 10, 13, 0, 15, 0, 0, utc)
    assert util.get_iso_8601_str(dt) == "1983-10-13T00:15:00Z"

    eastern = pytz.timezone("EST")
    dt = datetime.datetime(1983, 10, 13, 0, 15, 0, 0, eastern)
    assert util.get_iso_8601_str(dt) == "1983-10-13T00:15:00-0500"


def test_calc_ring_distance():
    kspan, ring_distance = util.calc_ring_distance((40.0, 10.0),
                                                   1.0,
                                                   (0, 0),
                                                   5,
                                                   105.0)
    assert kspan == 5
    assert ring_distance == 100.0


def test_nonzero_min():
    a = numpy.zeros((3, 3))
    assert util.nonzero_min(a) == None
    
    a[1, 1] = 1.0
    assert util.nonzero_min(a) == 1.0


def test_is_crossing_date_line():
    assert util.is_crossing_date_line(150.0, -170.0) == True
    assert util.is_crossing_date_line(-10.0,   10.0) == False


def test_AbstractLengthFactory_create_factory():
    f = util.AbstractLengthFactory.create_factory(HeightUnit.METERS)
    assert isinstance(f, util.LengthInMetersFactory)
    
    f = util.AbstractLengthFactory.create_factory(HeightUnit.FEET)
    assert isinstance(f, util.LengthInFeetFactory)
    
    try:
        f = util.AbstractLengthFactory.create_factory(99999)
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "unknown length unit type 99999"


def test_LengthInMetersFactory_create_instance():
    f = util.LengthInMetersFactory()
    
    o = f.create_instance(1.0)
    assert isinstance(o, util.LengthInMeters)
    assert o.v == 1.0
    
    o = f.create_instance(1.0, HeightUnit.FEET)
    assert isinstance(o, util.LengthInMeters)
    assert o.v == 0.3048


def test_LengthInFeetFactory_create_instance():
    f = util.LengthInFeetFactory()
    
    o = f.create_instance(1.0)
    assert isinstance(o, util.LengthInFeet)
    assert o.v == 3.28084
    
    o = f.create_instance(1.0, HeightUnit.FEET)
    assert isinstance(o, util.LengthInFeet)
    assert o.v == 1.0
    

def test_LengthInMeters___init__():
    o = util.LengthInMeters(1.0)
    assert str(o) == "1 m"
    
    o = util.LengthInMeters(1.0, False)
    assert str(o) == "1.0 m"


def test_LengthInMeters___int__():
    o = util.LengthInMeters(1.2)
    assert int(o) == 1

    
def test_LengthInFeet___init__():
    o = util.LengthInFeet(1.0)
    assert str(o) == "1 ft"
    
    o = util.LengthInFeet(1.0, False)
    assert str(o) == "1.0 ft"


def test_LengthInFeet___int__():
    o = util.LengthInFeet(1.2)
    assert int(o) == 1
