import logging
import math
import numpy
from matplotlib.path import Path
from abc import ABC, abstractmethod
from hysplit4 import const, util
from hysplit4.conc import model


logger = logging.getLogger(__name__)


class GISFileWriterFactory:
    
    @staticmethod
    def create_instance(selector, kml_option):
        if selector == const.GISOutput.GENERATE_POINTS:
            return PointsGenerateFileWriter(PointsGenerateFileWriter.DecimalFormWriter())
        elif selector == const.GISOutput.GENERATE_POINTS_2:
            return PointsGenerateFileWriter(PointsGenerateFileWriter.ExponentFormWriter())
        elif selector == const.GISOutput.KML:
            return KMLWriter(kml_option)
        elif selector == const.GISOutput.PARTIAL_KML:
            return PartialKMLWriter(kml_option)
        elif selector != const.GISOutput.NONE:
            logger.warning("Unknown GIS file writer type %d", selector)
        return IdleWriter()
    

class AbstractWriter:
        
    def __init__(self):
        self.gis_alt_mode = const.GISOutputAltitude.CLAMPED_TO_GROUND
        self.KMLOUT = 0
        self.output_basename = "output"
        self.output_suffix = "ps"
        self.conc_type = None   # instance of ConcentrationType
        self.depo_type = None   # instance created by DepositFactory
        self.KMAP = const.ConcentrationMapType.CONCENTRATION
    
    def initialize(self, gis_alt_mode, KMLOUT, output_basename, output_suffix, conc_type, conc_map, depo_type, KMAP, NSSLBL, MAXCON, cntr_labels):
        self.gis_alt_mode       = gis_alt_mode
        self.KMLOUT             = KMLOUT
        self.output_basename    = "HYSPLIT" if KMLOUT == 0 else output_basename
        self.output_suffix      = output_suffix
        self.conc_type          = conc_type
        self.conc_map           = conc_map
        self.depo_type          = depo_type
        self.KMAP               = KMAP
        self.NSSLBL             = NSSLBL
        self.MAXCON             = MAXCON
        self.contour_labels     = cntr_labels
    
    def write(self, g, level_lower, level_cur, level_high, contour_set, min_conc, max_conc, conc_unit, raw_colors):
        pass
    
    def finalize(self):
        pass
    
    def _reformat_color(self, clr):
        r = clr[1:3]; g = clr[3:5]; b = clr[5:7]
        return "C8{}{}{}".format(b, g, r).upper()
     
    @staticmethod
    def _get_iso_8601_str(dt):
        year = util.restore_year(dt.year)
        return "{0:04d}-{1:02d}-{2:02d}T{3:02d}:{4:02d}:{5:02d}Z".format(
            year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
           
    
class IdleWriter(AbstractWriter):
    
    def __init__(self):
        AbstractWriter.__init__(self)


class PointsGenerateFileWriter(AbstractWriter):
    
    def __init__(self, formatter):
        AbstractWriter.__init__(self)
        self.formatter = formatter
    
    def write(self, g, level_lower, level_cur, level_upper, contour_set, min_conc, max_conc, conc_unit, raw_colors):
        basename = self.depo_type.make_gis_basename(g.time_index + 1, self.output_suffix)
        if basename is None:
            basename = self.conc_type.make_gis_basename(g.time_index + 1, self.output_suffix, level_cur, level_upper)
            
        with open(basename + ".txt", "wt") as f:
            for k, contour in enumerate(contour_set.allsegs):
                for seg in contour:
                    self.formatter.write_seg(f, seg, contour_set.levels[k])
            f.write("END\n")
            
        with open(basename + ".att", "wt") as f:
            f.write("#CONC,NAME,DATE,TIME,LLEVEL,HLEVEL,COLOR\n")
            for k, contour in enumerate(contour_set.allsegs):
                for seg in contour:
                    clr = self._reformat_color(contour_set.colors[k])
                    self.formatter.write_att(f, g, level_lower, level_upper, contour_set.levels[k], clr)


    class DecimalFormWriter:
        
        def write_seg(self, f, seg, contour_level):
            pts = seg[0]
            f.write("{0:10.5f}, {1:10.5f}, {2:10.5f}\n".format(math.log10(contour_level), pts[0], pts[1]))
            for pts in seg[1:]:
                f.write("{0:10.5f}, {1:10.5f}\n".format(pts[0], pts[1]))
            f.write("END\n")
            
        def write_att(self, f, grid, level1, level2, contour_level, color):
            f.write("{:7.3f},{:4s},{:4d}{:02d}{:02d},{:04d},{:05d},{:05d},{:8s}\n".format(
                math.log10(contour_level),
                grid.pollutant,
                util.restore_year(grid.ending_datetime.year),
                grid.ending_datetime.month,
                grid.ending_datetime.day,
                grid.ending_datetime.hour * 100,
                int(level1),
                int(level2),
                color));
            
    class ExponentFormWriter:
        
        def write_seg(self, f, seg, contour_level):
            pts = seg[0]
            f.write("{0:10.3e}, {1:10.5f}, {2:10.5f}\n".format(contour_level, pts[0], pts[1]))
            for pts in seg[1:]:
                f.write("{0:10.5f}, {1:10.5f}\n".format(pts[0], pts[1]))
            f.write("END\n")
        
        def write_att(self, f, grid, level1, level2, contour_level, color):
            f.write("{:10.3e},{:4s},{:4d}{:02d}{:02d},{:04d},{:05d},{:05d},{:8s}\n".format(
                contour_level,
                grid.pollutant,
                util.restore_year(grid.ending_datetime.year),
                grid.ending_datetime.month,
                grid.ending_datetime.day,
                grid.ending_datetime.hour * 100,
                int(level1),
                int(level2),
                color));
                
                
class KMLWriter(AbstractWriter):
    
    def __init__(self, kml_option):
        AbstractWriter.__init__(self)
        self.kml_option = kml_option    # IKML
        self.kml_file = None
        self.att_file = None
        self.cntr_writer = None
 
    def initialize(self, gis_alt_mode, KMLOUT, output_basename, output_suffix, conc_type, conc_map, depo_type, KMAP, NSSLBL, MAXCON, cntr_labels):
        AbstractWriter.initialize(self, gis_alt_mode, KMLOUT, output_basename, output_suffix, conc_type, conc_map, depo_type, KMAP, NSSLBL, MAXCON, cntr_labels)
        self.cntr_writer = KMLContourWriterFactory.create_instance(self.KMAP, conc_map, gis_alt_mode)

    def write(self, g, level_lower, level_cur, level_upper, contour_set, min_conc, max_conc, conc_unit, raw_colors):
        if self.kml_file is None:
            filename = "{}_{}.kml".format(self.output_basename, self.output_suffix)
            self.kml_file = open(filename, "wt")
            
            self._write_preamble(self.kml_file, g)
            
            if contour_set is not None:
                self._write_colors(self.kml_file, contour_set.colors)
                
            self._write_source_locs(self.kml_file, g)
            
            if self.kml_option != const.KMLOption.NO_EXTRA_OVERLAYS and self.kml_option != const.KMLOption.BOTH_1_AND_2:
                self._write_overlays(self.kml_file)
        
        self.cntr_writer.write(self.kml_file, g, contour_set, level_lower, level_upper, self.output_suffix, max_conc, conc_unit, self.contour_labels)

        if self.att_file is None:
            filename = "GELABEL_{}.txt".format(self.output_suffix)
            self.att_file = open(filename, "wt")
        
        self._write_attributes(self.att_file, g, min_conc, max_conc, conc_unit, contour_set.levels, raw_colors)

    def finalize(self):
        AbstractWriter.finalize(self)
        
        if self.kml_file is not None:
            self._write_postamble(self.kml_file)
            self.kml_file.close()
        
        if self.att_file is not None:
            self.att_file.close()
    
    @staticmethod
    def _get_att_datetime_str(dt):
        year = util.restore_year(dt.year)
        return "{} {:04d}&".format(dt.strftime("%H%M UTC %b %d"), year)
    
    def _write_attributes(self, f, g, min_conc, max_conc, conc_unit, contour_levels, raw_colors):
        f.write("{}\n".format(self.KMAP))
        f.write("{}&\n".format(conc_unit))
        
        starting_time = g.parent.release_datetime[0] if self.NSSLBL == 1 else g.starting_datetime
        f.write("Integrated: {}\n".format(self._get_att_datetime_str(starting_time)))
        f.write("        to: {}\n".format(self._get_att_datetime_str(g.ending_datetime)))
        
        if self.MAXCON == 1 or self.MAXCON == 2:
            f.write("{} {} {}\n".format(self.conc_map.format_conc(max_conc),
                                        self.conc_map.format_conc(min_conc),
                                        len(contour_levels)))
        else:
            f.write("NOMAXNM NOMAXNM {}\n".format(len(levels)))
        
        for level in contour_levels:
            f.write("{} ".format(self.conc_map.format_conc(level)))
        f.write("\n")
        
        for c in raw_colors:
            f.write("{:.2f} ".format(c[0]))
        f.write("\n")
        
        for c in raw_colors:
            f.write("{:.2f} ".format(c[1]))
        f.write("\n")
        
        for c in raw_colors:
            f.write("{:.2f} ".format(c[2]))
        f.write("\n")
        
        for label in self.contour_labels:
            f.write("{} ".format(label))
        
        f.write("\n")
        
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
                          self._get_iso_8601_str(g.starting_datetime)))
    
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
      </Placemark>\n""".format("relativeToGround" if self.gis_alt_mode == const.GISOutputAltitude.RELATIVE_TO_GROUND else "clampedToGround",
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
    
    def __init__(self, kml_option):
        KMLWriter.__init__(self, kml_option)

    def write(self, g, level_lower, level_cur, level_upper, contour_set, min_conc, max_conc, conc_unit, raw_colors):
        if self.kml_file is None:
            filename = "{}_{}.txt".format(self.output_basename, self.output_suffix)
            self.kml_file = open(filename, "wt")
            
        self.cntr_writer.write(self.kml_file, g, contour_set, level_lower, level_upper, self.output_suffix, max_conc, conc_unit, self.contour_labels)

        if self.att_file is None:
            filename = "GELABEL_{}.txt".format(self.output_suffix)
            self.att_file = open(filename, "wt")

        self._write_attributes(self.att_file, g, min_conc, max_conc, conc_unit, contour_set.levels, raw_colors)

    def _write_attributes(self, f, g, min_conc, max_conc, conc_unit, contour_levels, raw_colors):
        # do nothing
        pass


class KMLContourWriterFactory:
    
    @staticmethod
    def create_instance(KMAP, conc_map, gis_alt_mode):
        if KMAP == const.ConcentrationMapType.CONCENTRATION:
            return KMLConcentrationWriter(conc_map, gis_alt_mode)
        elif KMAP == const.ConcentrationMapType.EXPOSURE:
            return KMLConcentrationWriter(conc_map, gis_alt_mode)
        elif KMAP == const.ConcentrationMapType.DEPOSITION:
            return KMLDepositionWriter(conc_map, gis_alt_mode)
        elif KMAP == const.ConcentrationMapType.THRESHOLD_LEVELS:
            return KMLChemicalThresholdWriter(conc_map, gis_alt_mode)
        elif KMAP == const.ConcentrationMapType.VOLCANIC_ERUPTION:
            return KMLDepositionWriter(conc_map, gis_alt_mode)
        elif KMAP == const.ConcentrationMapType.DEPOSITION_6:
            return KMLDepositionWriter(conc_map, gis_alt_mode)
        elif KMAP == const.ConcentrationMapType.MASS_LOADING:
            return KMLMassLoadingWriter(conc_map, gis_alt_mode)


class AbstractKMLContourWriter(ABC):
    
    def __init__(self, conc_map, gis_alt_mode):
        self.frame_count = 0
        self.conc_map = conc_map
        self.gis_alt_mode = gis_alt_mode
    
    def write(self, f, g, contour_set, level1, level2, suffix, max_conc, conc_unit, contour_labels):
        self.frame_count += 1
    
    def _get_contour_height_at(self, k, level2):
        return int(level2) + (200 * k)
    
    def _write_contour(self, f, g, contour_set, conc_unit, level2, contour_labels):
        if contour_set is None:
            return
        
        if g.ending_datetime < g.starting_datetime:
            begin_ts = AbstractWriter._get_iso_8601_str(g.ending_datetime)
            end_ts = AbstractWriter._get_iso_8601_str(g.starting_datetime)
        else:
            begin_ts = AbstractWriter._get_iso_8601_str(g.starting_datetime)
            end_ts = AbstractWriter._get_iso_8601_str(g.ending_datetime)
            
        for k, contour in enumerate(contour_set.allsegs):
            # arbitrary height above ground in order of increasing concentration
            # TODO: method?
            level = self._get_contour_height_at(k, level2)
                        
            f.write("""\
      <Placemark>\n""")
            
            self._write_placemark_visibility(f)
            
            if len(contour_labels[k]) > 0:
                f.write("""
        <name LOC="{}">Contour Level: {} {}</name>\n""".format(contour_labels[k],
                                                               self.conc_map.format_conc(contour_set.levels[k]),
                                                               conc_unit))
            else:
                f.write("""
        <name>Contour Level: {} {}</name>\n""".format(self.conc_map.format_conc(contour_set.levels[k]),
                                                      conc_unit))
            
            self._write_placemark_visibility(f)
            
            f.write("""\
        <Snippet maxLines="0"></Snippet>
        <TimeSpan>
          <begin>{}</begin>
          <end>{}</end>
        </TimeSpan>
        <styleUrl>#conc{}</styleUrl>
        <MultiGeometry>\n""".format(begin_ts, end_ts,
                                    k + 1))
            
            path_code_set = contour_set.allkinds[k]
            for j, seg in enumerate(contour):
                path_codes = path_code_set[j]
                self._write_seg(f, g, seg, path_codes, level)
            
            f.write("""\
        </MultiGeometry>
      </Placemark>\n""")
    
    def _write_seg(self, f, g, seg, path_codes, level):
        # Each segment may contain more than one polygon. Need to separate them.
        paths = self._separate_paths(seg, path_codes, Path.MOVETO)
        
        if len(paths) > 0:
            f.write("""\
          <Polygon>
            <extrude>1</extrude>
            <altitudeMode>{}</altitudeMode>\n""".format(
                "relativeToGround" if self.gis_alt_mode == const.GISOutputAltitude.RELATIVE_TO_GROUND else "clampedToGround"))
        
            for path in paths:
                self._write_boundary(f, g, path, level)
                
            f.write("""\
          </Polygon>\n""")  
    
    @staticmethod
    def _separate_paths(seg, path_codes, separator_code):
        head = numpy.where(path_codes == separator_code)[0]
        
        tail = [k for k in head]
        tail.append(len(path_codes))
        tail.pop(0)
        
        paths = []
        for h, t in zip(head, tail):
            paths.append(seg[h:t])
            
        return paths
        
    def _write_boundary(self, f, g, bndry, level):
        lons, lats = numpy.transpose(bndry)
        
        # if cross the date line, change negative longitudes to positive
        if self._crossing_date_line(lons):
            lons = [v + 360.0 for v in lons]
        
        # compute the area of polygon to see if it is inner (area < 0, clockwise) or outer.
        area = self._compute_polygon_area(lons, lats)
        
        if area < 0:
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
            f.write("{:.5f},{:.5f},{:05d}\n".format(lons[k], lats[k], level))
            
        if lons[-1] != lons[0] or lats[-1] != lats[0]:
            f.write("{:.5f},{:.5f},{:05d}\n".format(lons[0], lats[0], level))
        
        if area < 0:
            f.write("""\
                </coordinates>
              </LinearRing>
            </innerBoundaryIs>\n""")
        else:
            f.write("""\
                </coordinates>
              </LinearRing>
            </outerBoundaryIs>\n""")
        
    @staticmethod
    def _crossing_date_line(lons):
        for k in range(1, len(lons)):
            if lons[k] < -180.0 and lons[k-1] > 0:
                return True
            
        return False
    
    @staticmethod
    def _compute_polygon_area(lons, lats):
        area = 0.0
        
        n = len(lons)
        if n == len(lats) and n > 0:
            area = (lons[0] + lons[-1]) * (lats[0] - lats[-1])
            for k in range(1, n):
                area += (lons[k] + lons[k-1]) * (lats[k] - lats[k-1])
            
            if lons[-1] != lons[0] or lats[-1] != lats[0]:
                area += (lons[0] + lons[-1]) * (lats[0] - lats[-1])
                
        return 0.5 * area

    @abstractmethod
    def _get_max_location_text(self):
        pass
    
    def _write_max_location(self, f, g, max_conc, level2, contour_label):
        dx = g.parent.grid_deltas[0]
        dy = g.parent.grid_deltas[1]
        hx = 0.5 * dx
        hy = 0.5 * dy
        
        loc = g.extension.max_locs[0]
        level2 = int(level2)
        
        if g.ending_datetime < g.starting_datetime:
            begin_ts = AbstractWriter._get_iso_8601_str(g.ending_datetime)
            end_ts = AbstractWriter._get_iso_8601_str(g.starting_datetime)
        else:
            begin_ts = AbstractWriter._get_iso_8601_str(g.starting_datetime)
            end_ts = AbstractWriter._get_iso_8601_str(g.ending_datetime)
        
        f.write("""\
      <Placemark>\n""")
        
        if len(contour_label) > 0:
            f.write("""\
        <name LOC="{}">Maximum Value Grid Cell</name>\n""".format(contour_label))
        else:
            f.write("""\
        <name>Maximum Value Grid Cell</name>\n""")            
        
        f.write("""\
        <description><![CDATA[<pre>
LAT: {:.4f} LON: {:.4f}
Value: {:.1g}
{}</pre>]]></description>\n""".format(loc[1], loc[0],
                                      max_conc,
                                      self._get_max_location_text(),))
        
        self._write_placemark_visibility(f)
        
        f.write("""\
        <Snippet maxLines="0"></Snippet>
        <TimeSpan>
          <begin>{}</begin>
          <end>{}</end>
        </TimeSpan>
        <styleUrl>#maxv</styleUrl>
        <visibility>0</visibility>
        <Polygon>
          <extrude>1</extrude>
          <altitudeMode>{}</altitudeMode>
          <outerBoundaryIs>
            <LinearRing>
              <coordinates>\n""".format(

                  begin_ts, end_ts,
                  "relativeToGround" if self.gis_alt_mode == const.GISOutputAltitude.RELATIVE_TO_GROUND else "clampedToGround"))

        for loc in g.extension.max_locs:
            f.write("{:.5f},{:.5f},{:05d}\n".format(loc[0]-hx, loc[1]-hy, level2))
            f.write("{:.5f},{:.5f},{:05d}\n".format(loc[0]+hx, loc[1]-hy, level2))
            f.write("{:.5f},{:.5f},{:05d}\n".format(loc[0]+hx, loc[1]+hy, level2))
            f.write("{:.5f},{:.5f},{:05d}\n".format(loc[0]-hx, loc[1]+hy, level2))
            f.write("{:.5f},{:.5f},{:05d}\n".format(loc[0]-hx, loc[1]-hy, level2))
        
        f.write("""\
              </coordinates>
            </LinearRing>
          </outerBoundaryIs>
        </Polygon>
      </Placemark>\n""")
            
    @staticmethod
    def _get_timestamp_str(dt):
        year = util.restore_year(dt.year)
        return "{:04d}{:02d}{:02d} {:02d}{:02d} UTC".format(
            year, dt.month, dt.day, dt.hour, dt.minute)

    def _write_placemark_visibility(self, f):
        pass
    
    
class KMLConcentrationWriter(AbstractKMLContourWriter):
    
    def __init__(self, conc_map, gis_alt_mode):
        AbstractKMLContourWriter.__init__(self, conc_map, gis_alt_mode)
    
    def write(self, f, g, contour_set, level1, level2, suffix, max_conc, conc_unit, contour_labels):
        super(KMLConcentrationWriter, self).write(f, g, contour_set, level1, level2, suffix, max_conc, conc_unit, contour_labels)
        
        if g.ending_datetime < g.starting_datetime:
            begin_ts = AbstractWriter._get_iso_8601_str(g.ending_datetime)
            end_ts = AbstractWriter._get_iso_8601_str(g.starting_datetime)
        else:
            begin_ts = AbstractWriter._get_iso_8601_str(g.starting_datetime)
            end_ts = AbstractWriter._get_iso_8601_str(g.ending_datetime)
            
        f.write("""\
    <Folder>
      <name><![CDATA[<pre>Concentration
(Valid:{})</pre>]]></name>\n""".format(self._get_timestamp_str(g.ending_datetime)))
        
        if contour_set is not None:
            if self.frame_count == 1:
                f.write("""\
      <visibility>1</visibility>
      <open>1</open>\n""")
            else:
                f.write("""\
      <visibility>0</visibility>\n""")
       
        f.write("""\
      <description><![CDATA[<pre>
Averaged from {} to {} m
Valid:{}</pre>]]></description>
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
      </ScreenOverlay>\n""".format(int(level1), int(level2),
                          self._get_timestamp_str(g.ending_datetime),
                          begin_ts, end_ts,
                          self.frame_count, suffix))
        
        self._write_contour(f, g, contour_set, conc_unit, level2, contour_labels)

        self._write_max_location(f, g, max_conc, level2, contour_labels[-1])
        
        f.write("""\
    </Folder>\n""")
    
    def _get_max_location_text(self):
        return """\
      The square represents the location
      of maximum concentration and the
      size of the square represents the
      concentration grid cell size."""

        
class KMLChemicalThresholdWriter(KMLConcentrationWriter):
    
    def __init__(self, conc_map, gis_alt_mode):
        KMLConcentrationWriter.__init__(self, conc_map, gis_alt_mode)

    def _get_contour_height_at(self, k, level2):
        return int(level2) if k == 1 else int(level2) + (200 * k)
            
    def write(self, f, g, contour_set, level1, level2, suffix, max_conc, conc_unit, contour_labels):
        super(KMLChemicalThresholdWriter, self).write(f, g, contour_set, level1, level2, suffix, max_conc, conc_unit, contour_labels)        


class KMLDepositionWriter(AbstractKMLContourWriter):
    
    def __init__(self, conc_map, gis_alt_mode):
        AbstractKMLContourWriter.__init__(self, conc_map, gis_alt_mode)
        
    def write(self, f, g, contour_set, level1, level2, suffix, max_conc, conc_unit, contour_labels):
        super(KMLDepositionWriter, self).write(f, g, contour_set, level1, level2, suffix, max_conc, conc_unit, contour_labels)
        
        if g.ending_datetime < g.starting_datetime:
            begin_ts = AbstractWriter._get_iso_8601_str(g.ending_datetime)
            end_ts = AbstractWriter._get_iso_8601_str(g.starting_datetime)
        else:
            begin_ts = AbstractWriter._get_iso_8601_str(g.starting_datetime)
            end_ts = AbstractWriter._get_iso_8601_str(g.ending_datetime)
            
        f.write("""\
    <Folder>
      <name><![CDATA[<pre>Deposition
(Valid:{})</pre>]]></name>\n""".format(self._get_timestamp_str(g.ending_datetime)))
        
        if contour_set is not None:
            if self.frame_count == 1:
                f.write("""\
      <visibility>1</visibility>
      <open>1</open>\n""")
            else:
                f.write("""\
      <visibility>0</visibility>\n""")
       
        f.write("""\
      <description><![CDATA[<pre>
Valid:{}</pre>]]></description>
      <ScreenOverlay>
        <name>Legend</name>\n""".format(self._get_timestamp_str(g.ending_datetime)))
        
        if self.frame_count > 1:
            f.write("""\
        <visibility>0</visibility>\n""")
            
        f.write("""\
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
      </ScreenOverlay>\n""".format(begin_ts, end_ts,
                                   self.frame_count, suffix))
        
        self._write_contour(f, g, contour_set, conc_unit, max_conc, level2)

        self._write_max_location(f, g, max_conc, level2, contour_labels[-1])

        f.write("""\
    </Folder>\n""")               

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
        \n""");

      
