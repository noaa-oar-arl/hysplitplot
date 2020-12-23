# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# gisout.py
#
# To produce GIS outputs for concentration data. Also used for time-of-arrival
# plots.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
import copy
import datetime
import logging
import math
from matplotlib.path import Path
import numpy

from hysplitdata.conc import model
from hysplitplot import const, util


logger = logging.getLogger(__name__)


class GISFileWriterFactory:

    @staticmethod
    def create_instance(selector, kml_option, time_zone=None):
        if selector == const.GISOutput.GENERATE_POINTS:
            formatter = PointsGenerateFileWriter.DecimalFormWriter(time_zone)
            return PointsGenerateFileWriter(formatter, time_zone)
        elif selector == const.GISOutput.GENERATE_POINTS_2:
            formatter = PointsGenerateFileWriter.ExponentFormWriter(time_zone)
            return PointsGenerateFileWriter(formatter, time_zone)
        elif selector == const.GISOutput.GENERATE_POINTS_STR:
            formatter = PointsGenerateFileWriter.StringFormWriter(time_zone)
            return PointsGenerateFileWriter(formatter, time_zone)
        elif selector == const.GISOutput.KML:
            return KMLWriter(kml_option, time_zone)
        elif selector == const.GISOutput.PARTIAL_KML:
            return PartialKMLWriter(kml_option, time_zone)
        elif selector != const.GISOutput.NONE:
            logger.warning("Unknown GIS file writer type %d", selector)
        return NullWriter(time_zone)


class AbstractWriter(ABC):

    def __init__(self, time_zone=None):
        self.alt_mode_str = "clampedToGround"
        self.KMLOUT = 0
        self.output_suffix = "ps"
        self.KMAP = const.ConcentrationMapType.CONCENTRATION
        self.time_zone = time_zone

    def initialize(self, gis_alt_mode, KMLOUT, output_suffix, KMAP, NSSLBL,
                   show_max_conc, NDEP):
        if gis_alt_mode == const.GISOutputAltitude.RELATIVE_TO_GROUND:
            self.alt_mode_str = "relativeToGround"
        else:
            self.alt_mode_str = "clampedToGround"
        self.KMLOUT = KMLOUT
        self.output_suffix = output_suffix
        self.KMAP = KMAP
        self.NSSLBL = NSSLBL
        self.show_max_conc = show_max_conc
        self.NDEP = NDEP

    @abstractmethod
    def write(self, basename, g, contour_set, lower_vert_level,
              upper_vert_level):
        pass

    def finalize(self):
        pass

    @abstractmethod
    def make_output_basename(self, g, conc_type, depo_sum, output_basename,
                             output_suffix, KMLOUT, upper_vert_level):
        pass

    @staticmethod
    def _reformat_color(clr):
        r = clr[1:3]
        g = clr[3:5]
        b = clr[5:7]
        return "C8{}{}{}".format(b, g, r).upper()


class NullWriter(AbstractWriter):

    def __init__(self, time_zone=None):
        super(NullWriter, self).__init__(time_zone)

    def write(self, basename, g, contour_set, lower_vert_level,
              upper_vert_level):
        pass

    def make_output_basename(self, g, conc_type, depo_sum, output_basename,
                             output_suffix, KMLOUT, upper_vert_level):
        pass


