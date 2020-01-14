# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# datem.py
#
# Provides a DATEM file reader.
# ---------------------------------------------------------------------------

import datetime
import logging
import pytz

from hysplitdata import io


logger = logging.getLogger(__name__)


class Datem:

    def __init__(self):
        self.items = []

    def clear(self):
        self.items.clear()

    def get_reader(self):
        return DatemReader(self)

    def make_plot_data(self, starting_dt, ending_dt):
        r = dict()
        for m in self.items:
            if (starting_dt >= m.starting_datetime and ending_dt <= m.ending_datetime) \
              or (starting_dt <= m.starting_datetime and ending_dt >= m.ending_datetime):
                key = (m.longitude, m.latitude)
                if key in r:
                    if m.value > 0:
                        r[key].append(m.value_str)
                else:
                    if m.value > 0:
                        r[key] = [m.value_str]
                    else:
                        r[key] = []

        a = []
        for (lon, lat), val_strs in r.items():
            if len(val_strs) > 0:
                s = " "  # one-space for a marker
                for k, v in enumerate(val_strs):
                    if k > 0:
                        s += ";"
                    s += v
            else:
                s = None
            o = Datem.AggregatedItem(lon, lat, s)
            a.append(o)

        return a

    class Item:

        def __init__(self, start_dt, end_dt, lon, lat, val, stn):
            self.starting_datetime = start_dt
            self.ending_datetime = end_dt
            self.latitude = lat
            self.longitude = lon
            self.value = val
            self.station_name = "" if stn is None else stn.strip()

        @property
        def value_str(self):
            return "{:d}".format(int(self.value))

    class AggregatedItem:

        def __init__(self, lon, lat, val):
            self.latitude = lat
            self.longitude = lon
            self.value_str = val


class DatemReader(io.FormattedTextFileReader):

    def __init__(self, datem):
        super(DatemReader, self).__init__()
        self.datem = datem

    def read(self, filename):
        self.datem.clear()

        self.open(filename)

        # skip 2 header lines
        self.fetch_line()
        self.fetch_line()

        time_zone = pytz.utc
        while self.has_next():
            v = self.parse_line("I4,I3,I3,I5,I5,F6.2,F8.2,F8.1,A5")

            hour = int(v[3] / 100)
            minute = v[3] - hour * 100
            starting_datetime = datetime.datetime(v[0], v[1], v[2], hour,
                                                  minute, 0, 0, time_zone)

            hour = int(v[4] / 100)
            minute = v[4] - hour * 100
            ending_datetime = starting_datetime \
                + datetime.timedelta(hours=hour, minutes=minute)

            entry = Datem.Item(starting_datetime, ending_datetime, v[6], v[5],
                               v[7], v[8])
            self.datem.items.append(entry)

        return self.datem
