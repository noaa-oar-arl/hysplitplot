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

class Color: # TODO: rename this to TrajectoryPlotColor
    BLACK_AND_WHITE = 0
    COLOR = 1
    ITEMIZED = 2

class ConcentrationPlotColor: # KOLOR
    BLACK_AND_WHITE = 0
    COLOR = 1
    VAL_2 = 2
    VAL_3 = 3
    
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
    METERS = 0
    FEET = 1
    
class ContourLevelGenerator:
    EXPONENTIAL_DYNAMIC = 0
    EXPONENTIAL_FIXED = 1
    LINEAR_DYNAMIC = 2
    LINEAR_FIXED = 3
    USER_SPECIFIED = 4
    CLG_50 = 50 # TODO: what is this called?
    CLG_51 = 51 # TODO: what is this called?
    
    MAX_LEVELS = 32

class ExposureUnit:
    CONCENTRATION = 0
    EXPOSURE = 1
    CHEMICAL_THRESHOLDS = 2
    VOLCANIC_ASH = 3
    MASS_LOADING = 4

class ConcentrationType: # KAVG
    EACH_LEVEL = 1
    VERTICAL_AVERAGE = 2
    
class DepositionSum: # NDEP
    NONE = 0
    TIME = 1
    SUM = 2
    TOTAL = 3

class ConcentrationMapType: # KMAP
    CONCENTRATION = 1
    EXPOSURE = 2
    DEPOSITION = 3          # NOT USED
    THRESHOLD_LEVELS = 4
    VOLCANIC_ERUPTION = 5
    DEPOSITION_6 = 6        # TODO: spell it out
    MASS_LOADING = 7

class SmoothingKernel:
    SIMPLE = 0

