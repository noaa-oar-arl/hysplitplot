# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# gisout.py
#
# To produce GIS outputs for trajectory data.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
import logging
import math
import xml.etree.ElementTree as ET

from hysplitdata.const import HeightUnit, VerticalCoordinate
from hysplitdata.traj import model
from hysplitplot import const, util
from hysplitplot.traj.color import (
   ColorCycle,
   ColorCycleFactory
)

logger = logging.getLogger(__name__)


class GISFileWriterFactory:

    @staticmethod
    def create_instance(selector, height_unit=HeightUnit.METERS,
                        time_zone=None):
        if selector == const.GISOutput.GENERATE_POINTS:
            return PointsGenerateFileWriter(time_zone)
        elif selector == const.GISOutput.GENERATE_LINES:
            return LinesGenerateFileWriter(time_zone)
        elif selector == const.GISOutput.KML:
            return KMLWriter(height_unit, time_zone)
        elif selector == const.GISOutput.PARTIAL_KML:
            return PartialKMLWriter(height_unit, time_zone)
        elif selector != const.GISOutput.NONE:
            logger.warning("Unknown GIS file writer type %d", selector)
        return NullGISFileWriter(time_zone)


class AbstractTrajectoryStyle(ABC):

    def __init__(self):
        self.colors = ColorCycle._colors[0:3]  # first three colors

    @abstractmethod
    def write_styles(self, doc: ET.SubElement) -> None:
        pass

    @abstractmethod
    def get_id(self, t: model.Trajectory, t_index: int, thinner: bool = False) -> str:
        return None
     
    def set_colors(self, o: list) -> None:
        self.colors = o  # list of color strings formatted in '#RRGGBB'


class IndexBasedTrajectoryStyle(AbstractTrajectoryStyle):

    def __init__(self):
        super(IndexBasedTrajectoryStyle, self).__init__()

    def write_styles(self, doc: ET.SubElement) -> None:
        styles = []
        for k, clr in enumerate(self.colors):
           r = clr[1:3]
           g = clr[3:5]
           b = clr[5:7]
           bgr = f'{b}{g}{r}'

           if (k%3) == 0:
               iconhref = 'redball.png'
           elif (k%3) == 1:
               iconhref = 'blueball.png'
           else:
               iconhref = 'greenball.png'

           ln1 = {'id': f'traj{k+1}', 'linecolor': f'ff{bgr}', 'linewidth':'4',
                  'polycolor': f'7f{bgr}', 'iconhref':iconhref}
           styles.append(ln1)

           ln2 = {'id': f'traj{k+1}a', 'linecolor': f'ff{bgr}', 'linewidth':'1.25',
                  'polycolor': f'7f{bgr}', 'iconhref':iconhref}
           styles.append(ln2)

        # styles = [
        #     {'id': 'traj1', 'linecolor': 'ff0000ff', 'linewidth':'4',
        #      'polycolor': '7f0000ff', 'iconhref':'redball.png'},
        #     {'id': 'traj1a', 'linecolor': 'ff0000ff', 'linewidth':'1.25',
        #      'polycolor': '7f0000ff', 'iconhref':'redball.png'},
        #
        #     {'id': 'traj2', 'linecolor': 'ffff0000', 'linewidth':'4',
        #      'polycolor': '7fff0000', 'iconhref':'blueball.png'},
        #     {'id': 'traj2a', 'linecolor': 'ffff0000', 'linewidth':'1.25',
        #      'polycolor': '7fff0000', 'iconhref':'blueball.png'},
        #
        #     {'id': 'traj3', 'linecolor': 'ff00ff00', 'linewidth':'4',
        #      'polycolor': '7f00ff00', 'iconhref':'greenball.png'},
        #     {'id': 'traj3a', 'linecolor': 'ff00ff00', 'linewidth':'1.25',
        #      'polycolor': '7f00ff00', 'iconhref':'greenball.png'}
        # ]
        for s in styles:
            style = ET.SubElement(doc, 'Style', attrib={'id': s['id']})
            iconstyle = ET.SubElement(style, 'IconStyle')
            ET.SubElement(iconstyle, 'scale').text = '0.6'
            icon = ET.SubElement(iconstyle, 'Icon')
            ET.SubElement(icon, 'href').text = s['iconhref']
            linestyle = ET.SubElement(style, 'LineStyle')
            ET.SubElement(linestyle, 'color').text = s['linecolor']
            ET.SubElement(linestyle, 'width').text = s['linewidth']
            polystyle = ET.SubElement(style, 'PolyStyle')
            ET.SubElement(polystyle, 'color').text = s['polycolor']

    def get_id(self, t: model.Trajectory, t_index: int, thinner: bool = False) -> str:
        '''
        Return a style ID based on the trajectory index.
        '''
        n = len(self.colors)
        k = (t_index % n) + 1
        if thinner:
            return f'#traj{k:1d}a'
        return f'#traj{k:1d}'


