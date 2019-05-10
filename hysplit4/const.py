# declares constants

class GISOutput:
    NONE = 0
    GENERATE_POINTS = 1
    KML = 3
    PARTIAL_KML = 4
    GENERATE_LINES = 5

class KMLOption:
    NONE = 0
    NO_EXTRA_OVERLAYS = 1
    NO_ENDPOINTS = 2
    BOTH_1_AND_2 = 3

class Frames:
    ALL_FILES_ON_ONE = 0
    ONE_PER_FILE = 1

class Color:
    BLACK_AND_WHITE = 0
    COLOR = 1
    ITEMIZED = 2

class LatLonLabel:
    NONE = 0
    AUTO = 1
    SET = 2

class MapProjection:
    AUTO = 0
    POLAR = 1
    LAMBERT = 2
    MERCATOR = 3
    CYL_EQU = 4

class Vertical:
    NOT_SET = -1
    PRESSURE = 0
    ABOVE_GROUND_LEVEL = 1
    THETA = 2
    METEO = 3
    NONE = 4

class ZoomFactor:
    LEAST_ZOOM = 0
    MOST_ZOOM = 100

class HeightUnit:
    METER = 0
    FEET = 1
