import sys
import os
import logging
import numpy
import math
import geopandas
import shapely.geometry
import cartopy.crs
from hysplit4 import io, util
from hysplit4.traj import plot


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
            stream.write("seg {0}, lat {1}, lon {2}, clr {3}, thk {4}\n".format(
                self.number, self.latitudes, self.longitudes, self.color, self.thickness))


class ARLMapReader(io.FormattedTextFileReader):

    def __init__(self, map):
        io.FormattedTextFileReader.__init__(self)
        self.map = map
        self.colors = {"BOUNDARY": util.make_color(.0,.0,.0),
                       "COUNTIES": util.make_color(.8,.8,.8),
                       "ROADS": util.make_color(.8,.0,.0),
                       "RIVERS": util.make_color(.0,.0,.8),
                       "default": util.make_color(.4,.6,.8)}
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
            segno = v[0]; npts = v[1]
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

            clr = self.colors[line_type] if line_type in self.colors else self.colors["default"]
            thk = self.thickness[line_type] if line_type in self.thickness else self.thickness["default"]
            self.map.segments.append(ARLMap.Segment(segno, lats, lons, clr, thk))

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
            gs.crs = plot.TrajectoryPlot._WGS84
            drawables.append( DrawableBackgroundMap(gs, colors[k], thicknesses[k]) )

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

        if os.path.exists(filename) == False:
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
            if state == 0: # looking for opening quote
                if c == "'":
                    t = ""; state = 1
            elif state == 1:
                if c == "'":
                    state = 2
                else:
                    t += c
            elif state == 2:
                if c == "'": # escaped single quote
                    t += c; state = 1
                else:
                    tokens.append(t)
                    if c == " ":
                        t = ""; state = 3
                    else:
                        t = c; state = 4
            elif state == 3:
                if c != " ":
                    t += c; state = 4
            elif state == 4:
                if c == " ":
                    tokens.append(t); t = ""; state = 3
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

        raise Exception("file not found {0}: please see the error messages above".format(filename))


class ShapeFileConverter:

    @staticmethod
    def convert(shapefile):
        map = geopandas.read_file(shapefile.filename)
        if len(map.crs) == 0:
            map.crs = plot.TrajectoryPlot._WGS84
        o = DrawableBackgroundMap(map,
                                  util.make_color(shapefile.red, shapefile.green, shapefile.blue),
                                  shapefile.thickness)
        o.linestyle = ShapeFileConverter.make_linestyle(shapefile.dash)
        return o

    @staticmethod
    def make_linestyle(dash):
        if dash == 0:
            return '-'
        d = abs(72.0/(2*dash))
        return (0, (d, d))


class MapBox:

    def __init__(self):
        self.hit_map = None
        self.sz = [360, 181]
        self.grid_delta = 1.0
        self.grid_corner = [0.0, -90.0] # (lon, lat)
        self.plume_sz = [0.0, 0.0]      # (lon, lat)
        self.plume_loc = [0, 0]         # lon-, lat-indices
        self.hit_count = 0
        self._i = 0
        self._j = 0

    def dump(self, stream):
        stream.write("MapBox: grid delta {0}, sz {1}, corner {2}\n".format(
            self.grid_delta, self.sz, self.grid_corner))
        for j in range(self.sz[1]):
            for i in range(self.sz[0]):
                if self.hit_map[i,j] != 0:
                    stream.write("hit_map[{0},{1}] = {2}\n".format(i, j, self.hit_map[i,j]))

    def allocate(self):
        self.hit_map = numpy.zeros(self.sz, dtype=int)
        self.hit_count = 0

    def add(self, lonlat):
        lon, lat = lonlat
        if lon < 0.0:
            lon += 360.0
        self._i = min(self.sz[0], int((lon - self.grid_corner[0]) / self.grid_delta))
        self._j = min(self.sz[1], int((lat - self.grid_corner[1]) / self.grid_delta))
        # count hits
        self.hit_map[self._i, self._j] += 1
        self.hit_count += 1

    def determine_plume_extent(self):
        self.plume_sz[1] = 0.0
        self.plume_loc[1] = self.sz[1] - 1
        for j in range(self.sz[1]):
            for i in range(self.sz[0]):
                if self.hit_map[i, j] > 0:
                    self.plume_sz[1] += self.grid_delta
                    self.plume_loc[1] = min(self.plume_loc[1], j)
                    break

        self.plume_sz[0] = 0.0
        self.plume_loc[0] = self.sz[0] - 1
        for i in range(self.sz[0]):
            for j in range(self.sz[1]):
                if self.hit_map[i, j] > 0:
                    self.plume_sz[0] += self.grid_delta
                    self.plume_loc[0] = min(self.plume_loc[0], i)
                    break

        return

    def need_to_refine_grid(self):
        return True if (self.plume_sz[0] <= 2.0 and self.plume_sz[1] <= 2.0) else False

    def refine_grid(self):
        # new corner point based on minimum
        self.grid_corner[0] += self.plume_loc[0] * self.grid_delta
        self.grid_corner[1] += self.plume_loc[1] * self.grid_delta
        self.grid_delta = 0.10
        self.sz[1] = int(self.plume_sz[1] / self.grid_delta)
        self.sz[0] = int(self.plume_sz[0] / self.grid_delta)
        self.hit_map = None

    def clear_hit_map(self):
        self.hit_map.fill(0)
        self.hit_count = 0

    def set_ring_extent(self, settings):
        kspan = settings.adjust_ring_distance(self.plume_sz, self.grid_delta)
        logger.debug("set_ring_extent: span %d, distance %g", kspan, settings.ring_distance)
        # plots should be centered about the source point
        self.add(settings.center_loc)
        # set vertical extent of the rings
        half = int(kspan/2)
        for j in range(max(self._j-half, 0), min(self._j+half+1, self.sz[1])):
            self.hit_map[self._i, j] += 1


