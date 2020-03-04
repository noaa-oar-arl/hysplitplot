# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# timezone.py
#
# For providing time zone utilities.
# ---------------------------------------------------------------------------

import logging
import pytz
from timezonefinder import TimezoneFinder


logger = logging.getLogger(__name__)


class TimeZoneHelper:

    def __init__(self):
        self.time_zone_finder = TimezoneFinder()

    def _normalize_time_zone_name(self, time_zone_name):
        # See if the time zone is in the HYSPLIT format.
        if len(time_zone_name) == 6 and (time_zone_name[3] == "+" or time_zone_name[3] == "-"):
            try:
                tz = time_zone_name[0:3].upper()
                if tz == "UTC" or tz == "GMT":
                    sgn = time_zone_name[3]
                    offset = int(time_zone_name[4:6])
                    return "Etc/GMT" if offset == 0 else "Etc/GMT{}{:d}".format(sgn, offset)                
            except ValueError:
                pass
        return time_zone_name

    def lookup_time_zone(self, time_zone_name):
        time_zone = None
        time_zone_name = self._normalize_time_zone_name(time_zone_name)
        try:
            time_zone = pytz.timezone(time_zone_name)
        except pytz.exceptions.UnknownTimeZoneError as ex:
            logger.error("unrecognized time zone {}".format(time_zone_name))

        return time_zone

    def get_time_zone_at(self, lonlat):
        lon, lat = lonlat

        time_zone = None
        time_zone_name = None
        try:
            finder = self.time_zone_finder
            time_zone_name = finder.timezone_at(lng=lon, lat=lat)
            if time_zone_name is None:
                time_zone_name = finder.closest_timezone_at(lng=lon, lat=lat)
            if time_zone_name is None:
                logger.warning("cannot find time zone for lon %f, lat %f: "
                               "using UTC", lon, lat)

            time_zone = self.lookup_time_zone(time_zone_name)
        except ValueError as ex:
            logger.error("cannot find time zone for "
                         "lon {}, lat {}: {}".format(lon, lat, ex))
            pass

        return pytz.utc if time_zone is None else time_zone
