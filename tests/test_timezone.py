# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_timezone.py
#
# Performs unit tests on functions and class methods declared in timezone.py.
# ---------------------------------------------------------------------------

import datetime
import pytest
import pytz

from hysplitplot import timezone
        

def test_TimeZoneHelper___init__():
    p = timezone.TimeZoneHelper()

    assert hasattr(p, "time_zone_finder") and p.time_zone_finder is not None


def test_TimeZoneHelper__normalize_time_zone_name():
    p = timezone.TimeZoneHelper()

    assert p._normalize_time_zone_name("UTC+12") == "Etc/GMT+12"
    assert p._normalize_time_zone_name("UTC+11") == "Etc/GMT+11"
    assert p._normalize_time_zone_name("UTC+00") == "Etc/GMT"
    assert p._normalize_time_zone_name("UTC-11") == "Etc/GMT-11"
    assert p._normalize_time_zone_name("UTC-12") == "Etc/GMT-12"
    
    assert p._normalize_time_zone_name("GMT+12") == "Etc/GMT+12"
    assert p._normalize_time_zone_name("GMT+11") == "Etc/GMT+11"
    assert p._normalize_time_zone_name("GMT+00") == "Etc/GMT"
    assert p._normalize_time_zone_name("GMT-11") == "Etc/GMT-11"
    assert p._normalize_time_zone_name("GMT-12") == "Etc/GMT-12"
    
    # When calling with a non-HYSPLIT timezone string
    assert p._normalize_time_zone_name("UTC+0000") == "UTC+0000"
    assert p._normalize_time_zone_name("UTC+dd") == "UTC+dd"


def test_TimeZoneHelper_lookup_time_zone():
    p = timezone.TimeZoneHelper()
    
    tz = p.lookup_time_zone("US/Eastern")
    assert tz is not None
    assert tz.zone == "US/Eastern"
    
    tz = p.lookup_time_zone("Deep/InTheSpace")
    assert tz is None

    # Support the time zone specification used by TZONE in LABELS.CFG
    tz = p.lookup_time_zone("UTC+00")
    assert tz.zone == "Etc/GMT"


def test_TimeZoneHelper_get_time_zone_at():
    p = timezone.TimeZoneHelper()
    
    tz = p.get_time_zone_at((-73.9620, 40.7874))
    assert tz is not None
    assert tz.zone == "America/New_York"
    
    tz = p.get_time_zone_at((-157.9791, 21.4862))
    assert tz is not None
    assert tz.zone == "Pacific/Honolulu"
    
    # Somewhere in the Pacific Ocean
    tz = p.get_time_zone_at((-128.6962, 6.8179))
    assert tz is not None
    assert tz.zone == "Etc/GMT+9"
    # If "UTC" is returned, you will need to install a timezone database with oceans included.
    
    # somewhere in the Philippine Sea
    tz = p.get_time_zone_at((133.0391, 14.5434))
    assert tz is not None
    assert tz.zone == "Etc/GMT-9"
    # If "UTC" is returned, you will need to install a timezone database with oceans included.

