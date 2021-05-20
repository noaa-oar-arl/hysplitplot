# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# mapfile.py
#
# For reading an ARL map file or a shape file.
# ---------------------------------------------------------------------------

import geopandas
import logging
import os
import shapely.geometry

from hysplitdata import io
from hysplitplot import util, mapproj


logger = logging.getLogger(__name__)


class ARLMap:

    def __init__(self):
        self.segments = []
        return

    def get_reader(self):
        return ARLMapReader(self)

    def dump(self, stream):
        stream.write("ARLMap: {0} segments\n".format(len(self.segments)))
        for s in self.segments:
            s.dump(stream)

    class Segment:

        def __init__(self, no, lat, lon, clr, thk):
            self.number = no
            self.latitudes = lat
            self.longitudes = lon
            self.color = clr
            self.thickness = thk

        def dump(self, stream):
            stream.write("seg {0}, lat {1}, lon {2}, clr {3}, thk {4}\n"
                         .format(self.number, self.latitudes, self.longitudes,
                                 self.color, self.thickness))


class ARLMapReader(io.FormattedTextFileReader):

    def __init__(self, map):
        io.FormattedTextFileReader.__init__(self)
        self.map = map
        self.colors = {"BOUNDARY": util.make_color(.0, .0, .0),
                       "COUNTIES": util.make_color(.8, .8, .8),
                       "ROADS": util.make_color(.8, .0, .0),
                       "RIVERS": util.make_color(.0, .0, .8),
                       "default": util.make_color(.4, .6, .8)}
        self.thickness = {"BOUNDARY": 0.01,
                          "COUNTIES": 0.008,
                          "ROADS": 0.008,
                          "RIVERS": 0.008,
                          "default": 0.01}

    def read(self, filename):
        self.map.segments.clear()

        self.open(filename)

        while self.has_next():
            v = self.parse_line("2I5")
            segno = v[0]
            npts = v[1]
            line_type = self.get_current_line()[10:].strip()

            lats = []
            left = npts
            while left > 0:
                if left >= 10:
                    lats.extend(self.parse_line("10F6.2"))
                    left -= 10
                else:
                    lats.extend(self.parse_line("{0}F6.2".format(left)))
                    left = 0

            lons = []
            left = npts
            while left > 0:
                if left >= 10:
                    lons.extend(self.parse_line("10F7.2"))
                    left -= 10
                else:
                    lons.extend(self.parse_line("{0}F7.2".format(left)))
                    left = 0

            if line_type in self.colors:
                clr = self.colors[line_type]
            else:
                clr = self.colors["default"]
            if line_type in self.thickness:
                thk = self.thickness[line_type]
            else:
                thk = self.thickness["default"]
            self.map.segments.append(ARLMap.Segment(segno, lats, lons, clr,
                                                    thk))

        self.close()

        return self.map


class ARLMapConverter:

    @staticmethod
    def convert(arlmap):
        # group by line style
        segments = dict()
        colors = dict()
        thicknesses = dict()
        for s in arlmap.segments:
            lonlats = util.myzip(s.longitudes, s.latitudes)
            # LineString() requires at least two points.
            if len(lonlats) > 1:
                style = ARLMapConverter.style_ref(s.color, s.thickness)
                if style in segments:
                    segments[style].append(shapely.geometry.LineString(lonlats))
                else:
                    segments[style] = [shapely.geometry.LineString(lonlats)]
                    colors[style] = s.color
                    thicknesses[style] = s.thickness

        # create drawables
        drawables = []
        for k, v in segments.items():
            gs = geopandas.GeoSeries(v)
            gs.crs = mapproj.AbstractMapProjection._WGS84
            drawables.append(DrawableBackgroundMap(gs, colors[k],
                                                   thicknesses[k]))

        return drawables

    @staticmethod
    def style_ref(color, thickness):
        return "{0}_{1}".format(color, thickness)


class DrawableBackgroundMap:

    def __init__(self, map, clr, thickness):
        self.map = map
        self.linestyle = '-'
        self.linewidth = thickness * 50
        self.linecolor = clr


class ShapeFile:
    """An entry in a shapefiles file"""

    def __init__(self):
        self.filename = "arlmap.shp"
        self.dash = 0
        self.thickness = 0.01
        self.red = 0.4
        self.blue = 0.6
        self.green = 0.8


class ShapeFilesReader:
    """Reads a shapefiles file and puts its contents into a list"""

    def __init__(self):
        self.shapefiles = []

    def read(self, filename):
        self.shapefiles.clear()

        if not os.path.exists(filename):
            self.warn_and_create_sample(filename)
        else:
            with open(filename, "rt") as f:
                for ln in f:
                    tokens = self.parse_line(ln.rstrip("\n"))
                    o = ShapeFile()
                    o.filename = tokens[0]
                    o.dash = float(tokens[1])
                    o.thickness = float(tokens[2])
                    o.red = float(tokens[3])
                    o.green = float(tokens[4])
                    o.blue = float(tokens[5])
                    self.shapefiles.append(o)

        return self.shapefiles

    def parse_line(self, ln):
        tokens = []
        state = 0
        for c in ln:
            if state == 0:  # looking for opening quote
                if c == "'":
                    t = ""
                    state = 1
            elif state == 1:
                if c == "'":
                    state = 2
                else:
                    t += c
            elif state == 2:
                if c == "'":  # escaped single quote
                    t += c
                    state = 1
                else:
                    tokens.append(t)
                    if c == " ":
                        t = ""
                        state = 3
                    else:
                        t = c
                        state = 4
            elif state == 3:
                if c != " ":
                    t += c
                    state = 4
            elif state == 4:
                if c == " ":
                    tokens.append(t)
                    t = ""
                    state = 3
                else:
                    t += c

        if state == 4:
            tokens.append(t)

        return tokens

    def warn_and_create_sample(self, filename):
        logger.error("file not found %s", filename)
        logger.error("Record format: ''file.shp'' dash thick red green blue")
        logger.error("file.shp = /dir/name of input shapefile in quotes")
        logger.error("dash = {0} for solid; {dashes}/in; <0 color fill")
        logger.error("thick = line thickness in inches (default = 0.01)")
        logger.error("Red Green Blue = RGB values (0.0 0.0 0.0 is black)")
        logger.error("Sample file has been created in the working directory!")

        with open(filename, "wt") as f:
            f.write("'arlmap.shp' 0 0.01 0.4 0.6 0.8\n")

        raise Exception("file not found {0}: please see the error messages "
                        "above".format(filename))


class ShapeFileConverter:

    @staticmethod
    def convert(shapefile):
        map = geopandas.read_file(shapefile.filename)
        if map.crs is None or len(map.crs) == 0:
            map.crs = mapproj.AbstractMapProjection._WGS84
        o = DrawableBackgroundMap(map,
                                  util.make_color(shapefile.red,
                                                  shapefile.green,
                                                  shapefile.blue),
                                  shapefile.thickness)
        o.linestyle = ShapeFileConverter.make_linestyle(shapefile.dash)
        return o

    @staticmethod
    def make_linestyle(dash):
        if dash == 0:
            return '-'
        d = abs(72.0/(2*dash))
        return (0, (d, d))