class PointsGenerateFileWriter(AbstractWriter):

    def __init__(self, formatter, time_zone=None):
        super(PointsGenerateFileWriter, self).__init__(time_zone)
        self.formatter = formatter

    def make_output_basename(self, g, conc_type, depo_sum, output_basename,
                             output_suffix, KMLOUT, upper_vert_level):
        if g.vert_level == 0 and depo_sum is not None:
            basename = depo_sum.make_gis_basename(g.time_index + 1, output_suffix)
        else:
            basename = conc_type.make_gis_basename(g.time_index + 1,
                                                   output_suffix,
                                                   g.vert_level,
                                                   upper_vert_level)
        return basename

    def write(self, basename, g, contour_set, lower_vert_level,
              upper_vert_level):
        filename = basename + ".txt"
        logger.info("Creating file %s", filename)
        with open(filename, "wt") as f:
            for k, contour in enumerate(contour_set.contours):
                level = contour_set.levels[k]
                for polygon in contour.polygons:
                    for boundary in polygon.boundaries:
                        self.formatter.write_boundary(f, boundary, level)
            f.write("END\n")

        filename = basename + ".att"
        logger.info("Creating file %s", filename)
        with open(filename, "wt") as f:
            f.write("#CONC,NAME,DATE,TIME,LLEVEL,HLEVEL,COLOR\n")
            for k, contour in enumerate(contour_set.contours):
                level = contour_set.levels[k]
                clr = self._reformat_color(contour_set.colors[k])
                for polygon in contour.polygons:
                    for boundary in polygon.boundaries:
                        self.formatter.write_attributes(f, g,
                                                        lower_vert_level,
                                                        upper_vert_level,
                                                        level, clr)

    class DecimalFormWriter:

        def __init__(self, time_zone=None):
            self.time_zone = time_zone

        def write_boundary(self, f, boundary, contour_level):
            f.write("{:10.5f}, {:10.5f}, {:10.5f}\n"
                    .format(math.log10(contour_level),
                            boundary.longitudes[0],
                            boundary.latitudes[0]))
            for k in range(1, len(boundary.longitudes)):
                f.write("{:10.5f}, {:10.5f}\n".format(boundary.longitudes[k],
                                                      boundary.latitudes[k]))
            f.write("END\n")

        def write_attributes(self, f, g, lower_vert_level, upper_vert_level,
                             contour_level, color):
            if self.time_zone is None:
                dt = g.ending_datetime
            else:
                dt = g.ending_datetime.astimezone(self.time_zone)
            f.write("{:7.3f},{:4s},{:4d}{:02d}{:02d},{:02d}{:02d},{:05d}"
                    ",{:05d},{:8s}\n".format(math.log10(contour_level),
                                             g.pollutant,
                                             dt.year,
                                             dt.month,
                                             dt.day,
                                             dt.hour,
                                             dt.minute,
                                             int(lower_vert_level),
                                             int(upper_vert_level),
                                             color))

    class ExponentFormWriter:

        def __init__(self, time_zone=None):
            self.time_zone = time_zone

        def write_boundary(self, f, boundary, contour_level):
            f.write("{:10.3e}, {:10.5f}, {:10.5f}\n"
                    .format(contour_level,
                            boundary.longitudes[0],
                            boundary.latitudes[0]))
            for k in range(1, len(boundary.longitudes)):
                f.write("{:10.5f}, {:10.5f}\n"
                        .format(boundary.longitudes[k], boundary.latitudes[k]))
            f.write("END\n")

        def write_attributes(self, f, g, lower_vert_level, upper_vert_level,
                             contour_level, color):
            if self.time_zone is None:
                dt = g.ending_datetime
            else:
                dt = g.ending_datetime.astimezone(self.time_zone)
            f.write("{:10.3e},{:4s},{:4d}{:02d}{:02d},{:02d}{:02d},{:05d},"
                    "{:05d},{:8s}\n".format(contour_level,
                                            g.pollutant,
                                            dt.year,
                                            dt.month,
                                            dt.day,
                                            dt.hour,
                                            dt.minute,
                                            int(lower_vert_level),
                                            int(upper_vert_level),
                                            color))

    class StringFormWriter:

        def __init__(self, time_zone=None):
            self.time_zone = time_zone

        def write_boundary(self, f, boundary, contour_level_str):
            f.write("{}, {:10.5f}, {:10.5f}\n".format(contour_level_str,
                                                      boundary.longitudes[0],
                                                      boundary.latitudes[0]))
            for k in range(1, len(boundary.longitudes)):
                f.write("{:10.5f}, {:10.5f}\n".format(boundary.longitudes[k],
                                                      boundary.latitudes[k]))
            f.write("END\n")

        def write_attributes(self, f, g, lower_vert_level, upper_vert_level,
                             contour_level_str, color):
            if self.time_zone is None:
                dt = g.ending_datetime
            else:
                dt = g.ending_datetime.astimezone(self.time_zone)
            f.write("{},{:4s},{:4d}{:02d}{:02d},{:02d}{:02d},{:05d}"
                    ",{:05d},{:8s}\n".format(contour_level_str,
                                             g.pollutant,
                                             dt.year,
                                             dt.month,
                                             dt.day,
                                             dt.hour,
                                             dt.minute,
                                             int(lower_vert_level),
                                             int(upper_vert_level),
                                             color))