class AbstractGISFileWriter(ABC):

    def __init__(self, time_zone=None):
        self.output_suffix = "ps"           # for backward compatibility
        self.output_name = "trajplot.ps"    # for backward compatibility
        self.kml_option = const.KMLOption.NONE
        self.kml_trajectory_style = IndexBasedTrajectoryStyle()
        self.time_zone = time_zone

    @abstractmethod
    def write(self, file_no, plot_data):
        pass

    def finalize(self):
        pass


class NullGISFileWriter(AbstractGISFileWriter):

    def __init__(self, time_zone=None):
        super(NullGISFileWriter, self).__init__(time_zone)

    def write(self, file_no, plot_data):
        pass


class AbstractAttributeFileWriter(ABC):

    @staticmethod
    @abstractmethod
    def write(filename, plot_data, time_zone=None):
        pass


class PointsAttributeFileWriter(AbstractAttributeFileWriter):

    @staticmethod
    def write(filename, plot_data, time_zone=None):
        logger.info("Creating file %s", filename)
        with open(filename, "wt") as f:
            f.write("#TRAJNUM,YYYYMMDD,TIME,LEVEL\n")
            for k, t in enumerate(plot_data.trajectories):
                for j in range(len(t.longitudes)):
                    if time_zone is None:
                        dt = t.datetimes[j]
                    else:
                        dt = t.datetimes[j].astimezone(time_zone)
                    f.write("{0:6d},{1:4d}{2:02d}{3:02d},{4:02d}{5:02d},"
                            "{6:8d}.\n".format(
                                (k+1)*1000 + j,
                                dt.year,
                                dt.month,
                                dt.day,
                                dt.hour,
                                dt.minute,
                                int(t.heights[j])))


class LinesAttributeFileWriter(AbstractAttributeFileWriter):

    @staticmethod
    def write(filename, plot_data, time_zone=None):
        logger.info("Creating file %s", filename)
        with open(filename, "wt") as f:
            f.write("#TRAJNUM,YYYYMMDD,TIME,LEVEL\n")
            for k, t in enumerate(plot_data.trajectories):
                if time_zone is None:
                    dt = t.starting_datetime
                else:
                    dt = t.starting_datetime.astimezone(time_zone)
                f.write("{0:6d},{1:4d}{2:02d}{3:02d},{4:02d}{5:02d},"
                        "{6:8d}.\n".format(
                            (k+1),
                            dt.year,
                            dt.month,
                            dt.day,
                            dt.hour,
                            dt.minute,
                            int(t.starting_level)))


class GenerateAttributeFileWriter(PointsAttributeFileWriter):
    """Same as PointsAttributeFileWriter. Kept for backward compatibility"""

    @staticmethod
    def write(filename, plot_data, time_zone=None):
        PointsAttributeFileWriter.write(filename, plot_data, time_zone)


class PointsGenerateFileWriter(AbstractGISFileWriter):

    def __init__(self, time_zone=None, att_writer=None):
        super(PointsGenerateFileWriter, self).__init__(time_zone)
        if att_writer is not None:
            self.att_writer = att_writer
        else:
            self.att_writer = PointsAttributeFileWriter()

    def write(self, file_no, plot_data):
        gisout = "GIS_traj_{0}_{1:02d}.txt".format(self.output_suffix, file_no)
        logger.info("Creating file %s", gisout)
        with open(gisout, "wt") as f:
            for k, t in enumerate(plot_data.trajectories):
                for j in range(len(t.longitudes)):
                    f.write("{0:6d},{1:9.4f},{2:9.4f},{3:8d}.\n".format(
                        (k+1)*1000 + j,
                        t.longitudes[j],
                        t.latitudes[j],
                        int(t.heights[j])))
            f.write("END\n")

        gisatt = "GIS_traj_{0}_{1:02d}.att".format(self.output_suffix, file_no)
        self.att_writer.write(gisatt, plot_data, self.time_zone)


