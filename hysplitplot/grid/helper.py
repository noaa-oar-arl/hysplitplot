# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# helper.py
#
# Helper functions and classes for producing grid plots.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
import logging

from hysplitplot.conc.helper import AbstractGisOutputFilename


logger = logging.getLogger(__name__)


class GisOutputFilenameForGridPlot(AbstractGisOutputFilename):

    def __init__(self):
        super(GisOutputFilenameForGridPlot, self).__init__()

    def get_basename(self, time_index, output_suffix, level1=0, level2=99999):
        return "polygons_{:03d}_{}".format(time_index, output_suffix)


class KmlOutputFilenameForGridPlot(AbstractGisOutputFilename):

    def __init__(self):
        super(KmlOutputFilenameForGridPlot, self).__init__()

    def get_basename(self, time_index, output_suffix, level1=0, level2=99999):
        return "plot.ps"


class TextOutputForGridPlot:

    def __init__(self):
        self.fp = None
        self.frame_no = -1

    def open(self, time_index):
        self.frame_no = time_index + 1
        fn = "plot_{:03d}.txt".format(self.frame_no)
        self.fp = open(fn, "w")
        logger.info("Writing to %s", fn)

    def close(self):
        if self.fp is not None:
            self.fp.close()
            self.fp = None
    
    def write(self, i, j, c):
        if self.fp is not None:
            self.fp.write("{:10d}{:10d}{:10d}{:15.6E}\n".format(self.frame_no,
                                                          i + 1, j + 1, c))