class KMLWriter(AbstractWriter):

    def __init__(self, kml_option, time_zone=None):
        super(KMLWriter, self).__init__(time_zone)
        self.kml_option = kml_option    # IKML
        self.kml_file = None
        self.att_file = None
        self.contour_writer = None

    def make_output_basename(self, g, conc_type, depo_sum, output_basename,
                             output_suffix, KMLOUT, upper_vert_level):
        s = "HYSPLIT" if KMLOUT == 0 else output_basename
        return "{}_{}".format(s, output_suffix)

    def initialize(self, gis_alt_mode, KMLOUT, output_suffix, KMAP, NSSLBL,
                   show_max_conc, NDEP):
        super(KMLWriter, self).initialize(gis_alt_mode, KMLOUT, output_suffix,
                                          KMAP, NSSLBL, show_max_conc, NDEP)
        self.contour_writer = KMLContourWriterFactory.create_instance(
                self.KMAP, self.alt_mode_str, self.time_zone)
        self.contour_writer.set_show_max_conc(show_max_conc)
        self.deposition_contour_writer = self.create_deposition_contour_writer(
                KMAP, self.alt_mode_str, self.time_zone, NDEP, show_max_conc)

    def create_deposition_contour_writer(self, KMAP, alt_modestr, time_zine,
                                         NDEP, show_max_conc):
        if NDEP == const.DepositionType.NONE:
            return None

        if KMAP == const.ConcentrationMapType.VOLCANIC_ERUPTION:
            deposition_kmap = const.ConcentrationMapType.VOLCANIC_ERUPTION
        else:
            deposition_kmap = const.ConcentrationMapType.DEPOSITION_6

        w = KMLContourWriterFactory.create_instance(
                    deposition_kmap, self.alt_mode_str, self.time_zone)
        w.set_show_max_conc(show_max_conc)
        return w

    def write(self, basename, g, contour_set,
              lower_vert_level, upper_vert_level):
        if self.kml_file is None:
            filename = "{}.kml".format(basename)
            logger.info("Creating file %s", filename)
            self.kml_file = open(filename, "wt")

            self._write_preamble(self.kml_file, g)

            if contour_set is not None:
                self._write_colors(self.kml_file, contour_set.colors)

            self._write_source_locs(self.kml_file, g)

            if self.kml_option != const.KMLOption.NO_EXTRA_OVERLAYS \
                    and self.kml_option != const.KMLOption.BOTH_1_AND_2:
                self._write_overlays(self.kml_file)

        if g.vert_level == 0 and self.deposition_contour_writer is not None:
            self.deposition_contour_writer.write(self.kml_file, g, contour_set,
                                      lower_vert_level, upper_vert_level,
                                      self.output_suffix)
        else:
            self.contour_writer.write(self.kml_file, g, contour_set,
                                      lower_vert_level, upper_vert_level,
                                      self.output_suffix)

        if self.att_file is None:
            filename = "GELABEL_{}.txt".format(self.output_suffix)
            logger.info("Creating file %s", filename)
            self.att_file = open(filename, "wt")

        self._write_attributes(self.att_file, g, contour_set)

    def finalize(self):
        if self.kml_file is not None:
            self._write_postamble(self.kml_file)
            self.kml_file.close()

        if self.att_file is not None:
            self.att_file.close()

    def _get_att_datetime_str(self, dt):
        t = dt if self.time_zone is None else dt.astimezone(self.time_zone)
        return t.strftime("%H%M %Z %b %d %Y&")

    def _write_attributes(self, f, g, contour_set):
        f.write("{}\n".format(self.KMAP))
        f.write("{}&\n".format(contour_set.concentration_unit))

        if self.NSSLBL == 1:
            starting_time = g.parent.release_datetimes[0]
        else:
            starting_time = g.starting_datetime
        f.write("Integrated: {}\n".format(
            self._get_att_datetime_str(starting_time)))
        f.write("        to: {}\n".format(
            self._get_att_datetime_str(g.ending_datetime)))

        if self.show_max_conc == 1 or self.show_max_conc == 2:
            f.write("{:7s} {:7s} {:2d}\n".format(contour_set.max_concentration_str,
                                        contour_set.min_concentration_str,
                                        len(contour_set.levels)))
        else:
            f.write("NOMAXNM NOMAXNM {:2d}\n".format(len(contour_set.levels)))

        for level in contour_set.levels_str:
            f.write("{:8s}".format(self._quote_if_space_present(level)))
        f.write("\n")

        for c in contour_set.raw_colors:
            f.write("{:5.2f}".format(c[0]))
        f.write("\n")

        for c in contour_set.raw_colors:
            f.write("{:5.2f}".format(c[1]))
        f.write("\n")

        for c in contour_set.raw_colors:
            f.write("{:5.2f}".format(c[2]))
        f.write("\n")

        for label in contour_set.labels:
            f.write("{:8s} ".format(self._quote_if_space_present(label)))

        f.write("\n")

    def _quote_if_space_present(self, o):
        if isinstance(o, str) and o.count(" ") > 0:
            return "\"{}\"".format(o)
        return o

    def _write_preamble(self, f, g):
        first_release_loc = g.parent.release_locs[0]

        f.write("""\
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
  <Document>
    <name>NOAA HYSPLIT RESULTS</name>
    <open>1</open>
    <LookAt>
      <longitude>{:.4f}</longitude>
      <latitude>{:.4f}</latitude>
      <altitude>0</altitude>
      <tilt>0</tilt>
      <range>13700</range>
      <gx:TimeStamp>
        <when>{}</when>
      </gx:TimeStamp>
      <gx:altitudeMode>relativeToSeaFloor</gx:altitudeMode>
    </LookAt>\n""".format(first_release_loc[0],
                          first_release_loc[1],
                          util.get_iso_8601_str(g.starting_datetime,
                                                self.time_zone)))

    def _write_colors(self, f, colors):
        for k, color in enumerate(colors):
            f.write("""\
    <Style id="conc{:d}">
      <LineStyle>
        <color>C8000000</color>
      </LineStyle>
      <PolyStyle>
        <color>{}</color>
        <fill>1</fill>
        <outline>1</outline>
      </PolyStyle>
    </Style>\n""".format(k + 1,
                         self._reformat_color(color)))

        # max square
        f.write("""\
    <Style id="maxv">
      <LineStyle>
        <color>FFFFFFFF</color>
        <width>3</width>
      </LineStyle>
      <PolyStyle>
        <fill>0</fill>
      </PolyStyle>
    </Style>\n""")

    def _write_source_locs(self, f, g):
        f.write("""\
    <Folder>
      <name>Soure Locations</name>
      <visibility>0</visibility>\n""")

        release_heights = g.parent.release_heights
        level1 = min(release_heights)
        level2 = max(release_heights)

        for k, loc in enumerate(g.parent.release_locs):
            f.write("""\
      <Placemark>
        <description><![CDATA[<pre>
LAT: {:.6f} LON: {:.6f}
Released between {} and {} m AGL
</pre>]]></description>\n""".format(loc[1], loc[0], level1, level2))

            # white line to source height
            f.write("""\
        <Style id="sorc">
          <IconStyle>
            <color>ff0000ff</color>
            <scale>0.8</scale>
            <Icon>
              <href>icon63.png</href>
            </Icon>
            <hotSpot x="0.5" y="0.5" xunits="fraction" yunits="fraction"></hotSpot>
          </IconStyle>
          <LabelStyle>
            <color>ff0000ff</color>
          </LabelStyle>
          <LineStyle>
            <color>c8ffffff</color>
            <width>2</width>
          </LineStyle>
        </Style>
        <Point>
          <extrude>1</extrude>
          <altitudeMode>{}</altitudeMode>
          <coordinates>{:.6f},{:.6f},{:.1f}</coordinates>
        </Point>
      </Placemark>\n""".format(self.alt_mode_str,
                               loc[0], loc[1], float(level2)))

        f.write("""\
    </Folder>\n""")

    def _write_overlays(self, f):
        f.write("""\
    <ScreenOverlay>
      <name>HYSPLIT Information</name>
      <description>NOAA ARL HYSPLIT Model  http://www.arl.noaa.gov/HYSPLIT_info.php</description>
      <Icon>
        <href>logocon.gif</href>
      </Icon>
      <overlayXY x="1" y="1" xunits="fraction" yunits="fraction"/>
      <screenXY x="1" y="1" xunits="fraction" yunits="fraction"/>
      <rotationXY x="0" y="0" xunits="fraction" yunits="fraction"/>
      <size x="0" y="0" xunits="pixels" yunits="pixels"/>
    </ScreenOverlay>
    <ScreenOverlay>
      <name>NOAA</name>
      <Snippet maxLines="0"></Snippet>
      <description>National Oceanic and Atmospheric Administration  http://www.noaa.gov</description>
      <Icon>
        <href>noaa_google.gif</href>
      </Icon>
      <overlayXY x="0" y="1" xunits="fraction" yunits="fraction"/>
      <screenXY x="0.3" y="1" xunits="fraction" yunits="fraction"/>
      <rotationXY x="0" y="0" xunits="fraction" yunits="fraction"/>
      <size x="0" y="0" xunits="pixels" yunits="pixels"/>
    </ScreenOverlay>\n""")

        # add a link to NOAA NWS kml weather data overlays
        f.write("""\
    <Folder>
      <name>NOAA NWS kml Weather Data</name>
      <visibility>0</visibility>
      <description>http://weather.gov/gis/  Click on the link to access weather related overlays from the National Weather Service.</description>
    </Folder>\n""")

        # add a link to NOAA NESDIS kml smoke/fire data overlays
        f.write("""\
    <Folder>
      <name>NOAA NESDIS kml Smoke/Fire Data</name>
      <visibility>0</visibility>
      <description>http://www.ssd.noaa.gov/PS/FIRE/hms.html  Click on the link to access wildfire smoke overlays from NOAA NESDIS.</description>
    </Folder>\n""")

        # add a link to EPA AIRnow kml Air Quality Index (AQI)
        f.write("""\
    <Folder>
      <name>EPA AIRNow Air Quality Index (AQI)</name>
      <visibility>0</visibility>
      <description>http://www.epa.gov/airnow/today/airnow.kml  Click on the link to access AQI data from EPA. The results will appear in the list below.</description>
    </Folder>\n""")

    def _write_postamble(self, f):
        f.write("""\
  </Document>
</kml>\n""")