class CoordinateBase:

    EARTH_RADIUS = 6371.2 # radius of earth in km
    RADPDG = math.pi / 180.0
    DGPRAD = 180.0 / math.pi

    def __init__(self):
        self.parmap = numpy.zeros(9, dtype=float)
        self.grid = 0.0
        self.reflon = 0.0
        self.tnglat = 0.0
        self.slat = 0.0
        self.slon = 0.0
        self.glat = 0.0
        self.glon = 0.0
        return

    def setup(self, center_loc, xc, yc, deltas):
        # grid spacing as 0.5 of input grid spacing
        self.grid = 0.5*min(deltas)*100.0
        logger.debug("Spacing %f", self.grid)

        # projection cut
        self.reflon = center_loc[0]

        self.set_tangent_lat(center_loc)
        self.init_params(xc, yc)

    def init_params(self, xc, yc):
        # create projection
        self._STLMBR(self.parmap, self.tnglat, self.reflon)
        self._STCM1P(self.parmap, xc, yc, self.slat, self.slon, self.glat, self.glon, self.grid, 0.0)

    def rescale(self, xy, corners_lonlat):
        x1, y1 = xy
        alonl, alonr, alatb, alatt = corners_lonlat
        self._STLMBR(self.parmap, self.tnglat, self.reflon)
        self._STCM1P(self.parmap, x1, y1, alatb, alonl, self.glat, self.glon, self.grid, 0.0)
        return self.calc_xy(alonr, alatt)

    def calc_xy(self, plon, plat):
        return CoordinateBase._CLL2XY(self.parmap, plat, plon)

    def calc_lonlat(self, x, y):
        plat, plon = CoordinateBase._CXY2LL(self.parmap, x, y)
        return plon, plat

    @staticmethod
    def _STLMBR(stcprm, tnglat, xlong):
        stcprm[0] = math.sin(tnglat * CoordinateBase.RADPDG) # gamma = sine of the tangent latitude
        stcprm[1] = CoordinateBase._CSPANF(xlong, -180.0, 180.0) # lambda_0 = reference longitude
        stcprm[2] = 0.0 # x_0 = x-grid coordinate of origin (xi, eta) = (0, 0)
        stcprm[3] = 0.0 # y_0 = y-grid coordinate of origin (xi, eta) = (0, 0)
        stcprm[4] = 1.0 # cosine of rotation angle from xi, eta to x, y
        stcprm[5] = 0.0 # sine of rotation angle from xi, eta to x, y
        stcprm[6] = CoordinateBase.EARTH_RADIUS # gridsize in km at the equator
        xi, eta = CoordinateBase._CNLLXY(stcprm, 89.0, xlong)
        stcprm[7] = 2. * eta - stcprm[0] * eta * eta # radial coordinate for 1 deg from north pole
        xi, eta = CoordinateBase._CNLLXY(stcprm, -89.0, xlong)
        stcprm[8] = 2. * eta - stcprm[0] * eta * eta # radial coordinate for 1 deg from south pole
        logger.debug("_STLMBR: %s", stcprm)

    @staticmethod
    def _STCM1P(stcprm, x1, y1, xlat1, xlong1, xlatg, xlongg, gridsz, orient):
        stcprm[2] = 0
        stcprm[3] = 0
        turn = CoordinateBase.RADPDG * (orient - stcprm[0] *
                                       CoordinateBase._CSPANF(xlongg - stcprm[1], -180.0, 180.0))
        stcprm[4] = math.cos(turn)
        stcprm[5] = -math.sin(turn)
        stcprm[6] = 1.0
        stcprm[6] = gridsz * stcprm[6] / CoordinateBase._CGSZLL(stcprm, xlatg, stcprm[1])
        x1a, y1a = CoordinateBase._CLL2XY(stcprm, xlat1, xlong1)
        stcprm[2] += x1 - x1a
        stcprm[3] += y1 - y1a
        logger.debug("_STCM1P: %s", stcprm)

    @staticmethod
    def _CGSZLL(stcprm, xlat, xlong):
        if xlat > 89.995:
            # close to north pole
            if stcprm[1] > 0.9999:
                # and gamma is 1.0
                return 2.0 * stcprm[6]
            efact = math.cos(CoordinateBase.RADPDG * xlat)
            if efact <= 0:
                return 0.0
            else:
                ymerc = -math.log(efact/(1.0 + math.sin(CoordinateBase.RADPDG * xlat)))
        elif xlat < -89.995:
            # close to south pole
            if stcprm[0] < -0.9999:
                return 2.0 * stcprm[6]
            efact = math.cos(CoordinateBase.RADPDG * xlat)
            if efact <= 0:
                return 0.0
            else:
                ymerc = math.log(efact/(1.0 - math.sin(CoordinateBase.RADPDG * xlat)))
        else:
            slat = math.sin(CoordinateBase.RADPDG * xlat)
            ymerc = math.log((1.0 + slat)/(1.0 - slat)) * 0.5
        return stcprm[6] * math.cos(CoordinateBase.RADPDG * xlat) * math.exp(stcprm[0] * ymerc)

    @staticmethod
    def _CLL2XY(stcprm, xlat, xlong):
        xi, eta = CoordinateBase._CNLLXY(stcprm, xlat, xlong)
        x = stcprm[2] + CoordinateBase.EARTH_RADIUS/stcprm[6] * (xi*stcprm[4] + eta * stcprm[5])
        y = stcprm[3] + CoordinateBase.EARTH_RADIUS/stcprm[6] * (eta*stcprm[4] - xi * stcprm[5])
        logger.debug("_CLL2XY: xi %f, eta %f -> x %f, y %f", xi, eta, x, y)
        return x, y

    @staticmethod
    def _CXY2LL(stcprm, x, y):
        xi0 = (x - stcprm[2]) * stcprm[6] / CoordinateBase.EARTH_RADIUS
        eta0 = (y - stcprm[3]) * stcprm[6] / CoordinateBase.EARTH_RADIUS
        xi = xi0 * stcprm[4] - eta0 * stcprm[5]
        eta = eta0 * stcprm[4] + xi0 * stcprm[5]
        plat, plon = CoordinateBase._CNXYLL(stcprm, xi, eta)
        plon = CoordinateBase._CSPANF(plon, -180.0, 180.0)
        return plat, plon

    @staticmethod
    def _CSPANF(value, fbegin, fend):
        first = min(fbegin, fend)
        last = max(fbegin, fend)
        val = (value - first) % (last - first)
        return val + last if val < 0.0 else val + first

    @staticmethod
    def _CNLLXY(stcprm, xlat, xlong):
        almst1 = 0.99999
        gamma = stcprm[0]
        dlat = xlat
        dlong = CoordinateBase._CSPANF(xlong - stcprm[1], -180.0, 180.0)
        dlong *= CoordinateBase.RADPDG
        gdlong = gamma * dlong
        if abs(gdlong) < 0.01:
            gdlong *= gdlong
            sndgam = dlong * (1.0 - gdlong/6.0*(1.0 - gdlong/20.0 * (1.0 - gdlong/42.)))
            csdgam = dlong * dlong * 0.5 * (1.0 - gdlong/12.0*(1.0 - gdlong/30.0*(1.0 - gdlong/56.0)))
        else:
            sndgam = math.sin(gdlong)/gamma
            csdgam = (1.0 - math.cos(gdlong))/(gamma*gamma)
        slat = math.sin(CoordinateBase.RADPDG * dlat)
        if (slat >= almst1) or (slat <= -almst1):
            eta = 1.0/stcprm[0]
            xi = 0.0
            return xi, eta
        mercy = 0.5 * math.log((1.0 + slat)/(1.0 - slat))
        gmercy = gamma * mercy
        if abs(gmercy) < 0.001:
            rhog1 = mercy * (1.0 - 0.5*gmercy*(1.0 - gmercy/3.0*(1.0 - gmercy/4.0)))
        else:
            rhog1 = (1.0 - math.exp(-gmercy)) / gamma
        eta = rhog1 + (1.0 - gamma*rhog1) * gamma * csdgam
        xi = (1.0 - gamma*rhog1) * sndgam
        return xi, eta

    @staticmethod
    def _CNXYLL(stcprm, xi, eta):
        gamma = stcprm[0]
        cgeta = 1.0 - gamma * eta
        gxi = gamma * xi
        # calculate equivalent mercator coordinate
        arg2 = eta + (eta * cgeta - gxi * xi)
        arg1 = gamma * arg2
        if arg1 >= 1.0:
            # distance to north (or south) pole is zero (or imaginary).
            xlat = 90.0 if stcprm[0] >= 0 else -90.0
            xlong = 90.0 + xlat
            return xlat, xlong
        if abs(arg1) < 0.01:
            # code for gamma small or zero to avoid round-off error or divide-by-zero.
            temp = pow(arg1 / (2.0 - arg1), 2.0)
            ymerc = arg2 / (2.0 - arg1) * (1.0 + temp*(1./3. + temp*(1./5. + temp*(1./7))))
        else:
            # code for moderate values of gamma
            ymerc = -math.log(1.0 - arg1) / (2.0 * gamma)
        # convert ymerc to latitude
        temp = math.exp(-abs(ymerc))
        xlat = util.sign(math.atan2((1.0 - temp)*(1.0 + temp), 2.0 * temp), ymerc)
        # find longitudes
        if abs(gxi) < 0.01*cgeta:
            # code for gamma small or zero to avoid round-off error or divide-by-zero.
            temp = pow(gxi/cgeta, 2.0)
            along = xi/cgeta * (1.0 - temp*(1./3. - temp*(1./5. - temp*(1./7.))))
        else:
            # code for moderate values of gamma
            along = math.atan2(gxi, cgeta) / gamma
        xlong = stcprm[1] + CoordinateBase.DGPRAD * along
        xlat = xlat * CoordinateBase.DGPRAD
        return xlat, xlong

    @staticmethod
    def normalize_lon(lon):
        if lon < 0.0:
            lon += 360.0
        if lon > 360.0:
            lon -= 360.0
        return lon


