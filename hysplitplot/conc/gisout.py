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
import xml.etree.ElementTree as ET

from hysplitdata.conc import model
from hysplitplot import const, util


logger = logging.getLogger(__name__)


# override CDATA serializer
def _cdata_serializer(text, encoding=None):
    return text

ET._escape_cdata = _cdata_serializer


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
        self.output_basename = "plot"
        self.output_suffix = "ps"
        self.KMAP = const.ConcentrationMapType.CONCENTRATION
        self.NSSLBL = 0
        self.show_max_conc = 1
        self.NDEP = const.DepositionType.TIME
        self.time_zone = time_zone

    def initialize(self, gis_alt_mode, output_basename, output_suffix,
                   KMAP, NSSLBL, show_max_conc, NDEP):
        if gis_alt_mode == const.GISOutputAltitude.RELATIVE_TO_GROUND:
            self.alt_mode_str = "relativeToGround"
        else:
            self.alt_mode_str = "clampedToGround"
        self.output_basename = output_basename
        self.output_suffix = output_suffix
        self.KMAP = KMAP
        self.NSSLBL = NSSLBL
        self.show_max_conc = show_max_conc
        self.NDEP = NDEP

    @abstractmethod
    def write(self, basename, g, contour_set, lower_vert_level,
              upper_vert_level, distinguishable_vert_level):
        pass

    def finalize(self):
        pass

    @abstractmethod
    def make_output_basename(self, g, conc_type, depo_sum, upper_vert_level):
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
              upper_vert_level, distinguishable_vert_level=True):
        pass

    def make_output_basename(self, g, conc_type, depo_sum, upper_vert_level):
        pass


