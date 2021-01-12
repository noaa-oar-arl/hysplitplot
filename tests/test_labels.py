# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_labels.py
#
# Performs unit tests on functions and class methods declared in labels.py.
# ---------------------------------------------------------------------------

import os
import pytest

from hysplitdata.const import HeightUnit
from hysplitplot import labels, const
from hysplitplot.traj import plot


def test_LabelsConfig___init__():
    c = labels.LabelsConfig()
    assert c.cfg is not None


def test_LabelsConfig_get():
    c = labels.LabelsConfig()
    assert c.has("TITLE") == True
    assert c.has("NONEXISTENT") == False


def test_LabelsConfig_get():
    c = labels.LabelsConfig()
    assert c.get("TITLE") == "NOAA HYSPLIT MODEL"
    assert c.get("NONEXISTENT") == ""
    assert c.get("NONEXISTENT", "default") == "default"


def test_LabelsConfig_get_reader():
    c = labels.LabelsConfig()
    r = c.get_reader()
    assert isinstance(r, labels.LabelsConfigReader)
    assert r.obj == c


def test_LabelsConfig_after_reading_file():
    c = labels.LabelsConfig()
    s = plot.TrajectoryPlotSettings()
    assert s.height_unit == HeightUnit.METERS
    c.after_reading_file(s)
    assert s.height_unit == HeightUnit.METERS
    c.cfg["VUNIT"] = "FEET"
    c.after_reading_file(s)
    assert s.height_unit == HeightUnit.FEET
    

def test_LabelsConfigReader_read():
    c = labels.LabelsConfig()
    r = c.get_reader()
    o = r.read("data/LABELS.CFG")
    assert isinstance(o, labels.LabelsConfig)
    assert c.get("TITLE") == "Sagebrush Exp #5"
    assert c.get("MAPID") == "Air Concentration"
    assert c.get("LAYER") == " between"
    assert c.get("UNITS") == "ppt"
    assert c.get("VOLUM") == ""
    assert c.get("RELEASE") == ""

    # create a scratch file.
    with open("__scratch.cfg", "wt") as f:
        f.write("'NTXBOXL&','2&'\n")
        f.write("'TXBOXL&','line 1&'\n")
        f.write("'TXBOXL&','line 2&'\n")

    c = labels.LabelsConfig()
    c.get_reader().read("__scratch.cfg")
    assert c.get("NTXBOXL") == "2"
    assert c.get("TXBOXL") == ["line 1", "line 2"]

    # when the CFG file has an issue
    with open("__scratch.cfg", "wt") as f:
        f.write("'TXBOXL&','line 1&'\n")
        f.write("'TXBOXL&','line 2&'\n")
        f.write("'NTXBOXL&','2&'\n")

    c = labels.LabelsConfig()
    try:
        c.get_reader().read("__scratch.cfg")
        pytest.fail("expected an exception")
    except Exception as ex:
        assert str(ex) == "Consistency check failed. Please fix __scratch.cfg"

    os.remove("__scratch.cfg")


def test_LabelsConfigReader_check_consistency():
    r = labels.LabelsConfig().get_reader()
    assert r.escape('meter&') == 'meter&'
    assert r.escape(' %&') == ' \%&'


def test_LabelsConfigReader_check_consistency():
    r = labels.LabelsConfig().get_reader()
    assert r.check_consistency("data/LABELS.CFG") == True

    # when TXBOXL appears before NTXBOXL
    with open("__scratch.cfg", "wt") as f:
        f.write("'TXBOXL&','line 1&'\n")
        f.write("'NTXBOXL&','2&'\n")

    c = labels.LabelsConfig()
    assert c.get_reader().check_consistency("__scratch.cfg") == False

    # when the TXBOXL count is not equal to NTXBOXL
    with open("__scratch.cfg", "wt") as f:
        f.write("'NTXBOXL&','2&'\n")
        f.write("'TXBOXL&','line 1&'\n")
        f.write("'TITLE&','MODEL&'\n")

    c = labels.LabelsConfig()
    assert c.get_reader().check_consistency("__scratch.cfg") == False

    os.remove("__scratch.cfg")


def test_LabelsConfigReader_parse_line():
    r = labels.LabelsConfig().get_reader()
    assert r.parse_line("'TITLE&','MODEL&'") == ("TITLE", "MODEL")
    assert r.parse_line("'TITLE&' , 'MODEL&'") == ("TITLE", "MODEL")
    assert r.parse_line("'TITLE&','MODEL ESCAPED '' &'") == ("TITLE", "MODEL ESCAPED ' ")
