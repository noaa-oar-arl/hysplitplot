# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_helper.py
#
# Performs unit tests on functions and class methods declared in grid/helper.py.
# ---------------------------------------------------------------------------
import logging
import os

from hysplitplot.grid import helper


logger = logging.getLogger(__name__)


def test_GisOutputFilenameForGridPlot_get_basename():
    o = helper.GisOutputFilenameForGridPlot()
    assert o.get_basename(1, 'ps') == 'polygons_001_ps'
    assert o.get_basename(2, 'jobid', 50) == 'polygons_002_jobid'


def test_KmlOutputFilenameForGridPlot_get_basename():
    o = helper.KmlOutputFilenameForGridPlot()
    assert o.get_basename(1, 'ps') == 'plot.ps'
    assert o.get_basename(2, 'jobid', 50) == 'plot.ps'


def test_TextOutputForGridPlot__init__():
    o = helper.TextOutputForGridPlot()
    assert o.fp is None
    assert o.frame_no < 0


def test_TextOutputForGridPlot_open():
    o = helper.TextOutputForGridPlot()
    fn = "plot_050.txt"
    if os.path.exists(fn):
        os.remove(fn)
    
    o.open(49)
    
    assert o.frame_no == 50
    assert o.fp is not None
    assert os.path.exists(fn)
    
    o.close()
    os.remove(fn)


def test_TextOutputForGridPlot_close():
    o = helper.TextOutputForGridPlot()
    fn = "plot_050.txt"
    if os.path.exists(fn):
        os.remove(fn)
    
    o.open(49)
    o.close()
    
    assert o.fp is None
    assert os.path.exists("plot_050.txt")
    
    os.remove("plot_050.txt")


def test_TextOutputForGridPlot_write():
    o = helper.TextOutputForGridPlot()
    fn = "plot_050.txt"
    if os.path.exists(fn):
        os.remove(fn)
    # write a grid value
    o.open(49)
    o.write(100, 150, 1.25)
    o.close()
    # read back the file
    lines = None
    with open("plot_050.txt", "rt") as f:
        lines = f.readlines()
    # check the line content
    assert len(lines) == 1
    assert lines[0] == "        50       101       151   1.250000E+00\n"
    # delete the temporary file.
    os.remove("plot_050.txt")
