import pytest
from hysplit4 import CommandLineArguments


def test_CommandLineArguments___init__():
    c = CommandLineArguments()

    assert c.args != None

    args = ["-a0", "+b1"]
    c2 = CommandLineArguments(args)

    assert c2.args["-a"] == "0"
    assert c2.args["+b"] == "1"


def test_CommandLineArguments_clear():
    args = ["-a0", "+b1"]
    c = CommandLineArguments(args)

    assert len(c.args) == 2
    c.clear()

    assert len(c.args) == 0


def test_CommandLineArguments_add():
    c = CommandLineArguments()

    # processing stops at "-:"
    c.add(["-a0", "-:", "+b1"])
    assert len(c.args) == 1

    # options start with "-" or "+"
    c.clear()
    c.add(["-a0", "+b1", "cc", "-d4"])

    assert len(c.args) == 3
    assert c.args["-a"] == "0"
    assert c.args["+b"] == "1"
    assert c.args["-d"] == "4"


def test_CommandLineArguments_has_arg():
    c = CommandLineArguments(["-a0", "+b1"])

    assert c.has_arg("-a") == True
    assert c.has_arg("+b") == True
    assert c.has_arg("-d") == False


def test_CommandLineArguments_get_value():
    c = CommandLineArguments(["-a0", "+b1"])

    assert c.get_value("-a") == "0"
    assert c.get_value("+b") == "1"

    assert c.get_value(["-a", "-A"]) == "0"


def test_CommandLineArguments_get_string_value():
    c = CommandLineArguments(["-afilename"])

    assert c.get_string_value("-a", "default") == "filename"
    assert c.get_string_value("+b", "default") == "default"


def test_CommandLineArguments_get_integer_value():
    c = CommandLineArguments(["-a314", "+sfile", "-c3.14"])

    assert c.get_integer_value("-a", 1) == 314
    assert c.get_integer_value("+b", 2) == 2

    # option values of invalid data types
    assert c.get_integer_value("+s", 1) == 1
    assert c.get_integer_value("-c", 1) == 1


def test_CommandLineArguments_get_float_value():
    c = CommandLineArguments(["-a3.14", "+sfile", "-c2"])

    assert c.get_float_value("-a", 1.0) == 3.14
    assert c.get_float_value("+b", 2.0) == 2.0

    # option values of invalid data types
    assert c.get_float_value("+s", 3.14) == 3.14
    assert c.get_float_value("-c", 3.14) == 2.0


def test_CommandLineArguments_get_boolean_value():
    c = CommandLineArguments(["-a0", "-b1", "-cT", "-d2", "-e-1"])

    assert c.get_boolean_value("-a", True) == False
    assert c.get_boolean_value("-b", False) == True

    # option values of invalid data types
    assert c.get_boolean_value("-c", False) == False

    assert c.get_boolean_value("-d", False) == True # 2 is modified to 1.
    assert c.get_boolean_value("-e", True) == False # -1 is modified to 0.