class LinesGenerateFileWriter(AbstractGISFileWriter):

    def __init__(self, time_zone=None, att_writer=None):
        super(LinesGenerateFileWriter, self).__init__(time_zone)
        if att_writer is not None:
            self.att_writer = att_writer
        else:
            self.att_writer = LinesAttributeFileWriter()

    def write(self, file_no, plot_data):
        gisout = "GIS_traj_{0}_{1:02d}.txt".format(self.output_suffix, file_no)
        logger.info("Creating file %s", gisout)
        with open(gisout, "wt") as f:
            for k, t in enumerate(plot_data.trajectories):
                f.write("{0:3d},{1:9.4f},{2:9.4f}\n".format(
                    (k+1),
                    t.starting_loc[0],
                    t.starting_loc[1]))
                for j in range(len(t.longitudes)):
                    f.write("{0:9.4f},{1:9.4f}\n".format(
                        t.longitudes[j],
                        t.latitudes[j]))
                f.write("END\n")
            f.write("END\n")

        gisatt = "GIS_traj_{0}_{1:02d}.att".format(self.output_suffix, file_no)
        self.att_writer.write(gisatt, plot_data, self.time_zone)


class KMLWriter(AbstractGISFileWriter):

    def __init__(self, height_unit=HeightUnit.METERS, time_zone=None):
        super(KMLWriter, self).__init__(time_zone)
        self.height_unit = height_unit
        self.create_kml_per_write = True  # for backward compatibility
        self.xml_root = None
        self.kml_filename = None
        self.next_trajectory_index = 0

    @staticmethod
    def make_filename(output_name, output_suffix, file_no):
        if output_name.startswith("trajplot.") \
                or output_name.startswith("trajplot "):
            return "HYSPLITtraj_{0}_{1:02d}.kml".format(output_suffix, file_no)
        else:
            k = output_name.find(".")
            if k == -1:
                k = output_name.find(" ")

            name = output_name if (k == -1) else output_name[0:k]
            return "{0}_{1:02d}.kml".format(name, file_no)

    @staticmethod
    def _get_timestamp_str(dt, time_zone=None):
        t = dt if time_zone is None else dt.astimezone(time_zone)
        return t.strftime("%m/%d/%Y %H%M %Z")

    @staticmethod
    def _get_alt_mode(t):
        return "absolute" if t.has_terrain_profile() else "relativeToGround"

    def _get_level_type(self, t):
        if self.height_unit == HeightUnit.METERS:
            return "m AMSL" if t.has_terrain_profile() else "m AGL"
        elif self.height_unit == HeightUnit.FEET:
            return "ft AMSL" if t.has_terrain_profile() else "ft AGL"
        else:
            return "AMSL" if t.has_terrain_profile() else "AGL"

    def write(self, file_no, plot_data):
        if self.xml_root is None:
            self.kml_filename = self.make_filename(self.output_name,
                                                   self.output_suffix,
                                                   file_no)

            self.xml_root = ET.Element('kml',
                    attrib={'xmlns':'http://www.opengis.net/kml/2.2',
                            'xmlns:gx':'http://www.google.com/kml/ext/2.2'})
            doc = ET.SubElement(self.xml_root, 'Document')
            self._write_preamble(doc, plot_data)

            if self.kml_option != const.KMLOption.NO_EXTRA_OVERLAYS \
                    and self.kml_option != const.KMLOption.BOTH_1_AND_2:
                self._write_overlay(doc)
        else:
            doc = self.xml_root.find("Document")

        for t in plot_data.trajectories:
            self._write_trajectory(doc, t, self.next_trajectory_index)
            self.next_trajectory_index += 1

        if self.create_kml_per_write:
            self.finalize()

    def finalize(self):
        if self.kml_filename is not None and self.xml_root is not None:
            doc = self.xml_root.find("Document")
            self._write_postamble(doc)

            logger.info("Creating file %s", self.kml_filename)
            tree = ET.ElementTree(self.xml_root)
            tree.write(self.kml_filename, encoding='UTF-8',
                       xml_declaration=True,
                       short_empty_elements=False)

        self.xml_root = None

    def _write_preamble(self, doc, plot_data):
        t = plot_data.trajectories[0]
        starting_loc = t.starting_loc
        starting_datetime = t.starting_datetime
        timestamp_str = util.get_iso_8601_str(starting_datetime,
                                              self.time_zone)

        ET.SubElement(doc, 'name').text = f'NOAA HYSPLIT Trajectory {self.output_suffix}'
        ET.SubElement(doc, 'open').text = '1'
        lookAt = ET.SubElement(doc, 'LookAt')
        timestamp = ET.SubElement(lookAt, 'gx:TimeStamp')
        ET.SubElement(timestamp, 'when').text = timestamp_str
        ET.SubElement(lookAt, 'longitude').text = f'{starting_loc[0]:.4f}'
        ET.SubElement(lookAt, 'latitude').text = f'{starting_loc[1]:.4f}'
        ET.SubElement(lookAt, 'altitude').text = '0'
        ET.SubElement(lookAt, 'tilt').text = '0'
        ET.SubElement(lookAt, 'range').text = '13700'
        ET.SubElement(lookAt, 'gx:altitudeMode').text = 'relativeToSeaFloor'
        
        self.kml_trajectory_style.write_styles(doc)

    def _write_postamble(self, doc):
        pass

    def _write_overlay(self, doc):
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
                      attrib={'x': '0', 'y': '1',
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

    def _write_trajectory(self, doc, t, t_index):
        vc = model.VerticalCoordinateFactory.create_instance(
            VerticalCoordinate.ABOVE_GROUND_LEVEL, self.height_unit, t)
        vc.make_vertical_coordinates()
        if (t.starting_loc is None) or (len(vc.values) == 0):
            logger.info("skip writing an empty trajectory")
            return

        folder = ET.SubElement(doc, 'Folder')
        ET.SubElement(folder, 'name').text = f'{t.starting_level:.1f} {self._get_level_type(t)} Trajectory'
        ET.SubElement(folder, 'open').text = '1'
        
        placemark = ET.SubElement(folder, 'Placemark')
        ET.SubElement(placemark, 'name').text = f'{t.starting_level:.1f} {self._get_level_type(t)} Trajectory'
        lookAt = ET.SubElement(placemark, 'LookAt')
        timestamp = ET.SubElement(lookAt, 'gx:TimeStamp')
        ET.SubElement(timestamp, 'when').text = util.get_iso_8601_str(t.starting_datetime,
                                                                      self.time_zone)
        ET.SubElement(lookAt, 'longitude').text = f'{t.starting_loc[0]:.4f}'
        ET.SubElement(lookAt, 'latitude').text = f'{t.starting_loc[1]:.4f}'
        ET.SubElement(lookAt, 'heading').text = '0.0'
        ET.SubElement(lookAt, 'tilt').text = '0.0'
        ET.SubElement(lookAt, 'range').text = '2000000.0'
        ET.SubElement(lookAt, 'gx:altitudeMode').text = 'relativeToSeaFloor'

        ET.SubElement(placemark, 'styleUrl').text = self.kml_trajectory_style.get_id(t, t_index)
        lineString = ET.SubElement(placemark, 'LineString')
        ET.SubElement(lineString, 'extrude').text = '1'
        ET.SubElement(lineString, 'altitudeMode').text = self._get_alt_mode(t)
        
        buffer = '\n'
        for k in range(len(t.longitudes)):
            buffer += f'{t.longitudes[k]:.4f},{t.latitudes[k]:.4f},{vc.values[k]:.1f}\n'
        ET.SubElement(lineString, 'coordinates').text = buffer
        
        starttime_str = self._get_timestamp_str(t.starting_datetime,
                                                self.time_zone)

        placemark = ET.SubElement(folder, 'Placemark')
        ET.SubElement(placemark, 'name').text = ''
        ET.SubElement(placemark, 'visibility').text = '1'
        ET.SubElement(placemark, 'description').text = """\
<![CDATA[<pre>Start Time
{0}
LAT: {1:.4f} LON: {2:.4f} Hght({3}): {4:.1f}
</pre>]]>""".format(starttime_str,
                    t.starting_loc[1],
                    t.starting_loc[0],
                    self._get_level_type(t),
                    t.starting_level)
        ET.SubElement(placemark, 'styleUrl').text = self.kml_trajectory_style.get_id(t, t_index)
        point = ET.SubElement(placemark, 'Point')
        ET.SubElement(point, 'altitudeMode').text = self._get_alt_mode(t)
        ET.SubElement(point, 'coordinates').text = f'{t.starting_loc[0]:.4f},{t.starting_loc[1]:.4f},{t.starting_level:.1f}'

        if t.has_trajectory_stddevs():
            self._write_ellipses_of_uncertainty(folder, t, t_index, vc)

        if self.kml_option != const.KMLOption.NO_ENDPOINTS \
                and self.kml_option != const.KMLOption.BOTH_1_AND_2:
            self._write_endpts(folder, t, t_index, vc)

    def _write_ellipses_of_uncertainty(self, doc, t, t_index, vc):
        is_backward = False if t.parent.is_forward_calculation() else True
        npts_ellipse = 64
        delta_theta = 2*math.pi / npts_ellipse

        folder = ET.SubElement(doc, 'Folder')
        ET.SubElement(folder, 'name').text = 'Ellipses of uncertainty for center-of-mass trajectory'
        ET.SubElement(folder, 'visibility').text = '0'
        for k in range(len(t.longitudes)):
            if k == 0:
                continue

            placemark = ET.SubElement(folder, 'Placemark')
            ET.SubElement(placemark, 'name').text = self._get_timestamp_str(t.datetimes[k], self.time_zone)
            ET.SubElement(placemark, 'visibility').text = '1'
            ET.SubElement(placemark, 'Snippet', attrib={'maxLines': '0'})
            ET.SubElement(placemark, 'description').text = """\
<![CDATA[<pre>HYSPLIT {0:4.0f}. hour ellipse of uncertainty

{1}
LAT: {2:9.4f} LON: {3:9.4f} Hght({4}): {5:8.1f}
</pre>]]>""".format(t.ages[k],
                    self._get_timestamp_str(t.datetimes[k], self.time_zone),
                    t.latitudes[k],
                    t.longitudes[k],
                    self._get_level_type(t),
                    vc.values[k])
            lookAt = ET.SubElement(placemark, 'LookAt')
            ET.SubElement(lookAt, 'longitude').text = f'{t.longitudes[k]:.4f}'
            ET.SubElement(lookAt, 'latitude').text = f'{t.latitudes[k]:.4f}'
            ET.SubElement(lookAt, 'heading').text = '0.0'
            ET.SubElement(lookAt, 'tilt').text = '60.0'
            ET.SubElement(lookAt, 'range').text = '20000.0'
            timeSpan = ET.SubElement(placemark, 'TimeSpan')
            # Use the entire time period so that the ellipse would be
            # initially visible with Google Earth.
            if is_backward:
                ET.SubElement(timeSpan, 'end').text = util.get_iso_8601_str(t.datetimes[-1], self.time_zone)
                ET.SubElement(timeSpan, 'begin').text = util.get_iso_8601_str(t.datetimes[0], self.time_zone)
            else:
                ET.SubElement(timeSpan, 'begin').text = util.get_iso_8601_str(t.datetimes[0], self.time_zone)
                ET.SubElement(timeSpan, 'end').text = util.get_iso_8601_str(t.datetimes[-1], self.time_zone)
            ET.SubElement(placemark, 'styleUrl').text = \
                    self.kml_trajectory_style.get_id(t, t_index, thinner=True)
            lineString = ET.SubElement(placemark, 'LineString')
            ET.SubElement(lineString, 'extrude').text = '1'
            ET.SubElement(lineString, 'altitudeMode').text = self._get_alt_mode(t)
            
            buffer = '\n'
            slon, slat = t.trajectory_stddevs[k]
            for j in range(npts_ellipse + 1):
                theta = j * delta_theta if j < npts_ellipse else 0
                y = t.latitudes[k] + slat * math.sin(theta)
                x = t.longitudes[k] + slon * math.cos(theta)
                buffer += f'{x:.4f},{y:.4f},{vc.values[k]:.1f}\n'
            ET.SubElement(lineString, 'coordinates').text = buffer

    def _write_endpts(self, doc, t, t_index, vc):
        is_backward = False if t.parent.is_forward_calculation() else True

        folder = ET.SubElement(doc, 'Folder')
        ET.SubElement(folder, 'name').text = 'Trajectory Endpoints'
        ET.SubElement(folder, 'visibility').text = '0'

        for k in range(len(t.longitudes)):
            if k == 0:
                continue
            placemark = ET.SubElement(folder, 'Placemark')
            ET.SubElement(placemark, 'name').text = self._get_timestamp_str(t.datetimes[k], self.time_zone)
            ET.SubElement(placemark, 'visibility').text = '1'
            ET.SubElement(placemark, 'Snippet', attrib={'maxLines': '0'})
            ET.SubElement(placemark, 'description').text = """\
<![CDATA[<pre>HYSPLIT {0:4.0f}. hour endpoint

{1}
LAT: {2:9.4f} LON: {3:9.4f} Hght({4}): {5:8.1f}
</pre>]]>""".format(t.ages[k],
                    self._get_timestamp_str(t.datetimes[k], self.time_zone),
                    t.latitudes[k],
                    t.longitudes[k],
                    self._get_level_type(t),
                    vc.values[k])
            lookAt = ET.SubElement(placemark, 'LookAt')
            ET.SubElement(lookAt, 'longitude').text = f'{t.longitudes[k]:.4f}'
            ET.SubElement(lookAt, 'latitude').text = f'{t.latitudes[k]:.4f}'
            ET.SubElement(lookAt, 'heading').text = '0.0'
            ET.SubElement(lookAt, 'tilt').text = '60.0'
            ET.SubElement(lookAt, 'range').text = '20000.0'
            timeSpan = ET.SubElement(placemark, 'TimeSpan')
            if is_backward:
                ET.SubElement(timeSpan, 'end').text = util.get_iso_8601_str(t.datetimes[k-1], self.time_zone)
                ET.SubElement(timeSpan, 'begin').text = util.get_iso_8601_str(t.datetimes[k], self.time_zone)
            else:
                ET.SubElement(timeSpan, 'begin').text = util.get_iso_8601_str(t.datetimes[k-1], self.time_zone)
                ET.SubElement(timeSpan, 'end').text = util.get_iso_8601_str(t.datetimes[k], self.time_zone)
            ET.SubElement(placemark, 'styleUrl').text = self.kml_trajectory_style.get_id(t, t_index)
            point = ET.SubElement(placemark, 'Point')
            ET.SubElement(point, 'altitudeMode').text = self._get_alt_mode(t)
            ET.SubElement(point, 'coordinates').text = f'{t.longitudes[k]:.4f},{t.latitudes[k]:.4f},{vc.values[k]:.1f}'


class PartialKMLWriter(KMLWriter):

    def __init__(self, height_unit=HeightUnit.METERS, time_zone=None):
        super(PartialKMLWriter, self).__init__(height_unit, time_zone)

    @staticmethod
    def make_filename(output_name, output_suffix, file_no):
        if output_name.startswith("trajplot.") \
                or output_name.startswith("trajplot "):
            return "HYSPLITtraj_{0}_{1:02d}.txt".format(output_suffix, file_no)
        else:
            k = output_name.find(".")
            if k == -1:
                k = output_name.find(" ")

            name = output_name if (k == -1) else output_name[0:k]
            return "{0}_{1:02d}.txt".format(name, file_no)

    def write(self, file_no, plot_data):
        if self.xml_root is None:
            self.kml_filename = self.make_filename(self.output_name,
                                                   self.output_suffix,
                                                   file_no)
 
            self.xml_root = ET.Element('kml',
                    attrib={'xmlns':'http://www.opengis.net/kml/2.2',
                            'xmlns:gx':'http://www.google.com/kml/ext/2.2'})
            doc = ET.SubElement(self.xml_root, 'Document')
        else:
            doc = self.xml_root.find("Document")

        for t_idx, t in enumerate(plot_data.trajectories):
            self._write_trajectory(doc, t, t_idx)

        if self.create_kml_per_write:
            self.finalize()

    def finalize(self):
        if self.kml_filename is not None and self.xml_root is not None:
            folder = self.xml_root.find('Document/Folder')
            tree = ET.ElementTree(folder)

            logger.info("Creating file %s", self.kml_filename)
            tree.write(self.kml_filename, encoding='UTF-8',
                       xml_declaration=False,
                       short_empty_elements=False)

        self.xml_root = None
