# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_helper.py
#
# Performs unit tests on functions and class methods declared in grid/helper.py.
# ---------------------------------------------------------------------------

import logging

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