class LambertCoordinate(CoordinateBase):

    def __init__(self):
        CoordinateBase.__init__(self)
        return

    def set_tangent_lat(self, center_loc):
        self.tnglat = center_loc[1]
        self.slat = center_loc[1]
        self.slon = center_loc[0]
        self.glat = center_loc[1]
        self.glon = center_loc[0]


class PolarCoordinate(CoordinateBase):

    def __init__(self):
        CoordinateBase.__init__(self)
        return

    def set_tangent_lat(self, center_loc):
        self.tnglat = 90.0 if center_loc[1] >= 0.0 else -90.0
        self.slat = self.tnglat
        self.slon = 0.0
        self.glat = center_loc[1]
        self.glon = self.reflon


class MercatorCoordinate(CoordinateBase):

    def __init__(self):
        CoordinateBase.__init__(self)
        return

    def set_tangent_lat(self, center_loc):
        self.tnglat = 0.0
        self.slat = center_loc[1]
        self.slon = center_loc[0]
        self.glat = 0.0
        self.glon = self.reflon


class CylindricalCoordinate(CoordinateBase):

    def __init__(self):
        CoordinateBase.__init__(self)
        self.xypdeg = 0.0
        self.coslat = 0.0
        self.rlat = 0.0
        self.rlon = 0.0
        self.xr = 0.0
        self.yr = 0.0

    def set_tangent_lat(self, center_loc):
        self.tnglat = 0.0
        self.slat = center_loc[1]
        self.slon = center_loc[0]
        self.glat = 0.0
        self.glon = self.reflon

    def init_params(self, xc, yc):
        self._CYLSET(self.grid, self.tnglat, self.slat, self.slon, xc, yc)

    def rescale(self, xy, corners_lonlat):
        x1, y1 = xy
        alonl, alonr, alatb, alatt = corners_lonlat
        self._CYLSET(self.grid, self.tnglat, alatb, alonl, x1, y1)
        return self.calc_xy(alonr, alatt)

    def calc_xy(self, plon, plat):
        return self._CYL2XY(plat, plon)

    def calc_lonlat(self, x, y):
        plat, plon = self._CYL2LL(x, y)
        return plon, plat

    def _CYLSET(self, distxy, clat, plat, plon, xp, yp):
        # position in x-y at reference lat-lon
        self.rlat = plat
        self.rlon = plon
        self.xr = xp
        self.yr = yp

        # internal system always 0-360
        self.rlon = self.normalize_lon(self.rlon)

        # latitude scale factor
        self.coslat = math.cos(clat * CoordinateBase.RADPDG)

        # gp/deg = (km/deg) / (km/gp)
        self.xypdeg = CoordinateBase.EARTH_RADIUS * CoordinateBase.RADPDG / distxy

    def _CYL2XY(self, plat, plon):
        # compute difference from reference longitude
        tlon = self.normalize_lon(plon) - self.rlon
        x = self.xypdeg * tlon * self.coslat + self.xr
        y = self.xypdeg * (plat - self.rlat) + self.yr
        return x, y

    def _CYL2LL(self, x, y):
        plat = self.rlat + (y - self.yr) / self.xypdeg
        tlon = self.rlon + (x - self.xr) / (self.coslat * self.xypdeg)
        # return with (-180,+180), (-90,+90) system
        plon = CoordinateBase._CSPANF(tlon, -180.0, 180.0)
        plat = CoordinateBase._CSPANF(plat, -90.0, 90.0)
        return plat, plon


