# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# clrtbl.py
#
# For color tables.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
import os
import logging

from hysplitdata import io
from .. import const, util

logger = logging.getLogger(__name__)


class ColorTableFactory:

    COLOR_TABLE_FILE_NAMES = ["CLRTBL.CFG", "../graphics/CLRTBL.CFG"]

    @staticmethod
    def create_instance(settings, color_opacity=100):
        ncolors = settings.contour_level_count
        logger.debug("ColorTableFactory::create_instance: color count %d, opacity %d",
                     ncolors, color_opacity)

        skip_std_colors = False
        if settings.contour_level_generator == \
                const.ContourLevelGenerator.USER_SPECIFIED:
            skip_std_colors = True
        elif settings.contour_level_generator in [
                const.ContourLevelGenerator.EXPONENTIAL_DYNAMIC,
                const.ContourLevelGenerator.CLG_50,
                const.ContourLevelGenerator.CLG_60] \
            and settings.IDYNC != 0:
            skip_std_colors = True

        if settings.KMAP == const.ConcentrationMapType.THRESHOLD_LEVELS \
                and settings.KHEMIN == 1:
            ct = DefaultChemicalThresholdColorTable(ncolors, skip_std_colors, color_opacity)
        elif settings.user_color:
            ct = UserColorTable(settings.user_colors, color_opacity)
        else:
            ct = DefaultColorTable(ncolors, skip_std_colors, color_opacity)
            f = ColorTableFactory._get_color_table_filename()
            if f is not None:
                ct.get_reader().read(f)
                if settings.contour_level_generator in [
                        const.ContourLevelGenerator.EXPONENTIAL_DYNAMIC,
                        const.ContourLevelGenerator.CLG_50,
                        const.ContourLevelGenerator.CLG_60] \
                    and settings.IDYNC != 0:
                    scaled_opacity = color_opacity * 0.01
                    for k in range(5):
                        ct.set_rgb(k, (1.0, 1.0, 1.0, scaled_opacity))

        if settings.IDYNC == 1:
            ct.enable_offset(True)

        if settings.color == const.ConcentrationPlotColor.BLACK_AND_WHITE \
                or settings.color == const.ConcentrationPlotColor.BW_NO_LINES:
            ct.change_to_grayscale()

        logger.debug("using color table: %s", ct)
        return ct

    @staticmethod
    def _get_color_table_filename():
        for s in ColorTableFactory.COLOR_TABLE_FILE_NAMES:
            if os.path.exists(s):
                return s

        return None


class AbstractColorTable(ABC):

    def __init__(self, ncolors, color_opacity=100):
        self.rgbs = []
        self.ncolors = ncolors
        self.scaled_opacity = color_opacity * 0.01
        self.offset = 0
        self.use_offset = False
        return

    def get_reader(self):
        return ColorTableReader(self)

    def set_rgb(self, k, rgb):
        if len(rgb) == 3:
            self.rgbs[k] = (rgb[0], rgb[1], rgb[2], self.scaled_opacity)
        else:
            self.rgbs[k] = rgb

    def change_to_grayscale(self):
        for k, rgb in enumerate(self.rgbs):
            lum = self.get_luminance(rgb)
            self.rgbs[k] = (lum, lum, lum, self.scaled_opacity)

    @staticmethod
    def get_luminance(rgb):
        if len(rgb) == 4:
            r, g, b, _ = rgb
        else:
            r, g, b = rgb
        return 0.299 * r + 0.587 * g + 0.114 * b

    @staticmethod
    def create_plot_colors(rgbs):
        if len(rgbs[0]) == 4:
            return [util.make_color(o[0], o[1], o[2], o[3]) for o in rgbs]
        else:
            return [util.make_color(o[0], o[1], o[2]) for o in rgbs]

    @property
    @abstractmethod
    def raw_colors(self):
        pass

    @property
    @abstractmethod
    def colors(self):
        pass

    def set_offset(self, offset):
        self.offset = offset if self.use_offset else 0

    def enable_offset(self, flag=True):
        self.use_offset = flag


