# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_datem.py
#
# Performs unit tests on functions and class methods declared in datem.py.
# ---------------------------------------------------------------------------

import datetime
import pytest
import pytz

from hysplitplot import datem


def test_Datem___init__():
    o = datem.Datem()
    assert len(o.items) == 0
    

def test_Datem_clear():
    o = datem.Datem()
    o.items.append(1)
    assert len(o.items) == 1
    
    o.clear()
    assert len(o.items) == 0


def test_Datem_get_reader():
    o = datem.Datem()
    r = o.get_reader()
    assert isinstance(r, datem.DatemReader)
    assert r.datem is o


def test_Datem_make_plot_data():
    o = datem.Datem()
    
    sampling_start_dt   = datetime.datetime(2019, 7, 12, 6, 0)
    sampling_end_dt     = datetime.datetime(2019, 7, 12, 9, 0)
    
    # before sampling ended
    starting_datetime   = datetime.datetime(2019, 7, 12, 4, 30)
    ending_datetime     = datetime.datetime(2019, 7, 12, 5, 30)
    latitude            =  43.18
    longitude           = -79.40
    value               =   3.14
    station_name        = "  552"
    m = datem.Datem.Item(starting_datetime, ending_datetime, longitude, latitude, value, station_name)
    o.items.append(m)
    
    # during the sampling period with zero value
    starting_datetime   = datetime.datetime(2019, 7, 12, 6, 30)
    ending_datetime     = datetime.datetime(2019, 7, 12, 8, 30)
    latitude            =  43.18
    longitude           = -79.40
    value               =   0.0
    station_name        = "  552"
    m = datem.Datem.Item(starting_datetime, ending_datetime, longitude, latitude, value, station_name)
    o.items.append(m)   
    
    # during the sampling period with non-zero value
    starting_datetime   = datetime.datetime(2019, 7, 12, 6, 30)
    ending_datetime     = datetime.datetime(2019, 7, 12, 8, 30)
    latitude            =  45.18
    longitude           = -77.40
    value               =   3.14
    station_name        = "  553"
    m = datem.Datem.Item(starting_datetime, ending_datetime, longitude, latitude, value, station_name)
    o.items.append(m)   

    # during the sampling period with non-zero value
    starting_datetime   = datetime.datetime(2019, 7, 12, 6, 30)
    ending_datetime     = datetime.datetime(2019, 7, 12, 8, 30)
    latitude            =  45.18
    longitude           = -77.40
    value               =   5.14
    station_name        = "  553"
    m = datem.Datem.Item(starting_datetime, ending_datetime, longitude, latitude, value, station_name)
    o.items.append(m) 
 
    filtered_data = o.make_plot_data(sampling_start_dt, sampling_end_dt)
    
    assert len(filtered_data) == 2

    assert filtered_data[0].latitude  ==  43.18
    assert filtered_data[0].longitude == -79.40
    assert filtered_data[0].value_str == None
    
    assert filtered_data[1].latitude  ==  45.18
    assert filtered_data[1].longitude == -77.40
    assert filtered_data[1].value_str == " 3;5"
    

def test_Item___init():
    starting_datetime   = datetime.datetime(2019, 7, 12, 11, 25)
    ending_datetime     = datetime.datetime(2019, 7, 12, 11, 30)
    latitude            =  43.18
    longitude           = -79.40
    value               =   3.14
    station_name        = "  552"
    
    o = datem.Datem.Item(starting_datetime, ending_datetime, longitude, latitude, value, station_name)
    
    assert o.starting_datetime == starting_datetime
    assert o.ending_datetime == ending_datetime
    assert o.latitude == 43.18
    assert o.longitude == -79.40
    assert o.value == 3.14
    assert o.station_name == "552"


def test_Item_value_str():
    starting_datetime   = datetime.datetime(2019, 7, 12, 11, 25)
    ending_datetime     = datetime.datetime(2019, 7, 12, 11, 30)
    latitude            =  43.18
    longitude           = -79.40
    value               =   3.14
    station_name        = "552"
    o = datem.Datem.Item(starting_datetime, ending_datetime, longitude, latitude, value, station_name)

    assert o.value_str == "3"
    

def test_AggregatedItem___init__():
    o = datem.Datem.AggregatedItem(-79.40, 43.18, "3")
    assert o.latitude == 43.18
    assert o.longitude == -79.40
    assert o.value_str == "3"

    
def test_DatemReader___init__():
    o = datem.Datem()
    r = datem.DatemReader(o)
    assert r.datem is o


def test_DatemReader_read():
    o = datem.Datem()
    r = o.get_reader()
    
    obj = r.read("data/meas-t1.txt")
    
    assert obj is o
    assert len(o.items) == 2281
    
    utc = pytz.utc
    
    # check the first entry
    k = o.items[0]
    assert k.starting_datetime == datetime.datetime(1983, 9, 18, 18, 0, 0, 0, utc)
    assert k.ending_datetime == datetime.datetime(1983, 9, 18, 21, 0, 0, 0, utc)
    assert k.latitude == 39.65
    assert k.longitude == -80.42
    assert k.value == 0.0
    assert k.station_name == "302"
    
    # check the last entry
    k = o.items[-1]
    assert k.starting_datetime == datetime.datetime(1983, 10, 31, 6, 0, 0, 0, utc)
    assert k.ending_datetime == datetime.datetime(1983, 10, 31, 12, 0, 0, 0, utc)
    assert k.latitude == 40.78
    assert k.longitude == -74.67
    assert k.value == 0.0
    assert k.station_name == "703"
    
    # nonzero value
    k = o.items[-3]
    assert k.value == 31.2    
    
    
    
    
    