class MapProjection:

    TOLERANCE = 0.5 #xy2ll->ll2xy allows difference <= TOLERANCE*grid
    CONTRACTION = 0.2 #contraction factor when corners are outside map

    def __init__(self, settings, center_loc, scale, grid_deltas):
        self.settings = settings
        self.scale = scale
        self.deltas = grid_deltas       # (dlon, dlat)
        #
        self.proj_type = None
        self.coord = None # set by a child class
        self.center_loc = center_loc    # (lon, lat)
        self.corners_xy = None # [x1, x2, y1, y2]
        self.corners_lonlat = None # [lon_left, lon_right, lat_bottom, lat_top]
        self.point_counts = None # [Nx, Ny]

    @staticmethod
    def determine_projection(map_proj, center_loc):
        kproj = map_proj
        if map_proj == plot.TrajectoryPlotSettings.MapProjection.AUTO:
            kproj = plot.TrajectoryPlotSettings.MapProjection.LAMBERT
            if center_loc[1] > 55.0 or center_loc[1] < -55.0:
                kproj = plot.TrajectoryPlotSettings.MapProjection.POLAR
            if center_loc[1] < 25.0 and center_loc[1] > -25.0:
                kproj = plot.TrajectoryPlotSettings.MapProjection.MERCATOR
        logger.debug("map projection %d -> %d", map_proj, kproj)
        return kproj

    @staticmethod
    def create_instance(settings, center_loc, scale, grid_deltas, map_box):
        obj = None

        kproj = MapProjection.determine_projection(settings.map_projection, center_loc)

        if kproj == settings.MapProjection.POLAR:
            obj = PolarProjection(settings, center_loc, scale, grid_deltas)
        elif kproj == settings.MapProjection.LAMBERT:
            obj = LambertProjection(settings, center_loc, scale, grid_deltas)
        elif kproj == settings.MapProjection.MERCATOR:
            obj = MercatorProjection(settings, center_loc, scale, grid_deltas)
        elif kproj == settings.MapProjection.CYL_EQU:
            obj = CylindricalEquidistantProjection(settings, center_loc, scale, grid_deltas)
        else:
            raise Exception("unknown map projection {0}".format(kproj))

        obj.do_initial_estimates(map_box, center_loc)

        # Lambert grids not permitted to encompass the poles
        if obj.sanity_check() == False:
            proj = obj.create_proper_projection(settings, center_loc, scale, grid_deltas)
            proj.do_initial_estimates(map_box, center_loc)
            return proj

        return obj

    def refine_corners(self, map_box, center_loc):
        corners_xy = self.validate_corners(self.corners_xy)

        # scale map per aspect ratio
        corners_saved = corners_xy
        corners_xy = self.scale_per_aspect_ratio(corners_xy, self.scale)
        corners_xy = self.choose_corners(corners_xy, corners_saved)
        logger.debug("X, Y asp-zum: %s", corners_xy)

        # projection zoom factor
        corners_saved = corners_xy
        corners_xy = self.zoom_corners(corners_xy, self.settings.zoom_factor)
        corners_xy = self.choose_corners(corners_xy, corners_saved)
        logger.debug("X, Y zum-adj: %s", corners_xy)

        # round map corners to match even grid index for plotting
        corners_saved = [util.nearest_int(a) for a in corners_xy]
        corners_xy = self.round_map_corners(corners_xy)
        corners_xy = self.choose_corners(corners_xy, corners_saved)
        logger.debug("X, Y Adj: %s", corners_xy)

        # alatb, alonl, alatt, alonr will be used later to setup map
        corners_lonlat = self.calc_corners_lonlat(corners_xy)

        # Lambert/Mercator corners should be away from pole
        if self.need_pole_exclusion(corners_lonlat):
            corners_xy, corners_lonlat = self.exclude_pole(corners_xy, corners_lonlat)

        # rescale map by defining 1, 1 at lower left corner
        x1, y1 = 1.0, 1.0
        x2, y2 = self.coord.rescale((x1, y1), corners_lonlat)
        corners_xy = (x1, x2, y1, y2)

        self.corners_xy = corners_xy
        self.corners_lonlat = corners_lonlat
        logger.debug("Final: %s", corners_xy)
        logger.debug("Final: lonlat %s", self.corners_lonlat)

        self.point_counts = (util.nearest_int(x2), util.nearest_int(y2))

    def validate_corners(self, corners):
        x1, x2, y1, y2 = corners

        # save x1, x2, y1, y2 before validation
        x1s, x2s, y1s, y2s = x1, x2, y1, y2

        alonl, alatb = self.coord.calc_lonlat(x1, y1)
        alonr, alatt = self.coord.calc_lonlat(x2, y2)
        x1, y1 = self.coord.calc_xy(alonl, alatb)
        x2, y2 = self.coord.calc_xy(alonr, alatt)

        # move lower left corner toward center
        if max(abs(x1-x1s), abs(y1s-y1)) >= self.TOLERANCE:
            x1 = x1s + self.CONTRACTION*(x2s - x1s)
            y1 = y1s + self.CONTRACTION*(y2s - y1s)

        # move upper right corner toward center
        if max(abs(x2-x2s), abs(y2s-y2)) >= self.TOLERANCE:
            x2 = x2s - self.CONTRACTION*(x2s - x1s)
            y2 = y2s - self.CONTRACTION*(y2s - y1s)

        return (x1, x2, y1, y2)

    def scale_per_aspect_ratio(self, corners_xy, aspect_ratio):
        x1, x2, y1, y2 = corners_xy

        # new map center
        xc = 0.5 * (x1 + x2)
        yc = 0.5 * (y1 + y2)

        # scale map according to aspect ratio
        if abs(x2-x1) <= aspect_ratio*abs(y2 - y1):
            # expand in x-direction
            delx = 0.5 * (y2-y1) * aspect_ratio
            x1 = xc - delx
            x2 = xc + delx
        else:
            # expand in y-direction
            dely = 0.5 * (x2-x1) / aspect_ratio
            y1 = yc - dely
            y2 = yc + dely
        logger.debug("X, Y Asp: %f %f %f %f", x1, y1, x2, y2)

        return (x1, x2, y1, y2)

    def choose_corners(self, corners_new, corners_prev):
        x1, x2, y1, y2 = corners_new

        # save x1, x2, y1, y2
        x1s, x2s, y1s, y2s = x1, x2, y1, y2

        alonl, alatb = self.coord.calc_lonlat(x1, y1)
        alonr, alatt = self.coord.calc_lonlat(x2, y2)
        x1, y1 = self.coord.calc_xy(alonl, alatb)
        x2, y2 = self.coord.calc_xy(alonr, alatt)

        if max(abs(x1-x1s), abs(x2-x2s), abs(y1-y1s), abs(y2-y2s)) >= self.TOLERANCE:
            return corners_prev

        return (x1, x2, y1, y2)

    def zoom_corners(self, corners_xy, zoom_factor):
        x1, x2, y1, y2 = corners_xy

        delx = abs(x2-x1)
        dely = abs(y2-y1)
        x_margin = util.sign(zoom_factor * delx * 0.5, x2 - x1)
        y_margin = util.sign(zoom_factor * dely * 0.5, y2 - y1)
        x1 = x1 - x_margin
        x2 = x2 + x_margin
        y1 = y1 - y_margin
        y2 = y2 + y_margin
        logger.debug("X, Y Zum: %f %f %f %f", x1, y1, x2, y2)

        return (x1, x2, y1, y2)

    def round_map_corners(self, corners_xy):
        x1, x2, y1, y2 = corners_xy
        x2b = util.nearest_int(x2)

        y1 = util.nearest_int(y1)
        y2 = util.nearest_int(y2)
        delx = (y2-y1)*self.scale
        if self.proj_type == plot.TrajectoryPlotSettings.MapProjection.CYL_EQU:
            delx *= 2.0
        x1 = util.nearest_int(x1)
        x2 = x1 + util.nearest_int(delx)
        if x2 <= x2b:
            x2 = x2b

        return (x1, x2, y1, y2)

    def calc_corners_lonlat(self, corners_xy):
        x1, x2, y1, y2 = corners_xy

        alonl, alatb = self.coord.calc_lonlat(x1, y1)
        alonr, alatt = self.coord.calc_lonlat(x2, y2)
        logger.debug("Corners: %f %f %f %f", alonl, alonr, alatb, alatt)

        # map exceeds limits
        if alatt > 90.0 or alatb < -90.0:
            logger.warning("map projection exceeds limits")
            logger.warning("Increase zoom or change/force projection")

        return (alonl, alonr, alatb, alatt)

    def need_pole_exclusion(self, corners_lonlat):
        # A child class may override this.
        return False

    def exclude_pole(self, corners_xy, corners_lonlat):
        x1, x2, y1, y2 = corners_xy
        alonl, alonr, alatb, alatt = corners_lonlat

        if alatt > 80.0:
            alatt = 80.0
            x2, y2 = self.coord.calc_xy(alonr, alatt)
        if alatb < -80.0:
            alatb = -80.0
            x1, y1 = self.coord.calc_xy(alonl, alatb)

        return (x1, x2, y1, y2), (alonl, alonr, alatb, alatt)

    def do_initial_estimates(self, map_box, center_loc):

        # initial point
        xc = 500.0; yc = 500.0

        # set up the coordinate reference system
        self.coord.setup(center_loc, xc, yc, self.deltas)
        logger.debug("Map Prj: %d", self.proj_type)
        logger.debug("Center : %f %f", center_loc[1], center_loc[0])
        logger.debug("Tangent: %f  Reflon: %f", self.coord.tnglat, self.coord.reflon)

        # find new map corners
        half_delta = map_box.grid_delta * 0.5
        x1, y1 = self.coord.calc_xy(center_loc[0] - half_delta, center_loc[1] - half_delta)
        x2, y2 = self.coord.calc_xy(center_loc[0] + half_delta, center_loc[1] + half_delta)

        logger.debug("X, Y Set : %f %f %f %f", x1, y1, x2, y2)
        logger.debug("Grid corner, increment from mapbox or conndx : %f %f %f",
                     map_box.grid_corner[1],
                     map_box.grid_corner[0],
                     map_box.grid_delta)
        logger.debug("1st guess center : %f %f", self.center_loc[1], self.center_loc[0])

        for j in range(map_box.sz[1]):
            for i in range(map_box.sz[0]):
                if map_box.hit_map[i,j] > 0:
                    plon = i * map_box.grid_delta + map_box.grid_corner[0]
                    plat = j * map_box.grid_delta + map_box.grid_corner[1]
                    if plon > 180.0:
                        plon -= 360.0
                    xc, yc = self.coord.calc_xy(plon, plat)
                    x1 = min(x1, xc)
                    y1 = min(y1, yc)
                    x2 = max(x2, xc)
                    y2 = max(y2, yc)
        logger.debug("X, Y Ini: %f %f %f %f", x1, y1, x2, y2)
        self.corners_xy = (x1, x2, y1, y2)

        # find new map center
        xc = 0.5*(x1 + x2)
        yc = 0.5*(y1 + y2)
        qlon, qlat = self.coord.calc_lonlat(xc, yc)
        logger.debug("Center : %f %f", qlat, qlon)
        self.center_loc = (qlon, qlat)

        # compute new map corners
        alonl, alatb = self.coord.calc_lonlat(x1, y1)
        alonr, alatt = self.coord.calc_lonlat(x2, y2)
        self.corners_lonlat = (alonl, alonr, alatb, alatt)
        logger.debug("Corners: %f %f %f %f", alonl, alonr, alatb, alatt)

    def sanity_check(self):
        # A child class may override this.
        return True

    def create_proper_projection(self, settings, center_loc, scale, grid_deltas):
        # A child class should override this.
        raise Exception("This should not happen")

    def create_crs(self):
        # A child class should override this.
        raise Exception("This should not happen")


