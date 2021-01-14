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

