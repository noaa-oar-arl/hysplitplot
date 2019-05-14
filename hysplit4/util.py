import logging
import sys
import os


logger = logging.getLogger(__name__)


def run(mainFunction, programName):
    """Provides a common main entry point.

    Initializes a logger, prints banner, calls the main function, and exits
    with a code returned by the main function.

    :param mainFunction: main function to be executed. It should return an integer.
    :param programName: program name.
    """
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s"
    )

    logging.info("This is {0}.".format(programName))

    exitCode = mainFunction()
    logging.info("exiting with code [{0}]".format(exitCode))

    sys.exit(exitCode)


def myzip(xlist, ylist):
    if sys.version_info[0] >= 3:
        # Python 3 or later
        return list(zip(xlist, ylist))
    else:
        # Python 1 and 2
        return zip(xlist, ylist)

def convert_integer_to_boolean(val):
    # limit the integer value to 0 or 1 for historical reasons.
    return False if max(0, min(1, int(val))) == 0 else True

def sign(a, b):
    return abs(a) if b >= 0 else -abs(a)

def nearest_int(a):
    return int(round(a))

def make_color(r, g, b):
    ir = nearest_int(r*255)
    ig = nearest_int(g*255)
    ib = nearest_int(b*255)
    return "#{:02x}{:02x}{:02x}".format(ir, ig, ib)

def make_int_if_same(a):
    ia = int(a)
    return ia if float(ia) == a else a

def is_valid_lonlat(ll):
    lon, lat = ll
    return False if lon == 99.0 and lat == 99.0 else True

def union_ranges(a, b):
    if a == None or len(a) == 0:
        return b
    elif b == None or len(b) == 0:
        return a
    else:
        amin = min(a[0], b[0])
        amax = max(a[1], b[1])
        return [amin, amax]

def make_file_list(input_endpoints):
    files = []

    if input_endpoints[0:1] == "+":
        list_file = input_endpoints[1:]
        if os.path.exists(list_file):
            with open(input_endpoints[1:], "r") as f:
                try:
                    for line in f:
                        files.append(line.rstrip())
                    f.close()
                except:
                    raise Exception("FATAL ERROR - Cannot read file: {0}".format(list_file))
        else:
            raise Exception("FATAL ERROR - File not found: {0}".format(list_file))
    elif input_endpoints.count("+"):
        files = input_endpoints.split("+")
    else:
        files.append(input_endpoints)

    return files

def restore_year(yr):
    return 2000 + yr if (yr < 40) else 1900 + yr