class LambertProjection(MapProjection):

    def __init__(self, settings, center_loc, scale, grid_deltas):
        MapProjection.__init__(self, settings, center_loc, scale, grid_deltas)
        self.proj_type = plot.TrajectoryPlotSettings.MapProjection.LAMBERT
        self.coord = LambertCoordinate()

    def sanity_check(self):
        x1, x2, y1, y2 = self.corners_xy
        xc, yc = self.coord.calc_xy(0.0, util.sign(90.0, self.center_loc[1]))
        logger.debug("Pole xy: %f %f", xc, yc)
        if xc >= x1 and xc <= x2 and yc >= y1 and yc <= y2:
            logger.debug("Force polar stereographic!")
            return False
        return True

    def create_proper_projection(self, settings, center_loc, scale, grid_deltas):
        obj = PolarProjection(settings, center_loc, scale, grid_deltas)
        return obj

    def need_pole_exclusion(self, corners_lonlat):
        alonl, alonr, alatb, alatt = corners_lonlat
        return True if alatt > 80.0 or alatb < -80.0 else False

    def create_crs(self):
        return cartopy.crs.LambertConformal(central_longitude=self.coord.reflon,
                                            central_latitude=self.coord.tnglat,
                                            false_easting=1.0*1000.0,
                                            false_northing=1.0*1000.0)


