# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_timezone.py
#
# Performs unit tests on functions and class methods declared in timezone.py.
#
# Last update: 13 OCT 2026
# ---------------------------------------------------------------------------

import datetime
from datetime import timezone
from zoneinfo import ZoneInfo

from ..hysplitplot.timezone import (
    TimeZoneHelper,
    determine_timezone,
    get_utctime_from_localtime,
    get_localtime_from_utctime,
)

def test_TimeZoneHelper___init__():
    p = TimeZoneHelper()

    assert hasattr(p, "time_zone_finder") and p.time_zone_finder is not None


def test_TimeZoneHelper__normalize_time_zone_name():
    p = TimeZoneHelper()

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
    p = TimeZoneHelper()
    
    tz = p.lookup_time_zone("US/Eastern")
    assert tz is not None
    assert tz.key == "US/Eastern"
    
    tz = p.lookup_time_zone("Deep/InTheSpace")
    assert tz is None

    # Support the time zone specification used by TZONE in LABELS.CFG
    tz = p.lookup_time_zone("UTC+00")
    assert tz.key == "Etc/GMT"


def test_TimeZoneHelper_get_time_zone_at():
    p = TimeZoneHelper()
    
    tz = p.get_time_zone_at((-73.9620, 40.7874))
    assert tz is not None
    assert tz.key == "America/New_York"
    
    tz = p.get_time_zone_at((-157.9791, 21.4862))
    assert tz is not None
    assert tz.key == "Pacific/Honolulu"
    
    # Somewhere in the Pacific Ocean
    tz = p.get_time_zone_at((-128.6962, 6.8179))
    assert tz is not None
    assert tz.key == "Etc/GMT+9"
    # If "UTC" is returned, you will need to install a timezone database with oceans included.
    
    # somewhere in the Philippine Sea
    tz = p.get_time_zone_at((133.0391, 14.5434))
    assert tz is not None
    assert tz.key == "Etc/GMT-9"
    # If "UTC" is returned, you will need to install a timezone database with oceans included.


def test_determine_timezone():
   tz = determine_timezone(38.48, -99.58)
   assert tz == ZoneInfo('America/Chicago')


def test_get_utctime_from_localtime():
   loc = datetime.datetime(2022, 12, 29, 6, 0, 0)
   utc = get_utctime_from_localtime(loc, ZoneInfo('America/New_York'))
   # add 5
   assert utc == datetime.datetime(2022, 12, 29, 11, 0, 0, tzinfo=timezone.utc)


def test_get_localtime_from_utctime():
   utc = datetime.datetime(2022, 12, 29, 11, 0, 0, tzinfo=timezone.utc)
   loc = get_localtime_from_utctime(utc, ZoneInfo('America/New_York'))
   assert str(loc) == '2022-12-29 06:00:00-05:00'
