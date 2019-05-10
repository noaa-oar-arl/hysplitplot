import pytest
from hysplit4 import util


def test_myzip():
    a = util.myzip([1, 2], [3, 4])

    assert len(a) == 2
    assert a[0] == (1, 3)
    assert a[1] == (2, 4)


def test_convert_integer_to_boolean():
    assert util.convert_integer_to_boolean(-1) == False # strange but it is to retain the existing capability.
    assert util.convert_integer_to_boolean(0) == False
    assert util.convert_integer_to_boolean(1) == True
    assert util.convert_integer_to_boolean(2) == True


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
