import pytest
from hysplit4 import io


def test_FormattedLineReader_parse_format():
    r = io.FormattedLineReader()

    v = r.parse_format("A8")
    assert len(v) == 1

    assert v[0][0] == 1
    assert v[0][1] == "A"
    assert v[0][2] == 8

    v = r.parse_format("I5")
    assert len(v) == 1

    assert v[0][0] == 1
    assert v[0][1] == "I"
    assert v[0][2] == 5

    v = r.parse_format("F8.3")
    assert len(v) == 1

    assert v[0][0] == 1
    assert v[0][1] == "F"
    assert v[0][2] == 8
    assert v[0][3] == 3

    v = r.parse_format("2X")
    assert len(v) == 1

    assert v[0][0] == 2
    assert v[0][1] == "X"

    v = r.parse_format("I6, I6, 5I6, I6, F8.1, 2F9.3, 1X, F8.1")
    assert len(v) == 8

    assert v[0][0] == 1
    assert v[0][1] == "I"
    assert v[0][2] == 6

    assert v[1][0] == 1
    assert v[1][1] == "I"
    assert v[1][2] == 6

    assert v[2][0] == 5
    assert v[2][1] == "I"
    assert v[2][2] == 6

    assert v[3][0] == 1
    assert v[3][1] == "I"
    assert v[3][2] == 6

    assert v[4][0] == 1
    assert v[4][1] == "F"
    assert v[4][2] == 8

    assert v[5][0] == 2
    assert v[5][1] == "F"
    assert v[5][2] == 9

    assert v[6][0] == 1
    assert v[6][1] == "X"

    assert v[7][0] == 1
    assert v[7][1] == "F"
    assert v[7][2] == 8


def test_FormattedLineReader_parse():
    r = io.FormattedLineReader()

    v = r.parse("A8, 5I6", "    NGM     95    10    16     0     0")
    assert len(v) == 6
    assert v[0] == "    NGM "
    assert v[1] == 95
    assert v[2] == 10
    assert v[3] == 16
    assert v[4] == 0
    assert v[5] == 0

    v = r.parse("8I6, F8.1, 2F9.3, 1X, F8.1", "     3     1    95    10    16     0     0     0     0.0   40.000  -90.000   1000.0    879.8")
    assert len(v) == 12
    assert v[0] == 3
    assert v[1] == 1
    assert v[2] == 95
    assert v[3] == 10
    assert v[4] == 16
    assert v[5] == 0
    assert v[6] == 0
    assert v[7] == 0
    assert v[8] == 0.0
    assert v[9] == 40.0
    assert v[10] == -90.0
    assert v[11] == 1000.0

    v = r.parse("2I3", "  1")
    assert len(v) == 1
    assert v[0] == 1


def test_FormattedTextFileReader___init__():
    r = io.FormattedTextFileReader()
    assert r.lines != None
    assert r.line_index == -1
    assert r.buffer == None
    assert isinstance(r.formatter, io.FormattedLineReader)


def test_FormattedTextFileReader_open():
    r = io.FormattedTextFileReader()

    r.line_index = 13
    r.buffer = "text"

    r.open("data/three_lines")
    assert len(r.lines) == 3
    assert r.line_index == -1
    assert r.buffer == None
    r.close()


def test_FormattedTextFileReader_close():
    r = io.FormattedTextFileReader()
    r.open("data/tdump")
    r.close()   # just check if close() is declared.


def test_FormattedTextFileReader_fetch_line():
    r = io.FormattedTextFileReader()
    r.open("data/three_lines")

    r.fetch_line()
    assert r.buffer == "line 1"

    r.fetch_line()
    assert r.buffer == "line 2"

    r.close()


def test_FormattedTextFileReader_has_next():
    r = io.FormattedTextFileReader()
    r.open("data/three_lines")

    assert r.has_next() == True
    r.fetch_line()

    assert r.has_next() == True
    r.fetch_line()

    assert r.has_next() == True
    r.fetch_line()

    assert r.has_next() == False

    r.close()


def test_FormattedTextFileReader_parse_line():
    r = io.FormattedTextFileReader()
    r.open("data/tdump")

    r.fetch_line()
    v = r.parse_line("A8,5I6")
    assert v[0] == "    NGM "
    assert v[1] == 95
    assert v[2] == 10
    assert v[3] == 16
    assert v[4] == 0
    assert v[5] == 0

    r.close()


def test_FormattedTextFileReader_look_ahead():
    r = io.FormattedTextFileReader()
    r.open("data/tdump")

    r.fetch_line()
    v = r.look_ahead("A8,5I6")
    assert v[0] == "    NGM "
    assert v[1] == 95
    assert v[2] == 10
    assert v[3] == 16
    assert v[4] == 0
    assert v[5] == 0

    w = r.parse_line("A8,5I6")
    assert w[0] == "    NGM "
    assert w[1] == 95
    assert w[2] == 10
    assert w[3] == 16
    assert w[4] == 0
    assert w[5] == 0

    r.close()


def test_FormattedTextFileReader_get_current_line():
    r = io.FormattedTextFileReader()
    r.open("data/tdump")

    r.fetch_line()
    assert r.get_current_line() ==  "     1     1"