class PointsGenerateFileWriter(AbstractWriter):

    def __init__(self, formatter, time_zone=None):
        super(PointsGenerateFileWriter, self).__init__(time_zone)
        self.formatter = formatter

    def make_output_basename(self, g, conc_type, depo_sum, upper_vert_level):
        if g.vert_level == 0 and depo_sum is not None:
            basename = depo_sum.make_gis_basename(g.time_index + 1,
                                                  self.output_suffix)
        else:
            basename = conc_type.make_gis_basename(g.time_index + 1,
                                                   self.output_suffix,
                                                   g.vert_level,
                                                   upper_vert_level)
        return basename

    def write(self, basename, g, contour_set, lower_vert_level,
              upper_vert_level, distinguishable_vert_level=True):
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
        self.att_file = None
        self.contour_writer = None
        self.xml_root = None
        self.kml_filename = None

    def make_output_basename(self, g, conc_type, depo_sum, upper_vert_level):
        return conc_type.make_kml_basename(g.time_index + 1,
                                           self.output_suffix,
                                           g.vert_level,
                                           upper_vert_level)

    def initialize(self, gis_alt_mode, output_basename, output_suffix,
                   KMAP, NSSLBL, show_max_conc, NDEP):
        super(KMLWriter, self).initialize(gis_alt_mode, output_basename,
                                          output_suffix, KMAP, NSSLBL,
                                          show_max_conc, NDEP)
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
              lower_vert_level, upper_vert_level,
              distinguishable_vert_level=True):
        if self.xml_root is None:
            self.kml_filename = "{}.kml".format(basename)
            logger.info("Creating file %s", self.kml_filename)

            self.xml_root = ET.Element('kml',
                    attrib={'xmlns':'http://www.opengis.net/kml/2.2',
                            'xmlns:gx':'http://www.google.com/kml/ext/2.2'})
            doc = ET.SubElement(self.xml_root, 'Document')
            self._write_preamble(doc, g)

            if contour_set is not None:
                self._write_colors(doc, contour_set.colors)

            self._write_source_locs(doc, g)

            if self.kml_option != const.KMLOption.NO_EXTRA_OVERLAYS \
                    and self.kml_option != const.KMLOption.BOTH_1_AND_2:
                self._write_overlays(doc)
        else:
            doc = self.xml_root.find("Document")

        if g.vert_level == 0 and self.deposition_contour_writer is not None:
            self.deposition_contour_writer.write(doc, g, contour_set,
                                      lower_vert_level, upper_vert_level,
                                      self.output_suffix,
                                      distinguishable_vert_level)
        else:
            self.contour_writer.write(doc, g, contour_set,
                                      lower_vert_level, upper_vert_level,
                                      self.output_suffix,
                                      distinguishable_vert_level)

        if self.att_file is None:
            filename = "GELABEL_{}.txt".format(self.output_suffix)
            logger.info("Creating file %s", filename)
            self.att_file = open(filename, "wt")

        self._write_attributes(self.att_file, g, contour_set)

    def finalize(self):
        if self.kml_filename is not None and self.xml_root is not None:
            tree = ET.ElementTree(self.xml_root)
            tree.write(self.kml_filename, encoding='UTF-8',
                       xml_declaration=True,
                       short_empty_elements=False)

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

        # Always use 4 levels for chemical thresholds
        additional_levels = 0
        if self.KMAP == const.ConcentrationMapType.THRESHOLD_LEVELS:
            if len(contour_set.levels) < 4:
                additional_levels = 4 - len(contour_set.levels)

        if self.show_max_conc == 1 or self.show_max_conc == 2:
            f.write("{:7s} {:7s} {:2d}\n".format(contour_set.max_concentration_str,
                                        contour_set.min_concentration_str,
                                        len(contour_set.levels) + additional_levels))
        else:
            f.write("NOMAXNM NOMAXNM {:2d}\n".format(len(contour_set.levels)
                                                     + additional_levels))

        for k in range(additional_levels):
            f.write("{:8s}".format(str(0)))
        for level in contour_set.levels_str:
            f.write("{:8s}".format(self._quote_if_space_present(level)))
        f.write("\n")

        f.write("{:5.2f}".format(1.0))
        for k in range(additional_levels):
            f.write("{:5.2f}".format(1.0))
        for c in contour_set.raw_colors:
            f.write("{:5.2f}".format(c[0]))
        f.write("\n")

        f.write("{:5.2f}".format(1.0))
        for k in range(additional_levels):
            f.write("{:5.2f}".format(1.0))
        for c in contour_set.raw_colors:
            f.write("{:5.2f}".format(c[1]))
        f.write("\n")

        f.write("{:5.2f}".format(1.0))
        for k in range(additional_levels):
            f.write("{:5.2f}".format(1.0))
        for c in contour_set.raw_colors:
            f.write("{:5.2f}".format(c[2]))
        f.write("\n")

        contour_set.labels.reverse()
        for label in contour_set.labels:
            f.write("{:8s} ".format(self._quote_if_space_present(label)))
        contour_set.labels.reverse()
        for k in range(additional_levels):
            f.write("{:8s} ".format(" "))
        f.write("\n")

    def _quote_if_space_present(self, o):
        if isinstance(o, str) and o.count(" ") > 0:
            return "\"{}\"".format(o)
        return str(o)

    def _write_preamble(self, doc, g):
        first_release_loc = g.parent.release_locs[0]

        ET.SubElement(doc, 'name').text = 'NOAA HYSPLIT RESULTS'
        ET.SubElement(doc, 'open').text = '1'
        lookAt = ET.SubElement(doc, 'LookAt')
        ET.SubElement(lookAt, 'longitude').text = '{:.4f}'.format(first_release_loc[0])
        ET.SubElement(lookAt, 'latitude').text = '{:.4f}'.format(first_release_loc[1])
        ET.SubElement(lookAt, 'altitude').text = '0'
        ET.SubElement(lookAt, 'tilt').text = '0'
        ET.SubElement(lookAt, 'range').text = '13700'
        timestamp = ET.SubElement(lookAt, 'gx:TimeStamp')
        ET.SubElement(timestamp, 'when').text = util.get_iso_8601_str(g.starting_datetime,
                                                                      self.time_zone)
        ET.SubElement(lookAt, 'gx:altitudeMode').text = 'relativeToSeaFloor'

    def _write_colors(self, doc, colors):
        for k, color in enumerate(colors):
            style = ET.SubElement(doc, 'Style', attrib={'id': 'conc{:d}'.format(k + 1)})
            linestyle = ET.SubElement(style, 'LineStyle')
            ET.SubElement(linestyle, 'color').text = 'C8000000'
            polystyle = ET.SubElement(style, 'PolyStyle')
            ET.SubElement(polystyle, 'color').text = self._reformat_color(color)
            ET.SubElement(polystyle, 'fill').text = '1'
            ET.SubElement(polystyle, 'outline').text = '1'
        # max square
        style = ET.SubElement(doc, 'Style', attrib={'id': 'maxv'})
        linestyle = ET.SubElement(style, 'LineStyle')
        ET.SubElement(linestyle, 'color').text = 'FFFFFFFF'
        ET.SubElement(linestyle, 'width').text = '3'
        polystyle = ET.SubElement(style, 'PolyStyle')
        ET.SubElement(polystyle, 'fill').text = '0'

    def _write_source_locs(self, doc, g):
        folder = ET.SubElement(doc, 'Folder')
        ET.SubElement(folder, 'name').text = 'Soure Locations'
        ET.SubElement(folder, 'visibility').text = '0'
        
        release_heights = g.parent.release_heights
        level1 = min(release_heights)
        level2 = max(release_heights)

        for k, loc in enumerate(g.parent.release_locs):
            placemark = ET.SubElement(folder, 'Placemark')
            ET.SubElement(placemark, 'description').text = """<![CDATA[<pre>
LAT: {:.6f} LON: {:.6f}
Released between {} and {} m AGL
</pre>]]>""".format(loc[1], loc[0], level1, level2)
            # white line to source height
            style = ET.SubElement(placemark, 'Style', attrib={'id': 'sorc'})
            iconstyle = ET.SubElement(style, 'IconStyle')
            ET.SubElement(iconstyle, 'color').text = 'ff0000ff'
            ET.SubElement(iconstyle, 'scale').text = '0.8'
            icon = ET.SubElement(iconstyle, 'Icon')
            ET.SubElement(icon, 'href').text = 'icon63.png'
            ET.SubElement(iconstyle, 'hotSpot',
                          attrib={'x': '0.5', 'y': '0.5',
                                  'xunits': 'fraction', 'yunits': 'fraction'})
            labelstyle = ET.SubElement(style, 'LabelStyle')
            ET.SubElement(labelstyle, 'color').text = 'ff0000ff'
            linestyle = ET.SubElement(style, 'LineStyle')
            ET.SubElement(linestyle, 'color').text = 'c8ffffff'
            ET.SubElement(linestyle, 'width').text = '2'
            point = ET.SubElement(placemark, 'Point')
            ET.SubElement(point, 'extrude').text = '1'
            ET.SubElement(point, 'altitudeMode').text = self.alt_mode_str
            ET.SubElement(point, 'coordinates').text = \
                    '{:.6f},{:.6f},{:.1f}'.format(loc[0], loc[1], float(level2))

    def _write_overlays(self, doc):
        screenoverlay = ET.SubElement(doc, 'ScreenOverlay')
        ET.SubElement(screenoverlay, 'name').text = 'HYSPLIT Information'
        ET.SubElement(screenoverlay, 'description').text = 'NOAA ARL HYSPLIT Model  http://www.arl.noaa.gov/HYSPLIT_info.php'
        icon = ET.SubElement(screenoverlay, 'Icon')
        ET.SubElement(icon, 'href').text = 'logocon.gif'
        ET.SubElement(screenoverlay, 'overlayXY',
                      attrib={'x': '1', 'y': '1',
                              'xunits': 'fraction', 'yunits': 'fraction'})
        ET.SubElement(screenoverlay, 'screenXY',
                      attrib={'x': '1', 'y': '1',
                              'xunits': 'fraction', 'yunits': 'fraction'})
        ET.SubElement(screenoverlay, 'rotationXY',
                      attrib={'x': '0', 'y': '0',
                              'xunits': 'fraction', 'yunits': 'fraction'})
        ET.SubElement(screenoverlay, 'size',
                      attrib={'x': '0', 'y': '0',
                              'xunits': 'pixels', 'yunits': 'pixels'})

        screenoverlay = ET.SubElement(doc, 'ScreenOverlay')
        ET.SubElement(screenoverlay, 'name').text = 'NOAA'
        ET.SubElement(screenoverlay, 'Snippet', attrib={'maxLines': '0'})
        ET.SubElement(screenoverlay, 'description').text = 'National Oceanic and Atmospheric Administration  http://www.noaa.gov'
        icon = ET.SubElement(screenoverlay, 'Icon')
        ET.SubElement(icon, 'href').text = 'noaa_google.gif'
        ET.SubElement(screenoverlay, 'overlayXY',
                      attrib={'x': '0', 'y': '1',
                              'xunits': 'fraction', 'yunits': 'fraction'})
        ET.SubElement(screenoverlay, 'screenXY',
                      attrib={'x': '0.3', 'y': '1',
                              'xunits': 'fraction', 'yunits': 'fraction'})
        ET.SubElement(screenoverlay, 'rotationXY',
                      attrib={'x': '0', 'y': '0',
                              'xunits': 'fraction', 'yunits': 'fraction'})
        ET.SubElement(screenoverlay, 'size',
                      attrib={'x': '0', 'y': '0',
                              'xunits': 'pixels', 'yunits': 'pixels'})

        # add a link to NOAA NWS kml weather data overlays
        folder = ET.SubElement(doc, 'Folder')
        ET.SubElement(folder, 'name').text = 'NOAA NWS kml Weather Data'
        ET.SubElement(folder, 'visibility').text = '0'
        ET.SubElement(folder, 'description').text = 'http://weather.gov/gis/  Click on the link to access weather related overlays from the National Weather Service.'
        
        # add a link to NOAA NESDIS kml smoke/fire data overlays
        folder = ET.SubElement(doc, 'Folder')
        ET.SubElement(folder, 'name').text = 'NOAA NESDIS kml Smoke/Fire Data'
        ET.SubElement(folder, 'visibility').text = '0'
        ET.SubElement(folder, 'description').text = 'http://www.ssd.noaa.gov/PS/FIRE/hms.html  Click on the link to access wildfire smoke overlays from NOAA NESDIS.'
 
        # add a link to EPA AIRnow kml Air Quality Index (AQI)
        folder = ET.SubElement(doc, 'Folder')
        ET.SubElement(folder, 'name').text = 'EPA AIRNow Air Quality Index (AQI)'
        ET.SubElement(folder, 'visibility').text = '0'
        ET.SubElement(folder, 'description').text = 'http://www.epa.gov/airnow/today/airnow.kml  Click on the link to access AQI data from EPA. The results will appear in the list below.'