class KMLMassLoadingWriter(AbstractKMLContourWriter):
    
    def __init__(self, conc_map, gis_alt_mode):
        AbstractKMLContourWriter.__init__(self, conc_map, gis_alt_mode)
        
    def write(self, f, g, contour_set, level1, level2, suffix, max_conc, conc_unit, contour_labels):
        super(KMLMassLoadingWriter, self).write(f, g, contour_set, level1, level2, suffix, max_conc, conc_unit, contour_labels)
        
        if g.ending_datetime < g.starting_datetime:
            begin_ts = AbstractWriter._get_iso_8601_str(g.ending_datetime)
            end_ts = AbstractWriter._get_iso_8601_str(g.starting_datetime)
        else:
            begin_ts = AbstractWriter._get_iso_8601_str(g.starting_datetime)
            end_ts = AbstractWriter._get_iso_8601_str(g.ending_datetime)
            
        f.write("""\
    <Folder>
      <name><![CDATA[<pre>Mass_loading
(Valid:{})</pre>]]></name>\n""".format(self._get_timestamp_str(g.ending_datetime)))
        
        if contour_set is not None:
            if self.frame_count == 1:
                f.write("""\
      <visibility>1</visibility>
      <open>1</open>\n""")
            else:
                f.write("""\
      <visibility>0</visibility>\n""")
       
        f.write("""\
      <description><![CDATA[<pre>
From {} to {} m
Valid:{}</pre>]]></description>
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
      </ScreenOverlay>\n""".format(int(level1), int(level2),
                                   self._get_timestamp_str(g.ending_datetime),
                                   begin_ts, end_ts,
                                   self.frame_count, suffix))
        
        self._write_contour(f, g, contour_set, max_conc, conc_unit, level2)

        self._write_max_location(f, g, max_conc, level2, contour_labels[-1])

        f.write("""\
    </Folder>\n""")
        
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
        \n""");


