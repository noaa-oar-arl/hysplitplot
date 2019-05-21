import pytest
from hysplit4 import util


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


def test_normalize_output_filename():
    n, x = util.normalize_output_filename("output.PS", "ps")
    assert n, x == ("output.PS", "PS")

    n, x = util.normalize_output_filename("output.pdf", "ps")
    assert n, x == ("output.pdf", "pdf")

    n, x = util.normalize_output_filename("output.", "ps")
    assert n, x == ("output.ps", "pdf")

    n, x = util.normalize_output_filename("output", "ps")
    assert n, x == ("output.ps", "ps")


def test_restore_year():
    util.restore_year( 0) == 2000
    util.restore_year(39) == 2039
    util.restore_year(40) == 1940
    util.restore_year(99) == 1999


def test_calc_ring_distance():
    kspan, ring_distance = util.calc_ring_distance((40.0, 10.0),
                                                   1.0,
                                                   (0, 0), # TODO: check this??
                                                   5,
                                                   105.0)
    assert kspan == 5
    assert ring_distance == 100.0