class PartialKMLWriter(KMLWriter):

    def __init__(self, kml_option, time_zone=None):
        super(PartialKMLWriter, self).__init__(kml_option, time_zone)

    def write(self, basename, g, contour_set,
              lower_vert_level, upper_vert_level,
              distinguishable_vert_level=True):
        if self.xml_root is None:
            self.kml_filename = "{}.txt".format(basename)
            logger.info("Creating file %s", self.kml_filename)

            self.xml_root = ET.Element('kml',
                    attrib={'xmlns':'http://www.opengis.net/kml/2.2',
                            'xmlns:gx':'http://www.google.com/kml/ext/2.2'})
            doc = ET.SubElement(self.xml_root, 'Document')
        else:
            doc = self.xml_root.find("Document")

        if g.vert_level == 0 and self.deposition_contour_writer is not None:
            self.deposition_contour_writer.write(doc, g, contour_set,
                                      lower_vert_level, upper_vert_level,
                                      self.output_suffix, distinguishable_vert_level)
        else:
            self.contour_writer.write(doc, g, contour_set,
                                      lower_vert_level, upper_vert_level,
                                      self.output_suffix, distinguishable_vert_level)

        if self.att_file is None:
            filename = "GELABEL_{}.txt".format(self.output_suffix)
            logger.info("Creating file %s", filename)
            self.att_file = open(filename, "wt")

        self._write_attributes(self.att_file, g, contour_set)

    def _write_attributes(self, f, g, contour_set):
        super(PartialKMLWriter, self)._write_attributes(f, g, contour_set)

    def finalize(self):
        if self.kml_filename is not None and self.xml_root is not None:
            folder = self.xml_root.find('Document/Folder')
            tree = ET.ElementTree(folder)
            tree.write(self.kml_filename, encoding='UTF-8',
                       xml_declaration=False,
                       short_empty_elements=False)

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

    def write(self, doc, g, contour_set, lower_vert_level, upper_vert_level,
              suffix, distinguishable_vert_level=True):
        self.frame_count += 1

        begin_ts, end_ts = self._get_begin_end_timestamps(g)

        folder = ET.SubElement(doc, 'Folder')
        ET.SubElement(folder, 'name').text = '<![CDATA[{}]]>'.format(self._get_name_cdata(g.ending_datetime))

        # when not all of the concentration values are a zero
        if contour_set is not None and len(contour_set.contours) > 0:
            if self.frame_count == 1:
                ET.SubElement(folder, 'visibility').text = '1'
                ET.SubElement(folder, 'open').text = '1'
            else:
                ET.SubElement(folder, 'visibility').text = '0'

        ET.SubElement(folder, 'description').text = '<![CDATA[{}]]>'.format(
                self._get_description_cdata(lower_vert_level,
                                            upper_vert_level,
                                            g.ending_datetime))

        screenoverlay = ET.SubElement(folder, 'ScreenOverlay')
        ET.SubElement(screenoverlay, 'name').text = 'Legend'
        ET.SubElement(screenoverlay, 'Snippet', attrib={'maxLines': '0'})
        timespan = ET.SubElement(screenoverlay, 'TimeSpan')
        ET.SubElement(timespan, 'begin').text = begin_ts
        ET.SubElement(timespan, 'end').text = end_ts
        icon = ET.SubElement(screenoverlay, 'Icon')
        ET.SubElement(icon, 'href').text = 'GELABEL_{:02d}_{}.gif'.format(self.frame_count, suffix)
        ET.SubElement(screenoverlay, 'overlayXY',
                      attrib={'x': '0', 'y': '1',
                              'xunits': 'fraction', 'yunits': 'fraction'})
        ET.SubElement(screenoverlay, 'screenXY',
                      attrib={'x': '0', 'y': '1',
                              'xunits': 'fraction', 'yunits': 'fraction'})
        ET.SubElement(screenoverlay, 'rotationXY',
                      attrib={'x': '0', 'y': '0',
                              'xunits': 'fraction', 'yunits': 'fraction'})
        ET.SubElement(screenoverlay, 'size',
                      attrib={'x': '0', 'y': '0',
                              'xunits': 'pixels', 'yunits': 'pixels'})
        
        self._write_contour(folder, g, contour_set, upper_vert_level,
                            distinguishable_vert_level)

        if self.show_max_conc:
            self._write_max_location(folder, g, contour_set.max_concentration_str,
                                     upper_vert_level, contour_set.labels[-1])

    def _get_contour_height_at(self, k, vert_level):
        return int(vert_level) + (200 * k)

    def _write_contour(self, x, g, contour_set, vert_level,
                       distinguishable_vert_level):
        if contour_set is None:
            return

        vert_level_ref = vert_level
        begin_ts, end_ts = self._get_begin_end_timestamps(g)

        for i in range(len(contour_set.contours)):
            k = contour_set.contour_orders.index(i)
            contour = contour_set.contours[k]

            if distinguishable_vert_level:
                # arbitrary height above ground in order of
                # increasing concentration
                vert_level = self._get_contour_height_at(k, vert_level_ref)

            placemark = ET.SubElement(x, 'Placemark')
            
            contour_name = self._get_contour_name(
                                    contour_set.levels_str[k],
                                    contour_set.concentration_unit)

            if len(contour_set.labels[k]) > 0:
                ET.SubElement(placemark, 'name', attrib={'LOC': contour_set.labels[k]}).text = contour_name
            else:
                ET.SubElement(placemark, 'name').text = contour_name

            self._write_placemark_visibility(placemark)

            ET.SubElement(placemark, 'Snippet', attrib={'maxLines': '0'})
            timespan = ET.SubElement(placemark, 'TimeSpan')
            ET.SubElement(timespan, 'begin').text = begin_ts
            ET.SubElement(timespan, 'end').text = end_ts
            ET.SubElement(placemark, 'styleUrl').text = '#conc{}'.format(k + 1)
            
            multigeometry = ET.SubElement(placemark, 'MultiGeometry')
            for polygon in contour.polygons:
                self._write_polygon(multigeometry, polygon, vert_level)

    def _write_polygon(self, x, polygon, vert_level):
        if len(polygon.boundaries) > 0:
            polygon_node = ET.SubElement(x, 'Polygon')
            ET.SubElement(polygon_node, 'extrude').text = '1'
            ET.SubElement(polygon_node, 'altitudeMode').text = self.alt_mode_str
            for boundary in polygon.boundaries:
                self._write_boundary(polygon_node, boundary, vert_level)

    def _write_boundary(self, x, boundary, vert_level):
        lons = boundary.longitudes
        lats = boundary.latitudes

        if boundary.hole:
            boundaryIs = ET.SubElement(x, 'innerBoundaryIs')
        else:
            boundaryIs = ET.SubElement(x, 'outerBoundaryIs')

        linearRing = ET.SubElement(boundaryIs, 'LinearRing')

        coordinates_text = ['\n']
        for k in range(len(lons)):
            coordinates_text.append("{:.5f},{:.5f},{:05d}\n".format(lons[k],
                                                                 lats[k],
                                                                 int(vert_level)))
        ET.SubElement(linearRing, 'coordinates').text = ''.join(coordinates_text)

    @abstractmethod
    def _get_max_location_text(self):
        pass

    def _write_max_location(self, x, g, max_conc_str, vert_level,
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

        placemark = ET.SubElement(x, 'Placemark')

        if len(contour_label) > 0:
            ET.SubElement(placemark, 'name', attrib={'LOC': contour_label}).text = 'Maximum Value Grid Cell'
        else:
            ET.SubElement(placemark, 'name').text = 'Maximum Value Grid Cell'

        self._write_placemark_visibility(placemark)

        ET.SubElement(placemark, 'description').text = """<![CDATA[<pre>
LAT: {:.4f} LON: {:.4f}
Value: {}
{}</pre>]]>""".format(loc[1],
                      loc[0],
                      max_conc_str,
                      self._get_max_location_text())

        ET.SubElement(placemark, 'Snippet', attrib={'maxLines': '0'})
        timespan = ET.SubElement(placemark, 'TimeSpan')
        ET.SubElement(timespan, 'begin').text = begin_ts
        ET.SubElement(timespan, 'end').text = end_ts
        ET.SubElement(placemark, 'styleUrl').text = '#maxv'

        multigeometry = ET.SubElement(placemark, 'MultiGeometry')
        for loc in g.extension.max_locs:
            polygon = ET.SubElement(multigeometry, 'Polygon')
            ET.SubElement(polygon, 'extrude').text = '1'
            ET.SubElement(polygon, 'altitudeMode').text = self.alt_mode_str
            boundaryIs = ET.SubElement(polygon, 'outerBoundaryIs')
            linearRing = ET.SubElement(boundaryIs, 'LinearRing')
            
            coordinates_text = ['\n']
            coordinates_text.append("{:.5f},{:.5f},{:05d}\n".format(loc[0]-hx,
                                                                    loc[1]-hy,
                                                                    vert_level))
            coordinates_text.append("{:.5f},{:.5f},{:05d}\n".format(loc[0]+hx,
                                                                    loc[1]-hy,
                                                                    vert_level))
            coordinates_text.append("{:.5f},{:.5f},{:05d}\n".format(loc[0]+hx,
                                                                    loc[1]+hy,
                                                                    vert_level))
            coordinates_text.append("{:.5f},{:.5f},{:05d}\n".format(loc[0]-hx,
                                                                    loc[1]+hy,
                                                                    vert_level))
            coordinates_text.append("{:.5f},{:.5f},{:05d}\n".format(loc[0]-hx,
                                                                    loc[1]-hy,
                                                                    vert_level))
            ET.SubElement(linearRing, 'coordinates').text = ''.join(coordinates_text)

    def _get_timestamp_str(self, dt):
        t = dt if self.time_zone is None else dt.astimezone(self.time_zone)
        return t.strftime("%Y%m%d %H%M %Z")

    def _write_placemark_visibility(self, x):
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

    def _write_placemark_visibility(self, x):
        if self.frame_count > 1:
            ET.SubElement(x, 'visibility').text = '0'


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

    def _write_placemark_visibility(self, x):
        if self.frame_count > 1:
            ET.SubElement(x, 'visibility').text = '0'


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
