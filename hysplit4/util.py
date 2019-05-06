import sys


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