class PolarProjection(MapProjection):

    def __init__(self, settings, center_loc, scale, grid_deltas):
        MapProjection.__init__(self, settings, center_loc, scale, grid_deltas)
        self.proj_type = plot.TrajectoryPlotSettings.MapProjection.POLAR
        self.coord = PolarCoordinate()

    def create_crs(self):
        if self.center_loc[1] >= 0.0:
            return cartopy.crs.NorthPolarStereo(central_longitude=self.coord.reflon)
        else:
            return cartopy.crs.SouthPolarStereo(central_longitude=self.coord.reflon)


class MercatorProjection(MapProjection):

    def __init__(self, settings, center_loc, scale, grid_deltas):
        MapProjection.__init__(self, settings, center_loc, scale, grid_deltas)
        self.proj_type = plot.TrajectoryPlotSettings.MapProjection.MERCATOR
        self.coord = MercatorCoordinate()

    def need_pole_exclusion(self, corners_lonlat):
        alonl, alonr, alatb, alatt = corners_lonlat
        return True if alatt > 80.0 or alatb < -80.0 else False

    def create_crs(self):
        return cartopy.crs.Mercator(central_longitude=self.coord.reflon,
                                    latitude_true_scale=self.coord.tnglat,
                                    false_easting=1.0*1000.0,
                                    false_northing=1.0*1000.0)


