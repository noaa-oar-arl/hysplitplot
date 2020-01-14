# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# stnplot.py
#
# For reading a station plot file.
# ---------------------------------------------------------------------------

import logging

from hysplitdata import io


logger = logging.getLogger(__name__)


class StationPlotConfig:

    def __init__(self):
        self.stations = []
        return

    def get_reader(self):
        return StationPlotConfigReader(self)

    class Station:

        def __init__(self, lat, lon, label):
            self.latitude = lat
            self.longitude = lon
            self.label = label


class StationPlotConfigReader(io.FormattedTextFileReader):

    def __init__(self, cfg):
        super(StationPlotConfigReader, self).__init__()
        self.cfg = cfg

    def read(self, filename):
        self.cfg.stations.clear()

        self.open(filename)

        while self.has_next():
            v = self.parse_line("F6.2,1X,F7.2,1X,A80")
            if len(v) == 2:
                v.append("")
            if len(v) == 3:
                self.cfg.stations.append(
                    StationPlotConfig.Station(v[0], v[1], v[2].strip()))
            else:
                raise Exception("cannot parse a line in file "
                                "{0}".format(filename))

        self.close()

        return self.cfg
