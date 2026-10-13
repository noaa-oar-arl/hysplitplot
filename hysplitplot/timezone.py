# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# timezone.py - For providing time zone utilities.
#
# 22 MAR 2023 (SYZ) - moved non-class functions determine_timezone(),
#                     get_utctime_from_localtime(), and
#                     get_localtime_from_utctime() to here.
# 22 JUL 2026 (SYZ) - replace pytz with timezone
# 25 AUG 2026 (SYZ) - reformatted code, renamed variables, and added docstrings
# ---------------------------------------------------------------------------

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from timezonefinder import TimezoneFinder

logger = logging.getLogger(__name__)


class TimeZoneHelper:
    """
    A helper class for looking up time zones based on longitude and latitude.
    """

    def __init__(self):
        self.time_zone_finder = TimezoneFinder()

    def _normalize_time_zone_name(self, time_zone_name):
        """
        Normalize the time zone name to a format that can be used by ZoneInfo.
        """
        # See if the time zone is in the HYSPLIT format.
        if len(time_zone_name) == 6 and (
            time_zone_name[3] == "+" or time_zone_name[3] == "-"
        ):
            try:
                tz = time_zone_name[0:3].upper()
                if tz in (
                    "UTC",
                    "GMT",
                ):
                    sgn = time_zone_name[3]
                    offset = int(time_zone_name[4:6])
                    return "Etc/GMT" if offset == 0 else f"Etc/GMT{sgn}{offset:d}"
            except ValueError:
                logger.error("parsing time zone %s failed", time_zone_name)
        return time_zone_name

    def lookup_time_zone(self, time_zone_name):
        """
        Lookup a time zone by name and return a ZoneInfo object.
        """
        time_zone = None
        time_zone_name = self._normalize_time_zone_name(time_zone_name)
        try:
            time_zone = ZoneInfo(time_zone_name)
        except ZoneInfoNotFoundError:
            logger.error("unrecognized time zone %s", time_zone_name)

        return time_zone

    def get_time_zone_at(self, lonlat):
        """
        Get the time zone at a given longitude and latitude.
        """
        lon, lat = lonlat

        time_zone = None
        time_zone_name = None
        try:
            finder = self.time_zone_finder
            time_zone_name = finder.timezone_at(lng=lon, lat=lat)
            if time_zone_name is None:
                # closest_timezone_at() was removed from timezonefinder version 4.0.0.
                # We use timezone_at() instead of closest_timezone_at().
                time_zone_name = finder.timezone_at(lng=lon, lat=lat)
            if time_zone_name is None:
                logger.warning(
                    "cannot find time zone for lon %f, lat %f: using UTC", lon, lat
                )

            time_zone = self.lookup_time_zone(time_zone_name)
        except ValueError as ex:
            logger.error(
                "cannot find time zone for lon %f, lat %f: %s", lon, lat, str(ex)
            )

        return timezone.utc if time_zone is None else time_zone


def determine_timezone(lat: float, lon: float) -> object:
    """
    Determine the timezone at a given latitude and longitude.
    """
    helper = TimeZoneHelper()
    tz = helper.get_time_zone_at(
        (
            lon,
            lat,
        )
    )
    return tz


def get_utctime_from_localtime(
    dt_unaware: datetime, tz: timezone  # unaware of timezone
) -> datetime:
    """
    Convert a local datetime to a UTC datetime in the specified timezone.
    """
    loc_dt = dt_unaware.replace(tzinfo=tz)
    utc_dt = loc_dt.astimezone(timezone.utc)
    return utc_dt


def get_localtime_from_utctime(utc_dt: datetime, tz: timezone) -> datetime:
    """
    Convert a UTC datetime to a local datetime in the specified timezone.
    """
    loc_dt = utc_dt.astimezone(tz)
    return loc_dt
