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
