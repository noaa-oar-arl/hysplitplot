#!/usr/bin/env python3

# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# setup.py
#
# For installation of this package.
#
# usage: python setup.py install
# ---------------------------------------------------------------------------

from setuptools import setup
from hysplitplot import meta

setup(
    name="hysplitplot",
    version=meta.__version__,
    description="HYSPLIT Graphics",
    author=meta.__author__,
    author_email=meta.__email__,
    packages=["hysplitplot", "hysplitplot.traj", "hysplitplot.conc",
              "hysplitplot.toa", "hysplitplot.grid"],
    python_requires=">=3.10",  # contextily 1.7.1 needs 3.10 or later
    install_requires=[
        "hysplitdata==0.3.*",  # omit the patch level
        "geopandas==0.14.4",
        "cartopy==0.23.0",
        "numpy==2.0.2",
        "pytz==2025.2",
        "timezonefinder==6.5.9",
        "contextily==1.7.1"]
)