class CylindricalEquidistantProjection(MapProjection):

    def __init__(self, settings, center_loc, scale, grid_deltas):
        super(CylindricalEquidistantProjection, self).__init__(settings, center_loc, scale, grid_deltas)
        self.proj_type = plot.TrajectoryPlotSettings.MapProjection.CYL_EQU
        self.coord = CylindricalCoordinate()

    def create_crs(self):
        return cartopy.crs.LambertCylindrical(central_longitude=self.coord.reflon)


class LabelsConfig():

    def __init__(self):
        self.cfg = dict()
        self.cfg["TITLE"] = "NOAA HYSPLIT MODEL"
        return

    def get(self, name):
        return self.cfg[name] if name in self.cfg else ""

    def get_reader(self):
        return LabelsConfigReader(self)

    def after_reading_file(self, settings):
        if self.get("VUNIT") == "FEET":
            settings.height_unit = plot.TrajectoryPlotSettings.HeightUnit.FEET


class LabelsConfigReader():

    def __init__(self, cfg):
        self.obj = cfg

    def read(self, filename):
        if self.check_consistency(filename) == False:
            raise Exception("Consistency check failed. Please fix {0}".format(filename))

        with open(filename, "rt") as f:
            for ln in f:
                k, v = self.parse_line(ln.rstrip("\n"))
                if k == "TXBOXL":
                    if k in self.obj.cfg:
                        self.obj.cfg[k].append(v)
                    else:
                        self.obj.cfg[k] = [v]
                else:
                    self.obj.cfg[k] = v

        return self.obj

    def check_consistency(self, filename):
        with open(filename, "rt") as f:
            expected_count = tbox_count = 0
            state = 0
            for ln in f:
                k, v = self.parse_line(ln.rstrip("\n"))
                if state == 0:
                    # looking for the NTXBOXL line
                    if k == "NTXBOXL":
                        expected_count = int(v)
                        tbox_count = 0
                        state = 1
                    elif k == "TXBOXL":
                        logger.error("NTXBOXL line must proceed TXBOXL line(s)");
                        return False
                elif state == 1:
                    # already found the NTXBOXL line
                    if k == "TXBOXL":
                        tbox_count += 1
                    elif k == "NTXBOXL":
                        if tbox_count != expected_count:
                            logger.error("{0} text box lines must follow NTXBOXL in {1}".format( expected_count, filename))
                            return False
                        expected_count = int(v)
                        tbox_count = 0
            if expected_count > 0 and tbox_count != expected_count:
                logger.error("{0} text box lines must follow NTXBOXL in {1}".format( expected_count, filename))
                return False

        return True

    def parse_line(self, ln):
        list = []
        state = 0
        start = 0
        field = ""
        for k, c in enumerate(ln):
            if state == 0: # looking for opening quote
                if c == "'":
                    state = 1
            elif state == 1:
                if c == "'":
                    state = 2
                else:
                    field += c
            elif state == 2:
                if c == "'": # escaped single quote
                    field += c
                    state = 1
                elif c == ",":
                    list.append(field); field = ""
                    state = 0
        if state != 0:
            list.append(field)

        return list[0].rstrip("&"), list[1].rstrip("&")


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
        io.FormattedTextFileReader.__init__(self)
        self.cfg = cfg

    def read(self, filename):
        self.cfg.stations.clear()

        self.open(filename)

        while self.has_next():
            v = self.parse_line("F6.2,1X,F7.2,1X,A80")
            if len(v) == 2:
                v.append("")
            if len(v) == 3:
                self.cfg.stations.append(StationPlotConfig.Station(v[0], v[1], v[2].strip()))
            else:
                raise Exception("cannot parse a line in file {0}".format(filename))

        self.close()

        return self.cfg


def union_ranges(a, b):
    if a == None or len(a) == 0:
        return b
    elif b == None or len(b) == 0:
        return a
    else:
        amin = min(a[0], b[0])
        amax = max(a[1], b[1])
        return [amin, amax]