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

setup(
    name="hysplitplot",
    version="0.1.1",
    description="HYSPLIT Graphics",
    author="Sonny Zinn",
    author_email="sonny.zinn@noaa.gov",
    packages=["hysplitplot", "hysplitplot.traj", "hysplitplot.conc",
              "hysplitplot.toa"],
    python_requires="==3.7",
    install_requires=["hysplitdata==0.0.1", "geopandas==0.4.1", "cartopy==0.17.0",
                      "numpy==1.16.3", "pytz==2019.1", "timezonefinder==4.1.0",
                      "contextily==0.99.0", "mercantile==1.1.1"]
)