class PartialKMLWriter(KMLWriter):

    def __init__(self, kml_option, time_zone=None):
        super(PartialKMLWriter, self).__init__(kml_option, time_zone)

    def write(self, basename, g, contour_set,
              lower_vert_level, upper_vert_level):
        if self.kml_file is None:
            filename = "{}.txt".format(basename)
            logger.info("Creating file %s", filename)
            self.kml_file = open(filename, "wt")

        if g.vert_level == 0 and self.deposition_contour_writer is not None:
            self.deposition_contour_writer.write(self.kml_file, g, contour_set,
                                      lower_vert_level, upper_vert_level,
                                      self.output_suffix)
        else:
            self.contour_writer.write(self.kml_file, g, contour_set,
                                      lower_vert_level, upper_vert_level,
                                      self.output_suffix)

        if self.att_file is None:
            filename = "GELABEL_{}.txt".format(self.output_suffix)
            logger.info("Creating file %s", filename)
            self.att_file = open(filename, "wt")

        self._write_attributes(self.att_file, g, contour_set)

    def _write_attributes(self, f, g, contour_set):
        # do nothing
        pass

    def finalize(self):
        if self.kml_file is not None:
            self.kml_file.close()

        if self.att_file is not None:
            self.att_file.close()


class KMLContourWriterFactory:

    @staticmethod
    def create_instance(KMAP, alt_mode_str, time_zone=None):
        if KMAP == const.ConcentrationMapType.CONCENTRATION:
            return KMLConcentrationWriter(alt_mode_str, time_zone)
        elif KMAP == const.ConcentrationMapType.EXPOSURE:
            return KMLConcentrationWriter(alt_mode_str, time_zone)
        elif KMAP == const.ConcentrationMapType.DEPOSITION:
            return KMLDepositionWriter(alt_mode_str, time_zone)
        elif KMAP == const.ConcentrationMapType.THRESHOLD_LEVELS:
            return KMLChemicalThresholdWriter(alt_mode_str, time_zone)
        elif KMAP == const.ConcentrationMapType.VOLCANIC_ERUPTION:
            return KMLDepositionWriter(alt_mode_str, time_zone)
        elif KMAP == const.ConcentrationMapType.DEPOSITION_6:
            return KMLDepositionWriter(alt_mode_str, time_zone)
        elif KMAP == const.ConcentrationMapType.MASS_LOADING:
            return KMLMassLoadingWriter(alt_mode_str, time_zone)
        elif KMAP == const.ConcentrationMapType.TIME_OF_ARRIVAL:
            return KMLTimeOfArrivalWriter(alt_mode_str, time_zone)


