# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_stnplot.py
#
# Performs unit tests on functions and class methods declared in stnplot.py.
# ---------------------------------------------------------------------------

import os
import pytest

from hysplitplot import stnplot


def test_StationPlotConfig___init__():
    c = stnplot.StationPlotConfig()
    assert c.stations is not None
    assert len(c.stations) == 0


def test_StationPlotConfig_get_reader():
    c = stnplot.StationPlotConfig()
    r = c.get_reader()
    assert isinstance(r, stnplot.StationPlotConfigReader)
    assert r.cfg is c


def test_Station___init__():
    s = stnplot.StationPlotConfig.Station(30.0, -120.0, "STATION")
    assert s.longitude == -120.0
    assert s.latitude == 30.0
    assert s.label == "STATION"


def test_StationPlotConfigReader___init__():
    c = stnplot.StationPlotConfig()
    r = stnplot.StationPlotConfigReader(c)
    assert r.cfg == c


def test_StationPlotConfigReader_read():
    r = stnplot.StationPlotConfig().get_reader()
    c = r.read("data/STATIONPLOT.CFG")
    assert isinstance(c, stnplot.StationPlotConfig)
    assert len(c.stations) == 3
    assert c.stations[0].latitude == 40.0
    assert c.stations[0].longitude == -125.0
    assert c.stations[0].label == "STATION_1"
    assert c.stations[1].latitude == 50.0
    assert c.stations[1].longitude == -90.0
    assert c.stations[1].label == "STATION_2"
    assert c.stations[2].latitude == 40.0
    assert c.stations[2].longitude == -90.0
    assert c.stations[2].label == ""