class DefaultColorTable(AbstractColorTable):

    def __init__(self, ncolors, skip_std_colors, color_opacity=100):
        super(DefaultColorTable, self).__init__(ncolors, color_opacity)
        self.skip_std_colors = skip_std_colors
        self.__colors = None
        self.__raw_colors = None
        self.__current_offset = 0
        self.rgbs = [(c[0], c[1], c[2], self.scaled_opacity) for c in [
            (1.0, 1.0, 1.0), (1.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0),
            (0.0, 1.0, 1.0), (1.0, 0.0, 0.0), (1.0, 0.6, 0.0), (1.0, 1.0, 0.0),
            (0.8, 1.0, 0.0), (0.0, 0.6, 0.0), (0.0, 1.0, 0.4), (0.0, 1.0, 1.0),
            (0.0, 0.4, 1.0), (0.2, 0.0, 1.0), (0.6, 0.0, 1.0), (0.8, 0.0, 1.0),
            (0.4, 0.0, 0.4), (0.6, 0.0, 0.4), (0.4, 0.0, 0.2), (0.2, 0.0, 0.2),
            (0.6, 0.0, 0.0), (1.0, 0.8, 1.0), (0.4, 0.4, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0)]
        ]

    @property
    def raw_colors(self):
        if self.__raw_colors is None or self.__current_offset != self.offset:
            if self.skip_std_colors:
                self.__raw_colors = self.rgbs[4 + self.offset + self.ncolors:
                                              self.offset + 4:-1]
            else:
                self.__raw_colors = self.rgbs[self.offset + self.ncolors:
                                              self.offset:-1]

            self.__current_offset = self.offset

        return self.__raw_colors

    @property
    def colors(self):
        if self.__colors is None or self.__current_offset != self.offset:
            self.__colors = self.create_plot_colors(self.raw_colors)

        return self.__colors

    def set_rgb(self, k, rgb):
        super(DefaultColorTable, self).set_rgb(k, rgb)
        self.__raw_colors = None
        self.__colors = None


class DefaultChemicalThresholdColorTable(AbstractColorTable):

    def __init__(self, ncolors, skip_std_colors, color_opacity=100):
        super(DefaultChemicalThresholdColorTable, self).__init__(ncolors,
                                                                 color_opacity)
        self.skip_std_colors = skip_std_colors
        self.__colors = None
        self.__raw_colors = None
        self.__current_offset = 0
        self.rgbs = [(c[0], c[1], c[2], self.scaled_opacity) for c in [
            (1.0, 1.0, 1.0), (0.8, 0.8, 0.8), (1.0, 1.0, 0.0), (1.0, 0.5, 0.0),
            (1.0, 0.0, 0.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0)]
        ]

    @property
    def raw_colors(self):
        if self.__raw_colors is None or self.__current_offset != self.offset:
            if self.skip_std_colors:
                self.__raw_colors = self.rgbs[5 + self.offset:
                                              5 + self.offset + self.ncolors]
            else:
                self.__raw_colors = self.rgbs[1 + self.offset:
                                              1 + self.offset + self.ncolors]

            self.__current_offset = self.offset

        return self.__raw_colors

    @property
    def colors(self):
        if self.__colors is None or self.__current_offset != self.offset:
            self.__colors = self.create_plot_colors(self.raw_colors)

        return self.__colors


class UserColorTable(AbstractColorTable):

    def __init__(self, user_colors, color_opacity=100):
        super(UserColorTable, self).__init__(len(user_colors), color_opacity)
        self.rgbs = [(o[0], o[1], o[2], self.scaled_opacity) for o in user_colors]
        self.__colors = None

    @property
    def raw_colors(self):
        return self.rgbs

    @property
    def colors(self):
        if self.__colors is None:
            self.__colors = self.create_plot_colors(self.raw_colors)

        return self.__colors


class ColorTableReader(io.FormattedTextFileReader):

    def __init__(self, color_table):
        super(ColorTableReader, self).__init__()
        self.color_table = color_table

    def read(self, filename):
        self.open(filename)

        # skip two header lines
        self.fetch_line()
        self.fetch_line()

        w = 1.0 / 255.0
        rgbs = []
        k = 0
        while self.has_next() and k < 32:
            v = self.parse_line("A15,I3,4X,I3,4X,I3")
            logger.debug("color [%s], r %d, g %d, b %d",
                         v[0], v[1], v[2], v[3])
            rgbs.append((v[1] * w, v[2] * w, v[3] * w, self.color_table.scaled_opacity))
            k += 1

        self.color_table.rgbs = rgbs
        self.close()

        return self.color_table