class AbstractKMLContourWriter(ABC):

    def __init__(self, alt_mode_str, time_zone=None):
        self.frame_count = 0
        self.alt_mode_str = alt_mode_str
        self.time_zone = time_zone
        self.show_max_conc = True

    def set_show_max_conc(self, show_max_conc):
        self.show_max_conc = True if show_max_conc != 0 else False

    def _get_begin_end_timestamps(self, g):
        if g.ending_datetime < g.starting_datetime:
            begin_ts = util.get_iso_8601_str(g.ending_datetime,
                                             self.time_zone)
            end_ts = util.get_iso_8601_str(g.starting_datetime,
                                           self.time_zone)
        else:
            begin_ts = util.get_iso_8601_str(g.starting_datetime,
                                             self.time_zone)
            end_ts = util.get_iso_8601_str(g.ending_datetime,
                                           self.time_zone)
        return (begin_ts, end_ts)

    @abstractmethod
    def _get_name_cdata(self, dt):
        pass

    @abstractmethod
    def _get_description_cdata(self, lower_vert_level, upper_vert_level, dt):
        pass

    def _get_contour_name(self, level_str, conc_unit):
        return "Contour Level: {} {}".format(level_str, conc_unit)

    def write(self, f, g, contour_set, lower_vert_level, upper_vert_level,
              suffix):
        self.frame_count += 1

        begin_ts, end_ts = self._get_begin_end_timestamps(g)

        f.write("""\
    <Folder>
      <name><![CDATA[{}]]></name>\n""".format(
            self._get_name_cdata(g.ending_datetime)))

        # when not all of the concentration values are a zero
        if contour_set is not None and len(contour_set.contours) > 0:
            if self.frame_count == 1:
                f.write("""\
      <visibility>1</visibility>
      <open>1</open>\n""")
            else:
                f.write("""\
      <visibility>0</visibility>\n""")

        f.write("""\
      <description><![CDATA[{}]]></description>\n""".format(
          self._get_description_cdata(lower_vert_level,
                                      upper_vert_level,
                                      g.ending_datetime)))

        f.write("""\
      <ScreenOverlay>
        <name>Legend</name>
        <Snippet maxLines="0"></Snippet>
        <TimeSpan>
          <begin>{}</begin>
          <end>{}</end>
        </TimeSpan>
        <Icon>
          <href>GELABEL_{:02d}_{}.gif</href>
        </Icon>
        <overlayXY x="0" y="1" xunits="fraction" yunits="fraction"/>
        <screenXY x="0" y="1" xunits="fraction" yunits="fraction"/>
        <rotationXY x="0" y="0" xunits="fraction" yunits="fraction"/>
        <size x="0" y="0" xunits="pixels" yunits="pixels"/>
      </ScreenOverlay>\n""".format(begin_ts,
                                   end_ts,
                                   self.frame_count,
                                   suffix))

        self._write_contour(f, g, contour_set, upper_vert_level)

        if self.show_max_conc:
            self._write_max_location(f, g, contour_set.max_concentration_str,
                                     upper_vert_level, contour_set.labels[-1])

        f.write("""\
    </Folder>\n""")

    def _get_contour_height_at(self, k, vert_level):
        return int(vert_level) + (200 * k)

    def _write_contour(self, f, g, contour_set, vert_level):
        if contour_set is None:
            return

        vert_level_ref = vert_level
        begin_ts, end_ts = self._get_begin_end_timestamps(g)

        for i in range(len(contour_set.contours)):
            k = contour_set.contour_orders.index(i)
            contour = contour_set.contours[k]

            # arbitrary height above ground in order of
            # increasing concentration
            vert_level = self._get_contour_height_at(k, vert_level_ref)

            f.write("""\
      <Placemark>\n""")

            contour_name = self._get_contour_name(
                                    contour_set.levels_str[k],
                                    contour_set.concentration_unit)

            if len(contour_set.labels[k]) > 0:
                f.write("""\
        <name LOC="{}">{}</name>\n""".format(contour_set.labels[k],
                                             contour_name))
            else:
                f.write("""\
        <name>{}</name>\n""".format(contour_name))

            self._write_placemark_visibility(f)

            f.write("""\
        <Snippet maxLines="0"></Snippet>
        <TimeSpan>
          <begin>{}</begin>
          <end>{}</end>
        </TimeSpan>
        <styleUrl>#conc{}</styleUrl>
        <MultiGeometry>\n""".format(begin_ts, end_ts, k + 1))

            for polygon in contour.polygons:
                self._write_polygon(f, polygon, vert_level)

            f.write("""\
        </MultiGeometry>
      </Placemark>\n""")

    def _write_polygon(self, f, polygon, vert_level):
        if len(polygon.boundaries) > 0:
            f.write("""\
          <Polygon>
            <extrude>1</extrude>
            <altitudeMode>{}</altitudeMode>\n""".format(self.alt_mode_str))

            for boundary in polygon.boundaries:
                self._write_boundary(f, boundary, vert_level)

            f.write("""\
          </Polygon>\n""")

    def _write_boundary(self, f, boundary, vert_level):
        lons = boundary.longitudes
        lats = boundary.latitudes

        if boundary.hole:
            f.write("""\
            <innerBoundaryIs>
              <LinearRing>
                <coordinates>\n""")
        else:
            f.write("""\
            <outerBoundaryIs>
              <LinearRing>
                <coordinates>\n""")

        for k in range(len(lons)):
            f.write("{:.5f},{:.5f},{:05d}\n".format(lons[k],
                                                    lats[k],
                                                    int(vert_level)))

        if boundary.hole:
            f.write("""\
                </coordinates>
              </LinearRing>
            </innerBoundaryIs>\n""")
        else:
            f.write("""\
                </coordinates>
              </LinearRing>
            </outerBoundaryIs>\n""")

    @abstractmethod
    def _get_max_location_text(self):
        pass

    def _write_max_location(self, f, g, max_conc_str, vert_level,
                            contour_label):
        if g.extension is None or len(g.extension.max_locs) == 0:
            logger.warning("No max location is found: "
                           "skip outputting max location to KML")
            return

        dx = g.parent.grid_deltas[0]
        dy = g.parent.grid_deltas[1]
        hx = 0.5 * dx
        hy = 0.5 * dy

        loc = g.extension.max_locs[0]
        vert_level = int(vert_level)

        begin_ts, end_ts = self._get_begin_end_timestamps(g)

        f.write("""\
      <Placemark>\n""")

        if len(contour_label) > 0:
            f.write("""\
        <name LOC="{}">Maximum Value Grid Cell</name>\n""".format(
                contour_label))
        else:
            f.write("""\
        <name>Maximum Value Grid Cell</name>\n""")

        self._write_placemark_visibility(f)

        f.write("""\
        <description><![CDATA[<pre>
LAT: {:.4f} LON: {:.4f}
Value: {}
{}</pre>]]></description>\n""".format(loc[1],
                                      loc[0],
                                      max_conc_str,
                                      self._get_max_location_text()))

        f.write("""\
        <Snippet maxLines="0"></Snippet>
        <TimeSpan>
          <begin>{}</begin>
          <end>{}</end>
        </TimeSpan>
        <styleUrl>#maxv</styleUrl>
        <MultiGeometry>\n""".format(begin_ts,
                                    end_ts))

        for loc in g.extension.max_locs:
            f.write("""\
          <Polygon>
            <extrude>1</extrude>
            <altitudeMode>{}</altitudeMode>
            <outerBoundaryIs>
              <LinearRing>
                <coordinates>\n""".format(self.alt_mode_str))

            f.write("{:.5f},{:.5f},{:05d}\n".format(loc[0]-hx,
                                                    loc[1]-hy,
                                                    vert_level))
            f.write("{:.5f},{:.5f},{:05d}\n".format(loc[0]+hx,
                                                    loc[1]-hy,
                                                    vert_level))
            f.write("{:.5f},{:.5f},{:05d}\n".format(loc[0]+hx,
                                                    loc[1]+hy,
                                                    vert_level))
            f.write("{:.5f},{:.5f},{:05d}\n".format(loc[0]-hx,
                                                    loc[1]+hy,
                                                    vert_level))
            f.write("{:.5f},{:.5f},{:05d}\n".format(loc[0]-hx,
                                                    loc[1]-hy,
                                                    vert_level))

            f.write("""\
                </coordinates>
              </LinearRing>
            </outerBoundaryIs>
          </Polygon>\n""")

        f.write("""\
        </MultiGeometry>
      </Placemark>\n""")

    def _get_timestamp_str(self, dt):
        t = dt if self.time_zone is None else dt.astimezone(self.time_zone)
        return t.strftime("%Y%m%d %H%M %Z")

    def _write_placemark_visibility(self, f):
        pass


