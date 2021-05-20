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
    install_requires=[
        "hysplitdata==0.0.*",  # omit the patch level
        "geopandas==0.8.1",
        "cartopy==0.17.0",
        "numpy==1.20.1",
        "pytz==2021.1",
        "timezonefinder==5.2.0",
        "contextily==1.1.0",
        "mercantile==1.2.1"]
)
