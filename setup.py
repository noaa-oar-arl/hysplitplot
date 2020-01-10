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

meta = {}
with open("hysplitplot/meta.py") as f:
    exec(f.read(), meta)
    
setup(
    name="hysplitplot",
    version=meta["__version__"],
    description="HYSPLIT Graphics",
    author=meta["__author__"],
    author_email=meta["__email__"],
    packages=["hysplitplot", "hysplitplot.traj", "hysplitplot.conc",
              "hysplitplot.toa"],
    python_requires="==3.7",
    install_requires=["hysplitdata==0.0.3", "geopandas==0.4.1", "cartopy==0.17.0",
                      "numpy==1.16.3", "pytz==2019.1", "timezonefinder==4.1.0",
                      "contextily==0.99.0", "mercantile==1.1.1"]
)