class KMLConcentrationWriter(AbstractKMLContourWriter):

    def __init__(self, alt_mode_str, time_zone=None):
        super(KMLConcentrationWriter, self).__init__(alt_mode_str, time_zone)

    def _get_name_cdata(self, dt):
        return """<pre>Concentration
(Valid:{})</pre>""".format(self._get_timestamp_str(dt))

    def _get_description_cdata(self, lower_vert_level, upper_vert_level, dt):
        return """<pre>
Averaged from {} to {}
Valid:{}</pre>""".format(lower_vert_level,
                         upper_vert_level,
                         self._get_timestamp_str(dt))

    def _get_max_location_text(self):
        return """\
      The square represents the location
      of maximum concentration and the
      size of the square represents the
      concentration grid cell size."""


class KMLChemicalThresholdWriter(KMLConcentrationWriter):

    def __init__(self, alt_mode_str, time_zone=None):
        super(KMLChemicalThresholdWriter, self).__init__(alt_mode_str,
                                                         time_zone)

    def _get_contour_height_at(self, k, vert_level):
        return int(vert_level) if k == 1 else int(vert_level) + (200 * k)


class KMLDepositionWriter(AbstractKMLContourWriter):

    def __init__(self, alt_mode_str, time_zone=None):
        super(KMLDepositionWriter, self).__init__(alt_mode_str, time_zone)

    def _get_name_cdata(self, dt):
        return """<pre>Deposition
(Valid:{})</pre>""".format(self._get_timestamp_str(dt))

    def _get_description_cdata(self, lower_vert_level, upper_vert_level, dt):
        return """<pre>
Valid:{}</pre>""".format(self._get_timestamp_str(dt))

    def _get_max_location_text(self):
        return """\
      The square represents the location
      of maximum deposition and the
      size of the square represents the
      deposition grid cell size."""

    def _write_placemark_visibility(self, f):
        if self.frame_count > 1:
            f.write("""\
        <visibility>0</visibility>
        \n""")


