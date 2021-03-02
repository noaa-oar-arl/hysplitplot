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

from hysplitdata.const import HeightUnit, VerticalCoordinate
from hysplitdata.traj import model
from hysplitplot import const, util


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


class AbstractGISFileWriter(ABC):

    def __init__(self, time_zone=None):
        self.output_suffix = "ps"           # for backward compatibility
        self.output_name = "trajplot.ps"    # for backward compatibility
        self.kml_option = const.KMLOption.NONE
        self.time_zone = time_zone

    @abstractmethod
    def write(self, file_no, plot_data):
        pass


class NullGISFileWriter(AbstractGISFileWriter):

    def __init__(self, time_zone=None):
        super(NullGISFileWriter, self).__init__(time_zone)

    def write(self, file_no, plot_data):
        pass


class GenerateAttributeFileWriter:

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


class PointsGenerateFileWriter(AbstractGISFileWriter):

    def __init__(self, time_zone=None, att_writer=None):
        super(PointsGenerateFileWriter, self).__init__(time_zone)
        if att_writer is not None:
            self.att_writer = att_writer
        else:
            self.att_writer = GenerateAttributeFileWriter()

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
            self.att_writer = GenerateAttributeFileWriter()

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
        file_name = self.make_filename(self.output_name,
                                       self.output_suffix,
                                       file_no)

        logger.info("Creating file %s", file_name)
        with open(file_name, "wt") as f:
            self._write_preamble(f, plot_data)

            if self.kml_option != const.KMLOption.NO_EXTRA_OVERLAYS \
                    and self.kml_option != const.KMLOption.BOTH_1_AND_2:
                self._write_overlay(f)

            for t_idx, t in enumerate(plot_data.trajectories):
                self._write_trajectory(f, t, t_idx)

            self._write_postamble(f)

    def _write_preamble(self, f, plot_data):
        t = plot_data.trajectories[0]
        starting_loc = t.starting_loc
        starting_datetime = t.starting_datetime
        timestamp_str = util.get_iso_8601_str(starting_datetime,
                                              self.time_zone)

        f.write("""\
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
  <Document>
    <name>NOAA HYSPLIT Trajectory {0}</name>
    <open>1</open>
    <LookAt>
      <longitude>{1:.4f}</longitude>
      <latitude>{2:.4f}</latitude>
      <altitude>{3}</altitude>
      <tilt>0</tilt>
      <range>13700</range>
      <gx:TimeStamp>
        <when>{4}</when>
      </gx:TimeStamp>
      <gx:altitudeMode>{5}</gx:altitudeMode>
    </LookAt>
    <Style id="traj1">
      <LineStyle>
        <color>ff0000ff</color>
        <width>4</width>
      </LineStyle>
      <PolyStyle>
        <color>7f0000ff</color>
      </PolyStyle>
      <IconStyle>
        <scale>0.6</scale>
        <Icon>
          <href>redball.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <Style id="traj1a">
      <LineStyle>
        <color>ff0000ff</color>
        <width>1.25</width>
      </LineStyle>
      <PolyStyle>
        <color>7f0000ff</color>
      </PolyStyle>
      <IconStyle>
        <scale>0.6</scale>
        <Icon>
          <href>redball.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <Style id="traj2">
      <LineStyle>
        <color>ffff0000</color>
        <width>4</width>
      </LineStyle>
      <PolyStyle>
        <color>7fff0000</color>
      </PolyStyle>
      <IconStyle>
        <scale>0.6</scale>
        <Icon>
          <href>blueball.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <Style id="traj2a">
      <LineStyle>
        <color>ffff0000</color>
        <width>1.25</width>
      </LineStyle>
      <PolyStyle>
        <color>7fff0000</color>
      </PolyStyle>
      <IconStyle>
        <scale>0.6</scale>
        <Icon>
          <href>blueball.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <Style id="traj3">
      <LineStyle>
        <color>ff00ff00</color>
        <width>4</width>
      </LineStyle>
      <PolyStyle>
        <color>7f00ff00</color>
      </PolyStyle>
      <IconStyle>
        <scale>0.6</scale>
        <Icon>
          <href>greenball.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <Style id="traj3a">
      <LineStyle>
        <color>ff00ff00</color>
        <width>1.25</width>
      </LineStyle>
      <PolyStyle>
        <color>7f00ff00</color>
      </PolyStyle>
      <IconStyle>
        <scale>0.6</scale>
        <Icon>
          <href>greenball.png</href>
        </Icon>
      </IconStyle>
    </Style>\n""".format(
            self.output_suffix,
            starting_loc[0],
            starting_loc[1],
            0,
            timestamp_str,
            "relativeToSeaFloor"))

    def _write_postamble(self, f):
        f.write("""\
  </Document>
</kml>\n""")

    def _write_overlay(self, f):
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
      <screenXY x="0" y="1" xunits="fraction" yunits="fraction"/>
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

    def _write_trajectory(self, f, t, t_index):
        vc = model.VerticalCoordinateFactory.create_instance(
            VerticalCoordinate.ABOVE_GROUND_LEVEL, self.height_unit, t)
        vc.make_vertical_coordinates()
        if (t.starting_loc is None) or (len(vc.values) == 0):
            logger.info("skip writing an empty trajectory")
            return

        f.write("""\
    <Folder>
      <name>{0:.1f} {1} Trajectory</name>
      <open>1</open>
      <Placemark>
        <LookAt>
          <longitude>{2:.4f}</longitude>
          <latitude>{3:.4f}</latitude>\n""".format(
            t.starting_level,
            self._get_level_type(t),
            t.starting_loc[0],
            t.starting_loc[1]))

        timestamp_str = util.get_iso_8601_str(t.starting_datetime,
                                              self.time_zone)

        f.write("""\
          <range>2000000.0</range>
          <tilt>0.0</tilt>
          <heading>0.0</heading>
          <gx:TimeStamp>
            <when>{0}</when>
          </gx:TimeStamp>
          <gx:altitudeMode>{1}</gx:altitudeMode>
        </LookAt>\n""".format(
            timestamp_str,
            "relativeToSeaFloor"))

        f.write("""\
        <name>{0:.1f} {1} Trajectory</name>
        <styleUrl>#traj{2:1d}</styleUrl>
        <LineString>
          <extrude>1</extrude>
          <altitudeMode>{3}</altitudeMode>
          <coordinates>\n""".format(
            t.starting_level,
            self._get_level_type(t),
            (t_index % 3) + 1,
            self._get_alt_mode(t)))

        for k in range(len(t.longitudes)):
            f.write("""\
            {0:.4f},{1:.4f},{2:.1f}\n""".format(
                t.longitudes[k],
                t.latitudes[k],
                vc.values[k]))

        starttime_str = self._get_timestamp_str(t.starting_datetime,
                                                self.time_zone)

        f.write("""\
          </coordinates>
        </LineString>
      </Placemark>
      <Placemark>
        <visibility>0</visibility>
        <name></name>
        <visibility>1</visibility>
        <description><![CDATA[<pre>Start Time
{0}
LAT: {1:.4f} LON: {2:.4f} Hght({3}): {4:.1f}
</pre>]]></description>
        <styleUrl>#traj{5:1d}</styleUrl>
        <Point>
          <altitudeMode>{6}</altitudeMode>
          <coordinates>{7:.4f},{8:.4f},{9:.1f}</coordinates>
        </Point>
      </Placemark>\n""".format(
            starttime_str,
            t.starting_loc[1],
            t.starting_loc[0],
            self._get_level_type(t),
            t.starting_level,
            (t_index % 3) + 1,
            self._get_alt_mode(t),
            t.starting_loc[0],
            t.starting_loc[1],
            t.starting_level))

        if t.has_trajectory_stddevs():
            self._write_ellipses_of_uncertainty(f, t, t_index, vc)

        if self.kml_option != const.KMLOption.NO_ENDPOINTS \
                and self.kml_option != const.KMLOption.BOTH_1_AND_2:
            self._write_endpts(f, t, t_index, vc)

        f.write("""\
    </Folder>\n""")

    def _write_ellipses_of_uncertainty(self, f, t, t_index, vc):
        is_backward = False if t.parent.is_forward_calculation() else True
        npts_ellipse = 64
        delta_theta = 2*math.pi / npts_ellipse

        f.write("""\
      <Folder>
        <name>Ellipses of uncertainty for center-of-mass trajectory</name>
        <visibility>0</visibility>\n""")

        for k in range(len(t.longitudes)):
            if k == 0:
                continue

            f.write("""\
        <Placemark>
          <name>{0}</name>
          <visibility>1</visibility>
          <LookAt>
            <longitude>{1:.4f}</longitude>
            <latitude>{2:.4f}</latitude>
            <range>20000.0</range>
            <tilt>60.0</tilt>
            <heading>0.0</heading>
          </LookAt>
          <Snippet maxLines="0"/>
          <TimeSpan>\n""".format(
                self._get_timestamp_str(t.datetimes[k], self.time_zone),
                t.longitudes[k],
                t.latitudes[k]))

            # Use the entire time period so that the ellipse would be
            # initially visible with Google Earth.
            if is_backward:
                f.write("""\
            <end>{0}</end>
            <begin>{1}</begin>\n""".format(
                    util.get_iso_8601_str(t.datetimes[-1], self.time_zone),
                    util.get_iso_8601_str(t.datetimes[0], self.time_zone)))
            else:
                f.write("""\
            <begin>{0}</begin>
            <end>{1}</end>\n""".format(
                    util.get_iso_8601_str(t.datetimes[0], self.time_zone),
                    util.get_iso_8601_str(t.datetimes[-1], self.time_zone)))

            f.write("""\
          </TimeSpan>
          <description><![CDATA[<pre>HYSPLIT {0:4.0f}. hour ellipse of uncertainty

{1}
LAT: {2:9.4f} LON: {3:9.4f} Hght({4}): {5:8.1f}
</pre>]]></description>
          <styleUrl>#traj{6:1d}a</styleUrl>
          <LineString>
            <extrude>1</extrude>
            <altitudeMode>{7}</altitudeMode>
            <coordinates>\n""".format(
                t.ages[k],
                self._get_timestamp_str(t.datetimes[k], self.time_zone),
                t.latitudes[k],
                t.longitudes[k],
                self._get_level_type(t),
                vc.values[k],
                (t_index % 3) + 1,
                self._get_alt_mode(t)))

            slon, slat = t.trajectory_stddevs[k]
            for j in range(npts_ellipse + 1):
                theta = j * delta_theta if j < npts_ellipse else 0
                y = t.latitudes[k] + slat * math.sin(theta)
                x = t.longitudes[k] + slon * math.cos(theta)
                f.write("""\
              {0:.4f},{1:.4f},{2:.1f}\n""".format(
                    x,
                    y,
                    vc.values[k]))

            f.write("""\
            </coordinates>
          </LineString>
        </Placemark>\n""")

        f.write("""\
      </Folder>\n""")

    def _write_endpts(self, f, t, t_index, vc):
        is_backward = False if t.parent.is_forward_calculation() else True

        f.write("""\
      <Folder>
        <name>Trajectory Endpoints</name>
        <visibility>0</visibility>\n""")

        for k in range(len(t.longitudes)):
            if k == 0:
                continue

            f.write("""\
        <Placemark>
          <name>{0}</name>
          <visibility>1</visibility>
          <LookAt>
            <longitude>{1:.4f}</longitude>
            <latitude>{2:.4f}</latitude>
            <range>20000.0</range>
            <tilt>60.0</tilt>
            <heading>0.0</heading>
          </LookAt>
          <Snippet maxLines="0"/>
          <TimeSpan>\n""".format(
                self._get_timestamp_str(t.datetimes[k], self.time_zone),
                t.longitudes[k],
                t.latitudes[k]))

            if is_backward:
                f.write("""\
            <end>{0}</end>
            <begin>{1}</begin>\n""".format(
                    util.get_iso_8601_str(t.datetimes[k-1], self.time_zone),
                    util.get_iso_8601_str(t.datetimes[k], self.time_zone)))
            else:
                f.write("""\
            <begin>{0}</begin>
            <end>{1}</end>\n""".format(
                    util.get_iso_8601_str(t.datetimes[k-1], self.time_zone),
                    util.get_iso_8601_str(t.datetimes[k], self.time_zone)))

            f.write("""\
          </TimeSpan>
          <description><![CDATA[<pre>HYSPLIT {0:4.0f}. hour endpoint

{1}
LAT: {2:9.4f} LON: {3:9.4f} Hght({4}): {5:8.1f}
</pre>]]></description>
          <styleUrl>#traj{6:1d}</styleUrl>
          <Point>
            <altitudeMode>{7}</altitudeMode>
            <coordinates>{8:.4f},{9:.4f},{10:.1f}</coordinates>
          </Point>
        </Placemark>\n""".format(
                t.ages[k],
                self._get_timestamp_str(t.datetimes[k], self.time_zone),
                t.latitudes[k],
                t.longitudes[k],
                self._get_level_type(t),
                vc.values[k],
                (t_index % 3) + 1,
                self._get_alt_mode(t),
                t.longitudes[k],
                t.latitudes[k],
                vc.values[k]))

        f.write("""\
      </Folder>\n""")


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
        file_name = self.make_filename(self.output_name,
                                       self.output_suffix,
                                       file_no)

        logger.info("Creating file %s", file_name)
        with open(file_name, "wt") as f:
            for t_idx, t in enumerate(plot_data.trajectories):
                self._write_trajectory(f, t, t_idx)