class KMLMassLoadingWriter(AbstractKMLContourWriter):

    def __init__(self, alt_mode_str, time_zone=None):
        super(KMLMassLoadingWriter, self).__init__(alt_mode_str, time_zone)

    def _get_name_cdata(self, dt):
        return """<pre>Mass_loading
(Valid:{})</pre>""".format(self._get_timestamp_str(dt))

    def _get_description_cdata(self, lower_vert_level, upper_vert_level, dt):
        return """<pre>
From {} to {}
Valid:{}</pre>""".format(lower_vert_level,
                         upper_vert_level,
                         self._get_timestamp_str(dt))

    def _get_max_location_text(self):
        return """\
      The square represents the location
      of maximum deposition and the
      size of the square represents the
      deposition grid cell size."""

    def _write_placemark_visibility(self, f):
        if self.frame_count > 1:
            f.write("""\
        <visibility>0</visibility>
        \n""")


class KMLTimeOfArrivalWriter(AbstractKMLContourWriter):

    def __init__(self, alt_mode_str, time_zone=None):
        super(KMLTimeOfArrivalWriter, self).__init__(alt_mode_str, time_zone)

    def _get_name_cdata(self, dt):
        return """<pre>Time of arrival (h)
(Valid:{})</pre>""".format(self._get_timestamp_str(dt))

    def _get_description_cdata(self, lower_vert_level, upper_vert_level, dt):
        if int(lower_vert_level) == 0 and int(upper_vert_level) == 0:
            return """<pre>
At ground-level
Valid:{}</pre>""".format(self._get_timestamp_str(dt))
        else:
            return """<pre>
Averaged from {} to {}
Valid:{}</pre>""".format(lower_vert_level,
                         upper_vert_level,
                         self._get_timestamp_str(dt))

    def _get_contour_name(self, level_str, conc_unit):
        return "Time of arrival: {}".format(level_str)

    def _get_max_location_text(self):
        pass
